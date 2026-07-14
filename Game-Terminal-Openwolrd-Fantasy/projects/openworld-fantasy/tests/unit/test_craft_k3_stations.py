"""K3: craft stations bound to areas."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.craft import (
    craft,
    count_recipes_elsewhere,
    format_stations_line,
    list_recipes,
    station_ok_for_recipe,
    stations_at_location,
)
from game.domain.equipment import add_item


class _Ok:
    def random(self) -> float:
        return 0.0


def test_area_stations_data():
    reg = DataRegistry.load(DATA_DIR)
    assert "camp" in (reg.areas["dark_forest"].get("stations") or [])
    assert "forge" in (reg.areas["ancient_city"].get("stations") or [])
    assert "mystic" in (reg.areas["ancient_city"].get("stations") or [])
    assert "forge" in (reg.areas["mountain_rock"].get("stations") or [])
    assert "mystic" in (reg.areas["cave_shadow"].get("stations") or [])


def test_starter_forest_has_camp_only_forge_blocked():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k3a", "warrior", "เมษ")
    assert p["location"] == "dark_forest"
    st = stations_at_location(p, reg)
    assert st == ["camp"]
    recipes = list_recipes(reg, p, require_station=True)
    ids = {r.get("id") for r in recipes}
    assert "craft_potion_bundle" in ids
    assert "craft_steel_blade" not in ids
    assert count_recipes_elsewhere(reg, p) >= 1


def test_forge_recipe_requires_city_or_mountain():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k3b", "warrior", "เมษ")
    p["level"] = 10
    p["money_world"] = 500
    add_item(p, "iron_sword", reg, rarity="uncommon")
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    add_item(p, "rare_mat", reg)
    recipe = reg.recipes["craft_steel_blade"]
    assert station_ok_for_recipe(p, recipe, reg) is False
    msg = craft(p, reg, "craft_steel_blade", rng=_Ok())  # type: ignore[arg-type]
    assert "สถานี" in msg
    assert "steel_blade" not in (p.get("inventory_ids") or [])

    p["location"] = "ancient_city"
    assert station_ok_for_recipe(p, recipe, reg) is True
    msg2 = craft(p, reg, "craft_steel_blade", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg2
    assert "steel_blade" in (p.get("inventory_ids") or [])


def test_mountain_has_forge():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k3c", "warrior", "เมษ")
    p["location"] = "mountain_rock"
    p["level"] = 10
    recipes = list_recipes(reg, p)
    assert any(r.get("id") == "craft_steel_blade" for r in recipes)
    assert any(r.get("station") == "camp" for r in recipes)


def test_mystic_at_cave():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k3d", "mage", "เมถุน")
    p["location"] = "cave_shadow"
    p["level"] = 12
    recipes = list_recipes(reg, p)
    assert any(r.get("station") == "mystic" for r in recipes)
    assert not any(r.get("station") == "forge" for r in recipes)


def test_stations_line_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "k3e", "warrior", "เมษ")
    p["location"] = "ancient_city"
    line = format_stations_line(p, reg)
    assert "เมือง" in line or "ancient" in line.lower()
    assert "หลอม" in line or "forge" in line.lower()
