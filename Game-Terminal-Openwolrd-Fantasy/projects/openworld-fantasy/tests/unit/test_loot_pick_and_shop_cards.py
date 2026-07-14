"""Loot pick (A / comma) · shops never sell cards · card combat drops."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.inventory_sys import (
    build_combat_loot_table,
    parse_loot_indices,
    present_loot_choices,
    resolve_loot_pick,
)
from game.services.shop import _is_shop_banned_card, _normalize_stock


def test_parse_loot_all_and_comma():
    assert parse_loot_indices("A", 4) == [1, 2, 3, 4]
    assert parse_loot_indices("all", 3) == [1, 2, 3]
    assert parse_loot_indices("ทั้งหมด", 2) == [1, 2]
    assert parse_loot_indices("1,3", 4) == [1, 3]
    assert parse_loot_indices("1, 2, 4", 4) == [1, 2, 4]
    assert parse_loot_indices("2 3", 4) == [2, 3]
    assert parse_loot_indices("0", 3) == []
    assert parse_loot_indices("", 3) == []
    assert parse_loot_indices("9", 3) == []  # out of range ignored


def test_present_loot_shows_a_and_comma_hint():
    lines = present_loot_choices(
        [{"id": "a", "name": "ของ1"}, {"id": "b", "name": "ของ2"}]
    )
    text = "\n".join(lines)
    assert "A" in text or "ทั้งหมด" in text
    assert "," in text or "comma" in text.lower()


def test_resolve_loot_pick_all():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "la", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    drops = [
        {"id": "upgrade_mat", "name": "mat", "rarity": "common"},
        {"id": "potion_hp_small", "name": "ยา", "rarity": "common"},
    ]
    notes = resolve_loot_pick(p, reg, drops, "A")
    assert any("เก็บ" in n for n in notes)
    ids = p.get("inventory_ids") or []
    assert "upgrade_mat" in ids
    assert "potion_hp_small" in ids


def test_resolve_loot_pick_subset_comma():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "lb", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    drops = [
        {"id": "upgrade_mat", "name": "mat"},
        {"id": "potion_hp_small", "name": "ยา"},
        {"id": "herb_bundle", "name": "สมุนไพร"},
    ]
    notes = resolve_loot_pick(p, reg, drops, "1,3")
    assert any("เก็บ" in n for n in notes)
    ids = p.get("inventory_ids") or []
    assert "upgrade_mat" in ids
    assert "herb_bundle" in ids
    assert "potion_hp_small" not in ids


def test_resolve_loot_pick_none():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "lc", "warrior", "เมษ")
    before = list(p.get("inventory_ids") or [])
    notes = resolve_loot_pick(
        p, reg, [{"id": "upgrade_mat", "name": "m"}], "0"
    )
    assert "ทิ้ง" in notes[0]
    assert list(p.get("inventory_ids") or []) == before


def test_shops_have_no_cards_in_stock():
    reg = DataRegistry.load(DATA_DIR)
    for sid, shop in (reg.shops or {}).items():
        stock = _normalize_stock(shop, reg=reg)
        for row in stock:
            iid = str(row.get("id") or "")
            assert not _is_shop_banned_card(reg, iid), f"{sid} still sells {iid}"
            assert not iid.startswith("card_"), sid


def test_card_can_drop_from_combat_table():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cd", "mage", "เมถุน")
    mon = {
        "id": "boss_test",
        "name": "ทดสอบ",
        "boss": True,
        "elements": ["fire", "shadow"],
        "level": 10,
    }
    # high card chance with many rolls
    found = False
    for seed in range(80):
        loot = build_combat_loot_table(p, mon, reg, random.Random(seed))
        if any(
            str(d.get("id") or "").startswith("card_")
            or str(d.get("id") or "") in (reg.cards or {})
            for d in loot
        ):
            found = True
            break
    assert found, "expected card drop within 80 boss loot rolls"


def test_pick_card_goes_to_card_bag():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cb", "mage", "เมถุน")
    p["card_bag"] = []
    drops = [{"id": "card_fire", "name": "การ์ดไฟ", "rarity": "uncommon"}]
    notes = resolve_loot_pick(p, reg, drops, "A")
    assert "card_fire" in (p.get("card_bag") or [])
    assert any("การ์ด" in n or "เก็บ" in n for n in notes)
