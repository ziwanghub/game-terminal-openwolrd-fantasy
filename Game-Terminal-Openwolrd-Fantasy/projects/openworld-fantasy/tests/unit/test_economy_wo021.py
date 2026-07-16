"""WO-021: Economy Balance & Needs Connection."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import grant_combat_money, scaled_price
from game.domain.character import create_player
from game.domain.combat import resolve_victory
from game.domain.needs import is_food_item
from game.domain.quests import complete_quest
from game.runtime.auto_farm import auto_fight
from game.runtime.inventory_auto import (
    auto_free_bag_space,
    bag_used,
    ensure_inv_auto_prefs,
    try_auto_buy_supplies,
)


def _mon(lv: int = 3) -> dict:
    return {
        "id": "wolf",
        "name": "หมาป่า",
        "level": lv,
        "xp_mult": 1.0,
        "hp": 20,
        "max_hp": 20,
        "atk": 5,
    }


def test_grant_combat_money_always_world():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e1", "warrior", "เมษ")
    p["money_world"] = 0
    p["money_heaven"] = 0
    p["money_hell"] = 0
    rng = random.Random(0)
    lines = grant_combat_money(p, _mon(5), rng, auto=False)
    assert p["money_world"] >= 1
    assert any("เงินโลก" in x for x in lines)
    # always at least world; special may or may not
    assert p["money_world"] >= 10  # manual base includes mon_lv


def test_auto_fight_money_near_manual_range():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e2", "warrior", "เมษ")
    p["money_world"] = 0
    mon = dict(reg.monsters.get("wolf") or _mon(2))
    mon["level"] = 2
    mon["hp"] = 1
    mon["max_hp"] = 1
    mon["atk"] = 0
    # many wins — auto should not be 3–12 only
    samples = []
    for seed in range(12):
        p2 = create_player(reg, f"e2s{seed}", "warrior", "เมษ")
        p2["money_world"] = 0
        p2["level"] = 5
        p2["hp"] = int(p2.get("max_hp") or 80)
        m = dict(mon)
        m["hp"] = 1
        m["max_hp"] = 1
        m["atk"] = 0
        before = p2["money_world"]
        auto_fight(p2, m, reg, random.Random(seed), "dark_forest")
        gain = int(p2["money_world"]) - before
        if gain > 0:
            samples.append(gain)
    assert samples, "expected some auto wins with gold"
    assert max(samples) >= 10
    assert min(samples) >= 1
    # average closer to manual era than old 3–12
    avg = sum(samples) / len(samples)
    assert avg >= 8.0


def test_resolve_victory_always_world_gold():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e3", "warrior", "เมษ")
    p["money_world"] = 0
    mon = dict(reg.monsters.get("wolf") or _mon(1))
    mon["level"] = 1
    lines = resolve_victory(p, mon, reg, "dark_forest", random.Random(7))
    assert p["money_world"] >= 1
    assert any("เงินโลก" in x for x in lines)


def test_early_food_potion_prices_softer():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e4", "warrior", "เมษ")
    p["location"] = "dark_forest"
    p["level"] = 1
    bread = int((reg.items.get("city_bread") or {}).get("price_world") or 99)
    pot = int((reg.items.get("potion_hp_small") or {}).get("price_world") or 99)
    ration = int((reg.items.get("hunter_ration") or {}).get("price_world") or 99)
    assert bread <= 10
    assert pot <= 20
    assert ration <= 25
    # shop scale still works
    assert scaled_price(bread, reg, p) >= 1


def test_quest_grants_special_currency():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e5", "warrior", "เมษ")
    p["money_heaven"] = 0
    p["quests"] = {"first_blood": {"progress": 3, "completed": False}}
    q = reg.quests.get("first_blood") or {}
    assert int(q.get("reward_money_heaven") or 0) >= 1
    lines = complete_quest(p, reg, "first_blood")
    assert int(p.get("money_heaven") or 0) >= 1
    assert any("สวรรค์" in str(x) for x in lines)


def test_dungeon_forest_has_heaven_reward():
    reg = DataRegistry.load(DATA_DIR)
    found = False
    for row in (reg.dungeons_cfg or {}).get("dungeons") or []:
        if row.get("id") == "dung_forest_root":
            assert row.get("rewards", {}).get("money_heaven")
            found = True
            break
    assert found


def test_auto_sell_junk_gives_world_gold():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e6", "warrior", "เมษ")
    prefs = ensure_inv_auto_prefs(p)
    prefs["inv_sell_junk"] = True
    prefs["inv_drop_junk"] = False
    p["auto_prefs"] = prefs
    p["bag_cap"] = 5
    mats = ["upgrade_mat", "herb_bundle", "iron_arrowhead", "stone_chip", "rat_tail"]
    # filter to existing
    mats = [m for m in mats if m in (reg.items or {})] or ["upgrade_mat"] * 5
    p["inventory_ids"] = list(mats[:5])
    p["inventory"] = list(mats[:5])
    p["inventory_rarities"] = ["common"] * 5
    before_m = int(p.get("money_world") or 0)
    before_bag = bag_used(p)
    notes = auto_free_bag_space(p, reg, need_free=2, max_drops=3)
    assert bag_used(p) < before_bag or notes
    if any("ขาย" in n for n in notes):
        assert int(p.get("money_world") or 0) > before_m


def test_auto_buy_supplies_when_enabled():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e7", "warrior", "เมษ")
    prefs = ensure_inv_auto_prefs(p)
    prefs["auto_buy_supplies"] = True
    prefs["auto_buy_reserve"] = 20
    prefs["auto_buy_max"] = 2
    prefs["inv_min_food"] = 5
    p["auto_prefs"] = prefs
    p["money_world"] = 200
    p["location"] = "dark_forest"
    # strip food
    ids = []
    for iid in list(p.get("inventory_ids") or []):
        it = (reg.items or {}).get(str(iid)) or {}
        if not is_food_item(it):
            ids.append(str(iid))
    p["inventory_ids"] = ids
    p["inventory"] = list(ids)
    p["inventory_rarities"] = ["common"] * len(ids)
    before = int(p["money_world"])
    notes = try_auto_buy_supplies(p, reg)
    assert notes, "should buy food when low and gold enough"
    assert any("ออโต้ซื้อ" in n for n in notes)
    assert int(p["money_world"]) < before
    # stock improved
    from game.runtime.dungeon_auto import count_food

    assert count_food(p, reg) >= 1


def test_auto_buy_on_by_default_wo022():
    """WO-022: soft default ON; still respect explicit off."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "e8", "warrior", "เมษ")
    prefs = ensure_inv_auto_prefs(p)
    assert prefs.get("auto_buy_supplies") is True
    prefs["auto_buy_supplies"] = False
    p["auto_prefs"] = prefs
    p["money_world"] = 500
    prefs["inv_min_food"] = 99
    notes = try_auto_buy_supplies(p, reg)
    assert notes == []


def test_field_auto_money_factor_near_manual():
    """WO-022: field factor 0.90 keeps auto closer to manual."""
    from game.domain.balance import grant_combat_money

    man, auto = [], []
    mon = {"id": "w", "name": "w", "level": 4}
    for s in range(15):
        p1 = {"money_world": 0, "money_heaven": 0, "money_hell": 0, "world_modifiers": {}}
        p2 = dict(p1)
        grant_combat_money(p1, mon, random.Random(s), auto=False)
        grant_combat_money(p2, mon, random.Random(s), auto=True, money_factor=0.90)
        man.append(p1["money_world"])
        auto.append(p2["money_world"])
    avg_m = sum(man) / len(man)
    avg_a = sum(auto) / len(auto)
    # auto should land roughly 75–100% of manual avg (not the old ~half era)
    assert avg_a >= avg_m * 0.55
    assert avg_a <= avg_m * 1.05


def test_thrift_mode_limits_auto_buy():
    from game.runtime.inventory_auto import _auto_buy_budget

    r, mx, mp = _auto_buy_budget({"item_mode": "thrift", "auto_buy_reserve": 40, "auto_buy_max": 3})
    assert r >= 80 and mx <= 1 and mp is False
    r2, mx2, mp2 = _auto_buy_budget({"item_mode": "safe", "auto_buy_reserve": 50, "auto_buy_max": 2})
    assert r2 <= 30 and mx2 >= 3
