import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.inventory_sys import (
    bag_full,
    build_combat_loot_table,
    examine_item,
    format_equip_panel,
    resolve_loot_pick,
    try_add_item,
    upgrade_equipped_opaque,
    upgrade_success_chance,
)
from game.domain.party import (
    add_member,
    call_party_power,
    ensure_party,
    format_party_panel,
    max_party_size,
    member_from_template,
    try_consent_player_hire,
)


def test_party_max_three():
    reg = DataRegistry.load(DATA_DIR)
    assert max_party_size(reg) == 3
    p = create_player(reg, "pt", "warrior", "เมษ")
    ensure_party(p)
    templates = (reg.party or {}).get("templates") or []
    assert len(templates) >= 3
    for t in templates[:3]:
        msg = add_member(p, member_from_template(t), reg)
        assert "ร่วม" in msg or "เต็ม" in msg
    assert len(p["party"]) == 3
    msg = add_member(p, member_from_template(templates[0]), reg)
    assert "เต็ม" in msg


def test_call_party_is_free_relationship_info():
    """Call is free — no mana/gold; assists auto by relationship."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "call", "mage", "เมถุน")
    t = (reg.party or {}).get("templates")[0]
    add_member(p, member_from_template(t), reg)
    p["mana"] = 100
    p["max_mana"] = 100
    p["money_world"] = 50
    before_m, before_g = p["mana"], p["money_world"]
    ok, msg, bon = call_party_power(p, reg, 0)
    assert ok
    assert p["mana"] == before_m
    assert p["money_world"] == before_g
    assert "มานา" in msg or "ไม่เสีย" in msg or "ซุ่ม" in msg or "สัมพันธ์" in msg
    assert bon.get("atk", 0) >= 0


def test_player_hire_consent_can_fail():
    reg = DataRegistry.load(DATA_DIR)
    a = create_player(reg, "A", "warrior", "เมษ")
    b = create_player(reg, "B", "rogue", "พิจิก")
    # very low affinity
    ok, why = try_consent_player_hire(a, b, reg, affinity=-0.5, rng=random.Random(1))
    assert not ok


def test_examine_item_has_howto():
    reg = DataRegistry.load(DATA_DIR)
    lines = examine_item("iron_sword", reg)
    # soft: action/howto section may say "การกระทำ" or "วิธีใช้"
    assert any("การกระทำ" in x or "วิธีใช้" in x for x in lines)
    assert any("ดาบ" in x or "iron" in x.lower() for x in lines)


def test_loot_pick_and_bag():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "loot", "archer", "ตุลย์")
    drops = [
        {"id": "upgrade_mat", "name": "วัสดุอัพเกรด"},
        {"id": "potion_hp_small", "name": "ยา"},
    ]
    notes = resolve_loot_pick(p, reg, drops, "1,2")
    assert any("เก็บ" in n for n in notes)
    assert "upgrade_mat" in (p.get("inventory_ids") or [])


def test_upgrade_opaque_success_or_fail():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "up", "warrior", "เมษ")
    p["equip_ids"] = {"main_hand": "iron_sword", "body": None}
    p["money_world"] = 5000
    for _ in range(20):
        try_add_item(p, "upgrade_mat", reg)
    # force high success with low level
    assert upgrade_success_chance("main_hand", 0) > 0.8
    msg = upgrade_equipped_opaque(p, "main_hand", reg, rng=random.Random(0))
    assert "สำเร็จ" in msg or "ล้มเหลว" in msg or "ไม่พอ" in msg


def test_equip_panel_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "eq", "warrior", "เมษ")
    p["equip_ids"] = {"main_hand": "iron_sword", "body": "leather_armor"}
    from game.domain.equipment import recompute_stats

    recompute_stats(p, reg)
    lines = format_equip_panel(p, reg)
    assert any("มือหลัก" in x or "อาวุธ" in x for x in lines)
    assert any("เสริมพลัง" in x or "ATK" in x for x in lines)


def test_party_panel():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pp", "priest", "มีน")
    lines = format_party_panel(p, reg)
    assert any("ปาร์ตี้" in x for x in lines)
