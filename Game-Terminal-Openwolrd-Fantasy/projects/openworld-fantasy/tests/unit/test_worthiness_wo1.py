"""WO-Worthiness-1: loot ceiling · soft wall · trial grants · auto block."""
from __future__ import annotations

import random

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, recompute_stats
from game.domain.inventory_sys import build_combat_loot_table
from game.domain.rarity import roll_rarity, tier_rank
from game.domain.worthiness import (
    FARM_MAX_RARITY_RANK,
    auto_may_fight_boss,
    clamp_farm_rarity,
    ensure_worthiness,
    has_trial,
    is_first_trial_pending,
    item_blocked_on_farm,
    on_boss_defeated_worthiness,
    soft_wall_for_area,
    travel_worthiness_lines,
    trial_readiness_lines,
)
from game.runtime.auto_farm import auto_fight


def test_version_worthiness():
    assert "2.21" in APP_VERSION
    assert "worthiness" in PHASE or "wo-worthiness" in PHASE


def test_farm_rarity_ceiling():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(42)
    for _ in range(80):
        rid = roll_rarity(
            reg, rng, pool="drop", min_rank=1, max_rank=99, farm_ceiling=True
        )
        assert tier_rank(reg, rid) <= FARM_MAX_RARITY_RANK
    assert clamp_farm_rarity(reg, "mythic") == "legendary"
    assert clamp_farm_rarity(reg, "divine") == "legendary"
    assert clamp_farm_rarity(reg, "legendary") == "legendary"
    assert clamp_farm_rarity(reg, "divine", allow_god=True) == "divine"


def test_trial_exclusive_blocked_on_farm():
    reg = DataRegistry.load(DATA_DIR)
    assert item_blocked_on_farm("relic_god_eye", reg) is True
    assert item_blocked_on_farm("relic_divine_laurel", reg) is True
    assert item_blocked_on_farm("iron_sword", reg) is False
    # divine catalog item blocked
    assert item_blocked_on_farm("relic_hell_ember_blade", reg) is True


def test_soft_wall_whisper_then_open():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w1", "warrior", "เมษ")
    ensure_worthiness(p)
    assert soft_wall_for_area(p, "dark_forest") == "open"
    assert soft_wall_for_area(p, "mist_marsh") == "whisper"
    assert soft_wall_for_area(p, "mountain_rock") == "whisper"
    lines = travel_worthiness_lines(p, reg, "mist_marsh")
    assert lines
    assert any("ไม่พร้อม" in x or "สมควร" in x for x in lines)
    # after T1
    mon = {"id": "boss_forest_king", "boss": True, "name": "King"}
    notes = on_boss_defeated_worthiness(p, mon, reg, via_auto=False)
    assert has_trial(p, "t1_forest")
    assert any("พวงหรีด" in n or "พิสูจน์" in n or "ได้" in n for n in notes)
    assert soft_wall_for_area(p, "mist_marsh") == "open"
    assert soft_wall_for_area(p, "mountain_rock") == "whisper"


def test_trial_t2_god_eye_once_manual():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w2", "mage", "เมถุน")
    recompute_stats(p, reg)
    ensure_worthiness(p)
    # clear T1 first (path soft)
    on_boss_defeated_worthiness(
        p, {"id": "boss_forest_king", "boss": True}, reg, via_auto=False
    )
    assert "relic_divine_laurel" in (p.get("inventory_ids") or [])
    notes = on_boss_defeated_worthiness(
        p, {"id": "boss_mist_hydra", "boss": True}, reg, via_auto=False
    )
    assert has_trial(p, "t2_marsh")
    assert p["worthiness"].get("god_eye_owned") is True
    assert "relic_god_eye" in (p.get("inventory_ids") or [])
    assert any("ดวงตา" in n or "พิสูจน์" in n for n in notes)
    # no double grant
    n2 = on_boss_defeated_worthiness(
        p, {"id": "boss_mist_hydra", "boss": True}, reg, via_auto=False
    )
    assert any("ไม่ซ้ำ" in x or "รู้จัก" in x for x in n2)
    assert (p.get("inventory_ids") or []).count("relic_god_eye") == 1


def test_auto_blocks_first_trial():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w3", "rogue", "พิจิก")
    ensure_worthiness(p)
    mon = {
        "id": "boss_forest_king",
        "name": "King",
        "boss": True,
        "hp": 5,
        "max_hp": 5,
        "atk": 1,
        "level": 8,
        "elements": ["nature"],
        "attack_profiles": [{"id": "a", "power": 1, "weight": 1}],
        "statuses": [],
    }
    ok, why = auto_may_fight_boss(p, mon)
    assert ok is False
    assert "มือ" in why or "พิสูจน์" in why
    assert is_first_trial_pending(p, "boss_forest_king")
    lines = auto_fight(p, mon, reg, random.Random(1), "dark_forest")
    text = "\n".join(lines)
    assert "มือ" in text or "พิสูจน์" in text
    assert not has_trial(p, "t1_forest")
    assert "relic_divine_laurel" not in (p.get("inventory_ids") or [])


def test_auto_allows_rematch_after_trial_no_double_reward():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w4", "warrior", "เมษ")
    recompute_stats(p, reg)
    on_boss_defeated_worthiness(
        p, {"id": "boss_forest_king", "boss": True}, reg, via_auto=False
    )
    mon = {
        "id": "boss_forest_king",
        "name": "King",
        "boss": True,
        "hp": 3,
        "max_hp": 3,
        "atk": 1,
        "level": 8,
        "elements": ["nature"],
        "attack_profiles": [{"id": "a", "power": 1, "weight": 1}],
        "statuses": [],
        "xp_mult": 1.0,
    }
    ok, _ = auto_may_fight_boss(p, mon)
    assert ok is True
    before = (p.get("inventory_ids") or []).count("relic_divine_laurel")
    # via_auto grant path should not add another
    notes = on_boss_defeated_worthiness(p, mon, reg, via_auto=True)
    after = (p.get("inventory_ids") or []).count("relic_divine_laurel")
    assert after == before
    assert notes == [] or not any("ได้" in n and "พวงหรีด" in n for n in notes)


def test_combat_loot_no_god_eye():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w5", "warrior", "เมษ")
    mon = dict(reg.monsters.get("boss_forest_king") or {})
    mon["boss"] = True
    mon["id"] = "boss_forest_king"
    mon["hp"] = 1
    mon["max_hp"] = 1
    rng = random.Random(0)
    for seed in range(30):
        drops = build_combat_loot_table(p, mon, reg, random.Random(seed))
        ids = [str(d.get("id")) for d in drops]
        assert "relic_god_eye" not in ids
        assert "relic_divine_laurel" not in ids
        for d in drops:
            rid = str(d.get("rarity") or "common")
            assert tier_rank(reg, rid) <= FARM_MAX_RARITY_RANK


def test_trial_readiness_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w6", "priest", "มีน")
    p["level"] = 2
    lines = trial_readiness_lines(p, reg, "boss_forest_king")
    assert lines
    assert any("พิสูจน์" in x or "ไม่พร้อม" in x or "มือ" in x for x in lines)


def test_god_eye_item_exists():
    reg = DataRegistry.load(DATA_DIR)
    it = reg.items.get("relic_god_eye") or {}
    assert it.get("name")
    assert "ดวงตา" in str(it.get("name"))
    assert str(it.get("rarity")) == "divine"
