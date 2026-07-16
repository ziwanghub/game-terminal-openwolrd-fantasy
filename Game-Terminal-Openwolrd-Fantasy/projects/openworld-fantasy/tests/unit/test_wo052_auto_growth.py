"""WO-052 cut P @30 + Automatic Growth."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.auto_growth import (
    AUTO_GROWTH_LEVEL,
    AXIS_KEYS,
    activate_auto_growth_if_needed,
    effective_growth_rate,
    format_auto_growth_panel,
    is_auto_growth_mode,
    is_manual_p_locked,
    phase_out_residual_points,
    pulse_auto_growth,
    should_grant_stat_points,
    soft_threshold_flag,
)
from game.domain.character import create_player
from game.domain.progression import allocate_stat, ensure_progression, on_level_up_points


def _p(reg, name="g52", level=10):
    p = create_player(reg, name, "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = level
    p["grade_revealed"] = True
    p["player_grade"] = "B"
    p["growth_profile"] = "balanced"
    p["axis_progress"] = {k: 12.0 for k in AXIS_KEYS}
    p["stats_alloc"] = {k: 3 for k in AXIS_KEYS}
    return p


def test_gate_level_constant():
    assert AUTO_GROWTH_LEVEL == 30


def test_manual_p_before_30():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=20)
    p["stat_points"] = 5
    assert not is_manual_p_locked(p)
    assert should_grant_stat_points(p)
    msg = allocate_stat(p, reg, "atk", 2)
    assert p["stat_points"] == 3
    assert "ไม่อยู่ในมือ" not in msg


def test_soft_threshold_28_29():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=28)
    assert soft_threshold_flag(p)
    assert not is_auto_growth_mode(p)
    p["level"] = 30
    assert is_auto_growth_mode(p)


def test_level_up_no_points_after_30():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=30)
    p["stat_points"] = 0
    notes = on_level_up_points(p, reg, 1)
    assert p["stat_points"] == 0
    assert is_auto_growth_mode(p)
    blob = "\n".join(notes)
    assert "ไหล" in blob or "พัฒนา" in blob or "อัตโนมัติ" in blob


def test_level_up_still_grants_before_30():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=15)
    p["stat_points"] = 2
    on_level_up_points(p, reg, 1)
    assert p["stat_points"] >= 5  # +3 typical


def test_phase_out_residual():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=30)
    p["stat_points"] = 6
    p["_p_phase_out_done"] = False
    before = float(p["axis_progress"]["atk"])
    notes = phase_out_residual_points(p, reg)
    assert p["stat_points"] == 0
    assert p.get("_p_phase_out_done")
    assert float(p["axis_progress"]["atk"]) >= before
    assert any("แต้ม" in n or "ไหล" in n for n in notes)


def test_allocate_refused_after_lock():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=32)
    p["stat_points"] = 4
    activate_auto_growth_if_needed(p, reg)
    msg = allocate_stat(p, reg, "atk", 1)
    assert "30" in msg or "ไม่อยู่ในมือ" in msg
    assert p["stat_points"] == 0  # phased out


def test_s_grows_faster_than_f():
    reg = DataRegistry.load(DATA_DIR)
    p_s = _p(reg, "s", level=35)
    p_s["player_grade"] = "S"
    p_s["auto_growth_active"] = True
    p_s["_p_phase_out_done"] = True
    p_s["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    p_f = _p(reg, "f", level=35)
    p_f["player_grade"] = "F"
    p_f["auto_growth_active"] = True
    p_f["_p_phase_out_done"] = True
    p_f["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    assert effective_growth_rate(p_s) > effective_growth_rate(p_f)
    pulse_auto_growth(p_s, "quest", reg=reg, magnitude=1.0)
    pulse_auto_growth(p_f, "quest", reg=reg, magnitude=1.0)
    assert float(p_s["axis_progress"]["atk"]) > float(p_f["axis_progress"]["atk"])


def test_focused_profile_tilts_axis():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=40)
    p["player_grade"] = "A"
    p["growth_profile"] = "focused"
    p["stats_alloc"] = {"atk": 10, "defense": 1, "magic": 1, "speed": 1}
    p["auto_growth_active"] = True
    p["_p_phase_out_done"] = True
    p["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    pulse_auto_growth(p, "combat", reg=reg, magnitude=2.0)
    assert float(p["axis_progress"]["atk"]) > float(p["axis_progress"]["defense"])


def test_auto_panel_soft_no_raw():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=30)
    activate_auto_growth_if_needed(p, reg)
    panel = "\n".join(format_auto_growth_panel(p))
    assert "ไหล" in panel or "30" in panel
    assert "power_" not in panel.lower()
    assert "growth_mult" not in panel


def test_quest_and_combat_sources_noop_before_30():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=10)
    before = dict(p["axis_progress"])
    assert pulse_auto_growth(p, "quest", reg=reg) == []
    assert p["axis_progress"] == before
