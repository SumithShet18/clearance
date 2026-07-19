from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    pending = "pending"
    running = "running"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    acted = "acted"
    failed = "failed"


class Decision(str, Enum):
    approve = "approve"
    hold = "hold"
    reject = "reject"
    escalate = "escalate"


class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0
    confidence: float = 0.0


class InvoiceExtraction(BaseModel):
    vendor_name: str = ""
    vendor_confidence: float = 0.0
    invoice_number: str = ""
    invoice_number_confidence: float = 0.0
    invoice_date: str = ""
    invoice_date_confidence: float = 0.0
    due_date: str = ""
    currency: str = "USD"
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    total_confidence: float = 0.0
    line_items: list[LineItem] = Field(default_factory=list)
    raw_notes: str = ""


class AgentStep(BaseModel):
    name: str
    status: str  # started | completed | skipped | failed | waiting
    started_at: datetime
    finished_at: datetime | None = None
    detail: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    tokens: int = 0
    cost_usd: float = 0.0


class TaskLedger(BaseModel):
    """Magentic-One style outer-loop plan state."""

    facts: list[str] = Field(default_factory=list)
    guesses: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    risk_tier: str = "medium"
    effort_budget: str = "standard"


class ProgressLedger(BaseModel):
    """Magentic-One style inner-loop progress state."""

    current_step: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    stall_count: int = 0
    needs_human: bool = False
    human_reason: str = ""


class ValidationResult(BaseModel):
    ok: bool
    issues: list[str] = Field(default_factory=list)
    math_ok: bool = True
    schema_ok: bool = True
    policy_ok: bool = True


class CaseCreateResponse(BaseModel):
    id: str
    status: CaseStatus
    filename: str


class CaseSummary(BaseModel):
    id: str
    filename: str
    status: CaseStatus
    vendor_name: str | None = None
    total: float | None = None
    overall_confidence: float | None = None
    decision: Decision | None = None
    created_at: datetime
    updated_at: datetime
    cost_usd: float = 0.0


class CaseDetail(CaseSummary):
    extraction: InvoiceExtraction | None = None
    validation: ValidationResult | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    task_ledger: TaskLedger | None = None
    progress_ledger: ProgressLedger | None = None
    erp_bill_id: str | None = None
    audit: list[dict[str, Any]] = Field(default_factory=list)
    content_preview: str = ""


class ReviewAction(BaseModel):
    action: str  # approve | reject | edit_and_approve
    extraction: InvoiceExtraction | None = None
    note: str = ""


class MetricsResponse(BaseModel):
    total_cases: int
    auto_resolved: int
    needs_review: int
    acted: int
    auto_resolve_rate: float
    avg_confidence: float
    avg_cost_usd: float
    gold_eval: dict[str, Any] | None = None


class EvalRunResult(BaseModel):
    cases: int
    field_accuracy: float
    total_match_rate: float
    vendor_match_rate: float
    details: list[dict[str, Any]]
