import random
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.boss import check_phase_transition, spawn_boss
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats


def test_gear_set_bonus():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "set", "warrior", "สิงห์")
    base = int(p["bonus_atk"])
    add_item(p, "iron_sword", reg)
    add_item(p, "leather_armor", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "leather_armor", reg)
    recompute_stats(p, reg)
    assert p.get("active_sets")
    assert any("เหล็ก" in s or "iron" in s.lower() or "กองทัพ" in s for s in p["active_sets"])
    assert int(p["bonus_atk"]) > base


def test_boss_multi_phase():
    reg = DataRegistry.load(DATA_DIR)
    mon = spawn_boss(reg, "dark_forest", random.Random(0))
    assert mon and mon["max_phases"] >= 2
    mon["hp"] = int(mon["max_hp"] * 0.5)
    msg = check_phase_transition(mon, random.Random(0))
    assert msg is not None
    assert mon["phase"] == 2
    assert mon["atk"] > 0


def test_sets_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert "iron_legion" in reg.gear_sets
