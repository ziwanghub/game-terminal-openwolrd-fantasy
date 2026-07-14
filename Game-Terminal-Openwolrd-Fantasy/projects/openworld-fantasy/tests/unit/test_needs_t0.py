"""T0 needs: rest/explore deltas + soft labels."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import (
    apply_needs_event,
    ensure_needs,
    format_needs_soft_lines,
    get_needs,
    soft_label,
)


def test_ensure_and_defaults():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n1", "warrior", "เมษ")
    n = ensure_needs(p)
    assert 0 <= n["hunger"] <= 100
    assert "morale" in n


def test_rest_lowers_fatigue():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n2", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["fatigue"] = 60
    apply_needs_event(p, "rest", silent=True)
    assert p["needs"]["fatigue"] < 60


def test_explore_raises_hunger_and_fatigue():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n3", "mage", "เมถุน")
    ensure_needs(p)
    h0, f0 = p["needs"]["hunger"], p["needs"]["fatigue"]
    apply_needs_event(p, "explore", silent=True)
    assert p["needs"]["hunger"] >= h0
    assert p["needs"]["fatigue"] >= f0


def test_eat_lowers_hunger():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n4", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 80
    apply_needs_event(p, "eat", silent=True)
    assert p["needs"]["hunger"] < 80


def test_soft_labels_no_raw_numbers():
    assert soft_label("hunger", 10) == "อิ่ม"
    assert soft_label("fatigue", 90) == "หมดแรง"
    assert soft_label("morale", 80) == "ขวัญดี"
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n5", "warrior", "เมษ")
    ensure_needs(p)
    text = "\n".join(format_needs_soft_lines(p))
    assert "ท้อง" in text
    assert "%" not in text


def test_clamp_0_100():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n6", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["hunger"] = 99
    apply_needs_event(p, "explore", silent=True)
    apply_needs_event(p, "explore", silent=True)
    assert p["needs"]["hunger"] <= 100
    p["needs"]["fatigue"] = 5
    apply_needs_event(p, "rest", silent=True)
    assert p["needs"]["fatigue"] >= 0
