"""Lightweight agent observability — JSONL spans (Langfuse-compatible shape-ish)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

_TRACE_DIR = Path(settings.upload_dir).resolve().parent / "traces"


def _path(case_id: str) -> Path:
    _TRACE_DIR.mkdir(parents=True, exist_ok=True)
    return _TRACE_DIR / f"{case_id}.jsonl"


def emit_span(
    case_id: str,
    name: str,
    status: str,
    detail: str = "",
    data: dict[str, Any] | None = None,
    tokens: int = 0,
    cost_usd: float = 0.0,
) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "name": name,
        "status": status,
        "detail": detail,
        "tokens": tokens,
        "cost_usd": cost_usd,
        "data_keys": list((data or {}).keys()),
    }
    # keep payload small — store small data only
    if data and len(json.dumps(data, default=str)) < 2000:
        rec["data"] = data
    with _path(case_id).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def read_spans(case_id: str) -> list[dict[str, Any]]:
    p = _path(case_id)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
