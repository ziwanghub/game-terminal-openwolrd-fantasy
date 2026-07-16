"""WO-040 Anima × Relic Depth."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.divine_burden import try_auto_unequip_burden
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    on_relic_equip_depth,
    primary_relic_faction,
    relic_equipped_morale_mult,
    resolve_relic_faction,
    should_auto_unequip_for_anima,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO, FACTION_INFERNAL
from game.runtime.dungeon_auto import ensure_auto_prefs


def test_relic_lean_map():
    reg = DataRegistry.load(DATA_DIR)
    assert resolve_relic_faction("relic_storm_fang", reg=reg) == FACTION_DIVINE
    assert resolve_relic_faction("relic_hell_ember_blade", reg=reg) == FACTION_INFERNAL
    assert resolve_relic_faction("relic_void_whisper_ring", reg=reg) == FACTION_ECHO
    assert resolve_relic_faction("relic_aegis_sky", reg=reg) == FACTION_DIVINE


def test_catalog_relic_anima_codes():
    cat = get_catalog()
    for code in (
        "anima.relic_divine",
        "anima.relic_infernal",
        "anima.relic_echo",
        "world.relic_wind_gaze",
    ):
        assert code in cat


def test_divine_equip_raises_anima():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ra1", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["anima"] = 40.0
    lines = on_relic_equip_depth(
        p, reg, item_id="relic_storm_fang", item_name="เขี้ยว", tags=["storm", "holy"]
    )
    assert lines
    assert anima_value(p) > 40.0
    assert p.get("_relic_faction_lean") == FACTION_DIVINE


def test_infernal_equip_lowers_anima():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ra2", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["anima"] = 50.0
    on_relic_equip_depth(
        p, reg, item_id="relic_hell_ember_blade", item_name="เถ้า", tags=["hell", "fire"]
    )
    assert anima_value(p) < 50.0
    assert p.get("_relic_faction_lean") == FACTION_INFERNAL


def test_morale_mult_by_lean():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ra3", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    # force burden by low level
    m_d = relic_equipped_morale_mult(p, reg)
    assert primary_relic_faction(p, reg) == FACTION_DIVINE
    assert m_d < 1.0

    p["equip_ids"] = {"main_hand": "relic_hell_ember_blade"}
    p["equip_rarities"] = {"main_hand": "divine"}
    m_i = relic_equipped_morale_mult(p, reg)
    assert m_i > 1.0


def test_auto_unequip_anima_frail():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ra4", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["anima"] = 10.0
    p["needs"]["morale"] = 30
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    assert should_auto_unequip_for_anima(p, reg, morale=30, morale_th=40)
    notes = try_auto_unequip_burden(p, reg)
    assert notes
