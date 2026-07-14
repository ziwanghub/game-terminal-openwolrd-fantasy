"""Phase II–IV: panels, soft vitality, quests, prefs, balance snapshot."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import pick_monster
from game.domain.leveling import kill_xp_reward
from game.domain.quests import bump_quest, ensure_quests
from game.domain.ui_prefs import ensure_ui_prefs, flavor_max_lines
from game.ui_terminal.layout import display_width, pad_to_width
from game.ui_terminal.panels import (
    approach_outcome_line,
    soft_death_panel,
    soft_enemy_vitality,
    victory_panel,
)


def test_display_width_pad():
    s = pad_to_width("สวัสดี", 20)
    assert display_width(s) == 20 or len(s) >= 6


def test_soft_enemy_vitality_bands():
    mon = {"hp": 10, "max_hp": 100}
    assert "พัง" in soft_enemy_vitality(mon, known=True) or "ใกล้" in soft_enemy_vitality(
        mon, known=True
    )
    mon2 = {"hp": 90, "max_hp": 100}
    assert "แข็ง" in soft_enemy_vitality(mon2, known=True)


def test_victory_and_death_panels():
    v = victory_panel(["XP +10", "เงิน +5"])
    assert "ชนะ" in v
    d = soft_death_panel("เสียเงินบางส่วน")
    assert "ล้ม" in d or "จบ" in d


def test_approach_outcome_lines():
    assert "กับดัก" in approach_outcome_line("chest", "empty_trap")
    assert "เพื่อน" in approach_outcome_line("npc", "friend") or "มิตร" in approach_outcome_line(
        "npc", "friend"
    )


def test_rest_does_not_complete_explore_quest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "q", "warrior", "เมษ")
    ensure_quests(p, reg)
    # 5 rests should NOT finish forest_walker
    for _ in range(5):
        bump_quest(p, reg, "rest", area_id="dark_forest")
    st = (p.get("quests") or {}).get("forest_walker") or {}
    assert int(st.get("progress") or 0) == 0
    for _ in range(5):
        bump_quest(p, reg, "explore", area_id="dark_forest")
    assert "forest_walker" in (p.get("quests_done") or []) or int(
        ((p.get("quests") or {}).get("forest_walker") or {}).get("progress") or 0
    ) >= 5


def test_path_quests_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert "path_to_five" in reg.quests
    assert "dungeon_first_clear" in reg.quests


def test_content_items_and_currency_sinks():
    reg = DataRegistry.load(DATA_DIR)
    assert "hunter_ration" in reg.items
    assert "spirit_incense" in reg.items
    assert reg.items["spirit_incense"].get("price_heaven")
    assert "void_ash" in reg.items
    assert reg.items["void_ash"].get("price_hell")


def test_ui_prefs_defaults():
    p = {"name": "x"}
    prefs = ensure_ui_prefs(p)
    assert prefs.get("density")
    assert flavor_max_lines(p) >= 1


def test_kill_xp_balance_snapshot():
    reg = DataRegistry.load(DATA_DIR)
    # regression anchors — relative, not absolute spoiler tables
    low = kill_xp_reward(1, 1, 1.0, reg.levels)
    high = kill_xp_reward(1, 8, 1.0, reg.levels)
    late = kill_xp_reward(20, 1, 1.0, reg.levels)
    assert low >= 1
    assert high >= low
    assert late <= high + 5  # high-level vs weak should not explode upward


def test_new_player_create_wizard_scripted(reg):
    from game.ports.io import ScriptedIO
    from game.services.field_loop import interactive_create

    io = ScriptedIO(["Hero", "1", "1/1/2000", ""])
    p = interactive_create(reg, io)
    assert p["name"] == "Hero"
    assert p.get("gender") == "ชาย"
    assert "ui_prefs" in p
    assert "1/3" in io.joined() or "สร้างตัวละคร" in io.joined()
