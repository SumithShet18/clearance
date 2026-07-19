#!/usr/bin/env python3
"""Clearance Bench — per-field extraction + optional full pipeline metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from evals.datasets.schema import GoldInvoice, field_scores  # noqa: E402
from evals.datasets.synthetic import generate_corpus, load_synthetic_golds  # noqa: E402


def load_manual_golds() -> list[GoldInvoice]:
    gold_dir = ROOT / "evals" / "gold"
    items: list[GoldInvoice] = []
    for path in sorted(gold_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = raw["expected"]
        items.append(
            GoldInvoice(
                id=path.stem,
                source="manual",
                sample_path=f"samples/{raw['sample']}",
                vendor_name=exp["vendor_name"],
                invoice_number=exp.get("invoice_number", ""),
                invoice_date=exp.get("invoice_date", ""),
                total=float(exp["total"]),
                currency=exp.get("currency", "USD"),
                tax=exp.get("tax"),
                subtotal=exp.get("subtotal"),
            )
        )
    return items


def load_golds(source: str, limit: int | None) -> list[GoldInvoice]:
    if source == "synthetic":
        return load_synthetic_golds(limit)
    if source == "manual":
        g = load_manual_golds()
        return g[:limit] if limit else g
    if source == "cord":
        from evals.datasets.cord_loader import load_cord

        return load_cord(limit=limit or 50)
    if source == "all":
        g = load_manual_golds() + load_synthetic_golds(None)
        try:
            from evals.datasets.cord_loader import load_cord

            g += load_cord(limit=min(limit or 20, 20))
        except Exception:
            pass
        return g[:limit] if limit else g
    raise SystemExit(f"Unknown source: {source}")


def run_extract_bench(golds: list[GoldInvoice]) -> dict:
    from app.services.extractor import extract_invoice

    field_hits: Counter[str] = Counter()
    field_tot: Counter[str] = Counter()
    details = []

    for g in golds:
        path = ROOT / g.sample_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        pred, meta = extract_invoice(text, path.name)
        pred_d = pred.model_dump()
        scores = field_scores(pred_d, g)
        for k, ok in scores.items():
            field_tot[k] += 1
            if ok:
                field_hits[k] += 1
        details.append(
            {
                "id": g.id,
                "source": g.source,
                "scores": scores,
                "pred_total": pred.total,
                "gold_total": g.total,
                "mode": meta.get("mode"),
            }
        )

    per_field = {
        k: (field_hits[k] / field_tot[k] if field_tot[k] else 0.0) for k in field_tot
    }
    micro = (
        sum(field_hits.values()) / sum(field_tot.values()) if sum(field_tot.values()) else 0.0
    )
    return {
        "mode": "extract",
        "cases": len(details),
        "micro_field_accuracy": micro,
        "per_field": per_field,
        "details": details,
    }


def run_pipeline_bench(golds: list[GoldInvoice], limit: int = 20) -> dict:
    """Run full agent pipeline on a subset (slower, needs async)."""
    import asyncio

    from app.db import CaseRow, SessionLocal, init_db, new_id, now
    from app.models.schemas import CaseStatus
    from app.services.pipeline import run_pipeline

    async def _run() -> dict:
        await init_db()
        statuses: Counter[str] = Counter()
        n = 0
        async with SessionLocal() as session:
            for g in golds[:limit]:
                path = ROOT / g.sample_path
                if not path.exists():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                row = CaseRow(
                    id=new_id(),
                    filename=path.name,
                    status=CaseStatus.pending.value,
                    content_text=text,
                    file_path=str(path),
                    created_at=now(),
                    updated_at=now(),
                )
                session.add(row)
                await session.commit()
                await run_pipeline(session, row)
                await session.refresh(row)
                statuses[row.status] += 1
                n += 1
        total = n or 1
        return {
            "mode": "pipeline",
            "cases": n,
            "status_counts": dict(statuses),
            "auto_acted_rate": statuses.get("acted", 0) / total,
            "needs_review_rate": statuses.get("needs_review", 0) / total,
        }

    return asyncio.run(_run())


def write_report(result: dict, pipeline: dict | None) -> None:
    results_dir = ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "extract": result,
        "pipeline": pipeline,
    }
    # strip heavy details for latest summary? keep them
    (results_dir / "latest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Clearance Bench Report",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Extraction (per-field)",
        "",
        f"- Cases: **{result['cases']}**",
        f"- Micro field accuracy: **{result['micro_field_accuracy']*100:.1f}%**",
        "",
        "| Field | Accuracy |",
        "| --- | ---: |",
    ]
    for k, v in sorted(result.get("per_field", {}).items()):
        lines.append(f"| {k} | {v*100:.1f}% |")
    if pipeline:
        lines += [
            "",
            "## Full agent pipeline (subset)",
            "",
            f"- Cases: **{pipeline['cases']}**",
            f"- Auto-acted (STP proxy): **{pipeline['auto_acted_rate']*100:.1f}%**",
            f"- Needs review (HITL): **{pipeline['needs_review_rate']*100:.1f}%**",
            f"- Status counts: `{pipeline['status_counts']}`",
        ]
    lines += [
        "",
        "## Notes",
        "",
        "- Synthetic invoices are generated with fixed seed (reproducible, no PII).",
        "- CORD track is optional (`--source cord`) when HuggingFace `datasets` is available.",
        "- Mock extractor mode is default; set `CLEARANCE_MODE=llm` + API key for multimodal.",
        "",
    ]
    (ROOT / "evals" / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Clearance Bench")
    p.add_argument("--source", default="synthetic", choices=["synthetic", "manual", "cord", "all"])
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--regenerate", action="store_true", help="Regenerate synthetic corpus")
    p.add_argument("--pipeline", action="store_true", help="Also run full agent pipeline subset")
    p.add_argument("--pipeline-limit", type=int, default=20)
    args = p.parse_args()

    if args.regenerate or args.source in {"synthetic", "all"}:
        # ensure corpus exists
        syn_dir = ROOT / "evals" / "gold" / "synthetic"
        if args.regenerate or not syn_dir.exists() or not list(syn_dir.glob("*.json")):
            generate_corpus(50)
            print("Generated 50 synthetic invoices")

    golds = load_golds(args.source, args.limit)
    if not golds:
        print("No gold samples loaded", file=sys.stderr)
        sys.exit(1)

    print(f"Running extract bench on {len(golds)} docs (source={args.source})…")
    result = run_extract_bench(golds)
    print(f"Micro field accuracy: {result['micro_field_accuracy']*100:.1f}%")
    for k, v in result["per_field"].items():
        print(f"  {k}: {v*100:.1f}%")

    pipeline = None
    if args.pipeline:
        print(f"Running pipeline bench (limit={args.pipeline_limit})…")
        pipeline = run_pipeline_bench(golds, limit=args.pipeline_limit)
        print(f"  auto-acted: {pipeline['auto_acted_rate']*100:.1f}%")
        print(f"  needs_review: {pipeline['needs_review_rate']*100:.1f}%")

    write_report(result, pipeline)
    print("Wrote evals/REPORT.md and evals/results/latest.json")


if __name__ == "__main__":
    main()
