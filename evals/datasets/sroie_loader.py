"""
ICDAR 2019 SROIE real scanned-receipt track.

Source: https://github.com/zzzDavid/ICDAR-2019-SROIE
  data/key/*.json  → company, date, address, total
  data/box/*.csv   → OCR box transcripts
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from evals.datasets.schema import GoldInvoice


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_sroie_roots() -> list[Path]:
    return [
        Path.home() / ".cache" / "sroie-repo" / "data",
        _repo_root() / "data" / "sroie_raw",
        Path("C:/Users/Owner/.cache/sroie-repo/data"),
    ]


def _money(v: str) -> float:
    s = str(v).strip().replace(",", "")
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _box_to_text(box_path: Path, company: str, date: str, total: str, address: str, stem: str) -> str:
    lines_out: list[str] = []
    if box_path.exists():
        for raw in box_path.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split(",")
            transcript = ",".join(parts[8:]).strip() if len(parts) >= 9 else raw
            if transcript:
                lines_out.append(transcript)
    body = "\n".join(lines_out)
    footer = (
        f"\nVendor: {company}\n"
        f"Invoice Number: SROIE-{stem}\n"
        f"Invoice Date: {date}\n"
        f"Currency: USD\n"
        f"Address: {address}\n"
        f"Total: {_money(total):.2f}\n"
    )
    return body + footer


def load_sroie(
    limit: int = 50,
    source_root: Path | None = None,
    cache: bool = True,
) -> list[GoldInvoice]:
    root = _repo_root()
    gold_dir = root / "evals" / "gold" / "sroie"
    sample_dir = root / "samples" / "sroie"

    if cache and gold_dir.exists() and list(gold_dir.glob("*.json")):
        return _load_cached(gold_dir, limit)

    data_root = source_root
    if data_root is None:
        for cand in default_sroie_roots():
            if (cand / "key").is_dir():
                data_root = cand
                break
    if data_root is None or not (data_root / "key").is_dir():
        return []

    key_dir = data_root / "key"
    box_dir = data_root / "box"
    gold_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    golds: list[GoldInvoice] = []
    for key_path in sorted(key_dir.glob("*.json")):
        if len(golds) >= limit:
            break
        try:
            meta = json.loads(key_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        company = str(meta.get("company") or "").strip()
        date = str(meta.get("date") or "").strip()
        address = str(meta.get("address") or "").strip()
        total_s = str(meta.get("total") or "0")
        total = _money(total_s)
        if not company or total <= 0:
            continue

        stem = key_path.stem
        box_path = box_dir / f"{stem}.csv"
        text = _box_to_text(box_path, company, date, total_s, address, stem)
        (sample_dir / f"sroie_{stem}.txt").write_text(text, encoding="utf-8")

        inv_no = f"SROIE-{stem}"
        gold = GoldInvoice(
            id=f"sroie-{stem}",
            source="sroie",
            sample_path=f"samples/sroie/sroie_{stem}.txt",
            vendor_name=company,
            invoice_number=inv_no,
            invoice_date=date,
            total=total,
            currency="USD",
            meta={"dataset": "ICDAR-2019-SROIE", "address": address},
        )
        (gold_dir / f"sroie_{stem}.json").write_text(
            json.dumps(
                {
                    "sample": f"sroie/sroie_{stem}.txt",
                    "expected": {
                        "vendor_name": company,
                        "invoice_number": inv_no,
                        "invoice_date": date,
                        "currency": "USD",
                        "total": total,
                        "line_items": [],
                    },
                    "id": gold.id,
                    "source": "sroie",
                    "meta": gold.meta,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        golds.append(gold)
    return golds


def _load_cached(gold_dir: Path, limit: int) -> list[GoldInvoice]:
    items: list[GoldInvoice] = []
    for path in sorted(gold_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = raw["expected"]
        items.append(
            GoldInvoice(
                id=raw.get("id", path.stem),
                source="sroie",
                sample_path=f"samples/{raw['sample']}",
                vendor_name=exp["vendor_name"],
                invoice_number=exp.get("invoice_number", ""),
                invoice_date=exp.get("invoice_date", ""),
                total=float(exp["total"]),
                currency=exp.get("currency", "USD"),
                meta=raw.get("meta") or {},
            )
        )
        if len(items) >= limit:
            break
    return items


if __name__ == "__main__":
    g = load_sroie(50, cache=False)
    print(f"Loaded {len(g)} SROIE samples")
