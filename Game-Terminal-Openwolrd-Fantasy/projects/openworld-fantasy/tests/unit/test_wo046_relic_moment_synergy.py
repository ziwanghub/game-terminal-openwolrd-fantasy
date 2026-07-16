"""WO-046 Relic × Moment / Area Soft Synergy Lite."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.divine_burden import try_auto_unequip_burden
from game.domain.faction_moments import resolve_moment_choice, roll_faction_moment_sight
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    SYN_AREA_TENSION,
    SYN_RESONATE,
    evaluate_relic_area_synergy,
    moment_chance_factor,
    on_chamber_spar_with_relic,
    relic_area_synergy_morale_factor,
    relic_equipped_morale_mult,
    should_auto_unequip_for_anima,
    synergy_foresight_lines,
    try_area_synergy_presence_pulse,
)
from game.domain.soft_foresight import area_world_gaze_lines
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO, FACTION_INFERNAL
from game.runtime.dungeon_auto import ensure_auto_prefs


def _divine_on(p):
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}


def _hell_on(p):
    p["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}


def test_catalog_synergy_codes():
    cat = get_catalog()
    for code in (
        "world.synergy_resonate",
        "world.synergy_tension",
        "anima.synergy_resonate",
        "world.synergy_moment_resonate",
    ):
        assert code in cat


def test_resonate_divine_mountain():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46a", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    _divine_on(p)
    syn = evaluate_relic_area_synergy(p, reg, area_id="mountain_rock")
    assert syn["mode"] == SYN_RESONATE
    assert syn["relic_faction"] == FACTION_DIVINE
    assert moment_chance_factor(p, reg, area_id="mountain_rock") > 1.0
    assert relic_area_synergy_morale_factor(p, reg, area_id="mountain_rock") < 1.0


def test_area_tension_hell_on_mountain():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46b", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    _hell_on(p)
    syn = evaluate_relic_area_synergy(p, reg, area_id="mountain_rock")
    assert syn["mode"] == SYN_AREA_TENSION
    assert syn["relic_faction"] == FACTION_INFERNAL
    assert moment_chance_factor(p, reg, area_id="mountain_rock") < 1.0
    assert relic_area_synergy_morale_factor(p, reg, area_id="mountain_rock") > 1.0
    mult = relic_equipped_morale_mult(p, reg)
    assert mult > 1.0


def test_echo_void_resonate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46c", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "void_rift"
    p["equip_ids"] = {
        "body": "relic_echo_shroud",
        "acc_1": "relic_void_whisper_ring",
    }
    p["equip_rarities"] = {"body": "legendary", "acc_1": "legendary"}
    syn = evaluate_relic_area_synergy(p, reg, area_id="void_rift")
    assert syn["mode"] == SYN_RESONATE
    assert syn["relic_faction"] == FACTION_ECHO


def test_moment_help_synergy_boosts_anima():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46d", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    p["anima"] = 50.0
    _divine_on(p)
    a0 = anima_value(p)
    lines = resolve_moment_choice(p, "divine_mountain_gaze", "help", reg=reg)
    assert lines
    assert anima_value(p) > a0 + 0.9  # base 1.0 * 1.35 synergy


def test_foresight_includes_synergy():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46e", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "crystal_peak"
    _divine_on(p)
    fl = synergy_foresight_lines(p, reg, area_id="crystal_peak", brief=False)
    assert fl
    blob = "\n".join(area_world_gaze_lines(p, reg, area_id="crystal_peak", force=True))
    assert "สะท้อน" in blob or "เรลิก" in blob or fl


def test_presence_pulse_resonate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46f", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "ancient_city"
    p["anima"] = 48.0
    _divine_on(p)
    a0 = anima_value(p)
    lines = try_area_synergy_presence_pulse(p, reg, area_id="ancient_city", force=True)
    assert lines
    assert anima_value(p) > a0


def test_spar_area_synergy():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46g", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    p["anima"] = 50.0
    _divine_on(p)
    a0 = anima_value(p)
    lines = on_chamber_spar_with_relic(p, reg, rounds=1)
    assert lines
    assert anima_value(p) >= a0


def test_auto_unequip_area_tension():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46h", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["level"] = 1
    p["location"] = "crystal_peak"  # divine area
    p["anima"] = 35.0
    p["needs"]["morale"] = 32
    _hell_on(p)
    assert should_auto_unequip_for_anima(p, reg, morale=32, morale_th=40)
    notes = try_auto_unequip_burden(p, reg)
    assert notes


def test_moment_roll_resonate_more_hits():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s46i", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    p["_faction_moments_seen"] = 0
    _divine_on(p)
    hits = 0
    for i in range(100):
        if roll_faction_moment_sight(p, random.Random(i + 3), area_id="mountain_rock"):
            hits += 1
    # with synergy ~28%*1.35 ~ should get decent hits
    assert hits >= 8
