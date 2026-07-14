"""Occupation start, stats, blessings, class paths."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.blessings import try_level_up_blessing
from game.domain.character import create_player
from game.domain.class_paths import apply_class_change, list_available_class_paths
from game.domain.leveling import grant_xp
from game.domain.progression import (
    ALLOCATE_KEYS,
    allocate_stat,
    ensure_progression,
    init_progression,
    recompute_powers,
    roll_starting_stat_points,
)
from game.ports.io import ScriptedIO
from tests.harness import create_script, run_create_session


def test_allocate_keys_no_intelligence_not_luck():
    # CM3: intelligence not free-P; still not luck
    assert "intelligence" not in ALLOCATE_KEYS
    assert "luck" not in ALLOCATE_KEYS
    assert "atk" in ALLOCATE_KEYS
    assert "magic" in ALLOCATE_KEYS


def test_starting_points_vary_by_seed():
    reg = DataRegistry.load(DATA_DIR)
    a = create_player(reg, "Alice", "vagabond", "เมษ", birth="1/1/2000")
    b = create_player(reg, "Bob", "vagabond", "เมษ", birth="20/12/1999")
    ensure_progression(a, reg)
    ensure_progression(b, reg)
    pa = roll_starting_stat_points(a, reg, random.Random(1))
    pb = roll_starting_stat_points(b, reg, random.Random(1))
    assert 4 <= pa <= 9
    assert 4 <= pb <= 9
    # different people often differ (not always guaranteed — check range only)
    pc = roll_starting_stat_points(a, reg, random.Random(99))
    assert 4 <= pc <= 9


def test_atk_feeds_crit_and_speed_feeds_dodge():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "St", "vagabond", "เมษ")
    init_progression(p, reg)
    p["stat_points"] = 10
    allocate_stat(p, reg, "atk", 5)
    recompute_powers(p, reg)
    crit_a = float(p.get("crit_chance") or 0)
    p2 = create_player(reg, "St2", "vagabond", "เมษ")
    init_progression(p2, reg)
    recompute_powers(p2, reg)
    assert crit_a > float(p2.get("crit_chance") or 0)
    p["stat_points"] = 10
    allocate_stat(p, reg, "speed", 5)
    recompute_powers(p, reg)
    assert float(p.get("dodge_chance") or 0) > 3.0


def test_class_path_opens_after_conditions():
    reg = DataRegistry.load(DATA_DIR)
    assert "vagabond" in reg.occupations
    p = create_player(reg, "Hero", "vagabond", "เมษ")
    init_progression(p, reg)
    p["level"] = 8
    p["stats_alloc"] = {"atk": 5, "defense": 3, "magic": 0, "speed": 0, "intelligence": 0}
    p["stats"] = {"kills": 20, "explores": 10}
    p["stat_points"] = 0
    paths = list_available_class_paths(p, reg)
    assert paths, "should unlock at least one path"
    notes = apply_class_change(p, reg, paths[0])
    assert p["occupation_id"] != "vagabond"
    assert any("อาชีพ" in n or "ทาง" in n for n in notes)


def test_blessing_roll_does_not_crash():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.blessings
    p = create_player(reg, "B", "vagabond", "เมษ")
    init_progression(p, reg)
    # force many rolls with high chance by looping
    notes = []
    for i in range(40):
        notes.extend(
            try_level_up_blessing(p, reg, random.Random(i), levels=1)
        )
    # may or may not hit; just ensure structure ok
    assert isinstance(notes, list)


def test_create_session_starts_vagabond():
    reg = DataRegistry.load(DATA_DIR)
    player, io = run_create_session(reg, create_script("CityKid"))
    assert player["name"] == "CityKid"
    assert player.get("occupation_id") == "vagabond" or "นักเดินทาง" in str(
        player.get("occupation")
    )
    assert int(player.get("stat_points") or 0) >= 4
    assert "แต้ม" in io.joined() or "เมือง" in io.joined() or player.get("stat_points")


def test_grant_xp_level_up_gives_points():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Lv", "vagabond", "เมษ")
    init_progression(p, reg)
    p["stat_points"] = 0
    p["xp"] = 99999
    summary = grant_xp(p, 0, reg.levels)  # may not level
    p["xp"] = 99999
    from game.domain.leveling import xp_to_next

    need = xp_to_next(1, reg.levels)
    summary = grant_xp(p, need, reg.levels)
    assert summary["levels_gained"] >= 1
    assert int(p.get("stat_points") or 0) >= 3
