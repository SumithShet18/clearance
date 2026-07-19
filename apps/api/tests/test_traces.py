from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.traces import emit_span, read_spans


def test_emit_and_read_spans(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    # re-import path uses settings at module load — write directly via emit after patching dir
    from app.services import traces as tr

    tr._TRACE_DIR = tmp_path / "traces"
    emit_span("case-1", "ingest", "completed", "ok", {"chars": 10})
    emit_span("case-1", "extract", "completed", "done")
    spans = read_spans("case-1")
    # read_spans uses module _TRACE_DIR
    assert len(spans) >= 2
    assert spans[0]["name"] == "ingest"
