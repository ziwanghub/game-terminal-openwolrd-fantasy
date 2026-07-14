"""IC3 mon-line crafts + MC3 mid-role monsters."""
from __future__ import annotations

from pathlib import Path

import yaml

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.equipment import upgrade_cost
from game.domain.unit_system import MAX_UNIT_CHANCE


def test_mc3_role_monsters_and_pools():
    reg = DataRegistry.load(DATA_DIR)
    roles = {
        "forest_mantrap": ("dark_forest", "plant"),
        "forest_hornet": ("dark_forest", "insect"),
        "cave_skull_crawler": ("cave_shadow", "undead"),
        "city_bone_walker": ("ancient_city", "undead"),
        "desert_vulture": ("desert_heat", "bird"),
        "desert_scarab": ("desert_heat", "insect"),
        "marsh_reed_horror": ("mist_marsh", "plant"),
        "crystal_songbird": ("crystal_peak", "bird"),
        "mountain_carrion_crow": ("mountain_rock", "bird"),
        "void_bone_moth": ("void_rift", "insect"),
    }
    for mid, (area, role) in roles.items():
        m = reg.monsters[mid]
        assert m.get("role_tag") == role or role in str(m.get("elements"))
        assert m.get("card_id") in reg.cards
        for d in m.get("drops") or []:
            assert d["item"] in reg.items, (mid, d["item"])
        pools = [
            (x.get("id") if isinstance(x, dict) else x)
            for x in (reg.areas[area].get("monster_pools") or [])
        ]
        assert mid in pools
        assert len(pools) >= 7


def test_ic3_craft_recipes_and_outputs():
    reg = DataRegistry.load(DATA_DIR)
    recipes = yaml.safe_load(
        Path(DATA_DIR).joinpath("craft/recipes.yaml").read_text(encoding="utf-8")
    )
    need = [
        "craft_balm_nature",
        "craft_oil_shadow",
        "craft_chitin_vest",
        "craft_bone_circlet",
        "craft_quill_bow",
        "craft_fang_charm",
        "craft_ent_tonic",
        "craft_slime_antidote",
    ]
    ids = {r["id"] for r in recipes}
    for rid in need:
        assert rid in ids
        rec = next(r for r in recipes if r["id"] == rid)
        for iid in rec.get("inputs") or {}:
            assert iid in reg.items, iid
        assert rec["output"] in reg.items


def test_all_monster_drops_resolve():
    reg = DataRegistry.load(DATA_DIR)
    for mid, m in reg.monsters.items():
        for d in m.get("drops") or []:
            assert d.get("item") in reg.items, f"{mid} -> {d.get('item')}"


def test_late_upgrade_steeper_and_unit_cap():
    c5 = upgrade_cost("main_hand", 5)
    c9 = upgrade_cost("main_hand", 9)
    assert c9["money"] > c5["money"] * 1.5
    assert c9["rare_mat"] >= c5["rare_mat"]
    assert MAX_UNIT_CHANCE <= 0.05


def test_content_counts_after_ic3_mc3():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.monsters) >= 65
    assert len(reg.cards) >= 40
    assert len(reg.items) >= 120
