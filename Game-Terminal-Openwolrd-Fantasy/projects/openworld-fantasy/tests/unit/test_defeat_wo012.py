"""WO-012: Soft death symmetry + defeat cause + near-death warnings."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import apply_soft_death
from game.domain.character import create_player
from game.domain.defeat import (
    explain_defeat,
    near_death_warning_lines,
    resolve_player_defeat,
)
from game.domain.equipment import recompute_stats
from game.domain.needs import ensure_needs, get_needs
from game.runtime.auto_farm import auto_fight
from game.ui_terminal.panels import soft_death_panel


def test_explain_defeat_morale_primary():
    p = {
        "level": 5,
        "needs": {"hunger": 20, "fatigue": 20, "morale": 8},
        "hp": 1,
        "max_hp": 100,
    }
    mon = {"level": 5, "name": "Wolf"}
    info = explain_defeat(p, mon)
    assert info["primary"] == "morale"
    assert "สาเหตุหลัก" in info["line"]
    assert "ขวัญ" in info["line"] or "ขวัญ" in info["label_th"]


def test_explain_defeat_heavy_fight():
    p = {
        "level": 2,
        "needs": {"hunger": 20, "fatigue": 20, "morale": 70},
        "hp": 1,
        "max_hp": 100,
    }
    mon = {"level": 10, "name": "Boss", "boss": True}
    info = explain_defeat(p, mon)
    assert info["primary"] == "fight"
    assert "ไฟต์" in info["line"] or "ไฟต์" in info["label_th"]


def test_near_death_warn_once():
    p = {"hp": 20, "max_hp": 100}
    w1 = near_death_warning_lines(p, enemy_name="Wolf")
    assert w1
    assert "เลือดบาง" in "\n".join(w1) or "25%" in "\n".join(w1)
    w2 = near_death_warning_lines(p, enemy_name="Wolf")
    assert w2 == []  # dedup
    p["hp"] = 10
    w3 = near_death_warning_lines(p, enemy_name="Wolf")
    assert any("สลบ" in x or "⚠" in x for x in w3)


def test_resolve_soft_death_symmetric_money():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "d1", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["money_world"] = 1000
    p["xp"] = 200
    p["hp"] = 0
    p["needs"] = {"hunger": 90, "fatigue": 40, "morale": 50}
    mon = {"level": 8, "name": "Bear", "boss": False}
    r = resolve_player_defeat(p, reg, mon=mon, enemy_name="Bear", context="combat")
    assert int(p["hp"]) > 0
    assert int(p["money_world"]) < 1000
    assert "death_msg" in r
    assert any("สาเหตุ" in x for x in r["feedback"])
    text = soft_death_panel(r["death_msg"], extra=r["panel_extra"])
    assert "Soft Death" in text or "ล้มลง" in text
    assert "สาเหตุ" in text or "ผลกระทบ" in text


def test_auto_fight_uses_same_soft_death():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "d2", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 30, "fatigue": 20, "morale": 55}
    p["money_world"] = 500
    p["xp"] = 80
    p["hp"] = 5
    p["max_hp"] = 100
    mon = {
        "id": "forest_wolf",
        "name": "Wolf",
        "level": 15,
        "hp": 500,
        "max_hp": 500,
        "atk": 80,
        "elements": ["physical"],
        "attack_profiles": [{"id": "a", "power": 50, "weight": 1}],
    }
    before_m = get_needs(p)["morale"]
    before_money = p["money_world"]
    logs = auto_fight(p, mon, reg, random.Random(1), "dark_forest")
    text = "\n".join(logs)
    assert "แพ้" in text or "สลบ" in text
    assert "สาเหตุ" in text or "Soft Death" in text or "สลบ" in text
    assert int(p["hp"]) > 0
    assert int(p["money_world"]) < before_money  # same apply_soft_death
    assert get_needs(p)["morale"] < before_m
