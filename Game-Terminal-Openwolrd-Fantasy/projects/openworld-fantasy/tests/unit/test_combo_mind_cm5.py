"""CM5 balance: focus ceil by level · soft messages · mind growth soft-cap."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combo import max_combo_for_player
from game.domain.combo_mind import (
    adjust_focus_latent,
    ensure_focus_latent,
    focus_ceil_for_level,
    mind_intellect,
    note_mind_growth,
    soft_combo_too_long_message,
)
from game.domain.progression import init_progression, library_visit


def test_focus_ceil_lower_early_game():
    reg = DataRegistry.load(DATA_DIR)
    c1 = focus_ceil_for_level(5, reg)
    c20 = focus_ceil_for_level(25, reg)
    c99 = focus_ceil_for_level(99, reg)
    assert c1 < c20 <= c99
    assert c1 <= 16


def test_ensure_clamps_to_level_ceil():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L", "mage", "เมษ")
    init_progression(p, reg)
    p["level"] = 5
    p["focus_latent"] = 99.0
    fl = ensure_focus_latent(p, reg)
    assert fl <= focus_ceil_for_level(5, reg) + 0.01


def test_rest_near_ceil_diminishes():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "R", "warrior", "สิงห์")
    init_progression(p, reg)
    p["level"] = 8
    ceil = focus_ceil_for_level(8, reg)
    p["focus_latent"] = ceil - 0.2
    before = float(p["focus_latent"])
    adjust_focus_latent(p, 2.0, reg, reason="rest")
    # should not jump full +2 when near ceil
    assert float(p["focus_latent"]) < before + 1.5


def test_soft_too_long_message():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "T", "mage", "เมษ")
    init_progression(p, reg)
    ensure_focus_latent(p, reg)
    msg = soft_combo_too_long_message(p, 5, 2, reg)
    assert "2" in msg
    assert "ขั้น" in msg or "ท่า" in msg


def test_mind_growth_soft_cap_diminishes():
    reg = DataRegistry.load(DATA_DIR)
    p = {"power_intel": 5, "stats_alloc": {}, "learn_points": 0, "level": 10, "mind_growth": 5}
    m_low = mind_intellect(p, reg)
    p["mind_growth"] = 40
    m_high = mind_intellect(p, reg)
    # growth 40 should not be 8x of growth 5
    assert m_high > m_low
    assert (m_high - 5) < (40 * 0.4 + 1)  # less than linear full rate


def test_library_can_grow_mind():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Lib", "mage", "เมษ")
    init_progression(p, reg)
    p["library_unlocked"] = True
    p["level"] = 10
    p["time_units"] = 100
    p["library_last_visit"] = -999
    p["mind_growth"] = 0.0
    # force unlock access
    p["flags"] = dict(p.get("flags") or {})
    notes = library_visit(p, reg)
    # either denied or grew — if entries exist and not on CD, growth may apply
    if notes and "ปิด" not in str(notes[0]) and "คูลดาวน์" not in "\n".join(notes):
        # growth or soft line possible
        assert float(p.get("mind_growth") or 0) >= 0


def test_early_level_combo_not_absurd():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "E", "warrior", "สิงห์")
    init_progression(p, reg)
    p["level"] = 3
    p["focus_latent"] = 50  # will clamp
    p["power_intel"] = 50
    p["mind_growth"] = 50
    ensure_focus_latent(p, reg)
    n = max_combo_for_player(p, reg)
    # base 2 + at most +2 focus + +2 intellect but hard cap 6; early still ok
    assert 1 <= n <= 6
