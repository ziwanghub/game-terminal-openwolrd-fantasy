"""WO-016: God measurement — multi-run history archive."""
from __future__ import annotations

from game.ports.io import ScriptedIO
from game.runtime.auto_run_log import (
    emit_auto_run_summary,
    format_playtest_history,
    start_auto_run,
)


def test_emit_archives_playtest_history():
    p: dict = {
        "hp": 50,
        "max_hp": 100,
        "needs": {"hunger": 30, "fatigue": 30, "morale": 60},
    }
    start_auto_run(p, kind="field", label="Field Auto", max_ticks=5)
    p["_auto_run"]["ticks"] = 5
    p["_auto_run"]["fights"] = 2
    p["_auto_run"]["eats"] = 1
    io = ScriptedIO([])
    emit_auto_run_summary(p, io, "done")
    assert p.get("_playtest_run_history")
    assert len(p["_playtest_run_history"]) == 1
    hist = format_playtest_history(p)
    text = "\n".join(hist)
    assert "Playtest" in text or "History" in text or "รัน" in text
    assert "Field" in text or "field" in text.lower() or "ติก" in text
