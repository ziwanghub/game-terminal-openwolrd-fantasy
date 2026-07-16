"""WO-039 Faction Mini-Moments."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.faction_moments import (
    MINI_MOMENTS,
    auto_resolve_moment,
    moments_for_area,
    resolve_moment_choice,
)
from game.domain.needs import ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO, get_faction_score


def test_three_moments_defined():
    assert len(MINI_MOMENTS) >= 3
    assert moments_for_area("dark_forest")
    assert moments_for_area("mist_marsh")
    assert moments_for_area("ancient_city") or moments_for_area("crystal_peak")


def test_moment_alerts_in_catalog():
    cat = get_catalog()
    for code in (
        "world.moment_divine_help",
        "world.moment_infernal_gaze",
        "world.moment_echo_accept",
    ):
        assert code in cat


def test_echo_help_raises_faction_and_anima():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fm1", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    e0 = get_faction_score(p, FACTION_ECHO)
    a0 = anima_value(p)
    lines = resolve_moment_choice(p, "echo_forest_whisper", "help", reg=reg)
    assert get_faction_score(p, FACTION_ECHO) > e0
    assert anima_value(p) >= a0
    assert lines


def test_divine_help_raises_divine():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fm2", "warrior", "เมษ")
    ensure_stat_arch(p)
    d0 = get_faction_score(p, FACTION_DIVINE)
    resolve_moment_choice(p, "divine_wind_gaze", "help", reg=reg)
    assert get_faction_score(p, FACTION_DIVINE) > d0


def test_infernal_help_hurts_morale():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fm3", "warrior", "เมษ")
    ensure_needs(p)
    ensure_stat_arch(p)
    p["needs"]["morale"] = 55
    resolve_moment_choice(p, "infernal_haze_echo", "help", reg=reg)
    assert int(get_needs(p)["morale"]) < 55


def test_auto_resolve_returns_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fm4", "warrior", "เมษ")
    ensure_stat_arch(p)
    sight = {
        "kind": "faction_moment",
        "moment_id": "divine_wind_gaze",
        "moment": MINI_MOMENTS["divine_wind_gaze"],
    }
    lines = auto_resolve_moment(p, sight, reg=reg, prefs={"auto_avoid_cold_faction": True})
    assert lines
