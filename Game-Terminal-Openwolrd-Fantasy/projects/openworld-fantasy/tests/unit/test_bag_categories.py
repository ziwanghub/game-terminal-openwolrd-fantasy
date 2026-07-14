"""Categorized bag hub."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item
from game.domain.inventory_sys import (
    count_bag_categories,
    format_bag_hub,
    item_category,
    list_bag_entries,
)
from game.ports.io import ScriptedIO
from game.services.bag_hub import run_bag_hub, _use_inventory_index


def test_item_categories():
    reg = DataRegistry.load(DATA_DIR)
    assert item_category("iron_sword", reg) == "equipment"
    assert item_category("potion_hp", reg) == "healing"
    assert item_category("upgrade_mat", reg) == "material"
    assert item_category("card_fire", reg) == "card"
    assert item_category("antidote", reg) == "healing"
    assert item_category("balm_regen", reg) == "healing"
    assert item_category("city_bread", reg) == "food"
    assert item_category("hunter_ration", reg) == "food"
    assert item_category("traveler_ration", reg) == "food"
    assert item_category("sealed_chest_common", reg) == "chest"
    assert item_category("sealed_chest_s", reg) == "chest"


def test_list_and_counts():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "bag", "warrior", "เมษ")
    # clear starter potion noise somewhat
    add_item(p, "iron_sword", reg)
    add_item(p, "potion_hp", reg)
    add_item(p, "city_bread", reg)
    add_item(p, "upgrade_mat", reg)
    add_item(p, "card_fire", reg)
    c = count_bag_categories(p, reg)
    assert c["equipment"] >= 1
    assert c["healing"] >= 1
    assert c["food"] >= 1
    assert c["material"] >= 1
    assert c["card"] >= 1
    eq = list_bag_entries(p, reg, "equipment")
    assert any(e["id"] == "iron_sword" for e in eq)
    heal = list_bag_entries(p, reg, "healing")
    assert any(e["id"] == "potion_hp" for e in heal)
    food = list_bag_entries(p, reg, "food")
    assert any(e["id"] == "city_bread" for e in food)


def test_hub_text_has_categories():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h", "mage", "เมถุน")
    lines = format_bag_hub(p, reg)
    text = "\n".join(lines)
    assert "รักษา" in text
    assert "อาหาร" in text
    assert "อุปกรณ์" in text
    assert "หีบ" in text
    assert "วัตถุดิบ" in text
    assert "การ์ด" in text


def test_use_healing_from_hub():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "heal", "warrior", "เมษ")
    p["hp"] = 20
    p["max_hp"] = 100
    # clear inv and add one potion
    p["inventory_ids"] = ["potion_hp"]
    p["inventory"] = ["ยา HP"]
    p["inventory_rarities"] = ["common"]
    io = ScriptedIO([])
    assert _use_inventory_index(p, reg, 0, io)
    assert p["hp"] > 20
    assert "potion_hp" not in (p.get("inventory_ids") or [])


def test_bag_hub_healing_path():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hub", "warrior", "เมษ")
    p["hp"] = 30
    p["max_hp"] = 100
    p["inventory_ids"] = ["potion_hp"]
    p["inventory"] = ["ยา HP"]
    p["inventory_rarities"] = ["common"]
    # 3 = healing (after food=2), 1 = first item, 0 = back hub, 0 = exit
    io = ScriptedIO(["3", "1", "0", "0"])
    run_bag_hub(p, reg, io)
    assert p["hp"] > 30


def test_bag_hub_food_path_reduces_hunger():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "foodbag", "warrior", "เมษ")
    from game.domain.needs import ensure_needs

    ensure_needs(p)
    p["needs"]["hunger"] = 70
    p["inventory_ids"] = ["city_bread"]
    p["inventory"] = ["ขนมปังเมือง"]
    p["inventory_rarities"] = ["common"]
    # 2 = food, 1 = eat, 0 back, 0 exit
    io = ScriptedIO(["2", "1", "0", "0"])
    run_bag_hub(p, reg, io)
    assert p["needs"]["hunger"] < 70
    assert "city_bread" not in (p.get("inventory_ids") or [])


def test_socket_card_requires_yn_confirm():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sock", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบ"]
    p["inventory_rarities"] = ["common"]
    equip_item(p, "iron_sword", reg)
    p["card_bag"] = ["card_fire"]
    # cancel with n — card menu is now 6
    io = ScriptedIO(["6", "1", "1", "1", "n", "0", "0"])
    run_bag_hub(p, reg, io)
    assert "card_fire" in (p.get("card_bag") or [])
    assert not any((p.get("sockets") or {}).get("main_hand") or [])
    assert "ยกเลิก" in io.joined()
    # confirm with y
    io2 = ScriptedIO(["6", "1", "1", "1", "y", "0", "0"])
    run_bag_hub(p, reg, io2)
    assert "card_fire" not in (p.get("card_bag") or [])
    assert (p.get("sockets") or {}).get("main_hand") == ["card_fire"]
    assert "ยืนยันใส่การ์ด" in io2.joined() or "จะใส่" in io2.joined()
