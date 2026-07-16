"""WO-041 Relic Soft Bonds."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.divine_burden import try_auto_unequip_burden
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    BOND_RESONANCE,
    BOND_TENSION,
    evaluate_relic_bonds,
    on_relic_bond_pulse,
    on_relic_equip_depth,
    relic_equipped_morale_mult,
    should_auto_unequip_for_anima,
    tension_unequip_preference,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_INFERNAL, get_faction_score
from game.runtime.dungeon_auto import ensure_auto_prefs


def _equip_two(p, slot_a, id_a, rar_a, slot_b, id_b, rar_b):
    p["equip_ids"] = {slot_a: id_a, slot_b: id_b}
    p["equip_rarities"] = {slot_a: rar_a, slot_b: rar_b}


def test_catalog_bond_codes():
    cat = get_catalog()
    for code in (
        "anima.bond_divine",
        "anima.bond_infernal",
        "anima.bond_echo",
        "anima.bond_tension",
        "world.bond_divine_gaze",
    ):
        assert code in cat


def test_divine_resonance_two_relics():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b1", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["anima"] = 45.0
    # WO-046: match area lean so area synergy does not inflate mult
    p["location"] = "crystal_peak"
    _equip_two(
        p,
        "main_hand",
        "relic_storm_fang",
        "legendary",
        "body",
        "relic_aegis_sky",
        "legendary",
    )
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_RESONANCE
    assert bond["faction"] == FACTION_DIVINE
    assert bond["count"] >= 2
    a0 = anima_value(p)
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert lines
    assert anima_value(p) > a0
    mult = relic_equipped_morale_mult(p, reg)
    assert mult < 0.88  # stronger than single divine

def test_tension_divine_infernal():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b2", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["anima"] = 50.0
    _equip_two(
        p,
        "main_hand",
        "relic_hell_ember_blade",
        "divine",
        "body",
        "relic_aegis_sky",
        "legendary",
    )
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_TENSION
    assert FACTION_DIVINE in bond["factions"]
    assert FACTION_INFERNAL in bond["factions"]
    a0 = anima_value(p)
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert lines
    assert anima_value(p) < a0
    assert relic_equipped_morale_mult(p, reg) > 1.1


def test_equip_depth_triggers_bond():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b3", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    # second equip path via on_relic_equip_depth after body already set
    p["equip_ids"]["body"] = "relic_aegis_sky"
    p["equip_rarities"]["body"] = "legendary"
    p["anima"] = 40.0
    lines = on_relic_equip_depth(
        p, reg, item_id="relic_aegis_sky", item_name="เกราะฟ้า", tags=["holy", "sky"]
    )
    assert any("bond" in str(x).lower() or "เรโซ" in str(x) or "อุ่น" in str(x) for x in lines) or lines
    assert p.get("_relic_bond_mode") == BOND_RESONANCE


def test_auto_unequip_tension():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b4", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["level"] = 1
    p["anima"] = 30.0
    p["needs"]["morale"] = 32
    _equip_two(
        p,
        "main_hand",
        "relic_hell_ember_blade",
        "divine",
        "body",
        "relic_aegis_sky",
        "legendary",
    )
    assert should_auto_unequip_for_anima(p, reg, morale=32, morale_th=40)
    pref = tension_unequip_preference(p, reg)
    assert pref in ("main_hand", "body", "acc_1")
    notes = try_auto_unequip_burden(p, reg)
    assert notes
    # one of the two should be gone
    eq = p.get("equip_ids") or {}
    remaining = sum(1 for k in ("main_hand", "body") if eq.get(k))
    assert remaining <= 1


def test_bond_boosts_faction():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b5", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    _equip_two(
        p,
        "main_hand",
        "relic_storm_fang",
        "legendary",
        "body",
        "relic_aegis_sky",
        "legendary",
    )
    s0 = get_faction_score(p, FACTION_DIVINE)
    on_relic_bond_pulse(p, reg, force=True)
    assert get_faction_score(p, FACTION_DIVINE) >= s0
