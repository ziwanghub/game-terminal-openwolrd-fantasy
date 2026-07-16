"""WO-004 P1.4: Auto Inventory Management."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import ensure_needs, is_food_item
from game.runtime.inventory_auto import (
    auto_free_bag_space,
    auto_manage_inventory,
    bag_free_slots,
    bag_used,
    ensure_inv_auto_prefs,
    find_junk_drop_candidates,
    format_inv_auto_hud,
    inventory_stock_snapshot,
    soft_stock_warnings,
)


def test_ensure_inv_prefs_merge():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv1", "warrior", "ตุลย์")
    prefs = ensure_inv_auto_prefs(p)
    assert prefs.get("inv_manage") is True
    assert prefs.get("inv_drop_junk") is True
    assert int(prefs.get("inv_min_food") or 0) >= 0
    assert "hp_pct" in prefs  # still has combat auto prefs


def test_stock_snapshot_and_hud():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv2", "warrior", "เมษ")
    ensure_needs(p)
    snap = inventory_stock_snapshot(p, reg)
    assert "food" in snap and "hp_pots" in snap
    assert snap["bag_cap"] >= snap["slots_used"]
    hud = format_inv_auto_hud(p, reg)
    assert "กระเป๋า" in hud


def test_soft_stock_warnings_low_food():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv3", "warrior", "ตุลย์")
    prefs = ensure_inv_auto_prefs(p)
    prefs["inv_min_food"] = 5
    p["auto_prefs"] = prefs
    # strip food
    ids = []
    for iid in list(p.get("inventory_ids") or []):
        it = (reg.items or {}).get(str(iid)) or {}
        if not is_food_item(it):
            ids.append(str(iid))
    p["inventory_ids"] = ids
    warns = soft_stock_warnings(p, reg, prefs)
    assert any("เสบียง" in w or "อาหาร" in w for w in warns)


def test_auto_free_bag_space_drops_junk():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv4", "warrior", "ตุลย์")
    prefs = ensure_inv_auto_prefs(p)
    # force drop path for legacy P1.4 behavior
    prefs["inv_sell_junk"] = False
    prefs["inv_drop_junk"] = True
    p["auto_prefs"] = prefs
    p["bag_cap"] = 5
    # fill with materials if any
    mats = []
    for iid, it in (reg.items or {}).items():
        kind = str(it.get("kind") or "")
        if kind == "material" or "mat" in str(iid).lower():
            mats.append(str(iid))
        if len(mats) >= 6:
            break
    if len(mats) < 3:
        mats = ["upgrade_mat"] * 5
    p["inventory_ids"] = list(mats[:5])
    p["inventory"] = list(mats[:5])
    p["inventory_rarities"] = ["common"] * 5
    # keep one food protected
    for iid, it in (reg.items or {}).items():
        if is_food_item(it):
            p["inventory_ids"][0] = str(iid)
            break
    before = bag_used(p)
    assert before >= 4
    notes = auto_free_bag_space(p, reg, need_free=2, max_drops=3, sell=False)
    after_free = bag_free_slots(p)
    assert after_free >= 1 or notes  # dropped or reported cannot
    if notes and ("ทิ้ง" in "".join(notes) or "ขาย" in "".join(notes)):
        assert bag_used(p) < before


def test_find_junk_does_not_score_food():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv5", "warrior", "ตุลย์")
    food_ids = []
    for iid, it in (reg.items or {}).items():
        if is_food_item(it):
            food_ids.append(str(iid))
        if len(food_ids) >= 2:
            break
    p["inventory_ids"] = food_ids or list(p.get("inventory_ids") or [])
    p["inventory_rarities"] = ["common"] * len(p["inventory_ids"])
    cands = find_junk_drop_candidates(p, reg)
    # food should not appear as junk
    for _sc, _i, iid, _nm in cands:
        it = (reg.items or {}).get(iid) or {}
        assert not is_food_item(it)


def test_auto_manage_inventory_runs():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv6", "warrior", "ตุลย์")
    ensure_needs(p)
    p["needs"] = {"hunger": 80, "fatigue": 20, "morale": 50}
    notes = auto_manage_inventory(p, reg, context="test")
    # may eat or warn; must not crash
    assert isinstance(notes, list)
