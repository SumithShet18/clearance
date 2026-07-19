"""Write dual-track REPORT.md (synthetic + CORD)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from evals.datasets.cord_loader import load_cord
from evals.datasets.synthetic import load_synthetic_golds
from evals.run_benchmark import run_extract_bench, run_pipeline_bench


def main() -> None:
    syn = load_synthetic_golds(50)
    sr = run_extract_bench(syn)
    pr = run_pipeline_bench(syn, limit=25)
    cord = load_cord(limit=25, cache=True)
    cr = run_extract_bench(cord) if cord else {"cases": 0, "micro_field_accuracy": 0.0, "per_field": {}}

    lines = [
        "# Clearance Bench Report",
        "",
        "Dual-track evaluation (research-backed).",
        "",
        "## Track A — Synthetic invoices (reproducible, no PII)",
        "",
        f"- Cases: **{sr['cases']}**",
        f"- Micro field accuracy: **{sr['micro_field_accuracy'] * 100:.1f}%**",
        "",
        "| Field | Accuracy |",
        "| --- | ---: |",
    ]
    for k, v in sorted(sr["per_field"].items()):
        lines.append(f"| {k} | {v * 100:.1f}% |")
    lines += [
        "",
        "### Full agent pipeline (subset)",
        "",
        f"- Cases: **{pr['cases']}**",
        f"- Auto-acted (STP proxy): **{pr['auto_acted_rate'] * 100:.1f}%**",
        f"- Needs review (HITL): **{pr['needs_review_rate'] * 100:.1f}%**",
        f"- Status counts: `{pr['status_counts']}`",
        "",
        "## Track B — CORD v2 real receipts",
        "",
        "Source: HuggingFace `naver-clova-ix/cord-v2`. "
        "Text renders are built from public ground-truth annotations (honest offline path).",
        "",
        f"- Cases: **{cr['cases']}**",
        f"- Micro field accuracy: **{cr['micro_field_accuracy'] * 100:.1f}%**",
        "",
        "| Field | Accuracy |",
        "| --- | ---: |",
    ]
    for k, v in sorted((cr.get("per_field") or {}).items()):
        lines.append(f"| {k} | {v * 100:.1f}% |")
    if not cord:
        lines.append("")
        lines.append("_CORD not loaded (install `datasets` and re-run)._")
    lines += [
        "",
        "## Notes",
        "",
        "- Synthetic includes stress cases (noise / missing invoice # / math drift).",
        "- CORD track validates totals/fields from public receipt labels without shipping multi-GB images.",
        "- Default mock extractor; optional `CLEARANCE_MODE=llm` for vision.",
        "- One-click cloud deploy: see README Render button.",
        "",
    ]
    (ROOT / "evals" / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote evals/REPORT.md")
    print("synthetic micro", sr["micro_field_accuracy"], "pipeline STP", pr["auto_acted_rate"])
    print("cord micro", cr["micro_field_accuracy"], "n", cr["cases"])


if __name__ == "__main__":
    main()
