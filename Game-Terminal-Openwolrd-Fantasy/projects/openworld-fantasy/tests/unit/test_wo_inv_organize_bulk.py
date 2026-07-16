"""WO-INV: organize + bulk sell + relic category + junk protect."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.bag_organize import organize_bag
from game.domain.bag_sell import (
    execute_bulk_sell,
    is_relic_item,
    preview_bulk_sell,
)
from game.domain.bag_stack import count_item_units, qty_at
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.inventory_sys import format_bag_hub, item_category
from game.ports.io import ScriptedIO
from game.runtime.inventory_auto import find_junk_drop_candidates
from game.services.bag_hub import run_bag_hub
from game.services.shop import _confirm_and_bulk_sell, run_shop


def _empty(p) -> None:
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    p["inventory_items"] = []
    p["card_bag"] = []


def test_relic_category_and_not_stackable():
    reg = DataRegistry.load(DATA_DIR)
    assert is_relic_item("relic_storm_fang", reg.items.get("relic_storm_fang") or {})
    assert item_category("relic_storm_fang", reg) == "relic"
    assert item_category("iron_sword", reg) == "equipment"
    p = create_player(reg, "rl1", "warrior", "เมษ")
    _empty(p)
    add_item(p, "relic_storm_fang", reg)
    add_item(p, "relic_storm_fang", reg)
    # relics are equipment-like → 2 slots (no stack)
    assert p["inventory_ids"].count("relic_storm_fang") == 2


def test_organize_sorts_and_stacks():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "org1", "warrior", "เมษ")
    # messy unstacked legacy lists
    p["inventory_ids"] = [
        "upgrade_mat",
        "potion_hp",
        "iron_sword",
        "potion_hp",
        "upgrade_mat",
        "city_bread",
    ]
    p["inventory"] = ["a", "b", "c", "d", "e", "f"]
    p["inventory_rarities"] = ["common"] * 6
    p["inventory_qty"] = [1] * 6
    p["card_bag"] = []
    notes = organize_bag(p, reg)
    assert notes
    assert count_item_units(p, "potion_hp") == 2
    assert count_item_units(p, "upgrade_mat") == 2
    assert len([x for x in p["inventory_ids"] if x == "potion_hp"]) == 1
    # equipment first-ish then consumables ordered by cat
    ids = list(p["inventory_ids"] or [])
    assert "iron_sword" in ids


def test_hub_organize_key():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "org2", "warrior", "เมษ")
    p["inventory_ids"] = ["potion_hp", "potion_hp", "upgrade_mat"]
    p["inventory"] = ["x", "y", "z"]
    p["inventory_rarities"] = ["common"] * 3
    p["inventory_qty"] = [1] * 3
    io = ScriptedIO(["o", "", "0"])  # organize, enter, exit
    run_bag_hub(p, reg, io)
    assert count_item_units(p, "potion_hp") == 2
    assert len([x for x in p["inventory_ids"] if x == "potion_hp"]) == 1


def test_hub_text_has_organize_and_relic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hubt", "warrior", "เมษ")
    text = "\n".join(format_bag_hub(p, reg))
    assert "จัดระเบียบ" in text or "O" in text
    assert "เรลิก" in text


def test_bulk_sell_common_materials():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "blk1", "warrior", "เมษ")
    _empty(p)
    p["money_world"] = 0
    for _ in range(5):
        add_item(p, "upgrade_mat", reg)
    assert count_item_units(p, "upgrade_mat") == 5
    prev = preview_bulk_sell(p, reg, category="material", common_only=True)
    assert int(prev.get("units") or 0) >= 5
    sold, gains, notes = execute_bulk_sell(
        p, reg, category="material", common_only=True
    )
    assert sold >= 5
    assert int(gains.get("money_world") or 0) > 0
    assert "upgrade_mat" not in (p.get("inventory_ids") or [])


def test_bulk_sell_protects_relic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "blk2", "warrior", "เมษ")
    _empty(p)
    add_item(p, "relic_storm_fang", reg)
    add_item(p, "upgrade_mat", reg)
    prev = preview_bulk_sell(p, reg, category=None, common_only=False)
    ids = [c["id"] for c in prev.get("candidates") or []]
    assert "relic_storm_fang" not in ids
    assert "upgrade_mat" in ids


def test_shop_bulk_confirm_flow():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "blk3", "warrior", "เมษ")
    _empty(p)
    p["money_world"] = 10
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    io = ScriptedIO(["y"])
    _confirm_and_bulk_sell(
        p, reg, io, shop={}, category="material", common_only=True, label="test"
    )
    assert "upgrade_mat" not in (p.get("inventory_ids") or [])
    assert int(p.get("money_world") or 0) > 10


def test_junk_never_scores_relic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "junk1", "warrior", "เมษ")
    _empty(p)
    add_item(p, "relic_storm_fang", reg)
    add_item(p, "upgrade_mat", reg)
    cands = find_junk_drop_candidates(p, reg)
    for _sc, _i, iid, _nm in cands:
        assert not str(iid).startswith("relic_")
