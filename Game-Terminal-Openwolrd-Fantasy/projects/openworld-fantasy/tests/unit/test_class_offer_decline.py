"""Occupation offers: accept / permanent decline; free stats; unit affinity."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.class_paths import (
    apply_class_change,
    decline_class_offer,
    is_occupation_declined,
    list_available_class_paths,
)
from game.domain.unit_system import unit_skill_affinity_mult


def _make_eligible_vagabond(reg, name="v1"):
    p = create_player(reg, name, "vagabond", "เมษ")
    p["occupation_id"] = "vagabond"
    p["level"] = 10
    p["stats_alloc"] = {
        "atk": 5,
        "defense": 4,
        "magic": 5,
        "speed": 5,
        "intelligence": 4,
        "crit": 2,
    }
    p["stats"] = {
        "kills": 20,
        "combos": 20,
        "explores": 20,
        "flees": 5,
        "heals": 5,
    }
    p["library_entries_read"] = ["a"]
    p["stat_points"] = 0
    # personality for priest path
    p["personality_invest"] = {"compassion": 2}
    return p


def test_decline_removes_occupation_offer_only():
    reg = DataRegistry.load(DATA_DIR)
    p = _make_eligible_vagabond(reg)
    paths = list_available_class_paths(p, reg)
    assert paths, "should have at least one offer when broadly eligible"
    # decline first path's occupation
    target = paths[0]
    to_id = str(target.get("to_occupation"))
    notes = decline_class_offer(p, target)
    assert any("ปิด" in n or "ผลัก" in n for n in notes)
    assert is_occupation_declined(p, to_id)
    paths2 = list_available_class_paths(p, reg)
    assert all(str(x.get("to_occupation")) != to_id for x in paths2)
    # other occupations may still remain
    # (if only one was available, list can be empty — still ok)


def test_accept_class_and_cannot_reoffer_same_as_current():
    reg = DataRegistry.load(DATA_DIR)
    p = _make_eligible_vagabond(reg, "acc")
    paths = list_available_class_paths(p, reg)
    # pick warrior path if present else first
    path = next(
        (x for x in paths if x.get("to_occupation") == "warrior"),
        paths[0],
    )
    notes = apply_class_change(p, reg, path)
    assert any("รับ" in n or "→" in n for n in notes)
    assert p.get("occupation_id") == path.get("to_occupation")
    # free alloc note present
    assert any("อิสระ" in n for n in notes)
    # no longer vagabond offers for same system unless reclass flag
    paths_after = list_available_class_paths(p, reg)
    assert paths_after == [] or (p.get("flags") or {}).get("allow_reclass")


def test_unit_magic_skill_weak_without_magic_invest():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills.get("unit_nova_burst") or {
        "unit_only": True,
        "elements": ["arcane", "fire"],
        "power": 60,
    }
    p_lo = create_player(reg, "lo", "warrior", "เมษ")
    p_lo["power_atk"] = 40.0
    p_lo["power_mag"] = 3.0
    p_lo["power_crit"] = 5.0
    p_hi = create_player(reg, "hi", "mage", "เมถุน")
    p_hi["power_atk"] = 8.0
    p_hi["power_mag"] = 45.0
    p_hi["power_crit"] = 10.0
    m_lo = unit_skill_affinity_mult(p_lo, sk)
    m_hi = unit_skill_affinity_mult(p_hi, sk)
    assert m_lo < 0.55
    assert m_hi > m_lo
    assert m_hi >= 0.9


def test_unit_physical_skill_prefers_atk():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills.get("unit_iron_legion") or {
        "unit_only": True,
        "elements": ["physical", "holy"],
        "power": 78,
    }
    p = create_player(reg, "ph", "warrior", "เมษ")
    p["power_atk"] = 40.0
    p["power_mag"] = 5.0
    p["power_crit"] = 8.0
    # hybrid physical+holy uses blend — still should not be abysmal with high atk
    assert unit_skill_affinity_mult(p, sk) >= 0.45
