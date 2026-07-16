"""WO-047 feel polish smoke after synergy."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.relic_anima import (
    SYN_AREA_TENSION,
    SYN_RESONATE,
    evaluate_relic_area_synergy,
    relic_area_synergy_morale_factor,
    synergy_foresight_lines,
    try_area_synergy_presence_pulse,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch


def test_resonate_vs_tension_morale_feel():
    reg = DataRegistry.load(DATA_DIR)
    p_ok = create_player(reg, "f47a", "warrior", "เมษ")
    ensure_stat_arch(p_ok)
    p_ok["location"] = "mountain_rock"
    p_ok["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p_ok["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    p_bad = create_player(reg, "f47b", "warrior", "เมษ")
    ensure_stat_arch(p_bad)
    p_bad["location"] = "mountain_rock"
    p_bad["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p_bad["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}
    assert evaluate_relic_area_synergy(p_ok, reg)["mode"] == SYN_RESONATE
    assert evaluate_relic_area_synergy(p_bad, reg)["mode"] == SYN_AREA_TENSION
    assert relic_area_synergy_morale_factor(p_ok, reg) <= 0.96
    assert relic_area_synergy_morale_factor(p_bad, reg) >= 1.08


def test_foresight_tone_natural():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f47c", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "crystal_peak"
    p["equip_ids"] = {"main_hand": "relic_storm_fang", "body": "relic_aegis_sky"}
    p["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    lines = synergy_foresight_lines(p, reg, area_id="crystal_peak", brief=True)
    assert lines
    blob = "\n".join(lines)
    # less raw "lean〔…〕" jargon in brief
    assert "lean〔" not in blob


def test_presence_pulse_raises_anima_clearly():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f47d", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "ancient_city"
    p["anima"] = 50.0
    p["equip_ids"] = {"main_hand": "relic_storm_fang", "body": "relic_aegis_sky"}
    p["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    a0 = anima_value(p)
    lines = try_area_synergy_presence_pulse(p, reg, force=True)
    assert lines
    assert anima_value(p) >= a0 + 0.5
