"""Inventory sync fix: loot pick via add_item, sanitize, quest kill backfill."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import resolve_victory
from game.domain.equipment import equip_item
from game.domain.inventory_sys import (
    build_combat_loot_table,
    resolve_loot_pick,
    sanitize_inventory,
)
from game.domain.quests import ensure_quests
from game.domain.stats import bump_stat, ensure_stats


def test_combat_loot_pick_has_matching_ids():
    """Loot is chosen after victory (not auto-granted in resolve_victory)."""
    reg = DataRegistry.load(DATA_DIR)
    got = False
    for seed in range(80):
        p = create_player(reg, f"v{seed}", "warrior", "เมษ")
        mon = dict(reg.monsters.get("goblin_hunter") or {})
        mon.setdefault("id", "goblin_hunter")
        mon.setdefault("level", 1)
        mon.setdefault("xp_mult", 1.0)
        mon["_discovered_reactions"] = []
        # XP path still works
        resolve_victory(p, mon, reg, "dark_forest", random.Random(seed))
        loot = build_combat_loot_table(p, mon, reg, random.Random(seed + 1))
        if not loot:
            continue
        notes = resolve_loot_pick(p, reg, loot, "A")
        if not any("เก็บ" in n for n in notes):
            continue
        ids = list(p.get("inventory_ids") or [])
        inv = list(p.get("inventory") or [])
        # card-only pick is ok — bag may only gain card_bag
        if ids:
            assert len(ids) == len(inv), f"desync inv={inv} ids={ids} seed={seed}"
            for iid in ids:
                assert iid in reg.items or iid in reg.cards
            if "iron_sword" in ids:
                msg = equip_item(p, "iron_sword", reg)
                assert "สวม" in msg or "ดาบ" in msg
        got = True
        break
    assert got, "expected at least one combat loot table hit in 80 seeds"


def test_sanitize_repairs_orphan_iron_sword_name():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fix", "warrior", "เมษ")
    p["inventory"] = list(p.get("inventory") or []) + ["ดาบเหล็ก"]
    p["inventory_ids"] = list(p.get("inventory_ids") or [])  # shorter → orphan name
    # force desync like the playtest bug
    while len(p["inventory_ids"]) < len(p["inventory"]) - 1:
        p["inventory_ids"].append("potion_hp_small")
    # last name has no id
    notes = sanitize_inventory(p, reg)
    assert "iron_sword" in (p.get("inventory_ids") or [])
    assert any("ซ่อม" in n or "iron" in n.lower() or "ดาบ" in n for n in notes) or (
        "iron_sword" in p["inventory_ids"]
    )
    msg = equip_item(p, "iron_sword", reg)
    assert "สวม" in msg or "ดาบ" in msg


def test_kill_quest_backfill_on_unlock():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "kb", "warrior", "เมษ")
    ensure_stats(p)
    # simulate 5 kills before path_to_five unlocks
    for _ in range(5):
        bump_stat(p, "kills", 1)
    p["quests_done"] = ["first_blood"]
    p["quests"] = {}
    ensure_quests(p, reg)
    st = (p.get("quests") or {}).get("path_to_five") or {}
    assert int(st.get("progress") or 0) >= 5


def test_sanitize_keeps_valid_items():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ok", "mage", "เมถุน")
    from game.domain.equipment import add_item

    add_item(p, "iron_sword", reg)
    add_item(p, "antidote", reg)
    n_before = len(p["inventory_ids"])
    sanitize_inventory(p, reg)
    assert len(p["inventory_ids"]) == n_before
    assert len(p["inventory"]) == len(p["inventory_ids"])
