"""Mode Shell Phase A — explore short menu + PERSONAL hub."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.mode_shell import (
    MODE_COMBAT,
    MODE_EXPLORE,
    MODE_PERSONAL,
    active_mission_line,
    money_summary_lines,
    render_mode_actions,
)
from game.ports.io import ScriptedIO
from game.services.personal_hub import run_personal_hub
from game.ui_terminal.status import render_field_actions


def test_explore_actions_short_and_personal_entry():
    text = render_mode_actions(MODE_EXPLORE, stat_points=3, personality_points=1)
    assert "สำรวจ" in text or "พัก" in text
    assert "ตัวละคร" in text or "I" in text
    assert "1" in text and "พัก" in text
    assert "ร้าน" in text  # Phase B: 6 shop
    assert "ทำอะไรต่อ" in text
    # sectioned box — keep reasonably compact
    assert text.count("\n") <= 20


def test_field_actions_delegates_to_explore():
    t = render_field_actions(stat_points=2, boss_line="☠ บอส")
    assert "พัก" in t
    assert "ตัวละคร" in t or "I" in t


def test_personal_actions_menu():
    t = render_mode_actions(
        MODE_PERSONAL,
        stat_points=1,
        money_world=150,
        mission_line=" กระดาน: ทดสอบ",
    )
    assert "กระเป๋า" in t
    assert "ภารกิจ" in t
    # money lives on hub frame now — menu is actions-only
    assert "เมนูตัวละคร" in t or "1" in t


def test_combat_actions_no_travel():
    t = render_mode_actions(MODE_COMBAT)
    assert "โจมตี" in t
    assert "เดินทาง" not in t


def test_personal_hub_status_and_exit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ModeHero", "vagabond", "เมษ")
    p["stat_points"] = 2
    p["money_world"] = 99
    # 1 = full status (Enter), 5 = money (Enter), 0 = back
    io = ScriptedIO(["1", "", "5", "", "0"])
    run_personal_hub(p, reg, io, area_name="เมืองโบราณ")
    out = io.joined()
    assert "ตัวละคร" in out or "PERSONAL" in out or "สถานะ" in out
    assert "99" in out or "เงิน" in out


def test_personal_hub_points_alias():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Pts", "vagabond", "เมษ")
    p["stat_points"] = 1
    # 6 → 1 allocate → atk → 1 pt → Enter (no pts left) → 0 personal
    io = ScriptedIO(["6", "1", "1", "1", "", "0"])
    run_personal_hub(p, reg, io, area_name="x")
    assert int(p.get("stat_points") or 0) == 0


def test_money_and_mission_helpers():
    p = {
        "money_world": 10,
        "money_heaven": 1,
        "money_hell": 0,
        "board_mission": {"name": "ลาดตระเวน", "rank": "F"},
        "mission_rank": "F",
    }
    assert "ลาดตระเวน" in active_mission_line(p)
    lines = money_summary_lines(p)
    assert any("10" in x for x in lines)


def test_field_open_personal_via_i(reg, make_player, monkeypatch, tmp_path):
    from tests.harness import field_exit_script, isolated_saves, run_field_session

    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="IHub")
    p["tutorial_done"] = True
    # I → personal → 0 back → 0 exit field
    io = run_field_session(p, reg, field_exit_script("I", "0"))
    assert "ตัวละคร" in io.joined() or "PERSONAL" in io.joined() or "กระเป๋า" in io.joined()


def test_shop_hub_exit():
    from game.services.shop_hub import run_shop_hub

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Shopper", "vagabond", "เมษ")
    p["location"] = "ancient_city"
    io = ScriptedIO(["0"])
    run_shop_hub(p, reg, io, area_name="เมืองโบราณ")
    assert "ร้าน" in io.joined()


def test_field_open_shop_via_6(reg, make_player, monkeypatch, tmp_path):
    from tests.harness import field_exit_script, isolated_saves, run_field_session

    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="Shop6")
    p["tutorial_done"] = True
    p["location"] = "ancient_city"
    io = run_field_session(p, reg, field_exit_script("6", "0"))
    assert "ร้าน" in io.joined()


def test_starter_city_sights_softer():
    import random
    from game.domain.encounters import build_sights

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Town", "vagabond", "เมษ")
    p["location"] = "ancient_city"
    p["level"] = 1
    high = 0
    for seed in range(30):
        sights = build_sights(p, reg, random.Random(seed))
        mons = [s for s in sights if s.get("kind") == "monster"]
        assert len(mons) <= 2
        for s in mons:
            lv = int((s.get("monster") or {}).get("level") or 1)
            if lv >= 5:
                high += 1
    # most draws should not be high-level knights
    assert high < 20


def test_combat_menu_uses_mode_shell():
    from game.domain.mode_shell import MODE_COMBAT, render_mode_actions

    t = render_mode_actions(MODE_COMBAT)
    assert "โจมตี" in t
    assert "สติ" in t or "6" in t
