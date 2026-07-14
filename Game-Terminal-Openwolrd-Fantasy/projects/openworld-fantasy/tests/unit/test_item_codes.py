"""Short item codes + equipped manage menu."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, unequip_slot
from game.domain.inventory_sys import format_bag_hub
from game.domain.item_codes import (
    find_equipped_by_code,
    format_equipped_piece,
    item_code,
    rarity_observe_tag,
    resolve_code,
)
from game.ports.io import ScriptedIO
from game.services.bag_hub import run_bag_hub


def test_iron_sword_code_sw001():
    reg = DataRegistry.load(DATA_DIR)
    assert item_code("iron_sword", reg) == "sw001"
    assert resolve_code("sw001", reg) == "iron_sword"
    assert resolve_code("IRON_SWORD", reg) == "iron_sword"


def test_rarity_observe_has_thai_name():
    reg = DataRegistry.load(DATA_DIR)
    tag = rarity_observe_tag(reg, "common")
    assert "ธรรมดา" in tag
    assert "[" in tag


def test_hub_shows_sw001_when_equipped():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "code", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบเหล็ก"]
    p["inventory_rarities"] = ["common"]
    equip_item(p, "iron_sword", reg)
    text = "\n".join(format_bag_hub(p, reg))
    assert "sw001" in text
    assert "ดาบเหล็ก" in text
    assert "ธรรมดา" in text
    assert "พิมพ์ไอดี" in text or "sw001" in text


def test_manage_sw001_unequip():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "uneq", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบเหล็ก"]
    p["inventory_rarities"] = ["common"]
    equip_item(p, "iron_sword", reg)
    assert (p.get("equip_ids") or {}).get("main_hand") == "iron_sword"
    # hub → sw001 → 1 unequip → y confirm → 0 exit
    io = ScriptedIO(["sw001", "1", "y", "0"])
    run_bag_hub(p, reg, io)
    assert (p.get("equip_ids") or {}).get("main_hand") in (None, "")
    assert "iron_sword" in (p.get("inventory_ids") or [])
    assert "ถอด" in io.joined() or "sw001" in io.joined()


def test_manage_menu_options_shown():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "menu", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบ"]
    p["inventory_rarities"] = ["common"]
    equip_item(p, "iron_sword", reg)
    # open manage, back with 2, exit hub
    io = ScriptedIO(["sw001", "2", "0"])
    run_bag_hub(p, reg, io)
    out = io.joined()
    assert "ถอดออก" in out
    assert "ย้อนกลับ" in out
    assert "อัพเกรด" in out or "อัป" in out
    assert "ขาย" in out
    assert "ทิ้ง" in out
    assert find_equipped_by_code(p, reg, "sw001") is not None


def test_unequip_api():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "api", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    msg = unequip_slot(p, "weapon", reg)  # legacy alias
    assert "ถอด" in msg
    assert p["equip_ids"]["main_hand"] is None
