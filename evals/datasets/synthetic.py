"""Reproducible synthetic invoice corpus for offline CI + portfolio benchmarks."""

from __future__ import annotations

import json
import random
from pathlib import Path

from evals.datasets.schema import GoldInvoice

# Keep in sync with apps/api/app/services/policy.py KNOWN_VENDORS
KNOWN = [
    "ACME Supplies",
    "Northwind Traders",
    "Globex Industrial",
    "Initech Services",
    "Umbrella Logistics",
]
UNKNOWN = [
    "Quantum Parts LLC",
    "Stark Industries",
    "Wayne Enterprises",
    "Oscorp Materials",
    "Wonka Imports",
    "Cyberdyne Systems",
    "Tyrell Corp",
    "Soylent Foods",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def generate_corpus(n: int = 50, seed: int = 42) -> list[GoldInvoice]:
    """Write samples/synthetic/*.txt and evals/gold/synthetic/*.json; return golds."""
    rng = random.Random(seed)
    root = _repo_root()
    sample_dir = root / "samples" / "synthetic"
    gold_dir = root / "evals" / "gold" / "synthetic"
    sample_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    # clear previous synthetic only
    for p in sample_dir.glob("*.txt"):
        p.unlink()
    for p in gold_dir.glob("*.json"):
        p.unlink()

    golds: list[GoldInvoice] = []
    for i in range(n):
        known = rng.random() < 0.55
        vendor = rng.choice(KNOWN if known else UNKNOWN)
        currency = rng.choice(["USD", "USD", "USD", "EUR"])
        n_lines = rng.randint(1, 4)
        lines = []
        subtotal = 0.0
        for j in range(n_lines):
            qty = rng.choice([1, 2, 5, 10, 20])
            unit = round(rng.uniform(5, 400), 2)
            amt = round(qty * unit, 2)
            subtotal += amt
            desc = rng.choice(
                ["Widgets", "Cables", "Consulting hours", "Toner", "Sensors", "Freight"]
            )
            lines.append((desc, qty, unit, amt))
        subtotal = round(subtotal, 2)

        # Force some high-value / low-conf cases for HITL paths
        tag = ""
        if i % 11 == 0 and not known:
            # scale up to trigger POL-002
            factor = max(1.0, 10000 / max(subtotal, 1))
            lines = [(d, q, round(u * factor, 2), round(a * factor, 2)) for d, q, u, a in lines]
            subtotal = round(sum(a for *_, a in lines), 2)
            tag = "HIGHVALUE"
        if i % 13 == 0:
            tag = (tag + " LOWCONF").strip()

        tax_rate = 0.08 if currency == "USD" else 0.19
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)
        inv_no = f"SYN-{2026}-{i:04d}"
        inv_date = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        due = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"

        body_lines = [
            vendor,
            f"Vendor: {vendor}",
            f"Invoice Number: {inv_no}",
            f"Invoice Date: {inv_date}",
            f"Due Date: {due}",
            f"Currency: {currency}",
            "",
            "Line items:",
        ]
        for d, q, u, a in lines:
            body_lines.append(f"- {d} | {q} | {u:.2f} | {a:.2f}")
        body_lines += [
            "",
            f"Subtotal: {subtotal:.2f}",
            f"Tax: {tax:.2f}",
            f"Total: {total:.2f}",
        ]
        if "LOWCONF" in tag:
            body_lines.insert(0, "LOWCONF SAMPLE — partial OCR noise")
            body_lines[1] = vendor

        # Stress modes: intentional noise / gaps (honest <100% extract track)
        stress = ""
        if i % 17 == 0:
            stress = "noise"
            # corrupt Total line formatting (extractor may still recover)
            body_lines = [ln.replace("Total:", "T0tal approx:") if ln.startswith("Total:") else ln for ln in body_lines]
        elif i % 19 == 0:
            stress = "missing_invoice_no"
            body_lines = [ln for ln in body_lines if not ln.startswith("Invoice Number:")]
            inv_no = ""  # gold reflects missing → skip strict inv match via empty gold number
        elif i % 23 == 0:
            stress = "math_drift"
            # gold keeps true total; document shows drifted total
            body_lines = [
                (f"Total: {total + 12.34:.2f}" if ln.startswith("Total:") else ln) for ln in body_lines
            ]

        fname = f"syn_{i:04d}.txt"
        rel = f"samples/synthetic/{fname}"
        (sample_dir / fname).write_text("\n".join(body_lines) + "\n", encoding="utf-8")

        gold = GoldInvoice(
            id=f"syn-{i:04d}",
            source="synthetic",
            sample_path=rel,
            vendor_name=vendor,
            invoice_number=inv_no,
            invoice_date=inv_date,
            total=total,
            currency=currency,
            tax=tax,
            subtotal=subtotal,
            meta={"known_vendor": known, "tag": tag, "stress": stress},
        )
        gold_path = gold_dir / f"syn_{i:04d}.json"
        gold_path.write_text(
            json.dumps(
                {
                    "sample": f"synthetic/{fname}",
                    "expected": {
                        "vendor_name": gold.vendor_name,
                        "invoice_number": gold.invoice_number,
                        "invoice_date": gold.invoice_date,
                        "currency": gold.currency,
                        "subtotal": gold.subtotal,
                        "tax": gold.tax,
                        "total": gold.total,
                        "line_items": [],
                    },
                    "id": gold.id,
                    "source": "synthetic",
                    "meta": gold.meta,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        golds.append(gold)
    return golds


def load_synthetic_golds(limit: int | None = None) -> list[GoldInvoice]:
    root = _repo_root()
    gold_dir = root / "evals" / "gold" / "synthetic"
    if not gold_dir.exists() or not list(gold_dir.glob("*.json")):
        generate_corpus(50)
    items: list[GoldInvoice] = []
    for path in sorted(gold_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = raw["expected"]
        items.append(
            GoldInvoice(
                id=raw.get("id", path.stem),
                source=raw.get("source", "synthetic"),
                sample_path=f"samples/{raw['sample']}",
                vendor_name=exp["vendor_name"],
                invoice_number=exp.get("invoice_number", ""),
                invoice_date=exp.get("invoice_date", ""),
                total=float(exp["total"]),
                currency=exp.get("currency", "USD"),
                tax=exp.get("tax"),
                subtotal=exp.get("subtotal"),
                meta=raw.get("meta") or {},
            )
        )
        if limit and len(items) >= limit:
            break
    return items


if __name__ == "__main__":
    g = generate_corpus(50)
    print(f"Generated {len(g)} synthetic invoices")
