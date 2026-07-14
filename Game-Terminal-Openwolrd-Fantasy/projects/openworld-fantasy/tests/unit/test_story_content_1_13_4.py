"""1.13.4: story quests, content items, field_actions, combat waves."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.mission_board import list_visible_missions
from game.domain.quests import bump_quest, complete_quest, ensure_quests, list_quest_lines
from game.ports.io import ScriptedIO


def test_new_campaign_quests_loaded():
    reg = DataRegistry.load(DATA_DIR)
    for qid in (
        "city_roots",
        "crystal_path",
        "desert_trial",
        "world_round_clear",
        "board_regular",
    ):
        assert qid in reg.quests, qid
        assert reg.quests[qid].get("campaign")


def test_new_content_items():
    reg = DataRegistry.load(DATA_DIR)
    for iid in (
        "traveler_ration",
        "city_map_scrap",
        "crystal_dust",
        "round_token",
        "bronze_charm",
        "herb_bundle",
    ):
        assert iid in reg.items, iid


def test_board_story_crystal_chain_gated():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ch", "vagabond", "เมษ")
    p["mission_rank"] = "B"
    vis = {str(m.get("id")) for m in list_visible_missions(p, reg)}
    assert "board_story_crystal_1" not in vis
    p["board_missions_done"] = [
        "board_story_city_1",
        "board_story_city_2",
        "board_story_city_3",
        "board_story_road_1",
        "board_story_road_2",
    ]
    vis2 = {str(m.get("id")) for m in list_visible_missions(p, reg)}
    assert "board_story_crystal_1" in vis2


def test_board_complete_quest_bumps():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "bq", "vagabond", "เมษ")
    p["level"] = 3
    p["quests_done"] = ["first_blood"]
    ensure_quests(p, reg)
    assert "board_regular" in (p.get("quests") or {})
    notes = bump_quest(p, reg, "board_complete")
    notes += bump_quest(p, reg, "board_complete")
    notes += bump_quest(p, reg, "board_complete")
    assert "board_regular" in (p.get("quests_done") or []) or any(
        "ลูกจ้าง" in n or "กระดาน" in n for n in notes
    )


def test_campaign_round_on_complete():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rnd", "warrior", "เมษ")
    p["quests"] = {"world_round_clear": {"progress": 0, "completed": False}}
    notes = complete_quest(p, reg, "world_round_clear")
    assert p.get("campaign_round") == 1
    assert any("รอบ" in n for n in notes)
    lines = list_quest_lines(p, reg)
    assert any("รอบ" in x for x in lines)


def test_field_actions_rest_scripted():
    from game.services.field_actions import do_rest

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fr", "vagabond", "เมษ")
    p["hp"] = 10
    p["max_hp"] = 100
    io = ScriptedIO([])
    do_rest(p, reg, io, random.Random(1), area_id="ancient_city")
    assert int(p["hp"]) > 10
    assert "พัก" in io.joined()


def test_combat_wave_two_foes_smoke():
    from game.services.combat_session import run_combat_wave

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "wv", "warrior", "เมษ")
    p["hp"] = 500
    p["max_hp"] = 500
    p["mana"] = 200
    p["max_mana"] = 200
    p["level"] = 10
    p["bonus_atk"] = 80
    # flee each fight immediately if needed — script attack spam
    # ScriptedIO: each player turn needs choice. Use high atk and many "1" attacks
    # plus empty for any extra prompts; flee "4" if stuck
    inputs = ["1"] * 80 + ["4", "1"] * 10
    io = ScriptedIO(inputs)
    mon = {
        "id": "slime_weak",
        "name": "สไลม์อ่อน",
        "level": 1,
        "hp": 8,
        "max_hp": 8,
        "atk": 1,
        "elements": ["physical"],
        "xp_mult": 0.5,
        "attack_profiles": [{"telegraph": "พุ่ง", "power": 0.5}],
        "statuses": [],
    }
    mon2 = dict(mon)
    mon2["id"] = "slime_weak2"
    mon2["name"] = "สไลม์อ่อน 2"
    run_combat_wave(
        p,
        reg,
        io,
        random.Random(2),
        monsters=[mon, mon2],
        ambush=False,
    )
    out = io.joined()
    assert "กลุ่ม" in out or "ตัวที่" in out or "ชนะ" in out or int(p.get("hp") or 0) > 0
