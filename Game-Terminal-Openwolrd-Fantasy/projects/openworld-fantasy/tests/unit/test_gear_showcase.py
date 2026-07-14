"""Rarity-tiered equipment text showcase."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.inventory_sys import examine_item, format_category_list
from game.ports.io import ScriptedIO
from game.services.bag_hub import _resolve_equipment_pick, run_bag_hub
from game.ui_terminal.gear_showcase import (
    format_equipment_list_line,
    format_gear_showcase,
)


def test_list_line_shows_id_and_level():
    reg = DataRegistry.load(DATA_DIR)
    line = format_equipment_list_line(
        1, "iron_sword", "ดาบเหล็ก [○ธรรมดา]", "common", reg, hint="ATK+6"
    )
    assert "sw001" in line or "iron_sword" in line
    assert "Lv.1" in line
    assert "ธรรมดา" in line or "○" in line


def test_common_showcase_has_id_and_level():
    reg = DataRegistry.load(DATA_DIR)
    lines = format_gear_showcase("iron_sword", reg, rarity="common")
    text = "\n".join(lines)
    assert "iron_sword" in text
    assert "Lv.1" in text
    assert "ดาบ" in text or "เหล็ก" in text
    # plain frame
    assert "┌" in text or "│" in text


def test_legendary_more_ornate_than_common():
    reg = DataRegistry.load(DATA_DIR)
    common = "\n".join(format_gear_showcase("iron_sword", reg, rarity="common"))
    legend = "\n".join(format_gear_showcase("iron_sword", reg, rarity="legendary"))
    mythic = "\n".join(format_gear_showcase("iron_sword", reg, rarity="mythic"))
    assert "Lv.5" in legend
    assert "ตำนาน" in legend or "✦" in legend
    assert len(legend) > len(common)
    assert "Lv.8" in mythic
    assert "ปฐม" in mythic or "◈" in mythic
    assert len(mythic) >= len(legend)


def test_examine_equipment_uses_showcase():
    reg = DataRegistry.load(DATA_DIR)
    lines = examine_item("iron_sword", reg, rarity="rare")
    text = "\n".join(lines)
    assert "ไอดี" in text or "iron_sword" in text
    assert "Lv.3" in text or "หายาก" in text
    assert "วิธีใช้" in text


def test_category_list_equipment_shows_id():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "gs", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบเหล็ก"]
    p["inventory_rarities"] = ["common"]
    lines = format_category_list(p, reg, "equipment")
    text = "\n".join(lines)
    assert "sw001" in text or "iron_sword" in text
    assert "Lv.1" in text


def test_resolve_pick_by_id():
    reg = DataRegistry.load(DATA_DIR)
    entries = [
        {"index": 0, "id": "iron_sword", "name": "ดาบเหล็ก", "rarity": "common"},
        {"index": 2, "id": "steel_blade", "name": "ดาบเหล็กกล้า", "rarity": "uncommon"},
    ]
    assert _resolve_equipment_pick(entries, "1", reg)["id"] == "iron_sword"
    assert _resolve_equipment_pick(entries, "iron_sword", reg)["id"] == "iron_sword"
    assert _resolve_equipment_pick(entries, "sw001", reg)["id"] == "iron_sword"
    assert _resolve_equipment_pick(entries, "IRON_SWORD", reg)["id"] == "iron_sword"
    assert _resolve_equipment_pick(entries, "steel", reg)["id"] == "steel_blade"
    assert _resolve_equipment_pick(entries, "99", reg) is None


def test_bag_hub_type_id_examine():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hubid", "warrior", "เมษ")
    p["inventory_ids"] = ["iron_sword"]
    p["inventory"] = ["ดาบเหล็ก"]
    p["inventory_rarities"] = ["legendary"]
    # 1 equip cat → type iron_sword → skip equip → leave cat → leave hub
    io = ScriptedIO(["1", "iron_sword", "0", "0", "0"])
    run_bag_hub(p, reg, io)
    out = io.joined()
    assert "iron_sword" in out
    assert "Lv.5" in out or "ตำนาน" in out
