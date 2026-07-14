"""K4: higher-tier food / heal craft recipes at camp station."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.craft import craft, list_recipes, station_ok_for_recipe
from game.domain.equipment import add_item
from game.domain.quests import ensure_quests


class _Ok:
    def random(self) -> float:
        return 0.0


K4_IDS = (
    "craft_hunter_ration",
    "craft_mana_brew",
    "craft_focus_tea",
    "craft_balm",
    "craft_trail_stew",
    "craft_tonic_might",
    "craft_inn_feast",
)


def test_k4_recipes_loaded():
    reg = DataRegistry.load(DATA_DIR)
    for rid in K4_IDS:
        assert rid in (reg.recipes or {}), rid
        r = reg.recipes[rid]
        assert r.get("station") == "camp"
        out = str(r.get("output") or "")
        assert out in (reg.items or {}), f"output missing: {out}"


def test_k4_visible_at_camp_not_mystic_only_area():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4loc", "warrior", "เมษ")
    p["level"] = 12
    p["location"] = "dark_forest"
    ids = {r.get("id") for r in list_recipes(reg, p)}
    assert "craft_hunter_ration" in ids
    assert "craft_trail_stew" in ids
    # forge still blocked in forest
    assert "craft_steel_blade" not in ids


def test_craft_hunter_ration():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4h", "warrior", "เมษ")
    p["level"] = 5
    p["location"] = "dark_forest"
    p["money_world"] = 200
    add_item(p, "city_bread", reg)
    add_item(p, "herb_bundle", reg)
    add_item(p, "herb_bundle", reg)
    msg = craft(p, reg, "craft_hunter_ration", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg
    assert "hunter_ration" in (p.get("inventory_ids") or [])


def test_craft_trail_stew_chain():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4s", "warrior", "เมษ")
    p["level"] = 8
    p["location"] = "mist_marsh"
    p["money_world"] = 300
    add_item(p, "traveler_ration", reg)
    add_item(p, "herb_bundle", reg)
    add_item(p, "herb_bundle", reg)
    add_item(p, "city_bread", reg)
    msg = craft(p, reg, "craft_trail_stew", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg
    assert "trail_stew" in (p.get("inventory_ids") or [])


def test_craft_inn_feast_high_tier():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4f", "warrior", "เมษ")
    p["level"] = 12
    p["location"] = "ancient_city"  # camp also available
    p["money_world"] = 500
    add_item(p, "trail_stew", reg)
    add_item(p, "hunter_ration", reg)
    add_item(p, "herb_bundle", reg)
    add_item(p, "herb_bundle", reg)
    recipe = reg.recipes["craft_inn_feast"]
    assert station_ok_for_recipe(p, recipe, reg)
    msg = craft(p, reg, "craft_inn_feast", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg
    assert "inn_feast" in (p.get("inventory_ids") or [])


def test_inn_feast_blocked_without_station():
    """If somehow only mystic (no camp) — still OK: all areas have camp.
    Verify forge-only mountain still has camp so feast works."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4m", "warrior", "เมษ")
    p["level"] = 12
    p["location"] = "mountain_rock"
    assert "camp" in (reg.areas["mountain_rock"].get("stations") or [])
    assert station_ok_for_recipe(p, reg.recipes["craft_inn_feast"], reg)


def test_camp_cook_quests_chain():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4q", "warrior", "เมษ")
    p["level"] = 10
    ensure_quests(p, reg)
    # locked until forge_bread done
    assert "camp_cook" not in (p.get("quests") or {})
    p["quests_done"] = list(p.get("quests_done") or []) + [
        "gear_up",
        "forge_initiate",
        "forge_bread",
    ]
    # clear active to re-evaluate
    p["quests"] = {}
    ensure_quests(p, reg)
    assert "camp_cook" in (p.get("quests") or {})
    p["quests_done"] = list(p.get("quests_done") or []) + ["camp_cook"]
    p["quests"] = {}
    ensure_quests(p, reg)
    assert "camp_feast_master" in (p.get("quests") or {})


def test_mana_brew_and_balm():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k4b", "mage", "เมถุน")
    p["level"] = 6
    p["location"] = "dark_forest"
    p["money_world"] = 400
    add_item(p, "potion_hp_small", reg)
    add_item(p, "herb_bundle", reg)
    assert "สำเร็จ" in craft(p, reg, "craft_mana_brew", rng=_Ok())  # type: ignore[arg-type]
    assert "potion_mana" in (p.get("inventory_ids") or [])
    add_item(p, "potion_hp", reg)
    add_item(p, "herb_bundle", reg)
    assert "สำเร็จ" in craft(p, reg, "craft_balm", rng=_Ok())  # type: ignore[arg-type]
    assert "balm_regen" in (p.get("inventory_ids") or [])
