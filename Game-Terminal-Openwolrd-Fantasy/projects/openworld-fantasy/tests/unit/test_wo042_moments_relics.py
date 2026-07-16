"""WO-042 Area Mini-Moments + Relic content for Infernal/Echo bonds."""
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
from game.domain.relic_anima import (
    BOND_RESONANCE,
    evaluate_relic_bonds,
    on_relic_bond_pulse,
    resolve_relic_faction,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
    get_faction_score,
)


def test_new_moments_areas():
    assert "infernal_cave_coal" in MINI_MOMENTS
    assert "echo_desert_mirage" in MINI_MOMENTS
    assert "divine_crystal_prayer" in MINI_MOMENTS
    assert any(m["id"] == "infernal_cave_coal" for m in moments_for_area("cave_shadow"))
    assert any(m["id"] == "echo_desert_mirage" for m in moments_for_area("desert_heat"))
    assert any(m["id"] == "divine_crystal_prayer" for m in moments_for_area("crystal_peak"))
    assert len(MINI_MOMENTS) >= 6


def test_wo042_moment_alerts():
    cat = get_catalog()
    for code in (
        "world.moment_cave_coal_accept",
        "world.moment_desert_mirage_listen",
        "world.moment_crystal_pray",
    ):
        assert code in cat


def test_cave_coal_accept_infernal():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42a", "warrior", "เมษ")
    ensure_needs(p)
    ensure_stat_arch(p)
    p["needs"]["morale"] = 50
    s0 = get_faction_score(p, FACTION_INFERNAL)
    resolve_moment_choice(p, "infernal_cave_coal", "help", reg=reg)
    assert get_faction_score(p, FACTION_INFERNAL) > s0
    assert int(get_needs(p)["morale"]) < 50


def test_desert_mirage_listen_echo():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42b", "warrior", "เมษ")
    ensure_stat_arch(p)
    a0 = anima_value(p)
    e0 = get_faction_score(p, FACTION_ECHO)
    resolve_moment_choice(p, "echo_desert_mirage", "help", reg=reg)
    assert get_faction_score(p, FACTION_ECHO) > e0
    assert anima_value(p) >= a0


def test_crystal_pray_divine():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42c", "warrior", "เมษ")
    ensure_needs(p)
    ensure_stat_arch(p)
    d0 = get_faction_score(p, FACTION_DIVINE)
    resolve_moment_choice(p, "divine_crystal_prayer", "help", reg=reg)
    assert get_faction_score(p, FACTION_DIVINE) > d0


def test_new_relics_exist_and_lean():
    reg = DataRegistry.load(DATA_DIR)
    hell = (reg.items or {}).get("relic_hell_brand_charm") or {}
    echo = (reg.items or {}).get("relic_echo_shroud") or {}
    assert hell and hell.get("divine_burden")
    assert echo and echo.get("divine_burden")
    assert hell.get("slot") == "acc_1"
    assert echo.get("slot") == "body"
    assert resolve_relic_faction("relic_hell_brand_charm", reg=reg) == FACTION_INFERNAL
    assert resolve_relic_faction("relic_echo_shroud", reg=reg) == FACTION_ECHO


def test_infernal_bond_with_new_charm():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42d", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["anima"] = 50.0
    p["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p["equip_rarities"] = {
        "main_hand": "divine",
        "acc_1": "legendary",
    }
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_RESONANCE
    assert bond["faction"] == FACTION_INFERNAL
    a0 = anima_value(p)
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert lines
    # infernal bond slightly lowers anima (familiar heat)
    assert anima_value(p) <= a0 + 0.01


def test_echo_bond_with_new_shroud():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42e", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["level"] = 1
    p["anima"] = 48.0
    p["equip_ids"] = {
        "body": "relic_echo_shroud",
        "acc_1": "relic_void_whisper_ring",
    }
    p["equip_rarities"] = {
        "body": "legendary",
        "acc_1": "legendary",
    }
    bond = evaluate_relic_bonds(p, reg)
    assert bond["mode"] == BOND_RESONANCE
    assert bond["faction"] == FACTION_ECHO
    lines = on_relic_bond_pulse(p, reg, force=True)
    assert lines
    assert p.get("_relic_bond_mode") == BOND_RESONANCE


def test_auto_resolve_new_moment():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w42f", "warrior", "เมษ")
    ensure_stat_arch(p)
    sight = {
        "kind": "faction_moment",
        "moment_id": "echo_desert_mirage",
        "moment": MINI_MOMENTS["echo_desert_mirage"],
    }
    lines = auto_resolve_moment(p, sight, reg=reg, prefs={"auto_avoid_cold_faction": True})
    assert lines


def test_quest_rewards_new_relics():
    reg = DataRegistry.load(DATA_DIR)
    qs = getattr(reg, "quests", None) or {}
    # quests may be dict by id
    if isinstance(qs, dict):
        items = []
        for q in qs.values():
            if isinstance(q, dict):
                items.extend(q.get("reward_items") or [])
        assert "relic_hell_brand_charm" in items
        assert "relic_echo_shroud" in items
