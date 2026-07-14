from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.boss import can_challenge_boss, spawn_boss
from game.domain.character import create_player
from game.domain.craft import craft, list_recipes
from game.domain.equipment import add_item
from game.domain.quests import ensure_quests
import random


def test_bosses_and_area_links():
    reg = DataRegistry.load(DATA_DIR)
    assert "boss_forest_king" in reg.monsters
    assert reg.areas["dark_forest"].get("boss_id") == "boss_forest_king"
    mon = spawn_boss(reg, "dark_forest", random.Random(1))
    assert mon and mon.get("boss") and mon["hp"] > 100


def test_boss_level_gate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "b", "warrior", "เมษ")
    p["level"] = 1
    ok, msg = can_challenge_boss(p, reg, "dark_forest")
    assert ok is False
    p["level"] = 10
    ok2, _ = can_challenge_boss(p, reg, "dark_forest")
    assert ok2 is True


def test_craft_potion():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c", "warrior", "เมษ")
    add_item(p, "potion_hp_small", reg)
    add_item(p, "potion_hp_small", reg)
    p["money_world"] = 100
    recipes = list_recipes(reg, p)
    assert any(r.get("id") == "craft_potion_bundle" for r in recipes)
    msg = craft(p, reg, "craft_potion_bundle")
    assert "สำเร็จ" in msg


def test_quest_depends_on():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "d", "warrior", "เมษ")
    ensure_quests(p, reg)
    # card_socket depends on gear_up — should not be active yet
    assert "card_socket" not in p["quests"]
    p["quests_done"] = ["gear_up"]
    ensure_quests(p, reg)
    assert "card_socket" in p["quests"]
