"""Upgrade preview sheet + conditional upgrade menu."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item
from game.domain.inventory_sys import (
    can_upgrade_equipped,
    format_upgrade_preview,
)
from game.ports.io import ScriptedIO
from game.services.bag_hub import run_bag_hub


def test_can_upgrade_when_below_cap():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "up1", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    assert can_upgrade_equipped(p, "main_hand") is True
    p["upgrade_levels"] = {"main_hand": 10, "body": 0, "acc_1": 0}
    assert can_upgrade_equipped(p, "main_hand") is False
    assert can_upgrade_equipped(p, "body") is False  # empty slot


def test_preview_lists_materials_and_money():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "prev", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    add_item(p, "upgrade_mat", reg)
    p["money_world"] = 500
    lines = format_upgrade_preview(p, "main_hand", reg)
    text = "\n".join(lines)
    assert "พิธีอัปเกรด" in text
    assert "เงินโลก" in text
    assert "วัสดุ" in text or "upgrade_mat" in text
    assert "sw001" in text or "ดาบ" in text
    assert "✓" in text or "✗" in text


def test_manage_hides_upgrade_at_cap():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cap", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    p["upgrade_levels"] = {"main_hand": 10, "body": 0, "acc_1": 0}
    io = ScriptedIO(["sw001", "2", "0"])
    run_bag_hub(p, reg, io)
    out = io.joined()
    # menu should not offer upgrade line as selectable path clearly
    assert "ถึงขีด" in out or "อัปต่อไม่ได้" in out
    # when at cap, "3. อัพเกรด" should not appear
    assert "3. อัพเกรด" not in out


def test_upgrade_flow_shows_preview_then_cancel():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "flow", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    p["money_world"] = 200
    add_item(p, "upgrade_mat", reg)
    money0 = int(p["money_world"])
    # sw001 → 3 upgrade → n cancel → 0 exit
    io = ScriptedIO(["sw001", "3", "n", "0"])
    run_bag_hub(p, reg, io)
    assert int(p["money_world"]) == money0
    assert (p.get("upgrade_levels") or {}).get("main_hand", 0) == 0
    out = io.joined()
    assert "พิธีอัปเกรด" in out
    assert "ยืนยัน" in out
    assert "ยกเลิก" in out
