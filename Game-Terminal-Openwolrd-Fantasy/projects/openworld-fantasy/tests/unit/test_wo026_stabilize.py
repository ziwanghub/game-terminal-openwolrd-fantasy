"""WO-026: Playtest stabilize — balance, onboarding, chamber, summary."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.divine_burden import apply_burden_tick, gap_band, burden_gap, player_fit_rank
from game.domain.needs import ensure_needs, get_needs
from game.ui_terminal.help import CITY_ONBOARD_TIPS, TUTORIAL_PAGES, help_covers_keywords


def test_tutorial_has_relic_page():
    assert len(TUTORIAL_PAGES) >= 9
    blob = "\n".join("\n".join(p) for p in TUTORIAL_PAGES)
    assert "เรลิก" in blob or "ภาระ" in blob
    assert any("เรลิก" in t or "ภาระ" in t or "ห้องทดสอบ" in t for t in CITY_ONBOARD_TIPS)


def test_help_keywords_include_burden_terms():
    words = help_covers_keywords()
    blob = " ".join(words)
    assert "เรลิก" in blob or "ภาระ" in blob


def test_burden_drain_not_brutal_over_12_ticks():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w026a", "warrior", "เมษ")
    p["level"] = 2
    ensure_needs(p)
    p["needs"]["morale"] = 80
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    for i in range(12):
        p["auto_ticks"] = i + 1
        apply_burden_tick(p, reg, context="field", rng=random.Random(100 + i))
    mor = int(get_needs(p)["morale"])
    # medium-soft: should keep substantial morale
    assert mor >= 25
    assert 80 - mor < 55


def test_mid_level_legendary_often_strain_not_eternal_crush():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w026b", "warrior", "เมษ")
    p["level"] = 16
    # fit rank ~ 1+4 + maybe affinity
    assert player_fit_rank(p, reg) >= 5
    g = burden_gap(p, reg, "legendary")
    assert gap_band(g) in ("fit", "strain", "crush")
    # at 16 with //4 should not be huge gap
    assert g <= 2


def test_chamber_money_and_return():
    from game.services.godforge_chamber import (
        CHAMBER_RELICS,
        enter_godforge,
        exit_godforge,
        loan_relic,
        spar_dummy,
    )

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w026c", "warrior", "เมษ")
    p["money_world"] = 400
    enter_godforge(p, reg)
    loan_relic(p, reg, CHAMBER_RELICS[1]["id"])
    spar_dummy(p, reg, random.Random(9))
    exit_godforge(p, reg)
    assert int(p["money_world"]) == 400
    assert CHAMBER_RELICS[1]["id"] not in (p.get("inventory_ids") or [])


def test_god_summary_mentions_burden():
    from game.runtime.auto_run_log import format_auto_run_summary, start_auto_run

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w026d", "warrior", "เมษ")
    ensure_needs(p)
    start_auto_run(p, kind="field", label="t", max_ticks=3)
    p["_auto_run"]["active"] = False
    p["_auto_run"]["ticks"] = 3
    p["_burden_active"] = "crush"
    p["_burden_drain_total"] = 6
    p["_auto_run"]["burden_unequips"] = 1
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["level"] = 1
    p["_auto_run_last"] = dict(p["_auto_run"])
    lines = format_auto_run_summary(p, reg, reason="done")
    blob = "\n".join(lines)
    assert "ภาระ" in blob
