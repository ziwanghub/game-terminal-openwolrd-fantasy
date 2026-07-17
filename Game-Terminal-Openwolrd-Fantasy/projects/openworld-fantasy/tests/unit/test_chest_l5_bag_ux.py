"""L5: chest stash UX in bag — rank sort, summary, open-all."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.chest_loot import (
    format_chest_stash_summary,
    rank_order_index,
    summarize_chest_ranks,
)
from game.domain.equipment import add_item
from game.domain.inventory_sys import format_category_list, list_bag_entries
from game.ports.io import ScriptedIO
from game.services.bag_hub import run_bag_hub


def test_rank_order():
    assert rank_order_index("sss") > rank_order_index("common")
    assert rank_order_index("s") > rank_order_index("rare")
    assert rank_order_index("unit") >= rank_order_index("sss")


def test_list_chests_sorted_high_first():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "l5a", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    add_item(p, "sealed_chest_common", reg)
    add_item(p, "sealed_chest_s", reg)
    add_item(p, "sealed_chest_rare", reg)
    entries = list_bag_entries(p, reg, "chest")
    ranks = [str(e.get("chest_rank") or "") for e in entries]
    assert ranks[0] == "s"
    assert "common" in ranks
    assert ranks.index("s") < ranks.index("common")


def test_stash_summary_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "l5b", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    add_item(p, "sealed_chest_common", reg)
    add_item(p, "sealed_chest_common", reg)
    add_item(p, "sealed_chest_s", reg)
    rows = summarize_chest_ranks(p, reg)
    by = dict(rows)
    assert by.get("common") == 2
    assert by.get("s") == 1
    lines = format_chest_stash_summary(p, reg)
    text = "\n".join(lines)
    assert "3" in text or "คลัง" in text
    assert "A" in text or "ทั้งหมด" in text


def test_category_list_has_l5_hints():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "l5c", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory"] = []
    p["inventory_rarities"] = []
    add_item(p, "sealed_chest_uncommon", reg)
    lines = format_category_list(p, reg, "chest")
    text = "\n".join(lines)
    assert "หีบ" in text
    assert "A" in text or "ทั้งหมด" in text
    # soft rank present on entry or header
    assert "สูง" in text or "▢" in text or "uncommon" in text.lower()


def test_open_all_from_bag_hub():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "l5d", "warrior", "เมษ")
    p["inventory_ids"] = ["sealed_chest_common", "sealed_chest_common"]
    p["inventory"] = ["หีบ1", "หีบ2"]
    p["inventory_rarities"] = ["common", "common"]
    # 4 = chest category, A = open all, y = confirm, Enter = summary, 0 hub, 0 exit
    io = ScriptedIO(["4", "A", "y", "", "0", "0"])
    run_bag_hub(p, reg, io)
    assert "sealed_chest_common" not in (p.get("inventory_ids") or [])
    out = io.joined()
    assert "เปิด" in out
