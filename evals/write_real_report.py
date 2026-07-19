"""Write multi-track REPORT.md: synthetic + SROIE + CORD."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from evals.datasets.cord_loader import load_cord
from evals.datasets.sroie_loader import load_sroie
from evals.datasets.synthetic import load_synthetic_golds
from evals.run_benchmark import run_extract_bench, run_pipeline_bench


def _section(title: str, result: dict, extra: list[str] | None = None) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"- Cases: **{result.get('cases', 0)}**",
        f"- Micro field accuracy: **{result.get('micro_field_accuracy', 0) * 100:.1f}%**",
        "",
        "| Field | Accuracy |",
        "| --- | ---: |",
    ]
    for k, v in sorted((result.get("per_field") or {}).items()):
        lines.append(f"| {k} | {v * 100:.1f}% |")
    if extra:
        lines.append("")
        lines.extend(extra)
    lines.append("")
    return lines


def main() -> None:
    syn = load_synthetic_golds(50)
    sr = run_extract_bench(syn)
    pr = run_pipeline_bench(syn, limit=25)

    sroie = load_sroie(limit=50, cache=True)
    if not sroie:
        sroie = load_sroie(limit=50, cache=False)
    sro = run_extract_bench(sroie) if sroie else {"cases": 0, "micro_field_accuracy": 0.0, "per_field": {}}

    cord = load_cord(limit=25, cache=True)
    cr = run_extract_bench(cord) if cord else {"cases": 0, "micro_field_accuracy": 0.0, "per_field": {}}

    lines = [
        "# Clearance Bench Report",
        "",
        "Multi-track evaluation on **synthetic stress data** and **public real receipt datasets**.",
        "",
    ]
    lines += _section(
        "Track A — Synthetic invoices (reproducible, no PII)",
        sr,
        [
            "### Full agent pipeline (subset)",
            "",
            f"- Cases: **{pr['cases']}**",
            f"- Auto-acted (STP proxy): **{pr['auto_acted_rate'] * 100:.1f}%**",
            f"- Needs review (HITL): **{pr['needs_review_rate'] * 100:.1f}%**",
            f"- Status counts: `{pr['status_counts']}`",
        ],
    )
    lines += _section(
        "Track B — ICDAR 2019 SROIE (real scanned receipts)",
        sro,
        [
            "Source: [zzzDavid/ICDAR-2019-SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) "
            "public labels (`company`, `date`, `total`) + OCR box transcripts.",
            "This is a **standard research IE setup** for real receipts — not synthetic only.",
        ],
    )
    lines += _section(
        "Track C — CORD v2 receipt fixtures",
        cr,
        [
            "Source: HuggingFace `naver-clova-ix/cord-v2` ground-truth renders (committed fixtures).",
        ],
    )
    lines += [
        "## How to read these numbers",
        "",
        "- **Field accuracy** measures extraction vs gold labels (vendor, invoice #, total, currency).",
        "- **STP / HITL** measures the *agent policy graph*, not OCR alone — ~50% auto is intentional risk control.",
        "- Default extractor is **mock/rules** (offline). Optional `CLEARANCE_MODE=llm` for multimodal models.",
        "- These results support a **portfolio / production-pattern** claim, not “beats Vic.ai SOTA.”",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python evals/run_benchmark.py --source sroie --limit 50",
        "python evals/run_benchmark.py --source synthetic --limit 50 --pipeline",
        "python evals/write_real_report.py",
        "```",
        "",
    ]
    (ROOT / "evals" / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote evals/REPORT.md")
    print("synthetic", sr["micro_field_accuracy"], "sroie", sro.get("micro_field_accuracy"), "cord", cr.get("micro_field_accuracy"))


if __name__ == "__main__":
    main()
