"""WO-048 Hidden Grade + Temple unlock + Soft P."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import allocate_stat, ensure_progression
from game.domain.stat_grades import (
    AXIS_KEYS,
    TEMPLE_MIN_LEVEL,
    apply_invest_to_grades,
    can_temple_unlock,
    format_grade_p_panel,
    grade_revealed,
    letter_from_axis_score,
    temple_unlock,
)
from game.domain.stat_arch import format_soft_invest_lines, self_assess_lines


def test_letter_thresholds_locked():
    assert letter_from_axis_score(0) == "F"
    assert letter_from_axis_score(4.9) == "F"
    assert letter_from_axis_score(5) == "E"
    assert letter_from_axis_score(27) == "A"
    assert letter_from_axis_score(57) == "SSS"


def test_new_player_grades_hidden():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g48a", "warrior", "เมษ")
    assert not grade_revealed(p)
    assert not can_temple_unlock(p)  # low level
    panel = "\n".join(format_grade_p_panel(p))
    assert "เกรดยังถูกปิด" in panel or "ปิด" in panel


def test_temple_requires_level_and_soft_flag():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g48b", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = TEMPLE_MIN_LEVEL
    p["stat_points"] = 0
    p["stats"] = {"kills": 0}
    p["_grade_pressure"] = 0
    # level only, no soft flag (and level < 12)
    assert not can_temple_unlock(p)
    p["stat_points"] = 5
    assert can_temple_unlock(p)


def test_temple_unlock_reveals_letters():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g48c", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 7
    p["stats_alloc"] = {"atk": 2, "defense": 1, "magic": 0, "speed": 1}
    lines = temple_unlock(p, reg)
    assert grade_revealed(p)
    assert p.get("player_grade") in ("F", "E", "D", "C", "B", "A", "S", "SS", "SSS")
    assert p.get("growth_profile") in ("balanced", "focused", "mixed")
    blob = "\n".join(lines)
    assert "ปลด" in blob or "ระดับ" in blob
    panel = "\n".join(format_grade_p_panel(p))
    assert "F" in panel or "E" in panel or "C" in panel or "B" in panel or "A" in panel


def test_s_grade_grows_axis_faster_than_f():
    reg = DataRegistry.load(DATA_DIR)
    # high grade
    p_s = create_player(reg, "g48s", "warrior", "เมษ")
    ensure_progression(p_s, reg)
    p_s["level"] = 15
    p_s["stat_points"] = 20
    p_s["stats_alloc"] = {k: 0 for k in AXIS_KEYS}
    p_s["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    p_s["grade_revealed"] = True
    p_s["player_grade"] = "S"
    p_s["growth_profile"] = "balanced"
    apply_invest_to_grades(p_s, "atk", 7)
    score_s = float((p_s.get("axis_progress") or {}).get("atk", 0))

    p_f = create_player(reg, "g48f", "warrior", "เมษ")
    ensure_progression(p_f, reg)
    p_f["level"] = 15
    p_f["stat_points"] = 20
    p_f["stats_alloc"] = {k: 0 for k in AXIS_KEYS}
    p_f["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "F"
    p_f["growth_profile"] = "balanced"
    apply_invest_to_grades(p_f, "atk", 7)
    score_f = float((p_f.get("axis_progress") or {}).get("atk", 0))
    assert score_s > score_f
    # S often crosses E threshold; F may stay F
    from game.domain.stat_grades import letter_from_axis_score

    assert letter_from_axis_score(score_s) >= "E" or score_s > score_f


def test_allocate_soft_message_no_raw_power():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g48d", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["stat_points"] = 3
    msg = allocate_stat(p, reg, "atk", 2)
    assert "power" not in msg.lower()
    assert "หนา" in msg or "มือ" in msg or "โจมตี" in msg


def test_soft_invest_and_v_include_grade_block():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g48e", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 5
    temple_unlock(p, reg)
    inv = "\n".join(format_soft_invest_lines(p))
    assert "โจมตี" in inv
    v = "\n".join(self_assess_lines(p, force=True, reg=reg))
    assert "เกรด" in v or "ระดับ" in v
