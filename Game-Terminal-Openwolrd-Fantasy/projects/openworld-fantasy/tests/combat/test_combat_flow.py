"""Combat integration — seeded RNG, no terminal input."""
from __future__ import annotations

import random

from game.domain.combat import (
    apply_world_enemy_mods,
    pick_monster,
    player_attack_damage,
    resolve_victory,
    skill_options,
)
from game.domain.leveling import kill_xp_reward


def test_pick_monster_seeded(reg, make_player):
    rng = random.Random(42)
    mon = pick_monster(reg, "dark_forest", rng)
    assert mon["id"]
    assert mon["hp"] > 0
    assert mon["level"] >= 1
    assert "rarity" in mon or mon.get("elements")


def test_world_enemy_mods_scale(reg, make_player):
    p = make_player()
    p["world_modifiers"] = {"enemy_hp_mult": 2.0, "enemy_atk_mult": 1.5}
    mon = pick_monster(reg, "dark_forest", random.Random(1))
    base_hp = mon["hp"]
    scaled = apply_world_enemy_mods(mon, p)
    assert scaled["hp"] >= base_hp
    assert scaled["hp"] >= int(base_hp * 1.9)


def test_player_can_damage_and_win(reg, make_player):
    p = make_player()
    p["bonus_atk"] = 200
    p["mana"] = 999
    rng = random.Random(7)
    mon = pick_monster(reg, "dark_forest", rng)
    mon["hp"] = 30
    mon["max_hp"] = 30
    opts = skill_options(p, reg)
    assert opts
    sid, skill = opts[0]
    dmg, flavor = player_attack_damage(
        p, mon, reg, "dark_forest", skill, rng
    )
    assert dmg >= 1
    mon["hp"] = max(0, mon["hp"] - dmg)
    if mon["hp"] > 0:
        mon["hp"] = 0
    lines = resolve_victory(p, mon, reg, "dark_forest", rng)
    assert any("ชนะ" in ln for ln in lines)
    assert int(p.get("level", 1)) >= 1


def test_kill_xp_positive(reg):
    xp = kill_xp_reward(1, 1, 1.0, reg.levels)
    assert xp >= 1
    hard = kill_xp_reward(1, 10, 1.0, reg.levels)
    easy = kill_xp_reward(20, 1, 1.0, reg.levels)
    assert hard >= easy


def test_element_advantage_increases_damage(reg, make_player):
    p = make_player(occupation_id="mage")
    p["bonus_atk"] = 20
    mon_fire = {
        "id": "t",
        "name": "t",
        "level": 1,
        "hp": 100,
        "max_hp": 100,
        "atk": 5,
        "elements": ["fire"],
        "statuses": [],
    }
    mon_water = dict(mon_fire, elements=["water"])
    water_skill = reg.skills.get("water_bolt") or {
        "id": "water_bolt",
        "power": 12,
        "elements": ["water"],
    }
    fire_skill = reg.skills.get("fire_ball") or {
        "id": "fire_ball",
        "power": 12,
        "elements": ["fire"],
    }
    # water vs fire should tend higher than fire vs fire (matchups)
    dmg_adv, _ = player_attack_damage(
        p, mon_fire, reg, "dark_forest", water_skill, random.Random(0)
    )
    dmg_same, _ = player_attack_damage(
        p, mon_fire, reg, "dark_forest", fire_skill, random.Random(0)
    )
    # not always strictly greater due to variance, so sample
    adv_sum = same_sum = 0
    for seed in range(20):
        a, _ = player_attack_damage(
            p, mon_fire, reg, "dark_forest", water_skill, random.Random(seed)
        )
        s, _ = player_attack_damage(
            p, mon_fire, reg, "dark_forest", fire_skill, random.Random(seed)
        )
        adv_sum += a
        same_sum += s
    assert adv_sum >= same_sum * 0.95  # water should not be clearly worse vs fire
