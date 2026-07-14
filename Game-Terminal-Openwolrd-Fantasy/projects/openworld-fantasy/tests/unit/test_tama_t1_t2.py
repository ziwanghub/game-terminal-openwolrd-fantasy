"""Wave D T1–T2: load delta needs + Tama panel."""
from __future__ import annotations

import time

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.needs import (
    apply_load_delta,
    compute_load_delta_hours,
    ensure_needs,
    format_tama_panel,
    personal_eat_first_food,
    personal_rest_care,
    stamp_saved_at,
    tama_mood_line,
)
from game.services.save_service import load_player, save_player


def test_stamp_and_compute_hours():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t1", "warrior", "เมษ")
    now = time.time()
    stamp_saved_at(p, when=now - 5 * 3600)
    h = compute_load_delta_hours(p, now=now)
    assert 4.5 <= h <= 5.5


def test_load_delta_worsens_needs_capped():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t1b", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"] = {"hunger": 10, "fatigue": 10, "morale": 80}
    stamp_saved_at(p, when=time.time() - 30 * 3600)
    p.pop("_load_delta_done", None)
    notes = apply_load_delta(p, force_hours=30.0)
    assert notes
    assert p["needs"]["hunger"] > 10
    assert p["needs"]["fatigue"] > 10
    assert p["needs"]["morale"] < 80
    # caps
    assert p["needs"]["hunger"] <= 10 + 42
    # second apply same session no-op
    notes2 = apply_load_delta(p, force_hours=30.0)
    assert notes2 == []


def test_tiny_gap_no_delta():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t1c", "mage", "เมถุน")
    ensure_needs(p)
    h0 = p["needs"]["hunger"]
    stamp_saved_at(p, when=time.time() - 5 * 60)
    p.pop("_load_delta_done", None)
    notes = apply_load_delta(p)
    assert notes == []
    assert p["needs"]["hunger"] == h0


def test_save_load_roundtrip_applies_delta(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "saveΔ", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"] = {"hunger": 15, "fatigue": 15, "morale": 70}
    p["world_id"] = "test_t1_world"
    path = save_player(p, world_id="test_t1_world")
    # age the save timestamps on disk payload
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    old = time.time() - 12 * 3600
    data["saved_at_unix"] = old
    data["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(old))
    data["updated_at"] = data["saved_at"]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = load_player(str(path))
    assert loaded["needs"]["hunger"] >= 15
    assert loaded.get("_pending_load_notes") or loaded["needs"]["hunger"] > 15


def test_tama_panel_has_soft_ui():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t2", "warrior", "เมษ")
    ensure_needs(p)
    lines = format_tama_panel(p)
    text = "\n".join(lines)
    assert "Tama" in text or "สถานะ" in text
    assert "ท้อง" in text
    assert "%" not in text
    assert tama_mood_line(p)


def test_personal_rest_and_eat():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "care", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["fatigue"] = 70
    p["needs"]["hunger"] = 70
    personal_rest_care(p)
    assert p["needs"]["fatigue"] < 70
    add_item(p, "city_bread", reg)
    personal_eat_first_food(p, reg)
    assert p["needs"]["hunger"] < 70
    assert "city_bread" not in (p.get("inventory_ids") or [])
