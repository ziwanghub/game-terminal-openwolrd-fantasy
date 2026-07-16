"""WO-002: world theme UX (code kept; feature gated by WORLD_THEME_UX_ENABLED)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.world_creation import (
    apply_world_theme_to_player,
    build_custom_profile,
    clear_theme_cache,
    list_themes,
    save_world_profile,
    soft_flavor_lines,
    theme_for_catalog_world,
    try_open_skill_emergence,
)
from game.services.world_service import (
    format_theme_picker_lines,
    format_world_picker_lines,
    list_world_menu_rows,
    prepare_player_for_world,
)
from game.ports.io import ScriptedIO


@pytest.fixture
def enable_theme_ux(monkeypatch):
    """Re-enable WO-002 for tests that exercise full path."""
    monkeypatch.setattr("game.config.WORLD_THEME_UX_ENABLED", True)
    monkeypatch.setattr("game.domain.world_creation.WORLD_THEME_UX_ENABLED", True)
    clear_theme_cache()
    yield
    clear_theme_cache()


def test_simple_picker_default_no_create_option():
    """Default product path: simple list, no theme/create-my-world."""
    from game.config import WORLD_THEME_UX_ENABLED

    assert WORLD_THEME_UX_ENABLED is False
    reg = DataRegistry.load(DATA_DIR)
    text = "\n".join(format_world_picker_lines(reg))
    assert "เลือกโลก" in text
    assert "1." in text
    assert "ความยาก" in text
    assert "สร้างโลกของฉัน" not in text
    assert "ธีม" not in text or "หมายเหตุ" in text  # no theme lines required
    # should not push theme flavor block
    assert "open skill" not in text.lower()


def test_simple_summary_no_theme_lines():
    reg = DataRegistry.load(DATA_DIR)
    from game.services.world_service import world_summary_lines

    lines = world_summary_lines(reg, "default")
    text = "\n".join(lines)
    assert "โลก:" in text
    assert "ธีม:" not in text
    assert "open skill" not in text.lower()


def test_apply_theme_disabled_no_mastery_seed():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "SimpleSeed", "vagabond", "เมษ", world_id="default")
    start = "dark_forest"
    before = int((p.get("area_mastery") or {}).get(start) or 0)
    notes = apply_world_theme_to_player(p, reg, world_id="default", force_seed=True)
    after = int((p.get("area_mastery") or {}).get(start) or 0)
    assert after == before  # no theme seed when disabled
    assert notes == []
    assert p.get("world_id") == "default"
    assert p.get("world_modifiers")


def test_emergence_disabled_returns_empty():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "NoEmerge", "vagabond", "กุมภ์", world_id="default")
    p["skill_chance_bonus"] = 99
    import random

    notes = try_open_skill_emergence(
        p, reg, random.Random(1), context_tags=["nature"]
    )
    assert notes == []


def test_themes_load_and_catalog_mapping(enable_theme_ux):
    clear_theme_cache()
    themes = list_themes()
    assert len(themes) >= 5
    reg = DataRegistry.load(DATA_DIR)
    t = theme_for_catalog_world("default", reg)
    assert t is not None
    assert t.get("starting_area") == "dark_forest"
    assert soft_flavor_lines(t)


def test_world_picker_shows_theme_and_create_option(enable_theme_ux):
    reg = DataRegistry.load(DATA_DIR)
    lines = format_world_picker_lines(reg)
    text = "\n".join(lines)
    assert "เลือกโลก" in text
    assert "สร้างโลกของฉัน" in text
    assert len(list_world_menu_rows(reg)) >= 2


def test_theme_picker_lists_areas(enable_theme_ux):
    reg = DataRegistry.load(DATA_DIR)
    text = "\n".join(format_theme_picker_lines(reg))
    assert "ธีม" in text
    assert "1." in text


def test_apply_theme_seeds_mastery_once(enable_theme_ux):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ThemeSeed", "vagabond", "เมษ", world_id="default")
    start = "dark_forest"
    before = int((p.get("area_mastery") or {}).get(start) or 0)
    notes = apply_world_theme_to_player(p, reg, world_id="default", force_seed=True)
    after = int((p.get("area_mastery") or {}).get(start) or 0)
    assert after > before
    assert p.get("world_theme_applied")
    assert int(p.get("skill_chance_bonus") or 0) > 0
    assert any("ธีม" in n or "ชำนาญ" in n for n in notes)
    mid = after
    apply_world_theme_to_player(p, reg, world_id="default", force_seed=False)
    assert int((p.get("area_mastery") or {}).get(start) or 0) == mid


def test_custom_world_profile_persists(enable_theme_ux, tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.domain.world_creation.SAVES_DIR", tmp_path)
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path)
    theme = list_themes()[0]
    wid = "my_test_world_wo2"
    prof = build_custom_profile(
        display_name="โลกทดสอบ WO2",
        theme=theme,
        world_id=wid,
    )
    path = save_world_profile(prof)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"] == "custom"
    p = create_player(reg, "CustomHero", "vagabond", "เมษ", world_id=wid)
    notes = prepare_player_for_world(p, reg, wid, new_character=True)
    assert p["world_id"] == wid
    assert p.get("world_theme_id") == theme["id"]
    assert notes


def test_open_skill_emergence_can_fire(enable_theme_ux):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Emerge", "vagabond", "กุมภ์", world_id="default")
    apply_world_theme_to_player(p, reg, world_id="default", force_seed=True)
    p["skill_chance_bonus"] = 80
    import random

    hits = 0
    for i in range(30):
        notes = try_open_skill_emergence(
            p, reg, random.Random(i), context_tags=["nature", "shadow"]
        )
        if notes:
            hits += 1
    assert hits >= 1


def test_pick_world_create_flow_scripted(enable_theme_ux, monkeypatch, tmp_path):
    from game.services import world_service as ws

    monkeypatch.setattr("game.domain.world_creation.SAVES_DIR", tmp_path)
    reg = DataRegistry.load(DATA_DIR)
    themes = list_themes()
    assert themes
    rows = ws.list_world_menu_rows(reg)
    create_n = str(len(rows) + 1)
    io = ScriptedIO([create_n, "ป่าในฝัน", "1", ""])
    wid = ws.pick_world_interactive(reg, io)
    assert wid
    prof_path = Path(tmp_path) / wid / "world_profile.json"
    assert prof_path.is_file()
