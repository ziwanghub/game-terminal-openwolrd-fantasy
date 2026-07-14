"""IC4 boss gear/cards/sets + MC4 elites."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats


def test_boss_exclusive_cards_and_gear_drops():
    reg = DataRegistry.load(DATA_DIR)
    expect = {
        "boss_forest_king": ("card_boss_forest_king", "thorn_blade"),
        "boss_shadow_queen": ("card_boss_shadow_queen", "umbra_veil_helm"),
        "boss_stone_titan": ("card_boss_stone_titan", "titan_plate"),
        "boss_ruin_oracle": ("card_boss_ruin_oracle", "oracle_tome_focus"),
        "boss_sun_scourge": ("card_boss_sun_scourge", "sunscourge_blade"),
        "boss_mist_hydra": ("card_boss_mist_hydra", "hydra_scale_mail"),
        "boss_prism_sovereign": ("card_boss_prism", "prism_staff"),
        "boss_void_herald": ("card_boss_void_herald", "void_herald_cloak"),
    }
    for bid, (cid, gear) in expect.items():
        m = reg.monsters[bid]
        assert m.get("boss") is True
        assert m.get("card_id") == cid
        assert cid in reg.cards
        items = [d["item"] for d in (m.get("drops") or [])]
        assert gear in items
        assert gear in reg.items


def test_boss_gear_sets_activate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "set1", "warrior", "เมษ")
    add_item(p, "titan_plate", reg, rarity="sacred")
    add_item(p, "titan_greaves", reg, rarity="rare")
    equip_item(p, "titan_plate", reg)
    equip_item(p, "titan_greaves", reg)
    recompute_stats(p, reg)
    active = " ".join(str(x) for x in (p.get("active_sets") or []))
    assert "หิน" in active or "ไททัน" in active or "stone" in active.lower() or p.get("active_sets")


def test_mc4_elites_flagged_and_in_pools():
    reg = DataRegistry.load(DATA_DIR)
    elites = {
        "elite_forest_alpha_wolf": "dark_forest",
        "elite_cave_abyss_matron": "cave_shadow",
        "elite_ridge_warlord": "mountain_rock",
        "elite_dune_warlock": "desert_heat",
        "elite_marsh_plague_toad": "mist_marsh",
        "elite_city_hex_captain": "ancient_city",
        "elite_prism_sentinel": "crystal_peak",
        "elite_void_riven_knight": "void_rift",
    }
    for mid, area in elites.items():
        m = reg.monsters[mid]
        assert m.get("elite") is True
        assert m.get("card_id") in reg.cards
        for d in m.get("drops") or []:
            assert d["item"] in reg.items
        pools = [
            (x.get("id") if isinstance(x, dict) else x)
            for x in (reg.areas[area].get("monster_pools") or [])
        ]
        assert mid in pools
        # low weight elites — pool still has them
        assert len(pools) >= 8


def test_new_gear_sets_registered():
    reg = DataRegistry.load(DATA_DIR)
    for sid in (
        "stone_bulwark",
        "umbra_court",
        "sun_scourge",
        "mist_hydra",
        "prism_court",
        "void_herald",
        "ruin_oracle",
    ):
        assert sid in reg.gear_sets
        pieces = [i for i, it in reg.items.items() if it.get("set_id") == sid]
        assert len(pieces) >= 2


def test_all_drops_still_resolve():
    reg = DataRegistry.load(DATA_DIR)
    for mid, m in reg.monsters.items():
        for d in m.get("drops") or []:
            assert d.get("item") in reg.items, f"{mid}->{d.get('item')}"


def test_content_counts_ic4_mc4():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.items) >= 135
    assert len(reg.monsters) >= 74
    assert len(reg.cards) >= 55
    assert len(reg.gear_sets) >= 10
