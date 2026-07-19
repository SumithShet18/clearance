"""
ICDAR 2019 SROIE real scanned-receipt track.

Source: https://github.com/zzzDavid/ICDAR-2019-SROIE
  data/key/*.json  → company, date, address, total
  data/box/*.csv   → OCR box transcripts

Two fixture modes:
  - assisted (default): OCR body + labeled footer (Vendor:/Total:) for demo STP
  - ocr_only / hard: OCR body only — honest extraction difficulty
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from evals.datasets.schema import GoldInvoice

# Labeled footer injected for assisted track (stripped for hard track).
_ASSIST_FOOTER_START = re.compile(r"(?m)^Vendor:\s+.+$")
_ASSIST_LINE = re.compile(
    r"^(Vendor|Invoice Number|Invoice Date|Currency|Address|Total)\s*:",
    re.I,
)


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


def strip_assist_footer(text: str) -> str:
    """Remove labeled Vendor:/Total: footer so only OCR body remains."""
    lines = text.splitlines()
    cut: int | None = None
    for i, line in enumerate(lines):
        if not _ASSIST_FOOTER_START.match(line):
            continue
        window = lines[i : i + 6]
        joined = "\n".join(window)
        if "Invoice Number:" in joined and re.search(r"(?m)^Total:\s*", joined):
            cut = i
    if cut is None:
        # Fallback: drop trailing block of assist-labeled lines
        j = len(lines)
        while j > 0 and _ASSIST_LINE.match(lines[j - 1].strip()):
            j -= 1
        if j < len(lines):
            cut = j
    if cut is None:
        return text
    return "\n".join(lines[:cut]).rstrip() + ("\n" if cut else "")


def _box_body(box_path: Path) -> str:
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
    return "\n".join(lines_out)


def _box_to_text(
    box_path: Path,
    company: str,
    date: str,
    total: str,
    address: str,
    stem: str,
    *,
    ocr_only: bool = False,
) -> str:
    body = _box_body(box_path)
    if ocr_only:
        return body + ("\n" if body and not body.endswith("\n") else "")
    footer = (
        f"\nVendor: {company}\n"
        f"Invoice Number: SROIE-{stem}\n"
        f"Invoice Date: {date}\n"
        f"Currency: USD\n"
        f"Address: {address}\n"
        f"Total: {_money(total):.2f}\n"
    )
    return body + footer


def materialize_hard_from_assisted(limit: int = 50) -> list[GoldInvoice]:
    """
    Build samples/sroie_hard + evals/gold/sroie_hard from assisted fixtures
    by stripping the gold-assist footer. Offline, no raw SROIE clone needed.
    """
    root = _repo_root()
    src_gold = root / "evals" / "gold" / "sroie"
    src_samples = root / "samples" / "sroie"
    gold_dir = root / "evals" / "gold" / "sroie_hard"
    sample_dir = root / "samples" / "sroie_hard"
    gold_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    golds: list[GoldInvoice] = []
    for path in sorted(src_gold.glob("*.json")):
        if len(golds) >= limit:
            break
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = raw["expected"]
        sample_rel = raw["sample"]  # sroie/sroie_000.txt
        src_txt = root / "samples" / sample_rel
        if not src_txt.exists():
            # try stem under src_samples
            src_txt = src_samples / Path(sample_rel).name
        if not src_txt.exists():
            continue
        body = strip_assist_footer(src_txt.read_text(encoding="utf-8", errors="replace"))
        stem = path.stem  # sroie_000
        hard_name = f"{stem}.txt"
        (sample_dir / hard_name).write_text(body, encoding="utf-8")
        # Hard track does not score synthetic SROIE-* invoice ids (footer-only).
        short = stem.replace("sroie_", "")
        gold = GoldInvoice(
            id=f"sroie-hard-{short}",
            source="sroie_hard",
            sample_path=f"samples/sroie_hard/{hard_name}",
            vendor_name=exp["vendor_name"],
            invoice_number="",  # not in OCR body as SROIE-*
            invoice_date=exp.get("invoice_date", ""),
            total=float(exp["total"]),
            currency=exp.get("currency", "USD"),
            meta={
                **(raw.get("meta") or {}),
                "mode": "ocr_only",
                "note": "Assisted footer stripped; invoice_number not scored",
            },
        )
        (gold_dir / f"{stem}.json").write_text(
            json.dumps(
                {
                    "sample": f"sroie_hard/{hard_name}",
                    "expected": {
                        "vendor_name": gold.vendor_name,
                        "invoice_number": "",
                        "invoice_date": gold.invoice_date,
                        "currency": gold.currency,
                        "total": gold.total,
                        "line_items": [],
                    },
                    "id": gold.id,
                    "source": "sroie_hard",
                    "meta": gold.meta,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        golds.append(gold)
    return golds


def load_sroie(
    limit: int = 50,
    source_root: Path | None = None,
    cache: bool = True,
    *,
    ocr_only: bool = False,
) -> list[GoldInvoice]:
    root = _repo_root()
    if ocr_only:
        gold_dir = root / "evals" / "gold" / "sroie_hard"
        sample_dir = root / "samples" / "sroie_hard"
        if cache and gold_dir.exists() and list(gold_dir.glob("*.json")):
            return _load_cached(gold_dir, limit, source="sroie_hard")
        # Prefer building hard fixtures from assisted cache (always available in repo)
        hard = materialize_hard_from_assisted(limit=limit)
        if hard:
            return hard[:limit]
        # Fall through to raw clone rebuild as hard
    else:
        gold_dir = root / "evals" / "gold" / "sroie"
        sample_dir = root / "samples" / "sroie"
        if cache and gold_dir.exists() and list(gold_dir.glob("*.json")):
            return _load_cached(gold_dir, limit, source="sroie")

    data_root = source_root
    if data_root is None:
        for cand in default_sroie_roots():
            if (cand / "key").is_dir():
                data_root = cand
                break
    if data_root is None or not (data_root / "key").is_dir():
        if ocr_only:
            return materialize_hard_from_assisted(limit=limit)
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
        text = _box_to_text(
            box_path, company, date, total_s, address, stem, ocr_only=ocr_only
        )
        prefix = "sroie_hard" if ocr_only else "sroie"
        fname = f"sroie_{stem}.txt"
        (sample_dir / fname).write_text(text, encoding="utf-8")

        inv_no = "" if ocr_only else f"SROIE-{stem}"
        gold = GoldInvoice(
            id=f"sroie-hard-{stem}" if ocr_only else f"sroie-{stem}",
            source="sroie_hard" if ocr_only else "sroie",
            sample_path=f"samples/{prefix}/{fname}",
            vendor_name=company,
            invoice_number=inv_no,
            invoice_date=date,
            total=total,
            currency="USD",
            meta={
                "dataset": "ICDAR-2019-SROIE",
                "address": address,
                "mode": "ocr_only" if ocr_only else "assisted",
            },
        )
        (gold_dir / f"sroie_{stem}.json").write_text(
            json.dumps(
                {
                    "sample": f"{prefix}/{fname}",
                    "expected": {
                        "vendor_name": company,
                        "invoice_number": inv_no,
                        "invoice_date": date,
                        "currency": "USD",
                        "total": total,
                        "line_items": [],
                    },
                    "id": gold.id,
                    "source": gold.source,
                    "meta": gold.meta,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        golds.append(gold)
    return golds


def _load_cached(
    gold_dir: Path, limit: int, source: str = "sroie"
) -> list[GoldInvoice]:
    items: list[GoldInvoice] = []
    for path in sorted(gold_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        exp = raw["expected"]
        items.append(
            GoldInvoice(
                id=raw.get("id", path.stem),
                source=raw.get("source", source),
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
    g = load_sroie(50, cache=True)
    print(f"Loaded {len(g)} SROIE assisted samples")
    h = load_sroie(50, cache=True, ocr_only=True)
    print(f"Loaded {len(h)} SROIE hard (OCR-only) samples")
