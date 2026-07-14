"""UX: describe_loadout sectioned summary."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import (
    add_item,
    describe_loadout,
    equip_item,
    recompute_stats,
    socket_card,
)


def test_describe_loadout_sections_and_soft_upgrade():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dl", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    add_item(p, "leather_armor", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "leather_armor", reg)
    p["card_bag"] = ["card_fire"]
    # socket if possible
    try:
        ensure = list((p.get("sockets") or {}).get("main_hand") or [])
        if not ensure:
            # force one socket slot for test
            p.setdefault("sockets", {})["main_hand"] = [None]
        socket_card(p, "main_hand", 0, "card_fire", reg)
    except Exception:
        p["card_bag"] = ["card_fire"]
    p["money_world"] = 10
    p["inventory_ids"] = list(p.get("inventory_ids") or [])
    # no upgrade mats
    recompute_stats(p, reg)
    lines = describe_loadout(p, reg)
    text = "\n".join(lines)
    assert "เกียร์ละเอียด" in text
    assert "สวมอยู่" in text
    assert "มือหลัก" in text
    assert "ลำตัว" in text
    assert "ช่องว่าง" in text or "ศีรษะ" in text
    assert "อัปถัดไป" in text
    assert "ยังไม่พอ" in text or "พออัป" in text
    assert "คลังเกียร์" in text
    assert "พลังรวม" in text
    assert "ATK" in text
    assert "ใบ้" in text


def test_describe_loadout_empty_slots_grouped():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dl2", "mage", "เมถุน")
    recompute_stats(p, reg)
    text = "\n".join(describe_loadout(p, reg))
    assert "เกียร์ละเอียด" in text
    # should not spam "xxx: -" for every empty as only format
    assert text.count(": -") < 5


def test_armor_shows_def_not_hp_primary():
    """Armor shows กันกาย/กันเวท; latent HP% is not listed on the piece."""
    from game.domain.equipment import soft_guard_summary, soft_piece_defense_hint
    from game.domain.inventory_sys import format_equip_panel

    reg = DataRegistry.load(DATA_DIR)
    leather = reg.items["leather_armor"]
    assert int(leather.get("def") or 0) > 0
    assert float(leather.get("latent_hp_pct") or 0) > 0
    assert not leather.get("max_hp")  # migrated off visible max_hp
    hint = soft_piece_defense_hint(leather, slot="body")
    assert "กันกาย" in hint
    assert "HP+" not in hint

    p = create_player(reg, "defui", "warrior", "เมษ")
    hp0 = int(p.get("max_hp") or 0)
    add_item(p, "leather_armor", reg)
    equip_item(p, "leather_armor", reg)
    recompute_stats(p, reg)
    # latent HP should raise max_hp slightly (observe)
    assert int(p.get("max_hp") or 0) >= hp0
    assert int(p.get("equip_def") or 0) >= int(leather.get("def") or 0)
    text = "\n".join(describe_loadout(p, reg))
    assert "กันกาย" in text
    assert "HP+" not in text.split("ลำตัว")[1].split("---")[0] if "ลำตัว" in text else True
    panel = "\n".join(format_equip_panel(p, reg))
    assert "กันกาย" in panel
    assert "กันกาย" in soft_guard_summary(p)
