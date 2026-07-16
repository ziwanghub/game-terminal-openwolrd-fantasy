"""WO-027: Relic depth quests + chamber polish + economy dampen."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import grant_combat_money
from game.domain.character import create_player
from game.domain.needs import ensure_needs, get_needs
from game.services.godforge_chamber import (
    CHAMBER_RELICS,
    enter_godforge,
    exit_godforge,
    format_chamber_burden_summary,
    loan_relic,
    spar_dummy,
)


def test_mid_relic_quests_exist():
    reg = DataRegistry.load(DATA_DIR)
    q_hell = (reg.quests or {}).get("embers_of_hell_relic") or {}
    assert "relic_hell_ember_blade" in (q_hell.get("reward_items") or [])
    assert "sun_end" in (q_hell.get("depends_on") or [])
    q_aegis = (reg.quests or {}).get("sky_aegis_burden") or {}
    assert "relic_aegis_sky" in (q_aegis.get("reward_items") or [])
    assert (reg.quests or {}).get("prism_sovereign_fall")


def test_prism_boss_has_aegis_drop():
    reg = DataRegistry.load(DATA_DIR)
    mon = (reg.monsters or {}).get("boss_prism_sovereign") or {}
    items = [str(d.get("item")) for d in (mon.get("drops") or []) if isinstance(d, dict)]
    assert "relic_aegis_sky" in items


def test_chamber_spar_stronger_and_summary():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w027a", "warrior", "เมษ")
    p["level"] = 2
    p["money_world"] = 300
    ensure_needs(p)
    p["needs"]["morale"] = 75
    enter_godforge(p, reg)
    loan_relic(p, reg, CHAMBER_RELICS[1]["id"])  # divine hell test blade
    # equip via ids
    from game.domain.equipment import equip_item

    equip_item(p, CHAMBER_RELICS[1]["id"], reg)
    notes = spar_dummy(p, reg, random.Random(7), rounds=3)
    blob = "\n".join(notes)
    assert "sparring" in blob.lower() or "ซ้อม" in blob
    assert "สรุป" in blob or "ขวัญ" in blob
    summ = format_chamber_burden_summary(p, reg)
    assert any("สรุป" in x or "ขวัญ" in x for x in summ)
    exit_godforge(p, reg)
    assert int(p["money_world"]) == 300
    assert CHAMBER_RELICS[1]["id"] not in (p.get("inventory_ids") or [])


def test_burden_money_dampen_when_crush():
    p = {
        "money_world": 0,
        "money_heaven": 0,
        "money_hell": 0,
        "world_modifiers": {},
        "_burden_active": "crush",
    }
    mon = {"id": "w", "level": 5}
    # average of samples lower than without burden roughly
    gains_crush = []
    gains_none = []
    for s in range(20):
        a = dict(p)
        a["money_world"] = 0
        grant_combat_money(a, mon, random.Random(s), auto=False)
        gains_crush.append(a["money_world"])
        b = {"money_world": 0, "money_heaven": 0, "money_hell": 0, "world_modifiers": {}}
        grant_combat_money(b, mon, random.Random(s), auto=False)
        gains_none.append(b["money_world"])
    assert sum(gains_crush) / len(gains_crush) < sum(gains_none) / len(gains_none)


def test_burden_still_playable_12_ticks():
    from game.domain.divine_burden import apply_burden_tick

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w027b", "warrior", "เมษ")
    p["level"] = 2
    ensure_needs(p)
    p["needs"]["morale"] = 80
    p["equip_ids"] = {"main_hand": "relic_hell_ember_blade"}
    p["equip_rarities"] = {"main_hand": "divine"}
    for i in range(12):
        p["auto_ticks"] = i + 1
        apply_burden_tick(p, reg, context="field", rng=random.Random(200 + i))
    mor = int(get_needs(p)["morale"])
    assert mor >= 15  # felt but not zeroed
    assert 80 - mor >= 8  # still feels pressure
