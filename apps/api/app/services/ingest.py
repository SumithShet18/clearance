"""Document intake: text, PDF text-layer, images (vision or HITL shell)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_text_from_pdf(path: Path) -> tuple[str, dict[str, Any]]:
    """Extract text layer from PDF. Empty body → scanned PDF needs human/vision."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return (
            f"[PDF upload: {path.name}]\n"
            "pypdf not installed — cannot extract text layer.\n",
            {"mode": "pdf_missing_dep", "pages": 0, "chars": 0},
        )

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001
        return (
            f"[PDF unreadable: {path.name}]\nError: {exc}\n",
            {"mode": "pdf_error", "error": str(exc), "pages": 0, "chars": 0},
        )

    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            t = ""
        if t.strip():
            parts.append(t.strip())
        else:
            parts.append(f"[page {i + 1}: no text layer]")

    text = "\n\n".join(parts).strip()
    meta = {
        "mode": "pdf_text",
        "pages": len(reader.pages),
        "chars": len(text),
    }
    if not text or len(text) < 20 or text.count("[page") == len(reader.pages):
        text = (
            f"[Scanned or empty PDF: {path.name}]\n"
            f"Pages: {len(reader.pages)}. No usable text layer found.\n"
            "Enter fields manually in review, or set CLEARANCE_MODE=llm + OPENAI_API_KEY for vision.\n"
        )
        meta["mode"] = "pdf_empty"
    return text, meta


def load_upload(
    path: Path,
    filename: str,
    raw: bytes,
) -> tuple[str, dict[str, Any], bool]:
    """
    Return (content_text, meta, is_image).
    is_image True when vision extractor should run first.
    """
    lower = filename.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "", {"mode": "image_pending"}, True

    if lower.endswith(".pdf"):
        text, meta = extract_text_from_pdf(path)
        return text, meta, False

    # plain text / csv
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    return text, {"mode": "text", "chars": len(text)}, False
