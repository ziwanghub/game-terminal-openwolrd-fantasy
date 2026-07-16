"""WO-049 Grade Surface UI + Axis Tier Soft."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import allocate_stat, ensure_progression
from game.domain.stat_arch import self_assess_lines
from game.domain.stat_grades import (
    AXIS_KEYS,
    TIER_EARLY,
    TIER_LATE,
    TIER_MID,
    TIER_SPECIAL,
    apply_invest_to_grades,
    format_axis_surface,
    format_grade_p_panel,
    format_grade_surface_lines,
    grade_hub_compact_lines,
    grade_revealed,
    letter_from_axis_score,
    player_soft_desc,
    temple_unlock,
    tier_from_axis_score,
    tier_label_th,
)
from game.ui_terminal.status import format_personal_hub_lines, render_status_l1


def test_tier_within_band():
    # F band 0–5
    assert tier_from_axis_score(0.0) == TIER_EARLY
    assert tier_from_axis_score(2.0) == TIER_MID
    assert tier_from_axis_score(3.5) == TIER_LATE
    assert tier_from_axis_score(4.7) == TIER_SPECIAL
    # E band 5–10
    assert letter_from_axis_score(5) == "E"
    assert tier_from_axis_score(5.0) == TIER_EARLY
    assert tier_from_axis_score(7.0) == TIER_MID
    # SSS special high
    assert letter_from_axis_score(100) == "SSS"
    assert tier_from_axis_score(100.0) == TIER_SPECIAL
    assert tier_from_axis_score(58.0) == TIER_EARLY


def test_player_soft_desc_ladder():
    assert player_soft_desc("F") == "นักฝึก"
    assert player_soft_desc("S") == "ตำนานแผ่ว"
    assert player_soft_desc("SSS") == "เสี้ยวเทพ"
    assert "ขั้น" in tier_label_th(TIER_EARLY)


def test_surface_hidden_before_temple():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g49a", "warrior", "เมษ")
    ensure_progression(p, reg)
    surf = "\n".join(format_grade_surface_lines(p))
    assert "ยังปิด" in surf or "ปิด" in surf
    assert "ขั้นต้น" not in surf  # no tier leak
    hub = "\n".join(format_personal_hub_lines(p, "forest"))
    assert "เกรด" in hub
    assert "ยังปิด" in hub or "ปิด" in hub


def test_surface_after_temple_has_letter_and_tier():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g49b", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 6
    p["stats_alloc"] = {"atk": 3, "defense": 2, "magic": 1, "speed": 1}
    temple_unlock(p, reg)
    assert grade_revealed(p)
    surf = "\n".join(format_grade_surface_lines(p, compact=False))
    assert "เกรดรวม" in surf or "ระดับ" in surf
    assert any(x in surf for x in ("F", "E", "D", "C", "B", "A", "S"))
    assert any(t in surf for t in ("ขั้นต้น", "ขั้นกลาง", "ขั้นปลาย", "พิเศษ"))
    assert "โจมตี" in surf
    # no raw score dumps
    assert "axis_progress" not in surf
    assert "power_" not in surf.lower()

    compact = "\n".join(grade_hub_compact_lines(p))
    assert "ระดับ" in compact or "〔" in compact

    panel = "\n".join(format_grade_p_panel(p))
    assert "ขั้น" in panel or "พิเศษ" in panel


def test_v_assess_and_status_include_surface():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g49c", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 5
    temple_unlock(p, reg)
    v = "\n".join(self_assess_lines(p, force=True, reg=reg))
    assert "เกรด" in v
    assert "โจมตี" in v or "เกรดรวม" in v or "ระดับ" in v
    st = render_status_l1(p, "ancient_city")
    assert "เกรด" in st
    assert "soft" in st.lower() or "ขั้น" in st or "〔" in st


def test_axis_surface_format():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g49d", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["grade_revealed"] = True
    p["player_grade"] = "B"
    p["growth_profile"] = "balanced"
    p["axis_progress"] = {"atk": 16.0, "defense": 5.0, "magic": 0.0, "speed": 10.0}
    line = format_axis_surface(p, "atk")
    assert "โจมตี" in line
    assert "C" in line  # score 16 → C
    assert "ขั้น" in line or "พิเศษ" in line
    # compact no full desc required
    c = format_axis_surface(p, "atk", compact=True)
    assert "C" in c


def test_invest_can_raise_tier_or_letter():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g49e", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["grade_revealed"] = True
    p["player_grade"] = "A"
    p["growth_profile"] = "balanced"
    p["axis_progress"] = {k: 4.0 for k in AXIS_KEYS}  # F late/special edge
    p["stats_alloc"] = {k: 0 for k in AXIS_KEYS}
    p["stat_points"] = 20
    old_l, new_l, old_t, new_t = apply_invest_to_grades(p, "atk", 5)
    assert old_l is not None and new_l is not None
    # progress advanced
    assert float(p["axis_progress"]["atk"]) > 4.0
    msg = allocate_stat(p, reg, "defense", 2)
    assert "power" not in msg.lower()
    assert "ป้องกัน" in msg or "ถึก" in msg or "defense" not in msg.lower()


def test_growth_still_s_faster_than_f():
    """Regression: WO-048 growth_mult still active."""
    reg = DataRegistry.load(DATA_DIR)
    p_s = create_player(reg, "g49s", "warrior", "เมษ")
    ensure_progression(p_s, reg)
    p_s["grade_revealed"] = True
    p_s["player_grade"] = "S"
    p_s["growth_profile"] = "balanced"
    p_s["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    apply_invest_to_grades(p_s, "atk", 7)
    p_f = create_player(reg, "g49f", "warrior", "เมษ")
    ensure_progression(p_f, reg)
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "F"
    p_f["growth_profile"] = "balanced"
    p_f["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    apply_invest_to_grades(p_f, "atk", 7)
    assert float(p_s["axis_progress"]["atk"]) > float(p_f["axis_progress"]["atk"])
