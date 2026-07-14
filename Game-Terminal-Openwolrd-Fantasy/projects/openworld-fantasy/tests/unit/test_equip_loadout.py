"""EL0–EL1: multi-slot loadout + grip rules."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import (
    EQUIP_SLOTS,
    add_item,
    equip_item,
    ensure_gear_fields,
    item_grip,
    migrate_equip_loadout,
    normalize_slot,
    recompute_stats,
    socket_card,
    unequip_slot,
)


def test_normalize_legacy_slots():
    assert normalize_slot("weapon") == "main_hand"
    assert normalize_slot("armor") == "body"
    assert normalize_slot("accessory") == "acc_1"
    assert normalize_slot("main_hand") == "main_hand"
    assert normalize_slot("off_hand") == "off_hand"


def test_migrate_weapon_armor_accessory():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "mig", "warrior", "มิก")
    p["equip_ids"] = {"weapon": "iron_sword", "armor": "leather_armor", "accessory": "copper_ring"}
    p["upgrade_levels"] = {"weapon": 2, "armor": 1, "accessory": 0}
    p["sockets"] = {"weapon": ["card_fire"], "armor": [], "accessory": []}
    p["equip_rarities"] = {"weapon": "rare", "armor": "common", "accessory": "common"}
    migrate_equip_loadout(p)
    assert p["equip_ids"]["main_hand"] == "iron_sword"
    assert p["equip_ids"]["body"] == "leather_armor"
    assert p["equip_ids"]["acc_1"] == "copper_ring"
    assert p["upgrade_levels"]["main_hand"] == 2
    assert p["sockets"]["main_hand"] == ["card_fire"]
    assert p["equip_rarities"]["main_hand"] == "rare"
    for s in EQUIP_SLOTS:
        assert s in p["equip_ids"]


def test_equip_one_hand_to_main():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "eq1", "warrior", "หนึ่ง")
    base = int(p["bonus_atk"])
    add_item(p, "iron_sword", reg)
    msg = equip_item(p, "iron_sword", reg)
    assert "สวม" in msg
    assert p["equip_ids"]["main_hand"] == "iron_sword"
    assert int(p["bonus_atk"]) >= base + 6


def test_dual_wield_auto_off_hand():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dual", "warrior", "คู่")
    add_item(p, "iron_sword", reg)
    add_item(p, "bandit_knife", reg)
    equip_item(p, "iron_sword", reg)
    assert p["equip_ids"]["main_hand"] == "iron_sword"
    msg = equip_item(p, "bandit_knife", reg)
    assert "สวม" in msg
    assert p["equip_ids"]["off_hand"] == "bandit_knife"
    notes = p.get("loadout_soft_notes") or []
    assert any("คู่" in n or "มือรอง" in n for n in notes)
    # off-hand ATK partial — total less than sum of full ATKs
    recompute_stats(p, reg)
    atk = int(p["bonus_atk"])
    # base ~5+ + 6 + floor(4*0.55)=2 → roughly base+8
    assert atk < 5 + 6 + 4 + 5  # not full dual stack
    assert atk >= 5 + 6 + 1


def test_two_hand_locks_and_clears_off():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "2h", "warrior", "สอง")
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    add_item(p, "oak_greatsword", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "wood_shield", reg)
    assert p["equip_ids"]["off_hand"] == "wood_shield"
    msg = equip_item(p, "oak_greatsword", reg)
    assert "สองมือ" in msg or "สวม" in msg
    assert p["equip_ids"]["main_hand"] == "oak_greatsword"
    assert p["equip_ids"]["off_hand"] in (None, "")
    # shield returned to bag
    assert "wood_shield" in (p.get("inventory_ids") or [])
    notes = p.get("loadout_soft_notes") or []
    assert any("สองมือ" in n for n in notes)


def test_shield_blocked_while_two_hand():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sh", "warrior", "โล่")
    add_item(p, "oak_greatsword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "oak_greatsword", reg)
    msg = equip_item(p, "wood_shield", reg)
    assert "ไม่ได้" in msg or "สองมือ" in msg
    assert p["equip_ids"]["off_hand"] in (None, "")
    assert "wood_shield" in (p.get("inventory_ids") or [])


def test_one_hand_plus_shield():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "1hs", "warrior", "แทงค์")
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "iron_sword", reg)
    msg = equip_item(p, "wood_shield", reg)
    assert "สวม" in msg
    assert p["equip_ids"]["main_hand"] == "iron_sword"
    assert p["equip_ids"]["off_hand"] == "wood_shield"
    notes = p.get("loadout_soft_notes") or []
    assert any("โล่" in n for n in notes)


def test_armor_parts_head_legs_feet():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "parts", "warrior", "ส่วน")
    for iid in ("iron_helm", "leather_greaves", "trail_boots", "leather_armor"):
        add_item(p, iid, reg)
        msg = equip_item(p, iid, reg)
        assert "สวม" in msg, msg
    assert p["equip_ids"]["head"] == "iron_helm"
    assert p["equip_ids"]["legs"] == "leather_greaves"
    assert p["equip_ids"]["feet"] == "trail_boots"
    assert p["equip_ids"]["body"] == "leather_armor"


def test_legacy_socket_weapon_alias():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sock", "warrior", "ซ็อก")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    add_item(p, "card_fire", reg)
    # legacy slot name still works
    msg = socket_card(p, "weapon", 0, "card_fire", reg)
    assert "ใส่" in msg
    assert (p.get("sockets") or {}).get("main_hand") == ["card_fire"]


def test_unequip_main_hand_legacy_name():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "un", "warrior", "ถอด")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    msg = unequip_slot(p, "weapon", reg)
    assert "ถอด" in msg
    assert p["equip_ids"]["main_hand"] in (None, "")


def test_item_grips_from_data():
    reg = DataRegistry.load(DATA_DIR)
    assert item_grip(reg.items["iron_sword"]) == "one_hand"
    assert item_grip(reg.items["oak_greatsword"]) == "two_hand"
    assert item_grip(reg.items["wood_shield"]) == "shield"
    assert item_grip(reg.items["focus_crystal"]) == "focus"


def test_ensure_gear_fields_creates_all_slots():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "all", "warrior", "ครบ")
    ensure_gear_fields(p)
    for s in EQUIP_SLOTS:
        assert s in p["equip_ids"]
        assert s in p["upgrade_levels"]
        assert s in p["sockets"]
