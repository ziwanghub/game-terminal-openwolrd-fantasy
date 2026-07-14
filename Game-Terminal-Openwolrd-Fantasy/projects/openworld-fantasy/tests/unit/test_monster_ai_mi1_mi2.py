"""MI1 smart profile pick · MI2 soft flee for elite/high intel monsters."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.boss import spawn_boss
from game.domain.combat import pick_monster, pick_monster_attack
from game.domain.monster_ai import (
    resolve_monster_intel_tier,
    score_attack_profiles,
    try_monster_flee,
)


def test_elite_gets_intel_tier_from_yaml_or_flag():
    reg = DataRegistry.load(DATA_DIR)
    mon = pick_monster(reg, "dark_forest", random.Random(11))
    # force an elite catalog entry if pool missed
    elite = dict(reg.monsters["elite_forest_alpha_wolf"])
    elite["hp"] = 100
    elite["max_hp"] = 100
    elite["atk"] = 16
    elite["attack_profiles"] = list(elite.get("attack_profiles") or [])
    assert resolve_monster_intel_tier(elite) >= 2
    assert elite.get("can_flee") is True or elite.get("elite") is True


def test_boss_never_flees_and_high_intel():
    reg = DataRegistry.load(DATA_DIR)
    boss = spawn_boss(reg, "dark_forest", random.Random(2))
    assert boss is not None
    assert resolve_monster_intel_tier(boss) >= 3
    assert boss.get("never_flee") or boss.get("boss")
    boss["hp"] = 1
    boss["max_hp"] = 200
    player = {"level": 99, "hp": 100, "max_hp": 100}
    fled, _ = try_monster_flee(boss, player, random.Random(0))
    assert fled is False


def test_mi1_prefers_finisher_when_player_low_hp():
    profiles = [
        {"id": "soft", "tags": ["physical"], "telegraph": "เบา", "power": 5},
        {"id": "heavy", "tags": ["physical"], "telegraph": "หนัก", "power": 22},
    ]
    mon_base = {
        "id": "t_elite",
        "elite": True,
        "intel_tier": 2,
        "atk": 10,
        "hp": 80,
        "max_hp": 100,
        "attack_profiles": profiles,
    }
    player = {"hp": 8, "max_hp": 100, "level": 5, "statuses": []}
    weights = score_attack_profiles(mon_base, profiles, player)
    assert weights[1] > weights[0]

    heavy = soft = 0
    for seed in range(80):
        # fresh mon each roll so variety penalty does not flip-flop samples
        mon = dict(mon_base)
        mon["attack_profiles"] = list(profiles)
        p = pick_monster_attack(mon, random.Random(seed), player=player)
        if p.get("id") == "heavy":
            heavy += 1
        else:
            soft += 1
    assert heavy > soft
    assert heavy >= 50  # clear bias toward finisher


def test_mi1_prefers_status_when_player_clean():
    mon = {
        "elite": True,
        "intel_tier": 2,
        "atk": 12,
        "hp": 50,
        "max_hp": 100,
        "attack_profiles": [
            {"id": "raw", "tags": ["physical"], "telegraph": "ตี", "power": 14},
            {
                "id": "venom",
                "tags": ["nature"],
                "telegraph": "พิษ",
                "power": 11,
                "status": "poison",
                "status_chance": 0.3,
            },
        ],
    }
    clean = {"hp": 70, "max_hp": 100, "level": 5, "statuses": []}
    dirty = {"hp": 70, "max_hp": 100, "level": 5, "statuses": [{"id": "poison"}]}
    w_clean = score_attack_profiles(mon, mon["attack_profiles"], clean)
    w_dirty = score_attack_profiles(mon, mon["attack_profiles"], dirty)
    assert w_clean[1] > w_clean[0]
    assert w_clean[1] >= w_dirty[1]


def test_mi1_random_when_no_player_context():
    mon = {
        "elite": True,
        "intel_tier": 2,
        "atk": 10,
        "attack_profiles": [
            {"id": "a", "power": 5, "telegraph": "a", "tags": ["physical"]},
            {"id": "b", "power": 50, "telegraph": "b", "tags": ["physical"]},
        ],
    }
    # without player, still returns a valid profile
    p = pick_monster_attack(mon, random.Random(1), player=None)
    assert p.get("id") in ("a", "b")


def test_mi2_elite_can_flee_when_low_hp():
    mon = {
        "id": "e1",
        "name": "ทดสอบเอลีท",
        "elite": True,
        "intel_tier": 2,
        "can_flee": True,
        "level": 5,
        "hp": 8,
        "max_hp": 100,
    }
    player = {"level": 10, "hp": 90, "max_hp": 100}
    # many seeds: at least some flees, never all (chance capped)
    flees = 0
    for seed in range(60):
        m = dict(mon)
        fled, msg = try_monster_flee(m, player, random.Random(seed))
        if fled:
            flees += 1
            assert msg
            assert m.get("_escaped")
            # second attempt blocked
            fled2, _ = try_monster_flee(m, player, random.Random(seed + 99))
            assert fled2 is False
    assert flees >= 8
    assert flees < 60


def test_mi2_dumb_beast_no_flee():
    mon = {
        "id": "slime",
        "name": "สไลม์",
        "level": 2,
        "hp": 2,
        "max_hp": 40,
        "rarity": "common",
    }
    assert resolve_monster_intel_tier(mon) == 0
    fled, _ = try_monster_flee(mon, {"level": 20, "hp": 100, "max_hp": 100}, random.Random(1))
    assert fled is False


def test_pick_monster_attaches_intel_on_elite_area():
    reg = DataRegistry.load(DATA_DIR)
    # mountain has ridge_reaver elite
    found_elite = None
    for seed in range(40):
        mon = pick_monster(reg, "mountain_rock", random.Random(seed))
        if mon.get("elite") or str(mon.get("id", "")).startswith("elite_"):
            found_elite = mon
            break
    if found_elite is None:
        # direct catalog path still ok
        base = reg.monsters["ridge_reaver"]
        assert base.get("elite")
        assert int(base.get("intel_tier") or 0) >= 2
        return
    assert resolve_monster_intel_tier(found_elite) >= 2
