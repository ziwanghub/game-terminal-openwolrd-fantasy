"""Intelligence resource — ATB spend, recovery, special options."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.intelligence import (
    apply_intel_item,
    can_use_special_option,
    ensure_intelligence,
    intel_current,
    intel_max,
    rest_intel_recovery,
    spend_intel_for_atb,
    spend_intelligence,
    try_special_option,
)
from game.domain.progression import init_progression, recompute_powers


def test_mind_growth_raises_intel_max():
    """CM3: intellect no longer free-P; learn/mind_growth expands capacity soft."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "I", "vagabond", "เมษ")
    init_progression(p, reg)
    ensure_intelligence(p, reg)
    m0 = intel_max(p)
    p["learn_points"] = int(p.get("learn_points") or 0) + 8
    p["mind_growth"] = float(p.get("mind_growth") or 0) + 4.0
    recompute_powers(p, reg)
    ensure_intelligence(p, reg)
    assert intel_max(p) > m0
    assert intel_current(p) >= 0


def test_spend_and_rest_recover():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "R", "vagabond", "เมษ")
    init_progression(p, reg)
    p["learn_points"] = 5
    recompute_powers(p, reg)
    ensure_intelligence(p, reg)
    p["intel_current"] = intel_max(p)
    ok, _ = spend_intelligence(p, 2, reason="choice")
    assert ok
    mid = intel_current(p)
    rest_intel_recovery(p)
    assert intel_current(p) >= mid


def test_atb_spend_when_not_full():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "A", "vagabond", "เมษ")
    init_progression(p, reg)
    p["learn_points"] = 5
    recompute_powers(p, reg)
    ensure_intelligence(p, reg)
    p["intel_current"] = intel_max(p)
    p["atb"] = 30.0
    ok, msg = spend_intel_for_atb(p, reg, random.Random(1))
    assert ok
    assert float(p["atb"]) > 30
    assert "จังหวะ" in msg or "สติ" in msg or "จิต" in msg


def test_special_option_requires_intel():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "S", "vagabond", "เมษ")
    init_progression(p, reg)
    p["learn_points"] = 15
    recompute_powers(p, reg)
    ensure_intelligence(p, reg)
    p["intel_current"] = 0
    can, why = can_use_special_option(p, 2)
    assert not can
    p["intel_current"] = intel_max(p)
    can2, _ = can_use_special_option(p, 2)
    assert can2
    before = intel_current(p)
    spent, msg, _suc = try_special_option(p, 2, random.Random(2))
    assert spent
    assert intel_current(p) == before - 2


def test_intel_item():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "T", "vagabond", "เมษ")
    init_progression(p, reg)
    ensure_intelligence(p, reg)
    p["intel_current"] = 0
    notes = apply_intel_item(p, {"restore_intel": 3})
    assert intel_current(p) >= 3
    assert notes
