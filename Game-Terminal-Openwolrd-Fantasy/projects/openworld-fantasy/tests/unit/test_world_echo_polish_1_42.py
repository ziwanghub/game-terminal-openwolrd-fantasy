"""W1/W0 polish 1.42 — echo freshness · self standing · combatant MI."""
from __future__ import annotations

import random
import time

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.world_social import (
    build_echo_snapshot,
    echo_freshness_label,
    format_ranking_lines,
    other_as_combatant,
    pick_echo_for_sight,
    soft_relation_hint,
    soft_self_standing,
    write_echo_snapshot,
)


def test_freshness_labels():
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    assert echo_freshness_label({"updated_at": now}) == "ร่องรอยสด"
    assert "เงา" in echo_freshness_label({}) or "เลือน" in echo_freshness_label({})
    old = {"updated_at": "2020-01-01T00:00:00"}
    assert echo_freshness_label(old) == "เงาเก่า"


def test_snapshot_has_intel_and_timestamp():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Snap", "warrior", "สิงห์", world_id="default")
    p["id"] = "snap_pol"
    snap = build_echo_snapshot(p)
    assert snap.get("schema") >= 1
    assert snap.get("updated_at")
    assert int(snap.get("intel_tier") or 0) >= 2
    assert snap.get("can_flee") is True


def test_combatant_smart_profiles():
    snap = {
        "id": "x1",
        "name": "ทดสอบ",
        "is_echo_snapshot": True,
        "bonus_atk": 15,
        "hp": 100,
        "max_hp": 100,
        "level": 8,
        "gear_tags": ["fire", "physical"],
        "intel_tier": 2,
        "can_flee": True,
        "skills": ["fire_ball"],
    }
    foe = other_as_combatant(snap)
    assert foe.get("is_player_echo")
    assert int(foe.get("intel_tier") or 0) >= 2
    assert len(foe.get("attack_profiles") or []) >= 3
    assert foe.get("can_flee") is True
    assert "เงา" in foe.get("name", "")


def test_pick_echo_includes_freshness(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    live = create_player(reg, "Live", "warrior", "สิงห์", world_id="default")
    live["id"] = "live_p"
    live["location"] = "dark_forest"
    ghost = create_player(reg, "Ghost", "mage", "เมถุน", world_id="default")
    ghost["id"] = "ghost_p"
    ghost["location"] = "dark_forest"
    write_echo_snapshot(ghost, "default")
    live["social_memory"] = {"ghost_p": {"relation": "friend"}}
    seen = None
    for seed in range(100):
        s = pick_echo_for_sight(live, reg, random.Random(seed))
        if s:
            seen = s
            break
    assert seen is not None
    hint = str(seen.get("hint") or "")
    assert "ร่องรอย" in hint or "เงา" in hint or "สด" in hint or "ผ่าน" in hint or "เก่า" in hint
    assert seen.get("echo_freshness")
    # relation soft when friend
    assert "มิตร" in hint or "friend" in soft_relation_hint(live, "ghost_p")


def test_self_standing_and_format_viewer():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Stand", "warrior", "สิงห์", world_id="default")
    p["id"] = "stand_1"
    line = soft_self_standing(p, "default", reg)
    assert line
    assert "ร่องรอย" in line or "โลก" in line
    lines = format_ranking_lines("default", reg, viewer=p)
    joined = "\n".join(lines)
    assert "อันดับ" in joined or "ชื่อเสียง" in joined
