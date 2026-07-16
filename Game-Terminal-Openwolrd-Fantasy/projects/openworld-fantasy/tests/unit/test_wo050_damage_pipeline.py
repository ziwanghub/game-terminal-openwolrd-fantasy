"""WO-050 Damage Pipeline v1 + Grade Soft Mult."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import apply_incoming_damage, monster_raw_damage, player_attack_damage
from game.domain.damage_pipeline import (
    DamageResult,
    grade_inbound_mult,
    grade_outbound_mult,
    resolve_monster_outbound,
    resolve_player_inbound,
    resolve_player_outbound,
)
from game.domain.progression import ensure_progression
from game.domain.stat_grades import AXIS_KEYS


def _base_player(reg, name="p50"):
    p = create_player(reg, name, "warrior", "เมษ")
    ensure_progression(p, reg)
    p["area_mastery"] = {"dark_forest": 40}
    p["bonus_atk"] = 5
    p["power_atk"] = 20.0
    p["power_mag"] = 18.0
    p["power_def"] = 15.0
    p["power_spd"] = 10.0
    p["crit_chance"] = 0.0  # stabilize
    p["luck_score"] = 0.0
    p["stats_alloc"] = {k: 5 for k in AXIS_KEYS}
    p["axis_progress"] = {k: 20.0 for k in AXIS_KEYS}  # ~B mid
    return p


def _mon():
    return {
        "id": "test_mon",
        "name": "ทดสอบ",
        "hp": 80,
        "max_hp": 80,
        "atk": 10,
        "elements": ["physical"],
        "statuses": [],
    }


def test_outbound_adapter_physical_and_magic():
    reg = DataRegistry.load(DATA_DIR)
    p = _base_player(reg)
    mon = _mon()
    sk_phys = {"id": "slash", "power": 10, "elements": ["physical"]}
    sk_mag = {"id": "bolt", "power": 10, "elements": ["arcane", "fire"]}
    r1 = resolve_player_outbound(p, mon, reg, "dark_forest", sk_phys, random.Random(7))
    r2 = resolve_player_outbound(p, mon, reg, "dark_forest", sk_mag, random.Random(7))
    assert isinstance(r1, DamageResult)
    assert r1.amount >= 1
    assert r2.amount >= 1
    assert r1.damage_class in ("physical", "dark")
    assert r2.damage_class in ("arcane", "light", "dark", "physical")
    # wrapper parity
    d1, f1 = player_attack_damage(p, mon, reg, "dark_forest", sk_phys, random.Random(7))
    assert d1 == r1.amount
    assert "power_" not in (f1 or "").lower()
    assert "mult" not in (f1 or "").lower()


def test_s_grade_outbound_soft_higher_than_f():
    reg = DataRegistry.load(DATA_DIR)
    mon = _mon()
    sk = {"power": 12, "elements": ["physical"]}

    p_s = _base_player(reg, "ps")
    p_s["grade_revealed"] = True
    p_s["player_grade"] = "S"
    p_s["growth_profile"] = "balanced"
    p_s["axis_progress"] = {k: 40.0 for k in AXIS_KEYS}  # S band

    p_f = _base_player(reg, "pf")
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "F"
    p_f["growth_profile"] = "balanced"
    p_f["axis_progress"] = {k: 2.0 for k in AXIS_KEYS}  # F

    # fixed seed: same crit/rng path
    rs = resolve_player_outbound(p_s, mon, reg, "dark_forest", sk, random.Random(42))
    rf = resolve_player_outbound(p_f, mon, reg, "dark_forest", sk, random.Random(42))
    assert rs.meta.get("grade_mult", 1) > rf.meta.get("grade_mult", 1)
    assert rs.amount >= rf.amount  # soft: S should not hit lower

    ms, _ = grade_outbound_mult(p_s, "physical")
    mf, _ = grade_outbound_mult(p_f, "physical")
    assert ms > mf
    assert 0.85 <= mf <= 1.18
    assert 0.85 <= ms <= 1.18
    # S in +10~15% zone-ish relative to C
    assert ms >= 1.05


def test_inbound_defense_grade_soft():
    reg = DataRegistry.load(DATA_DIR)
    p_high = _base_player(reg, "pdh")
    p_high["grade_revealed"] = True
    p_high["player_grade"] = "A"
    p_high["axis_progress"] = {
        "atk": 10.0,
        "defense": 50.0,  # SS-ish
        "magic": 10.0,
        "speed": 10.0,
    }
    p_high["dodge_chance"] = 0.0

    p_low = _base_player(reg, "pdl")
    p_low["grade_revealed"] = True
    p_low["player_grade"] = "F"
    p_low["axis_progress"] = {
        "atk": 10.0,
        "defense": 1.0,
        "magic": 10.0,
        "speed": 10.0,
    }
    p_low["dodge_chance"] = 0.0

    mh, _ = grade_inbound_mult(p_high, "physical")
    ml, _ = grade_inbound_mult(p_low, "physical")
    assert mh < ml  # high def → lower incoming mult

    rh = resolve_player_inbound(p_high, 20, random.Random(1), dmg_class="physical")
    rl = resolve_player_inbound(p_low, 20, random.Random(1), dmg_class="physical")
    assert rh.amount <= rl.amount


def test_wrapper_apply_incoming_compatible():
    reg = DataRegistry.load(DATA_DIR)
    p = _base_player(reg)
    p["dodge_chance"] = 0.0
    dmg, fl = apply_incoming_damage(p, 15, random.Random(3))
    assert dmg >= 1
    assert "power" not in (fl or "").lower()


def test_monster_raw_via_pipeline():
    mon = _mon()
    mon["atk"] = 12
    profile = {"power": 12, "tags": ["physical"]}
    d = monster_raw_damage(mon, profile, random.Random(0))
    r = resolve_monster_outbound(mon, profile, random.Random(0))
    assert d == r.amount
    assert d >= 1


def test_grade_mult_measurable_without_combat_rng():
    """Unit-level: mult tables alone prove grade effect."""
    reg = DataRegistry.load(DATA_DIR)
    p = _base_player(reg)
    p["grade_revealed"] = True
    p["player_grade"] = "S"
    p["axis_progress"] = {k: 40.0 for k in AXIS_KEYS}
    m_s, meta_s = grade_outbound_mult(p, "physical")
    p["player_grade"] = "F"
    p["axis_progress"] = {k: 1.0 for k in AXIS_KEYS}
    m_f, meta_f = grade_outbound_mult(p, "physical")
    assert m_s > m_f
    assert meta_s.get("player_part", 1) > meta_f.get("player_part", 1)
    # arcane uses magic axis
    p["grade_revealed"] = True
    p["player_grade"] = "C"
    p["axis_progress"] = {"atk": 1.0, "defense": 1.0, "magic": 45.0, "speed": 1.0}
    m_mag, meta_mag = grade_outbound_mult(p, "arcane")
    assert meta_mag.get("axis") == "magic"
    assert m_mag > 1.0


def test_soft_flavor_no_raw_formula():
    reg = DataRegistry.load(DATA_DIR)
    p = _base_player(reg)
    p["grade_revealed"] = True
    p["player_grade"] = "S"
    p["axis_progress"] = {k: 42.0 for k in AXIS_KEYS}
    mon = _mon()
    # many seeds to maybe get soft log
    blobs = []
    for seed in range(30):
        r = resolve_player_outbound(
            p, mon, reg, "dark_forest", {"power": 10, "elements": ["physical"]}, random.Random(seed)
        )
        blobs.append(r.flavor + "".join(r.soft_notes))
    text = " ".join(blobs)
    assert "power_atk" not in text
    assert "1.12" not in text
    assert "growth_mult" not in text
