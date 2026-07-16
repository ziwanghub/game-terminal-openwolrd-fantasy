"""1.13.3: instance SoT, party AI turns, mission chains, field_menus extract."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.item_instances import (
    append_instance,
    make_instance,
    sync_canonical_inventory,
)
from game.domain.mission_board import accept_mission, list_visible_missions
from game.domain.party import add_member, member_from_template, party_member_turns


def test_sync_canonical_prefers_instances():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sot", "vagabond", "เมษ")
    p["id"] = "sot_player"
    inst = make_instance("iron_sword", p, reg, rarity="rare", location="bag", inst_id="aabbcc")
    p["inventory_items"] = [inst]
    p["inventory_ids"] = ["wrong_or_stale"]
    sync_canonical_inventory(p, reg)
    assert p["inventory_ids"] == ["iron_sword"]
    assert p["inventory_rarities"] == ["rare"]
    assert p["inventory_items"][0]["inst_id"] == "aabbcc"
    assert p.get("inventory_source") == "instances"


def test_append_instance_keeps_inst():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap", "vagabond", "เมษ")
    p["id"] = "ap1"
    a = append_instance(p, "potion_hp", reg)
    assert a.get("inst_id")
    assert "potion_hp" in p["inventory_ids"]
    assert len(p["inventory_items"]) == len(p["inventory_ids"])


def test_party_member_turns_attack_or_heal():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pt", "warrior", "เมษ")
    templates = (reg.party or {}).get("templates") or []
    assert templates
    add_member(p, member_from_template(templates[0], reg, random.Random(1)), reg)
    # 0–100 scale (values ≤12 migrate from old bond scale)
    p["party_bonds"] = {str(p["party"][0]["id"]): 80}
    mon = {"hp": 100, "max_hp": 100, "name": "มอน"}
    notes = party_member_turns(p, mon, random.Random(0), reg)
    assert notes
    text = "".join(notes)
    assert any(
        k in text for k in ("ซุ่ม", "›", "ปาร์ตี้", "รอดู", "โจมตี", "รักษา")
    )


def test_mission_story_chain_hidden_until_done():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ms", "vagabond", "เมษ")
    p["mission_rank"] = "D"
    p["world_id"] = "default"
    # seed tax fund for wages
    from game.domain.market import load_market, save_market

    mkt = load_market("default")
    mkt["tax_fund"] = 500
    save_market("default", mkt)
    vis = {str(x.get("id")) for x in list_visible_missions(p, reg)}
    assert "board_story_city_1" in vis
    assert "board_story_city_2" not in vis  # chain locked
    p["board_missions_done"] = ["board_story_city_1"]
    vis2 = {str(x.get("id")) for x in list_visible_missions(p, reg)}
    assert "board_story_city_2" in vis2
    ok, msg = accept_mission(p, reg, "board_story_city_2", world_id="default")
    assert ok, msg


def test_field_menus_importable():
    from game.services import field_menus
    from game.services.field_loop import run_field

    assert hasattr(field_menus, "_party_menu")
    assert hasattr(field_menus, "_skill_tree_menu")
    assert callable(run_field)
