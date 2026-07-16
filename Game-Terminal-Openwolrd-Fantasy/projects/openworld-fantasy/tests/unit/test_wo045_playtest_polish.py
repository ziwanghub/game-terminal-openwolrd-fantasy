"""WO-045 playtest polish smoke."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.faction_moments import roll_faction_moment_sight
from game.domain.relic_anima import (
    BOND_CHORUS,
    evaluate_relic_bonds,
    on_relic_equip_depth,
)
from game.domain.soft_foresight import area_world_gaze_lines
from game.domain.stat_arch import ensure_stat_arch
import random


def test_brief_gaze_shorter_than_full():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "p45a", "warrior", "เมษ")
    ensure_stat_arch(p)
    full = area_world_gaze_lines(p, reg, area_id="void_rift", force=True)
    brief = area_world_gaze_lines(
        p, reg, area_id="void_rift", brief=True, include_moment_hint=True
    )
    assert full
    assert brief
    assert len(brief) <= len(full)


def test_brief_gaze_throttles_same_tick():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "p45b", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["auto_ticks"] = 5
    a = area_world_gaze_lines(p, reg, area_id="mountain_rock", brief=True)
    b = area_world_gaze_lines(p, reg, area_id="mountain_rock", brief=True)
    assert a
    assert b == []  # throttled


def test_multi_equip_prefers_bond_text():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "p45c", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["anima"] = 45.0
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
    }
    p["equip_rarities"] = {k: "legendary" for k in p["equip_ids"]}
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_CHORUS
    lines = on_relic_equip_depth(
        p, reg, item_id="relic_divine_laurel", item_name="พวงหรีด", tags=["holy"]
    )
    blob = "\n".join(lines)
    # should mention chorus/bond/เรโซ/คณะ more than triple lean dump
    assert lines
    assert "Chorus" in blob or "เรโซ" in blob or "คณะ" in blob or "bond" in blob.lower() or "เทพ" in blob


def test_moment_first_sight_higher_chance_smoke():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "p45d", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["_faction_moments_seen"] = 0
    hits = 0
    for i in range(80):
        if roll_faction_moment_sight(p, random.Random(i + 7), area_id="void_rift"):
            hits += 1
    # with ~28% over 80 rolls expect some hits
    assert hits >= 5
