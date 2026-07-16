"""WO-031: Area loop polish — cave_shadow + desert_heat."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.soft_foresight import area_loop_soft_lines
from game.domain.narrative import area_mood
import random


def test_cave_loop_quests():
    reg = DataRegistry.load(DATA_DIR)
    assert "cave_bat_cull" in (reg.quests or {})
    assert "cave_lantern_path" in (reg.quests or {})
    shadow = (reg.quests or {}).get("shadow_slayer") or {}
    deps = shadow.get("depends_on") or []
    assert "cave_lantern_path" in deps
    cull = (reg.quests or {}).get("cave_bat_cull") or {}
    assert cull.get("area") == "cave_shadow"


def test_desert_loop_quests():
    reg = DataRegistry.load(DATA_DIR)
    for qid in ("desert_dune_walk", "desert_scorpion_cull", "desert_sun_ready"):
        assert qid in (reg.quests or {}), qid
    sun = (reg.quests or {}).get("sun_end") or {}
    assert "desert_sun_ready" in (sun.get("depends_on") or [])
    dune = (reg.quests or {}).get("desert_dune_walk") or {}
    assert dune.get("area") == "desert_heat"


def test_cave_desert_loop_soft_tips():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "a031", "warrior", "เมษ")
    p["location"] = "cave_shadow"
    assert area_loop_soft_lines(p, reg)
    p["location"] = "desert_heat"
    assert area_loop_soft_lines(p, reg)
    cave = (reg.areas or {}).get("cave_shadow") or {}
    desert = (reg.areas or {}).get("desert_heat") or {}
    assert cave.get("loop_soft")
    assert desert.get("loop_soft")


def test_cave_desert_mood():
    reg = DataRegistry.load(DATA_DIR)
    assert area_mood(reg, "cave_shadow", random.Random(1))
    assert area_mood(reg, "desert_heat", random.Random(2))
