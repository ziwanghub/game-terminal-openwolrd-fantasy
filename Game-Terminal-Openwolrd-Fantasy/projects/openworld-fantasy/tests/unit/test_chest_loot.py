"""L0–L2 sealed chest loot: data, open, drop, bag category, unique."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.chest_loot import (
    all_rank_ids,
    decide_chest_drop,
    grant_sealed_chest,
    infer_combat_source,
    is_chest_item,
    note_kill_for_farm,
    open_chest,
    rank_def,
    sealed_item_for_rank,
    try_drop_and_grant_chest,
    unique_owned,
)
from game.domain.combat import resolve_victory
from game.domain.equipment import add_item
from game.domain.inventory_sys import format_bag_hub, item_category, list_bag_entries
from game.ports.io import ScriptedIO
from game.services.bag_hub import run_bag_hub


def test_registry_loads_chests_cfg():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.chests_cfg
    assert "ranks" in reg.chests_cfg
    assert "pools" in reg.chests_cfg
    assert "sources" in reg.chests_cfg
    ranks = all_rank_ids(reg)
    assert ranks == ["common", "uncommon", "rare", "s", "ss", "sss", "unit"]
    for rid in ranks:
        assert sealed_item_for_rank(reg, rid) in reg.items
        assert rank_def(reg, rid).get("id") == rid or rank_def(reg, rid).get("label")


def test_pool_item_ids_exist():
    reg = DataRegistry.load(DATA_DIR)
    buckets = (reg.chests_cfg.get("pools") or {}).get("buckets") or {}
    missing = []
    for b, ids in buckets.items():
        for iid in ids:
            if str(iid) not in reg.items:
                missing.append((b, iid))
    assert missing == []


def test_sealed_items_are_chest_category():
    reg = DataRegistry.load(DATA_DIR)
    for rid in all_rank_ids(reg):
        iid = sealed_item_for_rank(reg, rid)
        it = reg.items[iid]
        assert is_chest_item(it)
        assert item_category(iid, reg) == "chest"
        assert it.get("chest_rank") == rid


def test_open_common_grants_item_and_soft_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c", "warrior", "เมษ")
    before = list(p.get("inventory_ids") or [])
    lines = open_chest(p, reg, random.Random(7), "common")
    assert any("เปิด" in ln for ln in lines)
    assert any(ln.strip().startswith("·") for ln in lines)
    after = list(p.get("inventory_ids") or [])
    assert len(after) > len(before)
    assert int(p.get("chest_opens") or 0) >= 1


def test_open_unit_unique_once_then_echo():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "u", "warrior", "เมษ")
    p["world_id"] = "test_unit_once"
    p["id"] = "unit_once_player"
    lines1 = open_chest(p, reg, random.Random(0), "unit")
    owned = list(p.get("unique_owned") or [])
    assert len(owned) >= 1
    assert any(str(x).startswith("unit_") for x in (p.get("inventory_ids") or []))
    assert any("หนึ่ง" in ln or "พันธะ" in ln or "เงา" in ln for ln in lines1)

    # exhaust remaining uniques
    for seed in range(1, 8):
        open_chest(p, reg, random.Random(seed), "unit")
    assert "echo_shard" in (p.get("inventory_ids") or [])
    # no duplicate of first unique beyond one
    first = owned[0]
    assert (p.get("inventory_ids") or []).count(first) == 1


def test_grant_sealed_and_bag_open_path():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g", "warrior", "เมษ")
    ok, shown = grant_sealed_chest(p, reg, "rare")
    assert ok
    assert "หีบ" in shown or "หายาก" in shown
    assert "sealed_chest_rare" in (p.get("inventory_ids") or [])
    chests = list_bag_entries(p, reg, "chest")
    assert any(e["id"] == "sealed_chest_rare" for e in chests)

    # hub: 4=chest, 1=open first, 0 back, 0 exit
    p["inventory_ids"] = ["sealed_chest_common"]
    p["inventory"] = ["หีบ · ธรรมดา"]
    p["inventory_rarities"] = ["common"]
    n_before = len(p["inventory_ids"])
    io = ScriptedIO(["4", "1", "0", "0"])
    run_bag_hub(p, reg, io)
    # sealed consumed; loot may have been added
    assert "sealed_chest_common" not in (p.get("inventory_ids") or [])
    assert int(p.get("chest_opens") or 0) >= 1
    assert len(p.get("inventory_ids") or []) >= n_before - 1


def test_hub_shows_chest_category():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h", "mage", "เมถุน")
    text = "\n".join(format_bag_hub(p, reg))
    assert "หีบ" in text


def test_infer_combat_source():
    assert infer_combat_source({"boss": True, "dungeon_boss": True}) == "dungeon_boss"
    assert infer_combat_source({"boss": True}) == "area_boss"
    assert infer_combat_source({"elite": True}) == "elite_monster"
    assert infer_combat_source({}) == "normal_monster"


def test_area_boss_often_drops_sealed(make_player):
    reg = DataRegistry.load(DATA_DIR)
    hits = 0
    for i in range(40):
        p = make_player(name=f"boss{i}")
        mon = {"id": "area_boss_x", "boss": True, "name": "เงาใหญ่"}
        lines = try_drop_and_grant_chest(
            p,
            reg,
            random.Random(i + 100),
            source="area_boss",
            mon=mon,
            first_clear=True,
            auto_open=False,
        )
        if lines:
            hits += 1
            assert any("กล่อง" in ln or "หีบ" in ln for ln in lines)
            sealed = [x for x in (p.get("inventory_ids") or []) if str(x).startswith("sealed_chest_")]
            assert sealed
    assert hits >= 8  # first-clear boss should drop often


def test_normal_monster_rarely_drops(make_player):
    reg = DataRegistry.load(DATA_DIR)
    hits = 0
    for i in range(80):
        p = make_player(name=f"norm{i}")
        mon = {"id": "slime_a", "name": "สไลม์"}
        lines = try_drop_and_grant_chest(
            p,
            reg,
            random.Random(i + 3),
            source="normal_monster",
            mon=mon,
            first_clear=False,
        )
        if lines:
            hits += 1
    assert hits <= 12  # ~1% base + noise — soft upper bound


def test_anti_farm_reduces_chance(make_player):
    reg = DataRegistry.load(DATA_DIR)
    p = make_player(name="farm")
    mon = {"id": "farm_slime", "name": "สไลม์"}
    # warm farm window
    for _ in range(12):
        note_kill_for_farm(p, "farm_slime")
    drops = 0
    for i in range(60):
        # re-note each attempt like combat does
        r = decide_chest_drop(
            p,
            reg,
            random.Random(i + 50),
            source="normal_monster",
            mon=mon,
        )
        if r:
            drops += 1
        note_kill_for_farm(p, "farm_slime")
    # heavily farmed same id should stay rare
    assert drops <= 8


def test_resolve_victory_can_append_chest_lines(make_player):
    reg = DataRegistry.load(DATA_DIR)
    p = make_player(name="vic")
    mon = {
        "id": "victory_boss",
        "name": "บอสทดสอบ",
        "boss": True,
        "level": 5,
        "exp": 20,
        "gold": 10,
    }
    # force many victories with different rng seeds until chest or soft pass
    saw = False
    for seed in range(30):
        p2 = make_player(name=f"v{seed}")
        lines = resolve_victory(p2, mon, reg, "test_area", random.Random(seed + 200))
        if any("กล่อง" in ln or "หีบ" in ln for ln in lines):
            saw = True
            assert any(
                str(x).startswith("sealed_chest_")
                for x in (p2.get("inventory_ids") or [])
            )
            break
    # boss drop chance is high — expect at least one in 30
    assert saw
