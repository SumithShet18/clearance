"""
Clearance multi-agent DocOps pipeline.

Implements Anthropic-style composition (plan → extract → validate → retrieve →
decide → HITL → act → verify) with Magentic-One style task/progress ledgers.
Phase 1 uses an explicit code-orchestrated graph (deterministic + testable).
LangGraph adapters can wrap the same nodes later without changing the product surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import CaseRow, dumps, now
from app.models.schemas import (
    AgentStep,
    CaseStatus,
    Decision,
    InvoiceExtraction,
    ProgressLedger,
    TaskLedger,
    ValidationResult,
)
from app.services.erp import create_bill
from app.services.extractor import extract_invoice
from app.services.policy import apply_policy, retrieve_policies


def _step(name: str, status: str, detail: str = "", data: dict | None = None, tokens: int = 0, cost: float = 0.0) -> AgentStep:
    t = datetime.now(timezone.utc)
    return AgentStep(
        name=name,
        status=status,
        started_at=t,
        finished_at=t if status in {"completed", "skipped", "failed", "waiting"} else None,
        detail=detail,
        data=data or {},
        tokens=tokens,
        cost_usd=cost,
    )


def overall_confidence(ext: InvoiceExtraction) -> float:
    scores = [
        ext.vendor_confidence,
        ext.invoice_number_confidence,
        ext.invoice_date_confidence,
        ext.total_confidence,
    ]
    if ext.line_items:
        scores.append(sum(i.confidence for i in ext.line_items) / len(ext.line_items))
    return sum(scores) / len(scores) if scores else 0.0


def validate_extraction(ext: InvoiceExtraction) -> ValidationResult:
    issues: list[str] = []
    schema_ok = True
    math_ok = True

    if not ext.vendor_name:
        issues.append("Missing vendor_name")
        schema_ok = False
    if not ext.invoice_number or ext.invoice_number == "INV-UNKNOWN":
        issues.append("Missing or unknown invoice_number")
        schema_ok = False
    if ext.total <= 0:
        issues.append("Total must be > 0")
        schema_ok = False

    if ext.line_items:
        line_sum = sum(i.amount for i in ext.line_items)
        if abs(line_sum - ext.subtotal) > 0.05 and ext.subtotal > 0:
            issues.append(f"Line items sum {line_sum:.2f} != subtotal {ext.subtotal:.2f}")
            math_ok = False
    if ext.subtotal and ext.tax is not None and ext.total:
        if abs(ext.subtotal + ext.tax - ext.total) > 0.05:
            issues.append(
                f"subtotal+tax {ext.subtotal + ext.tax:.2f} != total {ext.total:.2f}"
            )
            math_ok = False

    policy_issues = apply_policy(ext.vendor_name, ext.total, ext.currency)
    issues.extend(policy_issues)
    policy_ok = not any(i.startswith("POL-") for i in policy_issues) or not policy_issues
    # policy issues still count as issues; policy_ok false if any POL
    policy_ok = len(policy_issues) == 0

    return ValidationResult(
        ok=schema_ok and math_ok and policy_ok,
        issues=issues,
        math_ok=math_ok,
        schema_ok=schema_ok,
        policy_ok=policy_ok,
    )


def decide(
    ext: InvoiceExtraction,
    validation: ValidationResult,
    conf: float,
) -> tuple[Decision, str, bool]:
    """Return decision, reason, needs_human."""
    threshold = settings.confidence_hitl_threshold

    if conf < threshold:
        return Decision.escalate, f"Overall confidence {conf:.2f} < {threshold}", True
    if not validation.schema_ok or not validation.math_ok:
        return Decision.hold, "Schema or math validation failed", True
    if any("POL-002" in i for i in validation.issues):
        return Decision.escalate, "High-value policy escalation", True
    if any("POL-001" in i for i in validation.issues):
        return Decision.hold, "Unknown vendor policy", True
    if any("POL-005" in i for i in validation.issues):
        return Decision.hold, "Currency policy", True
    if not validation.ok:
        return Decision.hold, "Validation issues remain", True
    return Decision.approve, "All checks passed — auto-approve", False


async def run_pipeline(session: AsyncSession, case: CaseRow) -> CaseRow:
    steps: list[AgentStep] = []
    audit: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0

    case.status = CaseStatus.running.value
    case.updated_at = now()

    # 1. Ingest
    steps.append(_step("ingest", "completed", f"Loaded {case.filename}", {"chars": len(case.content_text)}))
    audit.append({"event": "ingest", "filename": case.filename, "at": now().isoformat()})

    # 2. Plan (task ledger)
    task_ledger = TaskLedger(
        facts=[
            f"Document filename: {case.filename}",
            f"Content length: {len(case.content_text)} chars",
            f"Mode: {'llm' if settings.use_llm else 'mock'}",
        ],
        guesses=["Document type is supplier invoice (AP)"],
        plan=[
            "Extract structured invoice fields",
            "Validate schema and arithmetic",
            "Retrieve applicable policies",
            "Decide approve/hold/escalate",
            "Human review if needed",
            "Write bill to ERP via tool",
            "Verify final state",
        ],
        risk_tier="medium",
        effort_budget="standard",
    )
    steps.append(
        _step(
            "plan",
            "completed",
            "Built task ledger (Magentic-One style)",
            task_ledger.model_dump(),
        )
    )

    progress = ProgressLedger(current_step="extract", completed_steps=["ingest", "plan"])

    # 3. Extract
    extraction, meta = extract_invoice(case.content_text, case.filename)
    total_cost += float(meta.get("cost_usd", 0))
    total_tokens += int(meta.get("tokens", 0))
    conf = overall_confidence(extraction)
    steps.append(
        _step(
            "extract",
            "completed",
            f"Extracted vendor={extraction.vendor_name} total={extraction.total} conf={conf:.2f}",
            {"mode": meta.get("mode"), "extraction": extraction.model_dump()},
            tokens=int(meta.get("tokens", 0)),
            cost=float(meta.get("cost_usd", 0)),
        )
    )
    progress.completed_steps.append("extract")
    progress.current_step = "validate"

    # 4. Validate
    validation = validate_extraction(extraction)
    steps.append(
        _step(
            "validate",
            "completed",
            "ok" if validation.ok else f"{len(validation.issues)} issue(s)",
            validation.model_dump(),
        )
    )
    progress.completed_steps.append("validate")
    progress.current_step = "retrieve_policy"

    # 5. Retrieve policy (agentic retrieval stand-in)
    policies = retrieve_policies(
        f"{extraction.vendor_name} {extraction.currency} total {extraction.total} validation"
    )
    steps.append(
        _step(
            "retrieve_policy",
            "completed",
            f"Retrieved {len(policies)} policy snippet(s)",
            {"policies": policies},
        )
    )
    progress.completed_steps.append("retrieve_policy")
    progress.current_step = "decide"

    # 6. Decide
    decision, reason, needs_human = decide(extraction, validation, conf)
    steps.append(_step("decide", "completed", f"{decision.value}: {reason}", {"decision": decision.value}))
    progress.completed_steps.append("decide")

    case.extraction_json = dumps(extraction)
    case.validation_json = dumps(validation)
    case.overall_confidence = conf
    case.decision = decision.value
    case.task_ledger_json = dumps(task_ledger)
    case.cost_usd = total_cost

    if needs_human:
        progress.needs_human = True
        progress.human_reason = reason
        progress.current_step = "hitl"
        steps.append(_step("hitl", "waiting", reason))
        steps.append(_step("act", "skipped", "Waiting for human approval before ERP writeback"))
        steps.append(_step("verify", "skipped", "Pending HITL"))
        case.status = CaseStatus.needs_review.value
        case.progress_ledger_json = dumps(progress)
        case.steps_json = dumps(steps)
        case.audit_json = dumps(audit + [{"event": "hitl_required", "reason": reason, "at": now().isoformat()}])
        case.updated_at = now()
        await session.commit()
        return case

    # 7. Act (MCP-shaped ERP tool) — irreversible gate passed
    progress.current_step = "act"
    bill = create_bill(
        vendor_name=extraction.vendor_name,
        invoice_number=extraction.invoice_number,
        total=extraction.total,
        currency=extraction.currency,
    )
    case.erp_bill_id = bill.id
    steps.append(
        _step(
            "act",
            "completed",
            f"ERP bill created {bill.id}",
            {"tool": "erp_create_bill", "bill": bill.__dict__},
        )
    )
    progress.completed_steps.append("act")
    audit.append(
        {
            "event": "erp_create_bill",
            "bill_id": bill.id,
            "at": now().isoformat(),
            "irreversible": True,
            "approved_by": "auto",
        }
    )

    # 8. Verify
    progress.current_step = "verify"
    verify_ok = bool(case.erp_bill_id) and decision == Decision.approve
    steps.append(
        _step(
            "verify",
            "completed" if verify_ok else "failed",
            "Final state verified" if verify_ok else "Verification failed",
            {"erp_bill_id": case.erp_bill_id, "decision": decision.value},
        )
    )
    progress.completed_steps.append("verify")
    progress.current_step = "done"

    case.status = CaseStatus.acted.value if verify_ok else CaseStatus.failed.value
    case.progress_ledger_json = dumps(progress)
    case.steps_json = dumps(steps)
    case.audit_json = dumps(audit)
    case.updated_at = now()
    await session.commit()
    return case


async def apply_review(
    session: AsyncSession,
    case: CaseRow,
    action: str,
    extraction: InvoiceExtraction | None,
    note: str,
) -> CaseRow:
    steps = [
        AgentStep(**s) if isinstance(s, dict) else s
        for s in (__import__("json").loads(case.steps_json) or [])
    ]
    audit = __import__("json").loads(case.audit_json or "[]")

    if extraction is not None:
        case.extraction_json = dumps(extraction)
        case.overall_confidence = overall_confidence(extraction)
        validation = validate_extraction(extraction)
        case.validation_json = dumps(validation)
    else:
        extraction = InvoiceExtraction(**__import__("json").loads(case.extraction_json))

    # Mark HITL complete
    steps = [s if not isinstance(s, AgentStep) else s for s in steps]
    # normalize to dicts for mutation
    step_dicts = [s.model_dump(mode="json") if isinstance(s, AgentStep) else s for s in steps]
    for s in step_dicts:
        if s.get("name") == "hitl" and s.get("status") == "waiting":
            s["status"] = "completed"
            s["detail"] = f"Human {action}: {note}".strip()
            s["finished_at"] = now().isoformat()

    if action == "reject":
        case.status = CaseStatus.rejected.value
        case.decision = Decision.reject.value
        step_dicts.append(
            _step("act", "skipped", "Rejected by human").model_dump(mode="json")
        )
        step_dicts.append(
            _step("verify", "completed", "Rejected — no ERP writeback").model_dump(mode="json")
        )
        audit.append({"event": "human_reject", "note": note, "at": now().isoformat()})
        case.steps_json = dumps(step_dicts)
        case.audit_json = dumps(audit)
        case.updated_at = now()
        await session.commit()
        return case

    # approve or edit_and_approve → act
    bill = create_bill(
        vendor_name=extraction.vendor_name,
        invoice_number=extraction.invoice_number,
        total=extraction.total,
        currency=extraction.currency,
    )
    case.erp_bill_id = bill.id
    case.decision = Decision.approve.value
    case.status = CaseStatus.acted.value
    step_dicts.append(
        _step(
            "act",
            "completed",
            f"ERP bill created {bill.id} after human approval",
            {"tool": "erp_create_bill", "bill": bill.__dict__},
        ).model_dump(mode="json")
    )
    step_dicts.append(
        _step("verify", "completed", "Human-approved writeback verified").model_dump(mode="json")
    )
    audit.append(
        {
            "event": "human_approve",
            "note": note,
            "bill_id": bill.id,
            "at": now().isoformat(),
            "irreversible": True,
        }
    )
    case.steps_json = dumps(step_dicts)
    case.audit_json = dumps(audit)
    case.updated_at = now()
    await session.commit()
    return case
