"""WO-004 P1.1: auto_fight uses domain Needs like combat_session."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import ensure_needs, get_needs
from game.domain.equipment import recompute_stats
from game.runtime.auto_farm import auto_fight


def _weak_mon(**kwargs):
    mon = {
        "id": "forest_wolf",
        "name": "Wolf",
        "level": 1,
        "hp": 40,
        "max_hp": 40,
        "atk": 4,
        "xp_mult": 1.0,
        "elements": ["physical"],
        "attack_profiles": [{"id": "a", "power": 3, "weight": 1}],
    }
    mon.update(kwargs)
    return mon


def test_auto_fight_applies_combat_needs_ticks_and_win():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n1", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 20, "fatigue": 15, "morale": 70}
    mon = _weak_mon(hp=25, max_hp=25, atk=2)
    before = dict(get_needs(p))
    logs = auto_fight(
        p, mon, reg, random.Random(2), "dark_forest", xp_factor=1.0, skill_plan=[1]
    )
    after = get_needs(p)
    assert any("ออโต้ชนะ" in x for x in logs)
    # combat ticks + combat_win: hunger/fatigue tend up from ticks; morale up from win
    # at least one axis moved
    assert after != before
    # win should not leave morale collapsed vs start for easy fight
    assert after["morale"] >= before["morale"] - 5


def test_auto_fight_loss_applies_combat_loss_before_soft_revive():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n2", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 30, "fatigue": 20, "morale": 60}
    p["hp"] = 5
    p["max_hp"] = 100
    mon = _weak_mon(hp=500, max_hp=500, atk=80, level=20)
    mon["attack_profiles"] = [{"id": "a", "power": 50, "weight": 1}]
    before_m = get_needs(p)["morale"]
    logs = auto_fight(p, mon, reg, random.Random(0), "dark_forest")
    text = "".join(logs)
    assert "แพ้" in text
    assert int(p["hp"]) > 0  # soft revive
    # combat_loss drops morale (-14 softened)
    assert get_needs(p)["morale"] < before_m


def test_auto_fight_hunger_crit_still_resolves():
    """Hunger atk mult path (via player_attack_damage) must not crash auto."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n3", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 95, "fatigue": 10, "morale": 50}
    mon = _weak_mon(hp=20, max_hp=20, atk=1)
    logs = auto_fight(
        p, mon, reg, random.Random(3), "dark_forest", xp_factor=1.0, skill_plan=[1]
    )
    assert logs
    assert int(p["hp"]) > 0 or "แพ้" in "".join(logs)


def test_auto_fight_low_morale_can_log_skill_issues():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n4", "mage", "เมถุน")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 10}  # crit band
    p["mana"] = 50
    p["max_mana"] = 50
    # ensure a real skill id in plan if possible
    skills = list(p.get("skills") or [])
    mon = _weak_mon(hp=80, max_hp=80, atk=3)
    logs = auto_fight(
        p,
        mon,
        reg,
        random.Random(7),
        "dark_forest",
        xp_factor=1.0,
        skill_plan=[1, 2, 1, 2],
        use_regen=True,
    )
    # fight completes; low morale may add soft lines
    assert logs
    assert int(p.get("hp") or 0) >= 0
