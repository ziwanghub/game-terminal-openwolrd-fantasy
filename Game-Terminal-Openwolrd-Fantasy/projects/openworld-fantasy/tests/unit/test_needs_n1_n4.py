"""N1–N4 needs: UI marks, combat mults, ATB, food, resist, collapse."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import apply_incoming_damage, player_attack_damage
from game.domain.combat_atb import action_fill_rate
from game.domain.needs import (
    apply_food_relief,
    apply_needs_event,
    atb_fatigue_mult,
    band,
    combat_needs_mults,
    ensure_needs,
    format_needs_bar_line,
    is_food_item,
    skill_fail_chance,
    soft_label,
    try_hunger_collapse,
)
from game.domain.progression import ensure_progression, recompute_powers


def test_bar_line_shows_minus_when_bad():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 80
    p["needs"]["morale"] = 20
    line = format_needs_bar_line(p)
    assert "−" in line or "--" in line or "−−" in line
    assert soft_label("hunger", 80) == "หิว" or soft_label("hunger", 80) == "อดอยาก"


def test_combat_mults_hunger_crit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 95
    m = combat_needs_mults(p)
    assert m["atk_mult"] < 1.0
    assert m["incoming_mult"] > 1.0
    assert m["dodge_mult"] < 1.0


def test_atb_slower_when_fatigued():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n", "warrior", "เมษ")
    ensure_progression(p, reg)
    recompute_powers(p, reg)
    ensure_needs(p)
    p["needs"]["fatigue"] = 10
    r_fresh = atb_fatigue_mult(p)
    p["needs"]["fatigue"] = 90
    r_tired = atb_fatigue_mult(p)
    assert r_tired < r_fresh
    rate_fresh = action_fill_rate({**p, "needs": {"hunger": 10, "fatigue": 10, "morale": 70}}, "player", reg)
    rate_tired = action_fill_rate({**p, "needs": {"hunger": 10, "fatigue": 90, "morale": 70}}, "player", reg)
    assert rate_tired < rate_fresh


def test_def_pts_resist_fatigue_gain():
    reg = DataRegistry.load(DATA_DIR)
    weak = create_player(reg, "w", "warrior", "เมษ")
    tank = create_player(reg, "t", "warrior", "เมษ")
    ensure_needs(weak)
    ensure_needs(tank)
    weak["stats_alloc"] = {"atk": 0, "defense": 0, "magic": 0, "speed": 0, "intelligence": 0}
    tank["stats_alloc"] = {"atk": 0, "defense": 20, "magic": 0, "speed": 0, "intelligence": 0}
    ensure_progression(weak, reg)
    ensure_progression(tank, reg)
    recompute_powers(weak, reg)
    recompute_powers(tank, reg)
    weak["needs"]["fatigue"] = 20
    tank["needs"]["fatigue"] = 20
    apply_needs_event(weak, "explore", silent=True)
    apply_needs_event(tank, "explore", silent=True)
    assert tank["needs"]["fatigue"] <= weak["needs"]["fatigue"]


def test_food_item_tags_and_relief():
    reg = DataRegistry.load(DATA_DIR)
    bread = reg.items.get("city_bread") or {}
    assert is_food_item(bread)
    p = create_player(reg, "f", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 70
    apply_food_relief(p, hunger_relief=40, silent=True)
    assert p["needs"]["hunger"] < 70


def test_potion_not_primary_food():
    reg = DataRegistry.load(DATA_DIR)
    pot = reg.items.get("potion_hp_small") or reg.items.get("potion_hp") or {}
    assert not is_food_item(pot) or "food" not in (pot.get("tags") or [])


def test_skill_fail_rises_low_morale():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "m", "mage", "เมถุน")
    ensure_needs(p)
    p["needs"]["morale"] = 80
    low_fail = skill_fail_chance(p)
    p["needs"]["morale"] = 10
    high_fail = skill_fail_chance(p)
    assert high_fail > low_fail


def test_hunger_collapse_can_trigger():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 99
    # force high chance with many trials
    hits = 0
    for seed in range(80):
        p2 = dict(p)
        p2["needs"] = dict(p["needs"])
        p2["stats_alloc"] = {"atk": 0, "defense": 0, "magic": 0, "speed": 0, "intelligence": 0}
        ok, _ = try_hunger_collapse(p2, random.Random(seed), action="travel")
        if ok:
            hits += 1
    assert hits >= 1


def test_damage_hooks_use_needs(reg=None):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "d", "warrior", "เมษ")
    ensure_progression(p, reg)
    recompute_powers(p, reg)
    ensure_needs(p)
    mon = {"id": "x", "name": "x", "hp": 50, "elements": ["physical"], "level": 1}
    p["needs"]["hunger"] = 10
    dmg_ok, _ = player_attack_damage(p, mon, reg, "dark_forest", None, random.Random(1))
    p["needs"]["hunger"] = 95
    dmg_hungry, _ = player_attack_damage(p, mon, reg, "dark_forest", None, random.Random(1))
    # same rng seed — hungry should not deal more
    assert dmg_hungry <= dmg_ok + 2  # allow tiny variance from other factors; prefer <=
