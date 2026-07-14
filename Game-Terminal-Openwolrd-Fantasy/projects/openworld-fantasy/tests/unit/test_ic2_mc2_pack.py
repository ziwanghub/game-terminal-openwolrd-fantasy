"""IC2 unique cards + MC2 thicker pools smoke tests."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry


def test_ic2_unique_cards_bound_to_core_mons():
    reg = DataRegistry.load(DATA_DIR)
    expect = {
        "goblin_hunter": "card_goblin_hunter",
        "forest_wolf": "card_forest_wolf",
        "wood_ent": "card_wood_ent",
        "cave_bat": "card_cave_bat_swarm",
        "dark_slime": "card_dark_slime",
        "rock_golem": "card_rock_golem",
        "sand_scorpion": "card_sand_scorpion",
        "cursed_knight": "card_cursed_knight",
    }
    for mid, cid in expect.items():
        assert mid in reg.monsters
        assert reg.monsters[mid].get("card_id") == cid
        assert cid in reg.cards
        assert (reg.cards[cid].get("bonuses") or reg.cards[cid].get("name"))


def test_mc2_monsters_full_pack_and_pools():
    reg = DataRegistry.load(DATA_DIR)
    new_mons = {
        "cave_crystal_spider": "cave_shadow",
        "forest_boar": "dark_forest",
        "marsh_gas_blob": "mist_marsh",
        "peak_ice_sprite": "crystal_peak",
        "void_shade_larva": "void_rift",
        "ridge_goat": "mountain_rock",
    }
    for mid, area in new_mons.items():
        m = reg.monsters[mid]
        assert m.get("drops") and len(m["drops"]) >= 2
        assert m.get("card_id") in reg.cards
        for d in m["drops"]:
            assert d["item"] in reg.items, d["item"]
        pools = reg.areas[area].get("monster_pools") or []
        ids = [(x.get("id") if isinstance(x, dict) else x) for x in pools]
        assert mid in ids
        assert len(pools) >= 6, f"{area} pool {len(pools)}"


def test_all_areas_pool_at_least_six():
    reg = DataRegistry.load(DATA_DIR)
    for aid, a in reg.areas.items():
        n = len(a.get("monster_pools") or [])
        assert n >= 6, f"{aid} only {n}"


def test_ic3_lite_craft_recipes_exist():
    import yaml
    from pathlib import Path

    recipes = yaml.safe_load(
        Path(DATA_DIR).joinpath("craft/recipes.yaml").read_text(encoding="utf-8")
    )
    ids = {r["id"] for r in recipes}
    for rid in (
        "craft_bone_dagger",
        "craft_vine_wrap",
        "craft_cave_helm",
        "craft_kite_shield",
    ):
        assert rid in ids
    reg = DataRegistry.load(DATA_DIR)
    for r in recipes:
        if r["id"] not in (
            "craft_bone_dagger",
            "craft_vine_wrap",
            "craft_cave_helm",
            "craft_kite_shield",
        ):
            continue
        for iid in (r.get("inputs") or {}):
            assert iid in reg.items
        assert r["output"] in reg.items


def test_card_count_grew_for_ic2():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.cards) >= 30
    assert len(reg.monsters) >= 55
