"""Command parser, sight handles, item instances."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.commands import parse_command, resolve_sight_handle
from game.domain.encounters import assign_sight_handles, build_sights
from game.domain.equipment import add_item, equip_item
from game.domain.inventory_sys import format_bag_hub
from game.domain.item_instances import (
    ensure_item_instances,
    format_instance_ref,
    owner_short,
    parse_instance_ref,
)
from game.ports.io import ScriptedIO
from game.services.field_commands import try_field_command


def test_parse_fight_and_upgrade():
    p = parse_command("f_mn02")
    assert p and p.verb == "fight" and p.target == "mn02"
    p2 = parse_command("fmn02")
    assert p2 and p2.verb == "fight" and p2.target == "mn02"
    p3 = parse_command("upgrade_sw001")
    assert p3 and p3.verb == "upgrade" and "sw001" in p3.target
    assert parse_command("5") is None
    assert parse_command("S") is None or parse_command("s") is None


def test_sight_handles_assigned():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h", "warrior", "เมษ")
    sights = build_sights(p, reg, random.Random(1), count=4)
    assert sights
    handles = [s.get("handle") for s in sights]
    assert all(handles)
    assert len(handles) == len(set(handles))
    # resolve
    h0 = str(sights[0]["handle"])
    got = resolve_sight_handle(sights, h0)
    assert got and got.get("handle") == h0


def test_instance_ref_has_owner():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "เจ้าของ", "warrior", "เมษ")
    p["id"] = "player_test_001"
    add_item(p, "iron_sword", reg, rarity="common")
    equip_item(p, "iron_sword", reg)
    ensure_item_instances(p, reg)
    inst = (p.get("equip_instances") or {}).get("main_hand")
    assert inst
    ref = format_instance_ref(inst)
    assert ref.startswith("sw001_")
    assert "#" in ref
    assert owner_short(p) in ref
    # template alone is not full owned ref
    parsed = parse_instance_ref(ref)
    assert parsed["inst_id"]
    assert parsed["owner_short"] == owner_short(p)


def test_hub_shows_owned_ref():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hub", "warrior", "เมษ")
    p["id"] = "abc"
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    text = "\n".join(format_bag_hub(p, reg))
    assert "sw001" in text
    assert "เจ้าของ" in text or "_" in text  # owned form or legend
    assert "ชนิด" in text or "sw001_" in text or "xxxx" in text


def test_field_command_lists_targets_when_missing():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cmd", "warrior", "เมษ")
    sights = [
        {"handle": "mn01", "kind": "monster", "label": "???", "hint": "x", "risk": "?"},
        {"handle": "ch01", "kind": "chest", "label": "หีบ", "hint": "y", "risk": "?"},
    ]
    assign_sight_handles(sights)  # already has handles
    called = []

    def hs(s):
        called.append(s.get("handle"))

    io = ScriptedIO([])
    assert try_field_command(
        "f_mn01",
        p,
        reg,
        io,
        random.Random(1),
        sights,
        handle_sight=hs,
    )
    assert called == ["mn01"]
    # open chest
    called.clear()
    io2 = ScriptedIO([])
    assert try_field_command(
        "o_ch01",
        p,
        reg,
        io2,
        random.Random(1),
        sights,
        handle_sight=hs,
    )
    assert called == ["ch01"]


def test_help_command():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hlp", "mage", "เมถุน")
    io = ScriptedIO([])
    assert try_field_command(
        "?",
        p,
        reg,
        io,
        random.Random(1),
        [],
        handle_sight=lambda s: None,
    )
    assert "f_" in io.joined() or "คำสั่ง" in io.joined()
