"""WO-032: mountain / crystal / city / void area loops."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.soft_foresight import area_loop_soft_lines


def test_mountain_loop_and_titan_dep():
    reg = DataRegistry.load(DATA_DIR)
    for q in ("mountain_ridge_walk", "mountain_golem_cull", "mountain_titan_ready"):
        assert q in (reg.quests or {})
    titan = (reg.quests or {}).get("titan_fall") or {}
    assert "mountain_titan_ready" in (titan.get("depends_on") or [])


def test_crystal_loop_and_prism_dep():
    reg = DataRegistry.load(DATA_DIR)
    assert "crystal_shard_cull" in (reg.quests or {})
    assert "crystal_peak_watch" in (reg.quests or {})
    prism = (reg.quests or {}).get("prism_sovereign_fall") or {}
    assert "crystal_peak_watch" in (prism.get("depends_on") or [])


def test_city_and_void_soft_loops():
    reg = DataRegistry.load(DATA_DIR)
    assert "city_alley_patrol" in (reg.quests or {})
    assert "city_market_echo" in (reg.quests or {})
    assert "void_edge_walk" in (reg.quests or {})
    assert "void_whisper_cull" in (reg.quests or {})


def test_all_areas_have_loop_soft():
    reg = DataRegistry.load(DATA_DIR)
    missing = []
    for aid, area in (reg.areas or {}).items():
        if not (area or {}).get("loop_soft"):
            missing.append(aid)
    assert missing == [], f"areas missing loop_soft: {missing}"


def test_loop_soft_lines_resolve():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w32", "warrior", "เมษ")
    for aid in ("mountain_rock", "crystal_peak", "ancient_city", "void_rift"):
        p["location"] = aid
        assert area_loop_soft_lines(p, reg), aid
