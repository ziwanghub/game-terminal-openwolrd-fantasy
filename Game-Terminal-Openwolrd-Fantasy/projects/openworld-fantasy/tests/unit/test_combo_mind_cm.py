"""CM1–CM2: focus/intellect steps + mag mana relief on combos."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combo import max_combo_for_player, resolve_combo
from game.domain.combo_mind import (
    combo_mana_mind_multiplier,
    combo_step_bonuses,
    ensure_focus_latent,
    mind_intellect,
    soft_combo_mind_hint,
    soft_focus_label,
    soft_intellect_label,
)
from game.domain.progression import allocate_stat, init_progression, recompute_powers


def test_focus_init_and_labels():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "F", "mage", "เมษ")
    init_progression(p, reg)
    fl = ensure_focus_latent(p, reg)
    assert fl >= 0
    assert soft_focus_label(p, reg)
    assert soft_intellect_label(p, reg)
    assert "จิต" in soft_combo_mind_hint(p, reg) or "ฉลาด" in soft_combo_mind_hint(p, reg)


def test_high_focus_more_combo_steps():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "C", "warrior", "สิงห์")
    init_progression(p, reg)
    p["level"] = 5  # base max_combo 2 from table
    ensure_focus_latent(p, reg)
    p["focus_latent"] = 2.0
    low = max_combo_for_player(p, reg)
    p["focus_latent"] = 22.0
    high = max_combo_for_player(p, reg)
    assert high >= low
    fs_lo, _ = combo_step_bonuses({**p, "focus_latent": 2.0}, reg)
    fs_hi, _ = combo_step_bonuses({**p, "focus_latent": 22.0}, reg)
    assert fs_hi > fs_lo


def test_intellect_not_free_p_but_growth_works():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "I", "mage", "เมษ")
    init_progression(p, reg)
    p["level"] = 10
    recompute_powers(p, reg)
    m0 = mind_intellect(p, reg)
    # CM3: cannot dump P into intelligence
    p["stat_points"] = 20
    msg = allocate_stat(p, reg, "intelligence", 10)
    assert "ไม่ได้" in msg or "แจก" in msg
    assert int(p.get("stat_points") or 0) == 20
    # soft growth still raises mind
    from game.domain.combo_mind import note_mind_growth

    p["mind_growth"] = 0
    note_mind_growth(p, 5.0, reason="learn")
    recompute_powers(p, reg)
    m1 = mind_intellect(p, reg)
    assert m1 > m0
    _, steps0 = combo_step_bonuses({**p, "stats_alloc": {"intelligence": 0}, "power_intel": 3, "mind_growth": 0}, reg)
    p2 = dict(p)
    p2["power_intel"] = 20
    p2["mind_growth"] = 8
    p2["stats_alloc"] = dict(p.get("stats_alloc") or {})
    p2["stats_alloc"]["intelligence"] = 10  # legacy storage still counts
    _, steps1 = combo_step_bonuses(p2, reg)
    assert steps1 >= steps0


def test_mag_reduces_mind_mana_mult():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "M", "mage", "เมษ")
    init_progression(p, reg)
    ensure_focus_latent(p, reg)
    p["focus_latent"] = 10
    p["power_intel"] = 10
    p["power_mag"] = 2
    low_mag = combo_mana_mind_multiplier(p, reg)
    p["power_mag"] = 30
    high_mag = combo_mana_mind_multiplier(p, reg)
    assert high_mag < low_mag
    assert high_mag >= 0.75


def test_resolve_combo_applies_mind_mult():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "R", "mage", "เมษ")
    init_progression(p, reg)
    p["skills"] = ["water_bolt", "wind_slash"]
    p["level"] = 15
    ensure_focus_latent(p, reg)
    p["focus_latent"] = 5
    p["power_intel"] = 3
    p["power_mag"] = 2
    c_low = resolve_combo(["water_bolt", "wind_slash"], reg, max_n=3, player=p)
    p["power_mag"] = 30
    c_hi = resolve_combo(["water_bolt", "wind_slash"], reg, max_n=3, player=p)
    assert c_low.get("ok") and c_hi.get("ok")
    assert int(c_hi["total_mana"]) <= int(c_low["total_mana"])
