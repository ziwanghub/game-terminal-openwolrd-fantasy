
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import apply_soft_death, scaled_price, material_drop_chances
from game.domain.character import create_player
from game.domain.combat import apply_on_hit_cards
from game.domain.boss import spawn_boss, check_phase_transition
import random


def test_soft_death_loses_money():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "d", "warrior", "เมษ")
    p["money_world"] = 1000
    p["xp"] = 100
    p["hp"] = 1
    msg = apply_soft_death(p, reg)
    assert p["money_world"] < 1000
    assert p["xp"] < 100
    assert "เสีย" in msg or "สลบ" in msg


def test_shop_price_scales_with_tier():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "p", "warrior", "เมษ")
    p["location"] = "dark_forest"
    a = scaled_price(100, reg, p)
    p["location"] = "void_rift"
    b = scaled_price(100, reg, p)
    assert b > a


def test_on_hit_one_status_only():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c", "rogue", "พิจิก")
    p["on_hit_effects"] = [
        {"status": "burn", "chance": 1.0},
        {"status": "shock", "chance": 1.0},
    ]
    mon = {"statuses": [], "hp": 50, "max_hp": 50}
    notes = apply_on_hit_cards(p, mon, random.Random(1))
    assert len(notes) <= 1
    assert len(mon["statuses"]) <= 1


def test_new_areas_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert "mist_marsh" in reg.areas
    assert "crystal_peak" in reg.areas
    assert "void_rift" in reg.areas
    assert "boss_void_herald" in reg.monsters


def test_boss_mechanic_fields():
    reg = DataRegistry.load(DATA_DIR)
    mon = spawn_boss(reg, "crystal_peak", random.Random(0))
    assert mon
    mon["hp"] = int(mon["max_hp"] * 0.4)
    msg = check_phase_transition(mon, random.Random(0))
    assert msg
    # prism should get reflect eventually
    if mon.get("id") == "boss_prism_sovereign":
        assert mon.get("phase", 1) >= 2
