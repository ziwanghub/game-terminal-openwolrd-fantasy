"""W1 echo snapshots · W2 lite rank challenge."""
import json
import random
from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.world_social import (
    apply_rank_challenge_result,
    build_echo_snapshot,
    challenge_bounty,
    load_echo_snapshot,
    list_echo_snapshots,
    other_as_combatant,
    pick_echo_for_sight,
    try_rank_challenge,
    write_echo_snapshot,
)
from game.services.save_service import save_player


def test_build_snapshot_sanitized():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "EchoSrc", "warrior", "สิงห์", world_id="default")
    p["id"] = "echo_src_01"
    p["admin"] = True
    p["inventory_ids"] = ["iron_sword"] * 50
    p["money_world"] = 99999
    snap = build_echo_snapshot(p)
    assert snap["is_echo_snapshot"] is True
    assert snap["name"] == "EchoSrc"
    assert "inventory_ids" not in snap
    assert "money_world" not in snap
    assert "admin" not in snap
    assert snap["bonus_atk"] >= 1
    assert len(snap.get("skills") or []) >= 1


def test_write_and_load_echo(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    p = create_player(reg, "SnapA", "mage", "เมถุน", world_id="default")
    p["id"] = "snap_a"
    p["location"] = "dark_forest"
    path = write_echo_snapshot(p, "default")
    assert path is not None and path.is_file()
    loaded = load_echo_snapshot("default", "snap_a")
    assert loaded is not None
    assert loaded["name"] == "SnapA"
    assert loaded.get("is_echo_snapshot")
    snaps = list_echo_snapshots("default")
    assert any(s.get("id") == "snap_a" for s in snaps)


def test_save_player_writes_echo(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    p = create_player(reg, "SaveEcho", "warrior", "สิงห์", world_id="default")
    p["id"] = "save_echo_1"
    save_player(p, world_id="default")
    echo_path = tmp_path / "saves" / "default" / "echoes" / "save_echo_1.json"
    assert echo_path.is_file()
    data = json.loads(echo_path.read_text(encoding="utf-8"))
    assert data.get("is_echo_snapshot") or data.get("schema") == 1


def test_combatant_is_copy_not_owner():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Foe", "warrior", "สิงห์")
    p["id"] = "foe1"
    p["bonus_atk"] = 20
    snap = build_echo_snapshot(p)
    foe = other_as_combatant(snap)
    assert foe.get("is_player_echo")
    assert "เงา" in foe.get("name", "")
    foe["hp"] = 1
    # snapshot not mutated through combatant name reference
    assert int(snap.get("hp") or 0) != 1 or snap.get("hp") != 1
    assert foe.get("_echo_combat_copy")


def test_pick_echo_sight(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    a = create_player(reg, "Live", "warrior", "สิงห์", world_id="default")
    a["id"] = "live1"
    a["location"] = "dark_forest"
    b = create_player(reg, "Ghost", "mage", "เมถุน", world_id="default")
    b["id"] = "ghost1"
    b["location"] = "dark_forest"
    write_echo_snapshot(b, "default")
    # force sight
    seen = None
    for seed in range(80):
        sight = pick_echo_for_sight(a, reg, random.Random(seed))
        if sight:
            seen = sight
            break
    assert seen is not None
    assert seen.get("kind") == "player"
    assert "เงา" in str(seen.get("label") or "") or "ร่องรอย" in str(seen.get("hint") or "")
    assert isinstance(seen.get("player_echo"), dict)
    assert seen["player_echo"].get("id") == "ghost1"


def test_challenge_bounty_scales():
    assert challenge_bounty(1) > challenge_bounty(5)
    assert challenge_bounty(2) > 0


def test_rank_challenge_pay_and_result(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.market.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    champ = create_player(reg, "Champ", "warrior", "สิงห์", world_id="default")
    champ["id"] = "champ1"
    champ["stats"] = {"kills": 100, "boss_kills": 10, "quests_completed": 20}
    champ["level"] = 20
    save_player(champ, world_id="default")
    write_echo_snapshot(champ, "default")

    me = create_player(reg, "Challenger", "rogue", "พิจิก", world_id="default")
    me["id"] = "chal1"
    me["money_world"] = 5000
    me["stats"] = {"kills": 5}
    save_player(me, world_id="default")

    ok, msg, foe = try_rank_challenge(me, reg, random.Random(1), target_rank=1)
    assert ok, msg
    assert foe is not None
    assert me.get("_rank_challenge")
    assert int(me["money_world"]) < 5000
    # win result
    lines = apply_rank_challenge_result(me, reg, won=True)
    assert lines
    assert (me.get("flags") or {}).get("rank_challenge_wins")
