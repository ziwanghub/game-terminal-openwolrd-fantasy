"""Wave C: L3 quest/board chest rewards · L4 unit unique scopes."""
from __future__ import annotations

import random
from pathlib import Path

from game.config import DATA_DIR, SAVES_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.chest_loot import (
    apply_reward_block,
    can_grant_unique,
    claim_unique_world,
    grant_reward_chests,
    grant_unit_unique,
    is_unique_world_claimed,
    load_unique_claims,
    open_chest,
    unit_unique_defs,
    unique_claims_path,
)
from game.domain.mission_board import accept_mission, complete_mission_if_done, ensure_mission_player
from game.domain.quests import complete_quest, ensure_quests


def test_unit_uniques_catalog_loaded():
    reg = DataRegistry.load(DATA_DIR)
    defs = unit_unique_defs(reg)
    ids = {str(u.get("id")) for u in defs}
    assert "unit_blade_of_ash" in ids
    assert "unit_veil_of_dusk" in ids
    assert "unit_heart_of_ember" in ids
    assert all(str(u["id"]) in reg.items for u in defs)


def test_quest_reward_chest_grants_sealed():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "qchest", "warrior", "เมษ")
    ensure_quests(p, reg)
    notes = complete_quest(p, reg, "sealed_whisper")
    assert "sealed_whisper" in (p.get("quests_done") or [])
    assert any("หีบ" in n for n in notes)
    assert "sealed_chest_uncommon" in (p.get("inventory_ids") or [])


def test_quest_set_flags_hidden():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "flags", "warrior", "เมษ")
    notes = complete_quest(p, reg, "sealed_path")
    flags = p.get("flags") or {}
    assert flags.get("chest_favor") == 1
    assert any("หีบ" in n or "ผนึก" in n or "เส้นทาง" in n for n in notes)
    assert "sealed_chest_rare" in (p.get("inventory_ids") or [])


def test_grant_reward_chests_direct():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g", "mage", "เมถุน")
    lines = grant_reward_chests(p, reg, reward_spec="s", seed_salt="t1")
    assert lines
    assert "sealed_chest_s" in (p.get("inventory_ids") or [])


def test_mission_explicit_reward_chest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "mchest", "warrior", "เมษ")
    ensure_mission_player(p)
    p["board_mission"] = {
        "id": "board_boss_a",
        "name": "เงาแห่งพื้นที่",
        "rank": "A",
        "type": "kill",
        "target": 1,
        "start_stat": 0,
        "reward_money": 10,
        "reward_xp": 10,
        "reward_items": [],
        "reward_chest": "rare",
    }
    # force complete: kill snapshot already at target
    p["stats"] = dict(p.get("stats") or {})
    p["stats"]["kills"] = 1
    p["board_mission"]["start_stat"] = 0
    p["board_mission"]["type"] = "kill"
    p["board_mission"]["target"] = 1
    notes = complete_mission_if_done(p, reg)
    assert notes
    assert any("หีบ" in n or "ผนึก" in n for n in notes)
    assert "sealed_chest_rare" in (p.get("inventory_ids") or [])


def test_apply_reward_block_with_chance_always_at_one():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ch1", "warrior", "เมษ")
    lines = apply_reward_block(
        p,
        reg,
        {"id": "x", "reward_chest": "common", "reward_chest_chance": 1.0},
        seed_salt="always",
    )
    assert "sealed_chest_common" in (p.get("inventory_ids") or [])
    assert lines


def test_unit_save_scope_no_duplicate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "saveu", "warrior", "เมษ")
    p["world_id"] = "w_save_scope"
    p["id"] = "save_player"
    iid, lines = grant_unit_unique(p, reg, random.Random(1), preferred_id="unit_blade_of_ash")
    assert iid == "unit_blade_of_ash"
    assert not can_grant_unique(p, reg, "unit_blade_of_ash")
    iid2, lines2 = grant_unit_unique(p, reg, random.Random(2), preferred_id="unit_blade_of_ash")
    assert iid2 != "unit_blade_of_ash" or iid2 == "echo_shard" or iid2 in (
        "unit_veil_of_dusk",
        "unit_heart_of_ember",
        "echo_shard",
    )
    # preferred already owned → different unique or echo
    assert iid2 != "unit_blade_of_ash" or "echo" in str(lines2).lower() or iid2 == "echo_shard"


def test_unit_world_scope_exclusive(tmp_path, monkeypatch):
    # isolate claims under project saves (real path) but unique world id
    reg = DataRegistry.load(DATA_DIR)
    wid = f"test_world_claim_{random.randint(1, 10**9)}"
    p1 = create_player(reg, "w1", "warrior", "เมษ")
    p1["world_id"] = wid
    p1["id"] = "owner_a"
    p2 = create_player(reg, "w2", "mage", "เมถุน")
    p2["world_id"] = wid
    p2["id"] = "owner_b"

    iid, _ = grant_unit_unique(p1, reg, random.Random(0), preferred_id="unit_heart_of_ember")
    assert iid == "unit_heart_of_ember"
    assert is_unique_world_claimed(wid, "unit_heart_of_ember", except_player_id="owner_b")
    assert not can_grant_unique(p2, reg, "unit_heart_of_ember")

    iid2, lines2 = grant_unit_unique(p2, reg, random.Random(1), preferred_id="unit_heart_of_ember")
    assert iid2 == "echo_shard" or iid2 != "unit_heart_of_ember"
    # cleanup claims file
    path = unique_claims_path(wid)
    if path.exists():
        path.unlink()


def test_open_unit_picks_from_catalog():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cat", "warrior", "เมษ")
    p["world_id"] = "w_cat"
    p["id"] = "cat_p"
    lines = open_chest(p, reg, random.Random(42), "unit")
    assert any("เปิด" in ln for ln in lines)
    units = [x for x in (p.get("inventory_ids") or []) if str(x).startswith("unit_")]
    assert units or "echo_shard" in (p.get("inventory_ids") or [])
