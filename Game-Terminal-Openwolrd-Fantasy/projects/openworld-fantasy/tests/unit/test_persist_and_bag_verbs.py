"""Persistent instances, bag verbs, early upgrade balance."""
from __future__ import annotations

import json
import random
from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.commands import parse_command
from game.domain.equipment import add_item, equip_item, upgrade_cost
from game.domain.item_instances import (
    ensure_item_instances,
    format_instance_ref,
    get_equipped_instance,
)
from game.ports.io import ScriptedIO
from game.services.field_commands import try_field_command
from game.services.save_service import load_player, save_player


def test_upgrade_cost_early_is_soft():
    c0 = upgrade_cost("weapon", 0)  # +0 → +1
    c1 = upgrade_cost("weapon", 1)
    c5 = upgrade_cost("weapon", 5)
    assert c0["money"] <= 50
    assert c0["upgrade_mat"] == 1
    assert c0["rare_mat"] == 0
    assert c1["money"] < c5["money"]


def test_instance_id_survives_ensure_and_save(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.EXPORT_DIR", tmp_path / "exports")
    (tmp_path / "saves").mkdir(parents=True)
    (tmp_path / "exports").mkdir(parents=True)

    p = create_player(reg, "Persist", "warrior", "เมษ")
    p["id"] = "persist_hero_001"
    p["world_id"] = "default"
    add_item(p, "iron_sword", reg, rarity="legendary")
    equip_item(p, "iron_sword", reg)
    ensure_item_instances(p, reg)
    inst = get_equipped_instance(p, "main_hand")
    assert inst
    ref1 = format_instance_ref(inst)
    iid1 = inst["inst_id"]

    # ensure again must not change inst_id
    ensure_item_instances(p, reg)
    inst2 = get_equipped_instance(p, "main_hand")
    assert inst2["inst_id"] == iid1
    assert format_instance_ref(inst2) == ref1

    path = save_player(p, world_id="default")
    loaded = load_player(str(path))
    ensure_item_instances(loaded, reg)
    inst3 = get_equipped_instance(loaded, "main_hand")
    assert inst3 is not None
    assert inst3["inst_id"] == iid1
    assert str(inst3.get("rarity")) == "legendary"


def test_parse_equip_use_socket():
    assert parse_command("equip_sw001").verb == "equip"
    assert parse_command("use_potion_hp").verb == "use"
    assert parse_command("socket_card_fire>weapon").verb == "socket"


def test_equip_verb_from_field():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "eqv", "warrior", "เมษ")
    p["id"] = "eqv1"
    add_item(p, "iron_sword", reg)
    io = ScriptedIO(["y"])
    assert try_field_command(
        "equip_sw001",
        p,
        reg,
        io,
        random.Random(1),
        [],
        handle_sight=lambda s: None,
    )
    assert (p.get("equip_ids") or {}).get("main_hand") == "iron_sword"
    inst = get_equipped_instance(p, "main_hand")
    assert inst and inst.get("inst_id")


def test_use_verb_potion():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "usev", "warrior", "เมษ")
    p["hp"] = 20
    p["max_hp"] = 100
    p["inventory_ids"] = ["potion_hp"]
    p["inventory"] = ["ยา"]
    p["inventory_rarities"] = ["common"]
    p["inventory_items"] = []
    ensure_item_instances(p, reg)
    io = ScriptedIO(["y"])
    assert try_field_command(
        "use_potion_hp",
        p,
        reg,
        io,
        random.Random(1),
        [],
        handle_sight=lambda s: None,
    )
    assert p["hp"] > 20


def test_socket_verb():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sockv", "warrior", "เมษ")
    p["id"] = "sock1"
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    p["card_bag"] = ["card_fire"]
    io = ScriptedIO(["y"])
    assert try_field_command(
        "socket_card_fire>weapon",
        p,
        reg,
        io,
        random.Random(1),
        [],
        handle_sight=lambda s: None,
    )
    assert (p.get("sockets") or {}).get("main_hand") == ["card_fire"]
