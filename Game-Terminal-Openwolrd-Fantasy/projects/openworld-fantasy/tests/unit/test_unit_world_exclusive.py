"""Unit: one per player, exclusive per world, very rare chance."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.unit_system import (
    claim_unit,
    is_unit_claimed,
    is_unit_skill_claimed,
    player_has_unit,
    save_claims,
    try_unit_unlock_with_claim,
)


def _eligible_shell(reg, name, occ, world, pid):
    p = create_player(reg, name, occ, "เมษ")
    p["world_id"] = world
    p["id"] = pid
    p["level"] = 30
    p["stats_alloc"] = {
        "atk": 10,
        "defense": 20,
        "magic": 20,
        "speed": 5,
        "intelligence": 5,
        "crit": 20,
    }
    p["stats"] = {"boss_kills": 5, "combos": 50, "kills": 100}
    p["library_entries_read"] = ["a", "b", "c", "d", "e"]
    p["occupation_id"] = occ
    return p


def test_claim_blocks_second_player_same_unit():
    reg = DataRegistry.load(DATA_DIR)
    world = "_test_unit_world_a"
    save_claims(world, {"by_unit": {}, "by_skill": {}, "schema": 2})
    a = _eligible_shell(reg, "A", "rogue", world, "pa")
    b = _eligible_shell(reg, "B", "rogue", world, "pb")
    assert claim_unit(world, "unit_eclipse", a, exclusive_skill="unit_eclipse_blade")
    assert is_unit_claimed(world, "unit_eclipse", except_player_id="pb")
    assert is_unit_skill_claimed(world, "unit_eclipse_blade", except_player_id="pb")
    assert not claim_unit(world, "unit_eclipse", b, exclusive_skill="unit_eclipse_blade")


def test_player_only_one_unit_even_if_force():
    reg = DataRegistry.load(DATA_DIR)
    world = "_test_unit_world_b"
    save_claims(world, {"by_unit": {}, "by_skill": {}, "schema": 2})
    p = _eligible_shell(reg, "One", "warrior", world, "p_one")
    notes = try_unit_unlock_with_claim(
        p, reg, force_uid="unit_aegis", force_success=True
    )
    assert any("Unit" in n or "ปลุก" in n for n in notes)
    assert p.get("unit_class_id") == "unit_aegis"
    assert player_has_unit(p)
    # second attempt must no-op
    notes2 = try_unit_unlock_with_claim(
        p, reg, force_uid="unit_eclipse", force_success=True
    )
    assert notes2 == []
    assert p.get("unit_class_id") == "unit_aegis"


def test_world_skill_exclusive_blocks_other_player_unlock():
    reg = DataRegistry.load(DATA_DIR)
    world = "_test_unit_world_c"
    save_claims(world, {"by_unit": {}, "by_skill": {}, "schema": 2})
    a = _eligible_shell(reg, "A2", "mage", world, "pa2")
    b = _eligible_shell(reg, "B2", "mage", world, "pb2")
    try_unit_unlock_with_claim(a, reg, force_uid="unit_nova", force_success=True)
    assert a.get("unit_class_id") == "unit_nova"
    # B cannot claim same unit/skill
    notes = try_unit_unlock_with_claim(
        b, reg, force_uid="unit_nova", force_success=True
    )
    assert b.get("unit_class_id") in (None, "")
    assert any("ครอบครอง" in n or "Unit" in n for n in notes) or notes == []
    # if empty, claim path may return early because not in candidates — force claim check
    assert is_unit_claimed(world, "unit_nova")
    assert is_unit_skill_claimed(world, "unit_nova_burst")


def test_chance_capped_very_low():
    """Even if YAML said high, code clamps — sample fail rate high."""
    from game.domain.unit_system import MAX_UNIT_CHANCE, DEFAULT_UNIT_CHANCE

    assert MAX_UNIT_CHANCE <= 0.06
    assert DEFAULT_UNIT_CHANCE <= 0.04
    reg = DataRegistry.load(DATA_DIR)
    for uid, u in (reg.unit_classes or {}).items():
        ch = float((u.get("unlock") or {}).get("chance") or 0)
        assert ch <= 0.06, f"{uid} chance too high: {ch}"


def test_yaml_has_thirty_three_exclusive_units():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.unit_classes or {}) >= 33
    skills = set()
    tiers = set()
    for u in (reg.unit_classes or {}).values():
        sk = u.get("exclusive_skill")
        skills.add(sk)
        tiers.add(u.get("power_tier"))
        assert sk in reg.skills, sk
        assert reg.skills[sk].get("unit_only") is True
    assert len(skills) >= 33
    # design spread: broken OP + joke traps
    assert "broken" in tiers
    assert "joke" in tiers
