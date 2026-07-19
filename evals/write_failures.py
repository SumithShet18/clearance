"""Write evals/results/failures.md — top extraction misses for interview honesty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from evals.datasets.sroie_loader import load_sroie
from evals.datasets.synthetic import load_synthetic_golds
from evals.run_benchmark import run_extract_bench


def _miss_rows(details: list[dict], golds_by_id: dict, limit: int = 12) -> list[str]:
    rows: list[tuple[int, str]] = []
    for d in details:
        scores = d.get("scores") or {}
        fails = [k for k, ok in scores.items() if not ok]
        if not fails:
            continue
        g = golds_by_id.get(d["id"])
        pred_total = d.get("pred_total")
        gold_total = d.get("gold_total")
        vendor = (g.vendor_name if g else "?")[:48]
        line = (
            f"| `{d['id']}` | {', '.join(fails)} | {vendor} | "
            f"{pred_total} vs {gold_total} |"
        )
        rows.append((len(fails), line))
    rows.sort(key=lambda x: (-x[0], x[1]))
    return [r[1] for r in rows[:limit]]


def main() -> None:
    sections: list[str] = [
        "# Extraction failure gallery",
        "",
        "Honest miss list from offline Clearance Bench (mock extractor). "
        "Use in interviews: *where it breaks and why HITL exists*.",
        "",
    ]

    for title, golds in [
        ("Synthetic", load_synthetic_golds(50)),
        ("SROIE assisted (footer labels present)", load_sroie(limit=50, cache=True)),
        ("SROIE hard (OCR body only)", load_sroie(limit=50, cache=True, ocr_only=True)),
    ]:
        if not golds:
            sections += [f"## {title}", "", "_No fixtures loaded._", ""]
            continue
        result = run_extract_bench(golds)
        by_id = {g.id: g for g in golds}
        miss = _miss_rows(result.get("details") or [], by_id)
        n_fail = sum(
            1
            for d in (result.get("details") or [])
            if any(not ok for ok in (d.get("scores") or {}).values())
        )
        sections += [
            f"## {title}",
            "",
            f"- Cases: **{result['cases']}** · micro field acc: "
            f"**{result['micro_field_accuracy'] * 100:.1f}%** · "
            f"docs with ≥1 miss: **{n_fail}**",
            "",
            "| Case | Missed fields | Gold vendor | Pred total vs gold |",
            "| --- | --- | --- | --- |",
        ]
        if miss:
            sections.extend(miss)
        else:
            sections.append("| — | (none) | — | — |")
        sections.append("")

    sections += [
        "## Notes",
        "",
        "- **Assisted SROIE** includes labeled `Vendor:` / `Total:` lines — high scores are partly format-assisted.",
        "- **Hard SROIE** strips those lines; invoice # is not scored (synthetic `SROIE-*` ids only exist in the footer).",
        "- Mock rules fail on noisy OCR vendor names and multi-total receipts → policy/HITL is the product.",
        "",
        "Regenerate:",
        "",
        "```bash",
        "python evals/write_failures.py",
        "python evals/write_real_report.py",
        "```",
        "",
    ]

    out = ROOT / "evals" / "results" / "failures.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
