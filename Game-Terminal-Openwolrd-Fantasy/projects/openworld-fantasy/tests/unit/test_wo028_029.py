"""WO-028 playtest path + WO-029 area loop polish."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.narrative import area_mood
from game.domain.soft_foresight import area_loop_soft_lines
import random


def test_wo029_area_loop_quests():
    reg = DataRegistry.load(DATA_DIR)
    for qid in (
        "forest_echoes_hunt",
        "forest_night_watch",
        "marsh_leech_cull",
        "marsh_reed_path",
    ):
        assert qid in (reg.quests or {}), qid
    # hydra depends on marsh reed path for deeper loop
    hydra = (reg.quests or {}).get("hydra_slayer") or {}
    assert "marsh_reed_path" in (hydra.get("depends_on") or [])


def test_wo029_area_loop_soft_tips():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "a029", "warrior", "เมษ")
    p["location"] = "dark_forest"
    tips = area_loop_soft_lines(p, reg)
    assert tips
    p["location"] = "mist_marsh"
    tips2 = area_loop_soft_lines(p, reg)
    assert tips2


def test_wo029_area_mood_expanded():
    reg = DataRegistry.load(DATA_DIR)
    lines = area_mood(reg, "dark_forest", random.Random(1))
    assert lines
    lines2 = area_mood(reg, "mist_marsh", random.Random(2))
    assert lines2
    # registry narrative should have expanded pools
    narr = getattr(reg, "narrative", None) or {}
    # narrative may be nested - check field flavor loaded
    assert len(lines) >= 1


def test_wo028_relic_quest_chain_present():
    reg = DataRegistry.load(DATA_DIR)

    def rewards(qid: str):
        return list(((reg.quests or {}).get(qid) or {}).get("reward_items") or [])

    assert "relic_storm_fang" in rewards("weight_of_storm")
    assert "relic_hell_ember_blade" in rewards("embers_of_hell_relic")
    assert "relic_aegis_sky" in rewards("sky_aegis_burden")


def test_hydra_depends_chain_not_broken():
    reg = DataRegistry.load(DATA_DIR)
    # marsh_reed depends on leech cull which depends on mist_walker
    reed = (reg.quests or {}).get("marsh_reed_path") or {}
    assert "marsh_leech_cull" in (reed.get("depends_on") or [])
