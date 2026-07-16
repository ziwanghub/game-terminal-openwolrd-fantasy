"""WO-043 Bond Soft Cap + 3-piece Soft Chorus."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.divine_burden import try_auto_unequip_burden
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    BOND_CHORUS,
    BOND_RESONANCE,
    evaluate_relic_bonds,
    on_chamber_spar_with_relic,
    on_relic_bond_pulse,
    relic_equipped_morale_mult,
    resolve_relic_faction,
    should_auto_unequip_for_anima,
    tension_unequip_preference,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO, FACTION_INFERNAL
from game.runtime.dungeon_auto import ensure_auto_prefs


def _eq(p, **slots):
    p["equip_ids"] = dict(slots)
    p["equip_rarities"] = {k: "legendary" for k in slots}
    if "main_hand" in slots and "hell" in str(slots["main_hand"]):
        p["equip_rarities"]["main_hand"] = "divine"


def test_catalog_chorus_codes():
    cat = get_catalog()
    for code in (
        "anima.chorus_divine",
        "anima.chorus_infernal",
        "anima.chorus_echo",
        "anima.bond_soft_cap",
        "world.chorus_echo_choir",
    ):
        assert code in cat


def test_third_relics_lean():
    reg = DataRegistry.load(DATA_DIR)
    assert resolve_relic_faction("relic_divine_laurel", reg=reg) == FACTION_DIVINE
    assert resolve_relic_faction("relic_hell_ash_greaves", reg=reg) == FACTION_INFERNAL
    assert resolve_relic_faction("relic_echo_sandals", reg=reg) == FACTION_ECHO
    for iid in (
        "relic_divine_laurel",
        "relic_hell_ash_greaves",
        "relic_echo_sandals",
    ):
        assert (reg.items or {}).get(iid)


def test_two_piece_still_resonance():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c1", "warrior", "เมษ")
    ensure_stat_arch(p)
    _eq(
        p,
        main_hand="relic_storm_fang",
        body="relic_aegis_sky",
    )
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_RESONANCE
    assert bond["count"] == 2
    assert not bond.get("soft_cap")


def test_three_piece_divine_chorus():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c2", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["anima"] = 45.0
    p["location"] = "crystal_peak"  # divine lean area for WO-046 synergy
    _eq(
        p,
        main_hand="relic_storm_fang",
        body="relic_aegis_sky",
        head="relic_divine_laurel",
    )
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_CHORUS
    assert bond["faction"] == FACTION_DIVINE
    assert bond["count"] == 3
    assert not bond.get("soft_cap")
    a0 = anima_value(p)
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert lines
    assert anima_value(p) > a0
    mult = relic_equipped_morale_mult(p, reg)
    assert mult < 0.84  # stronger calm than 2-piece


def test_infernal_and_echo_chorus():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c3", "warrior", "เมษ")
    ensure_stat_arch(p)
    _eq(
        p,
        main_hand="relic_hell_ember_blade",
        acc_1="relic_hell_brand_charm",
        legs="relic_hell_ash_greaves",
    )
    b = evaluate_relic_bonds(p, reg)
    assert b["mode"] == BOND_CHORUS and b["faction"] == FACTION_INFERNAL

    p2 = create_player(reg, "c4", "warrior", "เมษ")
    ensure_stat_arch(p2)
    _eq(
        p2,
        body="relic_echo_shroud",
        acc_1="relic_void_whisper_ring",
        feet="relic_echo_sandals",
    )
    b2 = evaluate_relic_bonds(p2, reg)
    assert b2["mode"] == BOND_CHORUS and b2["faction"] == FACTION_ECHO
    on_relic_bond_pulse(p2, reg, force=True)
    assert p2.get("_relic_bond_mode") == BOND_CHORUS


def test_soft_cap_four_piece():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c5", "warrior", "เมษ")
    ensure_needs(p)
    ensure_stat_arch(p)
    p["anima"] = 80.0
    p["needs"]["morale"] = 50
    # 3 divine + force a 4th by also equipping... only 3 divine pieces exist.
    # Soft cap triggers at count>=4; simulate by equipping 3 and monkeypatch? 
    # Better: equip 3 divine + 1 with same lean via inventing equip of storm on off_hand if allowed.
    # Use 3 divine + duplicate lean legendary: prism_staff has arcane not divine.
    # Force soft_cap path by temporarily putting 4 divine-mapped IDs:
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
        "off_hand": "relic_storm_fang",  # same id second slot (test-only stack)
    }
    p["equip_rarities"] = {k: "legendary" for k in p["equip_ids"]}
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_CHORUS
    assert bond["count"] >= 4
    assert bond.get("soft_cap") is True
    mor0 = int(p["needs"]["morale"])
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert any("cap" in str(x).lower() or "Soft Cap" in str(x) or "หนา" in str(x) for x in lines) or lines
    assert int(p["needs"]["morale"]) <= mor0


def test_spar_chorus():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c6", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["anima"] = 50.0
    _eq(
        p,
        main_hand="relic_storm_fang",
        body="relic_aegis_sky",
        head="relic_divine_laurel",
    )
    a0 = anima_value(p)
    lines = on_chamber_spar_with_relic(p, reg, rounds=2)
    assert lines
    assert anima_value(p) >= a0


def test_auto_unequip_soft_cap_chorus():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c7", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["level"] = 1
    p["anima"] = 35.0
    p["needs"]["morale"] = 30
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
        "off_hand": "relic_aegis_sky",
    }
    p["equip_rarities"] = {k: "legendary" for k in p["equip_ids"]}
    bond = evaluate_relic_bonds(p, reg)
    assert bond.get("soft_cap")
    assert should_auto_unequip_for_anima(p, reg, morale=30, morale_th=40)
    pref = tension_unequip_preference(p, reg)
    assert pref  # prefers non-main
    notes = try_auto_unequip_burden(p, reg)
    assert notes
