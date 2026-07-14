"""1.13.7: campaign round 2, pack roster, tutorial modes."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.mission_board import list_visible_missions
from game.domain.quests import complete_quest, ensure_quests
from game.services.combat_session import format_enemy_pack_roster
from game.ui_terminal.help import TUTORIAL_PAGES


def test_round_two_quests_exist():
    reg = DataRegistry.load(DATA_DIR)
    for qid in (
        "second_horizon",
        "void_echo",
        "world_round_two",
        "board_veteran",
    ):
        assert qid in reg.quests
        assert reg.quests[qid].get("campaign")


def test_world_round_two_marks_round():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "R2", "warrior", "เมษ")
    p["quests"] = {"world_round_two": {"progress": 0, "completed": False}}
    notes = complete_quest(p, reg, "world_round_two")
    assert int(p.get("campaign_round") or 0) >= 2
    assert any("รอบ" in n for n in notes)


def test_void_board_chain_gated():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Vb", "vagabond", "เมษ")
    p["mission_rank"] = "A"
    vis = {str(m.get("id")) for m in list_visible_missions(p, reg)}
    assert "board_story_void_1" not in vis
    p["board_missions_done"] = [
        "board_story_city_1",
        "board_story_city_2",
        "board_story_city_3",
        "board_story_road_1",
        "board_story_road_2",
        "board_story_crystal_1",
        "board_story_crystal_2",
    ]
    vis2 = {str(m.get("id")) for m in list_visible_missions(p, reg)}
    assert "board_story_void_1" in vis2


def test_board_complete_backfill_from_mission_completes():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "BF", "vagabond", "เมษ")
    p["level"] = 5
    p["quests_done"] = ["first_blood", "board_regular"]
    p["mission_completes"] = 8
    ensure_quests(p, reg)
    # board_veteran should unlock via deps and backfill
    assert "board_veteran" in (p.get("quests") or {}) or "board_veteran" in (
        p.get("quests_done") or []
    )


def test_pack_roster_lines():
    pack = [
        {"name": "A", "hp": 10, "max_hp": 10},
        {"name": "B", "hp": 5, "max_hp": 10},
        {"name": "C", "hp": 0, "max_hp": 10},
    ]
    lines = format_enemy_pack_roster(pack, current=1)
    assert any("กลุ่ม" in x for x in lines)
    assert any("B" in x for x in lines)
    assert any("ล้ม" in x for x in lines)
    assert any("เลือกเป้า" in x or "พร้อมกัน" in x for x in lines)


def test_tutorial_eight_pages_mode_first():
    # 1.38+: onboarding 8 pages (was 7)
    assert len(TUTORIAL_PAGES) >= 8
    assert "โหมด" in "\n".join(TUTORIAL_PAGES[0])
