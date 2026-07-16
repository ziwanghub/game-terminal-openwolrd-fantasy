"""WO-038 World Relations Lite."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.stat_arch import ensure_stat_arch, set_world_relation
from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
    adjust_faction,
    get_faction_score,
    on_echo_approach,
    on_npc_outcome,
    on_relic_theme,
    world_relation_needs_mults,
)


def test_world_alert_catalog():
    cat = get_catalog()
    for code in (
        "world.divine_glance",
        "world.infernal_haze",
        "world.echo_stare",
        "world.chamber_hush",
    ):
        assert code in cat


def test_npc_friend_raises_divine():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "wr1", "warrior", "เมษ")
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    before = get_faction_score(p, FACTION_DIVINE)
    lines = on_npc_outcome(
        p, outcome="friend", archetype="priest", area_id="ancient_city"
    )
    after = get_faction_score(p, FACTION_DIVINE)
    assert after > before
    assert lines  # soft alert or moment


def test_echo_humble_raises_echo():
    p: dict = {}
    ensure_stat_arch(p)
    from game.domain.world_relations import ensure_world_relations

    ensure_world_relations(p)
    before = get_faction_score(p, FACTION_ECHO)
    on_echo_approach(p, choice="humble")
    assert get_faction_score(p, FACTION_ECHO) > before


def test_relic_storm_leans_divine():
    p: dict = {}
    ensure_stat_arch(p)
    from game.domain.world_relations import ensure_world_relations

    ensure_world_relations(p)
    before = get_faction_score(p, FACTION_DIVINE)
    on_relic_theme(p, item_id="relic_storm_fang", tags=["storm", "holy"])
    assert get_faction_score(p, FACTION_DIVINE) >= before


def test_divine_warm_slows_morale_loss():
    reg = DataRegistry.load(DATA_DIR)

    def loss(div: int, inf: int) -> int:
        p = create_player(reg, f"m{div}{inf}", "warrior", "เมษ")
        ensure_needs(p)
        ensure_stat_arch(p)
        set_world_relation(p, "faction", FACTION_DIVINE, div)
        set_world_relation(p, "faction", FACTION_INFERNAL, inf)
        p["needs"]["morale"] = 70
        for _ in range(5):
            apply_needs_event(p, "combat_loss", silent=True)
        return 70 - int(get_needs(p)["morale"])

    assert loss(80, 50) <= loss(40, 20)


def test_needs_mults_sane():
    p: dict = {}
    ensure_stat_arch(p)
    from game.domain.world_relations import ensure_world_relations

    ensure_world_relations(p)
    set_world_relation(p, "faction", FACTION_DIVINE, 80)
    m = world_relation_needs_mults(p)
    assert 0.75 <= m["morale_drain_mult"] <= 1.0
