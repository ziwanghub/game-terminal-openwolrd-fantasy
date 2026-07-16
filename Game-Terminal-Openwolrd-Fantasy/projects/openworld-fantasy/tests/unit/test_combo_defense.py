from game.data_load.registry import DataRegistry
from game.config import DATA_DIR
from game.domain.combo import apply_defense, parse_combo_input, resolve_combo


def test_parse_combo():
    # preferred: spaces (supports multi-digit skill indices)
    assert parse_combo_input("2 1") == [2, 1]
    assert parse_combo_input("2  1  3") == [2, 1, 3]
    assert parse_combo_input("10 13 15", max_n=3) == [10, 13, 15]
    # commas / plus still ok
    assert parse_combo_input("1,2,3") == [1, 2, 3]
    assert parse_combo_input("2, 1") == [2, 1]
    assert parse_combo_input("2+1") == [2, 1]
    # glued digits = ONE index (never 2 then 1)
    assert parse_combo_input("21", max_n=3) == [21]
    assert parse_combo_input("10") == [10]
    # single skill
    assert parse_combo_input("2") == [2]
    # empty
    assert parse_combo_input("") == []
    assert parse_combo_input("  ") == []


def test_water_wind_fusion():
    reg = DataRegistry.load(DATA_DIR)
    combo = resolve_combo(["water_bolt", "wind_slash"], reg)
    assert combo["ok"]
    assert combo["length"] == 2
    assert combo["total_mana"] > 0
    assert "ice" in combo["elements"] or combo.get("status") == "freeze"
    # Combo 2.0: length-2 mana_mult ~1.12
    assert combo["total_mana"] >= int(round((10 + 9) * 1.12))


def test_combo_mana_scales():
    reg = DataRegistry.load(DATA_DIR)
    one = resolve_combo(["fire_ball"], reg)
    two = resolve_combo(["fire_ball", "water_bolt"], reg)
    assert two["total_mana"] > one["total_mana"]


def test_defense_strong_vs_fire():
    guard = {
        "name": "ม่านน้ำ",
        "strong_vs": ["fire"],
        "weak_vs": ["lightning"],
        "damage_mult_strong": 0.05,
        "damage_mult_neutral": 0.55,
        "damage_mult_weak": 0.95,
    }
    dmg, grade, _ = apply_defense(20, ["fire"], guard)
    assert grade == "strong"
    assert dmg <= 2


def test_defense_weak_vs_lightning():
    guard = {
        "name": "ม่านน้ำ",
        "strong_vs": ["fire"],
        "weak_vs": ["lightning"],
        "damage_mult_strong": 0.05,
        "damage_mult_neutral": 0.55,
        "damage_mult_weak": 0.95,
    }
    dmg, grade, _ = apply_defense(20, ["lightning"], guard)
    assert grade == "weak"
    assert dmg >= 18
