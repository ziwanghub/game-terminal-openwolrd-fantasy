"""WO-011: Playtest Auto Run logger + end-of-run summary + Test Run hub."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.mode_shell import MODE_PERSONAL, render_mode_actions
from game.domain.needs import ensure_needs
from game.ports.io import ScriptedIO
from game.runtime.auto_farm import run_auto_farm
from game.runtime.auto_run_log import (
    finish_auto_run,
    format_auto_run_summary,
    format_god_compact_status,
    format_policy_status_line,
    is_god_compact,
    log_auto_event,
    observe_auto_lines,
    run_playtest_hub,
    set_god_compact,
    start_auto_run,
)


def test_start_finish_summary_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pt1", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 40, "fatigue": 55, "morale": 60}
    start_auto_run(p, kind="field", label="Field Auto", max_ticks=12)
    log_auto_event(p, "eat", "กินเสบียงประทังหิว")
    observe_auto_lines(p, ["  ออโต้: พักครู่", "ออโต้ชนะ Wolf · XP +3"])
    # manual bumps if heuristics miss
    sess = p["_auto_run"]
    assert sess["active"] is True
    lines = finish_auto_run(p, "done", reg=reg)
    text = "\n".join(lines)
    assert "สรุป Auto Run" in text
    assert "รอด" in text or "ผล" in text
    assert "กายใจ" in text or "หิว" in text
    assert p.get("_auto_run_last")
    assert p["_auto_run"]["active"] is False


def test_summary_stop_reasons():
    p = {
        "hp": 10,
        "max_hp": 100,
        "needs": {"hunger": 90, "fatigue": 20, "morale": 20},
        "_auto_run": {
            "active": True,
            "kind": "field",
            "label": "t",
            "started_unix": 1.0,
            "ticks": 5,
            "eats": 1,
            "rests": 0,
            "potions": 0,
            "fights": 2,
            "avoids": 1,
            "events": [],
        },
    }
    import time

    p["_auto_run"]["started_unix"] = time.time() - 30
    lines = finish_auto_run(p, "morale")
    text = "\n".join(lines)
    assert "ขวัญ" in text or "retreat" in text.lower() or "หยุด" in text


def test_god_compact_and_policy_line():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pt2", "mage", "เมถุน")
    ensure_needs(p)
    p["needs"] = {"hunger": 30, "fatigue": 70, "morale": 25}
    set_god_compact(p, True)
    assert is_god_compact(p)
    line = format_god_compact_status(p, "ป่ามืด", reg=reg, tick=3, max_ticks=12)
    assert "กายใจ" in line or "หิว" in line
    assert "HP" in line
    pol = format_policy_status_line(p, reg)
    assert "Policy" in pol or "Caution" in pol or "caution" in pol.lower() or "→" in pol


def test_personal_menu_has_test_run():
    text = render_mode_actions(MODE_PERSONAL)
    assert "Test Run" in text or "X" in text


def test_field_auto_emits_summary():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pt3", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["location"] = "dark_forest"
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 70}
    p["auto_prefs"] = {
        "low_morale_policy": "caution",
        "hunger": 80,
        "fatigue": 85,
        "hp_pct": 15,
        "mp_pct": 5,
        "skill_plan": [1],
    }
    # continuous; may pause on risk — feed skip/stop answers generously
    answers = ["2"] * 20 + ["s"] * 5 + [""] * 20
    io = ScriptedIO(answers, raise_on_empty=False)
    reason, _ = run_auto_farm(
        p, reg, io, random.Random(11), max_ticks=5, continuous=True
    )
    out = io.joined()
    assert reason in ("done", "stop", "hp", "food", "morale", "pause", "time")
    assert "สรุป Auto Run" in out
    assert p.get("_auto_run_last")


def test_playtest_hub_exit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pt4", "rogue", "พิจิก")
    ensure_needs(p)
    io = ScriptedIO(["5", "", "0"])  # view summary (empty), exit
    run_playtest_hub(p, reg, io, area_name="ป่ามืด")
    out = io.joined()
    assert "Playtest" in out or "Test Run" in out
