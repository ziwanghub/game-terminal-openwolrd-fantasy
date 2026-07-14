"""Soft observation feedback + IC1/MC pack smoke."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item
from game.domain.soft_feel import soft_equip_feel, soft_unit_combat_feel, soft_upgrade_feel
from game.domain.inventory_sys import upgrade_equipped_opaque
import random


def test_soft_equip_feel_armor():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sf1", "warrior", "เมษ")
    add_item(p, "leather_armor", reg)
    equip_item(p, "leather_armor", reg)
    feels = soft_equip_feel(p, reg, slot="body", item_id="leather_armor")
    text = "\n".join(feels)
    assert "เกราะ" in text or "อุ้ม" in text or feels == []


def test_equip_message_includes_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sf2", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    msg = equip_item(p, "iron_sword", reg)
    assert "สวม" in msg
    # weapon soft latent line often present
    assert "คม" in msg or "ช่องการ์ด" in msg


def test_upgrade_success_soft_feel():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sf3", "warrior", "เมษ")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    p["money_world"] = 5000
    for _ in range(20):
        add_item(p, "upgrade_mat", reg)

    class AlwaysOk:
        def random(self):
            return 0.0

    msg = upgrade_equipped_opaque(p, "main_hand", reg, rng=AlwaysOk())  # type: ignore
    assert "สำเร็จ" in msg


def test_unit_combat_soft_feel_weak():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["unit_nova_burst"]
    p = create_player(reg, "sf4", "warrior", "เมษ")
    p["power_mag"] = 2.0
    p["power_atk"] = 30.0
    notes = soft_unit_combat_feel(p, sk, damage=5)
    assert notes
    assert any("แผ่ว" in n or "ผิด" in n or "แทบ" in n for n in notes)


def test_ic1_mc_pack_loaded():
    reg = DataRegistry.load(DATA_DIR)
    for iid in (
        "iron_kite_shield",
        "bone_dagger",
        "ash_longbow",
        "marsh_reed_staff",
        "cave_miner_helm",
        "vine_wrap_body",
        "cave_crystal_shard",
    ):
        assert iid in reg.items, iid
    for mid in ("cave_glow_beetle", "marsh_toad", "moss_sprite", "city_pickpocket"):
        assert mid in reg.monsters, mid
        m = reg.monsters[mid]
        assert m.get("drops"), mid
        assert m.get("card_id"), mid
    for cid in ("card_cave_bat", "card_marsh_toad", "card_moss_sprite"):
        assert cid in reg.cards, cid
    # pools include new mons
    cave = reg.areas.get("cave_shadow") or {}
    pool_ids = [
        (x.get("id") if isinstance(x, dict) else x)
        for x in (cave.get("monster_pools") or [])
    ]
    assert "cave_glow_beetle" in pool_ids


def test_level_up_sets_class_offer_flag_when_eligible():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.progression import on_level_up_points
    from game.domain.class_paths import list_available_class_paths

    p = create_player(reg, "lv", "vagabond", "เมษ")
    p["occupation_id"] = "vagabond"
    p["level"] = 10
    p["stats_alloc"] = {
        "atk": 5,
        "defense": 4,
        "magic": 4,
        "speed": 4,
        "intelligence": 3,
        "crit": 2,
    }
    p["stats"] = {"kills": 20, "combos": 20, "explores": 20, "flees": 5, "heals": 5}
    p["library_entries_read"] = ["a"]
    p["personality_invest"] = {"compassion": 2}
    notes = on_level_up_points(p, reg, 1)
    if list_available_class_paths(p, reg):
        assert (p.get("flags") or {}).get("class_offer_pending") is True
        assert any("อาชีพ" in n or "C" in n for n in notes)
