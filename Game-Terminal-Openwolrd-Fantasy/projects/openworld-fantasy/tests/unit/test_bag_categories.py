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


def test_list_and_counts():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "bag", "warrior", "เมษ")
    # clear starter potion noise somewhat
    add_item(p, "iron_sword", reg)
    add_item(p, "potion_hp", reg)
    add_item(p, "upgrade_mat", reg)
    add_item(p, "card_fire", reg)
    c = count_bag_categories(p, reg)
    assert c["equipment"] >= 1
    assert c["healing"] >= 1
    assert c["material"] >= 1
    assert c["card"] >= 1
    eq = list_bag_entries(p, reg, "equipment")
    assert any(e["id"] == "iron_sword" for e in eq)
    heal = list_bag_entries(p, reg, "healing")
    assert any(e["id"] == "potion_hp" for e in heal)


def test_hub_text_has_categories():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h", "mage", "เมถุน")
    lines = format_bag_hub(p, reg)
    text = "\n".join(lines)
    assert "รักษา" in text
    assert "อุปกรณ์" in text
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
    # 2 = healing, 1 = first item, 0 = back hub, 0 = exit
    io = ScriptedIO(["2", "1", "0", "0"])
    run_bag_hub(p, reg, io)
    assert p["hp"] > 30


def test_socket_card_requires_yn_confirm():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sock", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบ"]
    p["inventory_rarities"] = ["common"]
    equip_item(p, "iron_sword", reg)
    p["card_bag"] = ["card_fire"]
    # cancel with n
    io = ScriptedIO(["4", "1", "1", "1", "n", "0", "0"])
    run_bag_hub(p, reg, io)
    assert "card_fire" in (p.get("card_bag") or [])
    assert not any((p.get("sockets") or {}).get("weapon") or [])
    assert "ยกเลิก" in io.joined()
    # confirm with y
    io2 = ScriptedIO(["4", "1", "1", "1", "y", "0", "0"])
    run_bag_hub(p, reg, io2)
    assert "card_fire" not in (p.get("card_bag") or [])
    assert (p.get("sockets") or {}).get("weapon") == ["card_fire"]
    assert "ยืนยันใส่การ์ด" in io2.joined() or "จะใส่" in io2.joined()
