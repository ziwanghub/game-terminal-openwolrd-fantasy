"""WO-030: human feedback polish — burden floor, quest hints, equip tip."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.divine_burden import apply_burden_tick
from game.domain.equipment import equip_item
from game.domain.needs import ensure_needs, get_needs
from game.domain.quests import list_quest_lines, ensure_quests
from game.runtime.auto_run_log import format_auto_run_summary, start_auto_run
from game.services.godforge_chamber import format_chamber_burden_summary, enter_godforge


def test_burden_soft_floor_not_instant_zero():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w030a", "warrior", "เมษ")
    p["level"] = 2
    ensure_needs(p)
    p["needs"]["morale"] = 40
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    for i in range(5):
        p["auto_ticks"] = i + 1
        apply_burden_tick(p, reg, context="field", rng=random.Random(i))
    assert int(get_needs(p)["morale"]) >= 8


def test_first_relic_equip_tip():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w030b", "warrior", "เมษ")
    p["level"] = 1
    p["inventory_ids"] = ["relic_storm_fang"]
    p["inventory_rarities"] = ["legendary"]
    p["inventory"] = ["x"]
    msg = equip_item(p, "relic_storm_fang", reg)
    assert "ครั้งแรก" in msg or "เรลิก" in msg


def test_quest_list_shows_soft_hint():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w030c", "warrior", "เมษ")
    ensure_quests(p, reg)
    # force active forest echoes if possible
    p["quests"] = {
        "forest_echoes_hunt": {"progress": 1, "completed": False},
    }
    p["quests_done"] = ["forest_walker", "first_blood"]
    lines = list_quest_lines(p, reg)
    blob = "\n".join(lines)
    # soft_hint line if quest active
    assert "เสียงในพุ่ม" in blob or "forest" in blob.lower() or "พุ่ม" in blob


def test_god_summary_unequipped_wording():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w030d", "warrior", "เมษ")
    ensure_needs(p)
    start_auto_run(p, kind="field", label="t", max_ticks=3)
    p["_auto_run"]["active"] = False
    p["_auto_run"]["ticks"] = 3
    p["_auto_run"]["burden_unequips"] = 2
    p["_burden_drain_total"] = 5
    p["_auto_run_last"] = dict(p["_auto_run"])
    lines = format_auto_run_summary(p, reg, reason="done")
    blob = "\n".join(lines)
    assert "ภาระ" in blob
    assert "ถอด" in blob or "เคยกด" in blob


def test_chamber_summary_has_recommend():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w030e", "warrior", "เมษ")
    ensure_needs(p)
    enter_godforge(p, reg)
    lines = format_chamber_burden_summary(p, reg)
    blob = "\n".join(lines)
    assert "แนะนำ" in blob or "สรุป" in blob
