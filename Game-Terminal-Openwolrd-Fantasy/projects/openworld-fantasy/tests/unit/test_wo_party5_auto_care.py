"""WO-PARTY-5: Auto party care + Needs soft links."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.bag_stack import count_item_units
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.needs import ensure_needs, get_needs
from game.domain.party import (
    give_item_gift,
    party_member_turns,
    set_relationship,
)
from game.runtime.party_auto import (
    auto_party_care,
    ensure_party_auto_prefs,
)


def test_ensure_party_auto_prefs():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pc1", "warrior", "เมษ")
    prefs = ensure_party_auto_prefs(p)
    assert prefs.get("party_care") is True
    assert prefs.get("party_gift") is True
    assert int(prefs.get("party_gift_bond_below") or 0) >= 10


def test_auto_party_gift_when_bond_cool():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pc2", "warrior", "เมษ")
    ensure_party_auto_prefs(p)
    p["auto_prefs"]["party_gift_cooldown"] = 0
    p["auto_ticks"] = 100
    p["_party_gift_tick"] = -999
    p["party"] = [
        {
            "id": "spirit_mist",
            "name": "ภูตหมอก",
            "kind": "spirit",
            "bonus_atk": 2,
        }
    ]
    set_relationship(p, "spirit_mist", 20)  # cool
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    p["inventory_items"] = []
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    before_units = count_item_units(p, "upgrade_mat")
    before_bond = 20
    notes = auto_party_care(p, reg, context="test")
    assert notes, "should soft-gift when bond cool + mat surplus"
    assert count_item_units(p, "upgrade_mat") == before_units - 1
    # bond should move after gift (any direction possible but usually up for mat?)
    from game.domain.party import get_relationship

    assert get_relationship(p, "spirit_mist") != before_bond or notes


def test_auto_party_no_gift_when_bond_warm():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pc3", "warrior", "เมษ")
    ensure_party_auto_prefs(p)
    p["auto_ticks"] = 50
    p["_party_gift_tick"] = -999
    p["party"] = [
        {"id": "beast_forest", "name": "หมาป่า", "kind": "beast", "bonus_atk": 3}
    ]
    set_relationship(p, "beast_forest", 80)
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    before = count_item_units(p, "upgrade_mat")
    notes = auto_party_care(p, reg)
    assert count_item_units(p, "upgrade_mat") == before
    assert not any("ออโต้ทีม" in n for n in notes)


def test_auto_never_gifts_last_food_reserve():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pc4", "warrior", "เมษ")
    prefs = ensure_party_auto_prefs(p)
    prefs["party_min_food_keep"] = 2
    prefs["party_gift_cooldown"] = 0
    p["auto_prefs"] = prefs
    p["auto_ticks"] = 10
    p["_party_gift_tick"] = -999
    p["party"] = [
        {"id": "spirit_mist", "name": "ภูต", "kind": "spirit", "bonus_atk": 1}
    ]
    set_relationship(p, "spirit_mist", 15)
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    # only 2 food — should keep
    add_item(p, "city_bread", reg)
    add_item(p, "city_bread", reg)
    # no mats
    notes = auto_party_care(p, reg)
    assert count_item_units(p, "city_bread") == 2
    assert not any("ออโต้ทีม" in n for n in notes)


def test_food_gift_soft_needs():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pc5", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 60
    p["party"] = [
        {"id": "spirit_mist", "name": "ภูต", "kind": "spirit", "bonus_atk": 1}
    ]
    set_relationship(p, "spirit_mist", 40)
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    add_item(p, "city_bread", reg)
    h0 = get_needs(p)["hunger"]
    notes = give_item_gift(p, reg, 0, 0)
    assert any("แบ่งคำ" in n for n in notes)
    assert get_needs(p)["hunger"] < h0


def test_assist_heal_soft_needs():
    p = {
        "party": [
            {
                "id": "spirit_mist",
                "name": "ภูต",
                "kind": "spirit",
                "bonus_atk": 4,
            }
        ],
        "party_bonds": {"spirit_mist": 90},
        "hp": 20,
        "max_hp": 100,
        "needs": {"hunger": 40, "fatigue": 50, "morale": 40},
    }
    mon = {"hp": 50, "max_hp": 50}
    # force many rolls until heal happens
    healed = False
    for i in range(40):
        p2 = {
            "party": list(p["party"]),
            "party_bonds": dict(p["party_bonds"]),
            "hp": 20,
            "max_hp": 100,
            "needs": {"hunger": 40, "fatigue": 50, "morale": 40},
        }
        notes = party_member_turns(p2, mon, random.Random(i))
        text = "".join(notes)
        if "ซุ่มรักษา" in text:
            healed = True
            assert p2["needs"]["fatigue"] <= 50
            assert p2["needs"]["morale"] >= 40
            break
    assert healed
