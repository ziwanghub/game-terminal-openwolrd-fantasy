"""CM3: intelligence not in free P · soft mind band · migrate."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import (
    ALLOCATE_KEYS,
    allocate_stat,
    ensure_progression,
    format_alloc_panel,
    init_progression,
)


def test_p_menu_four_stats_only():
    assert ALLOCATE_KEYS == ("atk", "defense", "magic", "speed")
    assert "intelligence" not in ALLOCATE_KEYS


def test_refuse_allocate_intelligence():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "X", "vagabond", "เมษ")
    init_progression(p, reg)
    p["stat_points"] = 5
    before = int((p.get("stats_alloc") or {}).get("intelligence") or 0)
    msg = allocate_stat(p, reg, "intelligence", 3)
    assert "ไม่ได้" in msg or "แจก" in msg
    assert int(p.get("stat_points") or 0) == 5
    assert int((p.get("stats_alloc") or {}).get("intelligence") or 0) == before


def test_panel_shows_soft_mind_not_int_invest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Y", "mage", "เมษ")
    init_progression(p, reg)
    lines = "\n".join(format_alloc_panel(p))
    assert "โจมตี" in lines and "เวท" in lines
    assert "ฉลาด" in lines or "ความคิด" in lines
    # should not offer invest slot 5 for intelligence as numbered invest of 5 keys
    assert "1–4" in lines or "1-4" in lines or "ไม่อยู่ในเมนู" in lines or "ความคิด" in lines


def test_migrate_old_int_invest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Z", "mage", "เมษ")
    p["stats_alloc"] = {
        "atk": 0,
        "defense": 0,
        "magic": 0,
        "speed": 0,
        "intelligence": 8,
    }
    p["flags"] = {}
    ensure_progression(p, reg)
    assert (p.get("flags") or {}).get("cm3_int_migrated")
    assert float(p.get("mind_growth") or 0) > 0 or int(p.get("learn_points") or 0) > 0
