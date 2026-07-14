"""ATB / action gauge combat pacing."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import pick_monster
from game.domain.combat_atb import (
    ATB_FULL,
    action_fill_rate,
    advance_until_ready,
    format_atb_strip,
    init_combat_atb,
    spend_action,
)
from game.domain.progression import allocate_stat, init_progression


def test_faster_player_fills_quicker():
    reg = DataRegistry.load(DATA_DIR)
    slow = create_player(reg, "Slow", "vagabond", "เมษ")
    fast = create_player(reg, "Fast", "vagabond", "เมษ")
    init_progression(slow, reg)
    init_progression(fast, reg)
    fast["stat_points"] = 20
    allocate_stat(fast, reg, "speed", 15)
    r_slow = action_fill_rate(slow, "player", reg)
    r_fast = action_fill_rate(fast, "player", reg)
    assert r_fast > r_slow


def test_advance_until_someone_ready():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "P", "warrior", "เมษ")
    init_progression(p, reg)
    mon = pick_monster(reg, "dark_forest", random.Random(3))
    init_combat_atb(p, mon, reg, random.Random(3), ambush=False)
    ready = advance_until_ready(p, mon, reg, random.Random(4))
    assert ready
    assert set(ready) <= {"player", "monster"}
    if "player" in ready:
        assert float(p.get("atb") or 0) >= ATB_FULL
    if "monster" in ready:
        assert float(mon.get("atb") or 0) >= ATB_FULL


def test_spend_drains_gauge():
    p = {"atb": 110.0}
    spend_action(p)
    assert float(p["atb"]) < 50


def test_ambush_enemy_starts_ahead():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "A", "mage", "เมษ")
    init_progression(p, reg)
    mon = pick_monster(reg, "dark_forest", random.Random(1))
    init_combat_atb(p, mon, reg, random.Random(1), ambush=True)
    assert float(mon.get("atb") or 0) > float(p.get("atb") or 0)


def test_atb_strip_soft_labels():
    p = {"atb": 100}
    m = {"atb": 20}
    s = format_atb_strip(p, m)
    assert "จังหวะ" in s or "[" in s
    assert "พร้อม" in s or "ช้า" in s
