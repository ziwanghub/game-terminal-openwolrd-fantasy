"""IC5 chest/shop economy close + MC5 late density."""
from __future__ import annotations

from pathlib import Path

import yaml

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry


def test_chest_pool_buckets_all_resolve():
    reg = DataRegistry.load(DATA_DIR)
    pools = yaml.safe_load(
        Path(DATA_DIR).joinpath("chests/pools.yaml").read_text(encoding="utf-8")
    )
    buckets = pools.get("buckets") or {}
    for name in ("material", "food", "heal", "equipment", "special"):
        assert name in buckets
        assert len(buckets[name]) >= 5
        for iid in buckets[name]:
            assert iid in reg.items, f"pool {name} missing item {iid}"
    # equipment should not be only starters
    eq = set(buckets["equipment"])
    assert "mid_steel_glaive" in eq or "chitin_vest" in eq
    assert "iron_sword" in eq


def test_shops_stock_resolves_no_cards():
    reg = DataRegistry.load(DATA_DIR)
    shops = yaml.safe_load(
        Path(DATA_DIR).joinpath("shops/shops.yaml").read_text(encoding="utf-8")
    )
    for s in shops:
        for row in s.get("stock") or []:
            iid = row if isinstance(row, str) else (row or {}).get("id")
            if not iid:
                continue
            assert not str(iid).startswith("card_"), f"shop {s.get('id')} sells card"
            assert iid in reg.items, f"shop {s.get('id')} stock {iid}"


def test_mc5_late_mons_and_elites():
    reg = DataRegistry.load(DATA_DIR)
    need = {
        "crystal_shard_swarm": "crystal_peak",
        "crystal_echo_wraith": "crystal_peak",
        "void_rift_mite": "void_rift",
        "void_whisperer": "void_rift",
        "elite_crystal_prism_guard": "crystal_peak",
        "elite_void_null_archon": "void_rift",
        "desert_sand_golem": "desert_heat",
    }
    for mid, area in need.items():
        m = reg.monsters[mid]
        assert m.get("card_id") in reg.cards
        for d in m.get("drops") or []:
            assert d["item"] in reg.items
        if mid.startswith("elite_"):
            assert m.get("elite") is True
        pools = [
            (x.get("id") if isinstance(x, dict) else x)
            for x in (reg.areas[area].get("monster_pools") or [])
        ]
        assert mid in pools
    assert len(reg.areas["crystal_peak"].get("monster_pools") or []) >= 10
    assert len(reg.areas["void_rift"].get("monster_pools") or []) >= 10


def test_late_craft_and_items():
    reg = DataRegistry.load(DATA_DIR)
    for iid in ("void_filament", "prism_shard", "late_void_edge", "late_prism_veil"):
        assert iid in reg.items
    recipes = yaml.safe_load(
        Path(DATA_DIR).joinpath("craft/recipes.yaml").read_text(encoding="utf-8")
    )
    ids = {r["id"] for r in recipes}
    assert "craft_late_void_edge" in ids
    assert "craft_late_prism_veil" in ids


def test_all_monster_drops_resolve_ic5():
    reg = DataRegistry.load(DATA_DIR)
    for mid, m in reg.monsters.items():
        for d in m.get("drops") or []:
            assert d.get("item") in reg.items, f"{mid}->{d.get('item')}"


def test_content_counts_ic5_mc5():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.items) >= 143
    assert len(reg.monsters) >= 80
    assert len(reg.cards) >= 65
