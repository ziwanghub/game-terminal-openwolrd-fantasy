"""WO-004 Phase 1: auto prefs morale, care decision, rest, dungeon care pass."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.needs import (
    apply_auto_rest,
    decide_auto_needs_care,
    ensure_needs,
    get_needs,
    is_food_item,
)
from game.runtime.dungeon_auto import (
    ensure_auto_prefs,
    run_auto_needs_care,
    _effective_thresholds,
)


def test_auto_prefs_include_morale_defaults():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap1", "warrior", "ตุลย์")
    prefs = ensure_auto_prefs(p)
    assert "morale" in prefs
    assert 10 <= int(prefs["morale"]) <= 70
    assert prefs["low_morale_policy"] in ("ignore", "caution", "retreat")
    th = _effective_thresholds(p, reg)
    assert "morale" in th


def test_decide_care_eat_and_rest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap2", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"] = {"hunger": 70, "fatigue": 80, "morale": 50}
    intents = decide_auto_needs_care(
        p,
        hunger_th=50,
        fatigue_th=55,
        morale_th=35,
        low_morale_policy="caution",
        food_available=True,
    )
    acts = [i["action"] for i in intents]
    assert "eat" in acts
    assert "rest" in acts
    assert any("กิน" in i["reason"] or "พัก" in i["reason"] for i in intents)


def test_decide_care_morale_caution_and_retreat():
    p = {
        "needs": {"hunger": 10, "fatigue": 10, "morale": 20},
    }
    caution = decide_auto_needs_care(
        p,
        hunger_th=50,
        fatigue_th=55,
        morale_th=35,
        low_morale_policy="caution",
        food_available=True,
    )
    assert any(i["action"] == "avoid_fight" for i in caution)
    retreat = decide_auto_needs_care(
        p,
        hunger_th=50,
        fatigue_th=55,
        morale_th=35,
        low_morale_policy="retreat",
        food_available=True,
    )
    assert any(i["action"] == "stop_retreat" for i in retreat)


def test_r2_mid_morale_does_not_eat_for_morale():
    """WO-017 R2: mid band must not burn food for morale (mid = morale ≥45)."""
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 50}}  # mid band
    intents = decide_auto_needs_care(
        p,
        hunger_th=58,
        fatigue_th=62,
        morale_th=30,
        low_morale_policy="caution",
        food_available=True,
    )
    acts = [i["action"] for i in intents]
    assert "eat_morale" not in acts
    assert "avoid_fight" not in acts


def test_apply_auto_rest_reduces_fatigue():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap3", "warrior", "ตุลย์")
    ensure_needs(p)
    p["needs"] = {"hunger": 20, "fatigue": 70, "morale": 40}
    before = get_needs(p)["fatigue"]
    notes = apply_auto_rest(p)
    after = get_needs(p)["fatigue"]
    assert after < before
    assert notes


def test_run_auto_needs_care_rest_skips_and_logs():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap4", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    ensure_auto_prefs(p)
    p["needs"] = {"hunger": 15, "fatigue": 85, "morale": 60}
    p["inventory_ids"] = ["bread"] if "bread" in (reg.items or {}) else list(
        p.get("inventory_ids") or []
    )
    # force fatigue over threshold
    p["auto_prefs"] = ensure_auto_prefs(p)
    p["auto_prefs"]["fatigue"] = 50
    lines, stop, avoid, rested = run_auto_needs_care(p, reg, allow_rest=True)
    assert rested is True
    assert any("พัก" in x or "ล้า" in x for x in lines)
    assert get_needs(p)["fatigue"] < 85


def test_run_auto_needs_care_morale_retreat_stops():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap5", "mage", "เมถุน")
    ensure_needs(p)
    prefs = ensure_auto_prefs(p)
    prefs["low_morale_policy"] = "retreat"
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["needs"] = {"hunger": 10, "fatigue": 10, "morale": 15}
    lines, stop, avoid, rested = run_auto_needs_care(p, reg, allow_rest=True)
    assert stop == "morale"
    assert any("ขวัญ" in x for x in lines)
    assert p.get("auto_care_notes")


def test_safe_mode_raises_morale_threshold():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap6", "warrior", "ตุลย์")
    prefs = ensure_auto_prefs(p)
    prefs["morale"] = 35
    prefs["item_mode"] = "normal"
    p["auto_prefs"] = prefs
    th_n = _effective_thresholds(p, reg)
    prefs["item_mode"] = "safe"
    p["auto_prefs"] = prefs
    ensure_auto_prefs(p)
    th_s = _effective_thresholds(p, reg)
    assert th_s["morale"] >= th_n["morale"]


def test_p13_morale_bands_drive_policy():
    from game.domain.needs import resolve_morale_auto_policy

    high = resolve_morale_auto_policy(
        {"needs": {"hunger": 10, "fatigue": 10, "morale": 80}},
        morale_th=35,
        low_morale_policy="caution",
    )
    assert high["band"] == "high"
    assert high["aggression"] == "high"
    assert high["avoid_fight"] is False

    low = resolve_morale_auto_policy(
        {"needs": {"hunger": 10, "fatigue": 10, "morale": 30}},
        morale_th=35,
        low_morale_policy="caution",
    )
    assert low["band"] == "low"
    assert low["avoid_fight"] is True
    assert low["eat_for_morale"] is True
    assert low["aggression"] == "low"
    assert low["boss_auto_ok"] is False

    crit = resolve_morale_auto_policy(
        {"needs": {"hunger": 10, "fatigue": 10, "morale": 12}},
        morale_th=35,
        low_morale_policy="retreat",
    )
    assert crit["band"] == "crit"
    assert crit["rest_long"] is True
    assert crit["stop_retreat"] is True
    assert crit["aggression"] == "passive"


def test_p13_eat_for_morale_intent():
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 28}}
    intents = decide_auto_needs_care(
        p,
        hunger_th=50,
        fatigue_th=55,
        morale_th=35,
        low_morale_policy="caution",
        food_available=True,
    )
    acts = [i["action"] for i in intents]
    assert "eat_morale" in acts
    assert "avoid_fight" in acts
    assert any(i["action"] == "set_aggression" and i["reason"] == "low" for i in intents)


def test_p13_consume_food_prefer_morale():
    from game.runtime.dungeon_auto import _consume_best_food

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap7", "warrior", "ตุลย์")
    ensure_needs(p)
    p["needs"] = {"hunger": 15, "fatigue": 15, "morale": 25}
    # two foods if possible
    ids = []
    for iid, it in (reg.items or {}).items():
        if is_food_item(it):
            ids.append(str(iid))
        if len(ids) >= 2:
            break
    if len(ids) < 1:
        return
    p["inventory_ids"] = ids[:2]
    p["inventory"] = ids[:2]
    p["inventory_rarities"] = ["common"] * len(p["inventory_ids"])
    before = get_needs(p)["morale"]
    notes = _consume_best_food(p, reg, prefer="morale")
    assert notes
    assert get_needs(p)["morale"] >= before


def test_p13_rest_long_on_crit_care():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap8", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    prefs = ensure_auto_prefs(p)
    prefs["low_morale_policy"] = "caution"
    prefs["morale"] = 40
    p["auto_prefs"] = prefs
    p["needs"] = {"hunger": 10, "fatigue": 30, "morale": 15}
    lines, stop, avoid, rested = run_auto_needs_care(p, reg, allow_rest=True)
    assert rested is True
    assert avoid is True
    assert any("ขวัญ" in x or "พัก" in x for x in lines)
