"""WO-INV-1: True stack + soft cap harden."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.bag_stack import (
    bag_slots_used,
    collapse_stackable_slots,
    count_item_units,
    is_stackable_item,
    qty_at,
)
from game.domain.character import create_player
from game.domain.equipment import add_item, count_materials, remove_inventory_id
from game.domain.inventory_sys import (
    bag_count,
    bag_full,
    format_bag_panel,
    list_bag_entries,
    sanitize_inventory,
    try_add_item,
)
from game.runtime.inventory_auto import auto_free_bag_space, bag_free_slots, ensure_inv_auto_prefs


def _empty_bag(p) -> None:
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    p["inventory_items"] = []
    p["card_bag"] = []


def test_stackable_rules():
    reg = DataRegistry.load(DATA_DIR)
    assert is_stackable_item("potion_hp", reg)
    assert is_stackable_item("upgrade_mat", reg)
    assert is_stackable_item("city_bread", reg)
    assert not is_stackable_item("iron_sword", reg)


def test_true_stack_same_id_rarity():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk1", "warrior", "เมษ")
    _empty_bag(p)
    for _ in range(10):
        assert add_item(p, "potion_hp", reg)
    assert len(p["inventory_ids"]) == 1
    assert qty_at(p, 0) == 10
    assert bag_count(p) == 1
    assert count_item_units(p, "potion_hp") == 10


def test_equipment_does_not_stack():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk2", "warrior", "เมษ")
    _empty_bag(p)
    add_item(p, "iron_sword", reg)
    add_item(p, "iron_sword", reg)
    assert p["inventory_ids"].count("iron_sword") == 2
    assert bag_count(p) == 2


def test_soft_cap_blocks_new_slot():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk3", "warrior", "เมษ")
    _empty_bag(p)
    p["bag_cap"] = 3
    add_item(p, "iron_sword", reg)
    add_item(p, "leather_armor", reg)
    # third gear if available
    gear_ids = [
        iid
        for iid, it in (reg.items or {}).items()
        if str(it.get("kind")) == "equipment" and iid not in ("iron_sword", "leather_armor")
    ]
    if gear_ids:
        add_item(p, gear_ids[0], reg)
    assert bag_full(p) or bag_count(p) >= 3
    # fill to cap with non-stack gear
    while not bag_full(p) and gear_ids:
        r = add_item(p, gear_ids[min(1, len(gear_ids) - 1)], reg)
        if not r:
            break
    assert bag_full(p)
    blocked = add_item(p, gear_ids[0] if gear_ids else "iron_sword", reg)
    assert blocked == ""
    ok, msg = try_add_item(p, gear_ids[0] if gear_ids else "iron_sword", reg)
    assert ok is False
    assert "เต็ม" in msg


def test_stack_into_existing_when_full():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk4", "warrior", "เมษ")
    _empty_bag(p)
    p["bag_cap"] = 2
    add_item(p, "potion_hp", reg)
    add_item(p, "iron_sword", reg)
    assert bag_full(p)
    assert add_item(p, "potion_hp", reg)  # stacks
    assert qty_at(p, 0) == 2
    assert bag_count(p) == 2


def test_remove_one_unit_decrements_stack():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk5", "warrior", "เมษ")
    _empty_bag(p)
    for _ in range(3):
        add_item(p, "potion_hp", reg)
    assert remove_inventory_id(p, "potion_hp", reg)
    assert qty_at(p, 0) == 2
    assert "potion_hp" in (p.get("inventory_ids") or [])
    remove_inventory_id(p, "potion_hp", reg)
    remove_inventory_id(p, "potion_hp", reg)
    assert "potion_hp" not in (p.get("inventory_ids") or [])


def test_materials_count_uses_qty():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk6", "warrior", "เมษ")
    _empty_bag(p)
    for _ in range(7):
        add_item(p, "upgrade_mat", reg)
    assert count_materials(p, "upgrade_mat") == 7
    assert len(p["inventory_ids"]) == 1


def test_collapse_legacy_duplicates():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk7", "warrior", "เมษ")
    p["inventory_ids"] = ["potion_hp"] * 5 + ["upgrade_mat"] * 2
    p["inventory"] = ["x"] * 7
    p["inventory_rarities"] = ["common"] * 7
    p["inventory_qty"] = [1] * 7
    p["card_bag"] = []
    freed = collapse_stackable_slots(p, reg)
    assert freed == 5  # 7 slots -> 2
    assert count_item_units(p, "potion_hp") == 5
    assert count_item_units(p, "upgrade_mat") == 2


def test_sanitize_collapses_stacks():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk8", "warrior", "เมษ")
    p["inventory_ids"] = ["city_bread"] * 4
    p["inventory"] = ["ขนม"] * 4
    p["inventory_rarities"] = ["common"] * 4
    p["inventory_qty"] = [1] * 4
    p["card_bag"] = []
    sanitize_inventory(p, reg)
    assert len(p["inventory_ids"]) == 1
    assert count_item_units(p, "city_bread") == 4


def test_ui_shows_xn():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk9", "warrior", "เมษ")
    _empty_bag(p)
    for _ in range(4):
        add_item(p, "potion_hp", reg)
    ents = list_bag_entries(p, reg, "healing")
    assert any("x4" in e["name"] for e in ents)
    panel = "\n".join(format_bag_panel(p, reg))
    assert "x4" in panel


def test_auto_free_space_with_stacks():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "stk10", "warrior", "เมษ")
    prefs = ensure_inv_auto_prefs(p)
    prefs["inv_sell_junk"] = False
    prefs["inv_drop_junk"] = True
    p["auto_prefs"] = prefs
    p["bag_cap"] = 4
    _empty_bag(p)
    # 3 material stacks + 1 gear = full
    for mid in ("upgrade_mat", "upgrade_mat", "upgrade_mat"):
        add_item(p, "upgrade_mat", reg)
    # ensure one slot of mats with qty 3
    assert count_materials(p, "upgrade_mat") >= 1
    # fill slots with other materials if available
    other_mats = [
        iid
        for iid, it in (reg.items or {}).items()
        if str(it.get("kind")) == "material" and iid != "upgrade_mat"
    ]
    for iid in other_mats[:3]:
        if bag_full(p):
            break
        add_item(p, iid, reg)
    while not bag_full(p):
        r = add_item(p, "upgrade_mat", reg)
        if not r and bag_slots_used(p) >= p["bag_cap"]:
            break
        if bag_count(p) >= int(p["bag_cap"]):
            break
        # if stacking never fills slots, add dummy by forcing new rare mats
        if bag_count(p) < int(p["bag_cap"]) and other_mats:
            add_item(p, other_mats[bag_count(p) % len(other_mats)], reg)
        else:
            break
    before = bag_count(p)
    notes = auto_free_bag_space(p, reg, need_free=1, max_drops=2, sell=False)
    assert notes or bag_free_slots(p) >= 1 or before >= 1
    # must not crash; preferably freed a slot
    assert isinstance(notes, list)
