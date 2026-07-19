"""Optional CORD v2 loader (HuggingFace) — real receipts for credibility track."""

from __future__ import annotations

import json
import re
from pathlib import Path

from evals.datasets.schema import GoldInvoice


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_total(gt: dict) -> float:
    """Best-effort total from CORD gt_parse structures."""
    # common shapes: menu items + total.total_price, or total dict
    total = gt.get("total") or {}
    if isinstance(total, dict):
        for key in ("total_price", "total", "cashprice", "changeprice"):
            if key in total and total[key] is not None:
                return _money(total[key])
    # nested list style
    if isinstance(gt.get("total"), list):
        for row in gt["total"]:
            if isinstance(row, dict) and "total_price" in row:
                return _money(row["total_price"])
    # flat
    for key in ("total_price", "total"):
        if key in gt:
            return _money(gt[key])
    return 0.0


def _money(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.]", "", str(v).replace(",", ""))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _vendor(gt: dict) -> str:
    menu = gt.get("menu")
    # CORD often has nm under store / menu header
    for key in ("store", "store_nm", "nm"):
        if key in gt and isinstance(gt[key], str):
            return gt[key]
    if isinstance(gt.get("store"), dict):
        for k in ("nm", "name", "store_nm"):
            if k in gt["store"]:
                return str(gt["store"][k])
    # fallback from first menu item category
    return str(gt.get("store_nm") or gt.get("company") or "Unknown Merchant")


def _date(gt: dict) -> str:
    for key in ("date", "sub_total"):
        block = gt.get(key)
        if isinstance(block, dict) and "date" in block:
            return str(block["date"])
        if key == "date" and isinstance(block, str):
            return block
    return ""


def cord_to_text(gt: dict, image_id: str) -> str:
    """Render a parseable text invoice-like document from CORD ground truth."""
    vendor = _vendor(gt)
    total = _parse_total(gt)
    date = _date(gt)
    lines = [
        vendor,
        f"Vendor: {vendor}",
        f"Invoice Number: CORD-{image_id}",
        f"Invoice Date: {date}" if date else "Invoice Date: 2020-01-01",
        "Currency: USD",
        "",
        "Line items:",
    ]
    menu = gt.get("menu") or []
    if isinstance(menu, list):
        for item in menu[:8]:
            if not isinstance(item, dict):
                continue
            name = item.get("nm") or item.get("name") or "item"
            price = _money(item.get("price") or item.get("unitprice") or 0)
            qty = item.get("cnt") or item.get("num") or 1
            try:
                qty_f = float(qty)
            except (TypeError, ValueError):
                qty_f = 1.0
            amt = price if price else 0.0
            lines.append(f"- {name} | {qty_f} | {amt:.2f} | {amt:.2f}")
    if total <= 0 and len(lines) > 6:
        # sum line amounts
        pass
    subtotal = total
    tax = 0.0
    lines += ["", f"Subtotal: {subtotal:.2f}", f"Tax: {tax:.2f}", f"Total: {total:.2f}"]
    return "\n".join(lines) + "\n"


def load_cord(
    limit: int = 50,
    split: str = "validation",
    cache: bool = True,
) -> list[GoldInvoice]:
    """
    Load CORD-v2 from HuggingFace if available.
    Writes text renders under samples/cord/ for the extractor.
    Returns [] if datasets package or network unavailable.
    """
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        return []

    root = _repo_root()
    out_dir = root / "samples" / "cord"
    gold_dir = root / "evals" / "gold" / "cord"
    if cache and gold_dir.exists() and list(gold_dir.glob("*.json")):
        return _load_cached(gold_dir, limit)

    try:
        ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    except Exception:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    golds: list[GoldInvoice] = []

    for i, row in enumerate(ds):
        if i >= limit:
            break
        # ground_truth may be string JSON
        gt_raw = row.get("ground_truth") or row.get("gt_parse") or "{}"
        if isinstance(gt_raw, str):
            try:
                gt_wrap = json.loads(gt_raw)
            except json.JSONDecodeError:
                continue
        else:
            gt_wrap = gt_raw
        gt = gt_wrap.get("gt_parse") if isinstance(gt_wrap, dict) and "gt_parse" in gt_wrap else gt_wrap
        if not isinstance(gt, dict):
            continue

        image_id = f"{i:04d}"
        text = cord_to_text(gt, image_id)
        rel_sample = f"samples/cord/cord_{image_id}.txt"
        (out_dir / f"cord_{image_id}.txt").write_text(text, encoding="utf-8")

        # also keep image if present
        img = row.get("image")
        if img is not None and hasattr(img, "save"):
            try:
                img.save(out_dir / f"cord_{image_id}.png")
            except Exception:
                pass

        gold = GoldInvoice(
            id=f"cord-{image_id}",
            source="cord",
            sample_path=rel_sample,
            vendor_name=_vendor(gt),
            invoice_number=f"CORD-{image_id}",
            invoice_date=_date(gt) or "2020-01-01",
            total=_parse_total(gt),
            currency="USD",
            meta={"split": split},
        )
        if gold.total <= 0:
            continue
        (gold_dir / f"cord_{image_id}.json").write_text(
            json.dumps(
                {
                    "sample": f"cord/cord_{image_id}.txt",
                    "expected": {
                        "vendor_name": gold.vendor_name,
                        "invoice_number": gold.invoice_number,
                        "invoice_date": gold.invoice_date,
                        "currency": gold.currency,
                        "total": gold.total,
                        "line_items": [],
                    },
                    "id": gold.id,
                    "source": "cord",
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
                source="cord",
                sample_path=f"samples/{raw['sample']}",
                vendor_name=exp["vendor_name"],
                invoice_number=exp.get("invoice_number", ""),
                invoice_date=exp.get("invoice_date", ""),
                total=float(exp["total"]),
                currency=exp.get("currency", "USD"),
            )
        )
        if len(items) >= limit:
            break
    return items
