"""Onboarding H/T, city tips, ui_prefs menu U, victory panel full lines."""
from __future__ import annotations

from game.domain.ui_prefs import (
    cycle_pref,
    ensure_ui_prefs,
    prefs_menu_lines,
)
from game.ports.io import ScriptedIO
from game.ui_terminal.help import (
    CITY_ONBOARD_TIPS,
    HELP_LINES,
    TUTORIAL_PAGES,
    maybe_onboarding_tip,
    show_help,
    show_tutorial,
)
from game.ui_terminal.panels import victory_panel


def _blob() -> str:
    return "\n".join("\n".join(p) for p in TUTORIAL_PAGES) + "\n" + "\n".join(HELP_LINES)


def test_tutorial_mode_shell_pages():
    assert len(TUTORIAL_PAGES) >= 7
    blob = _blob()
    for key in (
        "โหมด",
        "ตัวละคร",
        "ร้าน",
        "ATB",
        "แท่ง",
        "ตลาด",
        "กระดาน",
        "สติ",
        "sw001",
        "5 หรือ I",
    ):
        assert key in blob, f"missing onboarding keyword: {key}"


def test_help_mentions_market_board_modes():
    h = "\n".join(HELP_LINES)
    assert "M" in h and "ตลาด" in h
    assert "J" in h and "กระดาน" in h
    assert "สำรวจ" in h and "ร้าน" in h


def test_show_tutorial_scripted_pages():
    # 7 pages → 7 Enter
    io = ScriptedIO([""] * 10)
    show_tutorial(io)
    out = io.joined()
    assert "บทเรียน 1/" in out
    assert "บทเรียน 7/" in out or "โหมด" in out


def test_show_help_scripted():
    io = ScriptedIO([""])
    show_help(io)
    assert "ช่วยเหลือ" in io.joined() or "H" in io.joined()


def test_onboarding_tip_progresses():
    p = {
        "tutorial_done": True,
        "time_units": 2,
        "level": 1,
        "onboard_tip_index": 0,
        "location": "ancient_city",
    }
    io = ScriptedIO([])
    tip = maybe_onboarding_tip(p, io, area_id="ancient_city")
    assert tip
    assert p["onboard_tip_index"] == 1
    # wrong tick → no tip
    p["time_units"] = 3
    assert maybe_onboarding_tip(p, io, area_id="ancient_city") is None
    # exhaust tips
    p["onboard_tip_index"] = len(CITY_ONBOARD_TIPS)
    p["time_units"] = 5
    assert maybe_onboarding_tip(p, io, area_id="ancient_city") is None


def test_ui_prefs_menu_cycle():
    p: dict = {}
    ensure_ui_prefs(p)
    lines = prefs_menu_lines(p)
    assert any("ตั้งค่า" in x for x in lines)
    note = cycle_pref(p, 1)
    assert note
    assert p["ui_prefs"]["density"] in ("compact", "standard", "full")
    assert cycle_pref(p, 99) is None


def test_victory_panel_keeps_all_lines():
    lines = [f"line{i}" for i in range(10)]
    panel = victory_panel(lines, title="ชนะ")
    for i in range(10):
        assert f"line{i}" in panel


def test_wage_ratio_soft_band():
    """wage_cost roughly 25–45% of reward_money for sustainability."""
    from game.config import DATA_DIR
    from game.data_load.registry import DataRegistry

    reg = DataRegistry.load(DATA_DIR)
    board = getattr(reg, "mission_board", None) or {}
    missions = list(board.get("missions") or [])
    assert missions
    for m in missions:
        reward = int(m.get("reward_money") or 0)
        wage = int(m.get("wage_cost") or 0)
        if reward <= 0:
            continue
        ratio = wage / reward
        assert 0.2 <= ratio <= 0.5, f"{m.get('id')} wage ratio {ratio:.2f}"
