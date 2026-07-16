"""WO-ITEM-1..4: loot identity, mid gear, economy sink, gear identity."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import sell_price
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.inventory_sys import build_combat_loot_table
from game.domain.monster_drops import mon_drop_entries


def test_generic_loot_reduced_when_table_thick():
    reg = DataRegistry.load(DATA_DIR)
    # pick a mon with many drop rows
    mon_id = "forest_wolf"
    base = dict(reg.monsters[mon_id])
    assert len(mon_drop_entries(base)) >= 2
    p = create_player(reg, "L1", "warrior", "เมษ")
    thick_generic = 0
    thin_generic = 0
    n = 80
    for i in range(n):
        mon = dict(base)
        mon["level"] = 3
        loot = build_combat_loot_table(p, mon, reg, random.Random(i))
        # generic sources
        g = sum(
            1
            for d in loot
            if "สำรอง" in str(d.get("note") or "") or str(d.get("source") or "") == "สำรองสนาม"
        )
        thick_generic += g
    # mon without table
    empty = {
        "id": "no_table_test",
        "name": "ว่าง",
        "level": 1,
        "elements": ["physical"],
        "drops": [],
    }
    for i in range(n):
        loot = build_combat_loot_table(p, empty, reg, random.Random(i + 1000))
        g = sum(
            1
            for d in loot
            if d.get("id") in ("upgrade_mat", "rare_mat", "potion_hp_small", "potion_mana")
        )
        thin_generic += g
    # thick mon table should yield fewer generic pieces on average
    assert thick_generic < thin_generic * 0.85


def test_loot_has_soft_source_hint():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L2", "warrior", "เมษ")
    mon = dict(reg.monsters["goblin_hunter"])
    mon["level"] = 2
    found_src = False
    for i in range(40):
        loot = build_combat_loot_table(p, mon, reg, random.Random(i))
        for d in loot:
            note = str(d.get("note") or "")
            if any(k in note for k in ("จากมอน", "ชิ้นส่วน", "สำรอง", "การ์ด", "จากบอส")):
                found_src = True
                break
        if found_src:
            break
    assert found_src


def test_no_percent_in_loot_notes():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L3", "warrior", "เมษ")
    mon = dict(reg.monsters["forest_wolf"])
    for i in range(20):
        loot = build_combat_loot_table(p, mon, reg, random.Random(i))
        for d in loot:
            note = str(d.get("note") or "")
            assert "%" not in note
            assert "0.48" not in note


def test_mid_gear_exists_and_sets():
    reg = DataRegistry.load(DATA_DIR)
    assert "mid_forest_thorn_blade" in reg.items
    assert "mid_desert_sun_scimitar" in reg.items
    assert "forest_thorn" in (reg.gear_sets or {})
    assert "desert_sun" in (reg.gear_sets or {})


def test_mid_set_bonus_applies():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L4", "warrior", "เมษ")
    add_item(p, "mid_forest_thorn_blade", reg, rarity="uncommon")
    add_item(p, "mid_forest_bark_mail", reg, rarity="uncommon")
    # clear equip first
    p["equip_ids"] = {}
    equip_item(p, "mid_forest_thorn_blade", reg)
    equip_item(p, "mid_forest_bark_mail", reg)
    recompute_stats(p, reg)
    assert p.get("gear_primary_element") == "nature" or "nature" in (p.get("gear_tags") or [])
    # set atk bonus should raise atk vs base-ish
    assert int(p.get("bonus_atk") or 0) >= 10


def test_mat_sell_softer_than_default():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L5", "warrior", "เมษ")
    base = 50
    # equipment-like default path
    eq = sell_price(base, reg, p, rarity="common")
    mat = sell_price(
        base, reg, p, rarity="common", item_kind="material", item_id="upgrade_mat"
    )
    assert mat <= eq
    assert mat < eq  # sink active


def test_empty_table_still_has_soft_floor():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L6", "warrior", "เมษ")
    mon = {"id": "ghost_empty", "name": "x", "level": 1, "drops": [], "elements": []}
    # force no rolls by using mon with empty table and seed that fails generic? 
    # with gen_scale 1.0 should often get something; floor guarantees after many tries
    any_loot = False
    for i in range(30):
        loot = build_combat_loot_table(p, mon, reg, random.Random(i))
        if loot:
            any_loot = True
            break
    assert any_loot


def test_mat_sell_flows_through_bag_offer():
    """WO-ITEM-3: bag sell path must pass item_kind so mat sink applies."""
    from game.domain.bag_sell import compute_sell_offer
    from game.domain.balance import sell_price

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L7", "warrior", "เมษ")
    mat_offer = compute_sell_offer(p, reg, "upgrade_mat", "common", qty=1)
    assert mat_offer is not None
    assert int(mat_offer["unit_price"]) >= 1
    base = 50
    m = sell_price(base, reg, p, rarity="common", item_kind="material", item_id="upgrade_mat")
    e = sell_price(base, reg, p, rarity="common", item_kind="equipment", item_id="iron_sword")
    assert m < e
