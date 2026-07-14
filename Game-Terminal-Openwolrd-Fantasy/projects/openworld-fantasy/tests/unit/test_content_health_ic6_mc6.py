"""IC6/MC6 content health — pools, drops, economy, soft balance guards."""
from __future__ import annotations

from pathlib import Path

import yaml

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats, upgrade_cost
from game.domain.unit_system import MAX_UNIT_CHANCE


def test_no_duplicate_monsters_in_area_pools():
    reg = DataRegistry.load(DATA_DIR)
    for aid, a in reg.areas.items():
        ids = [
            (x.get("id") if isinstance(x, dict) else x)
            for x in (a.get("monster_pools") or [])
        ]
        assert len(ids) == len(set(ids)), f"dup pool {aid}"
        assert len(ids) >= 8, f"{aid} thin pool {len(ids)}"


def test_elite_weights_capped():
    reg = DataRegistry.load(DATA_DIR)
    for aid, a in reg.areas.items():
        for x in a.get("monster_pools") or []:
            if not isinstance(x, dict):
                continue
            mid = x.get("id")
            mon = reg.monsters.get(mid) or {}
            if mon.get("elite"):
                assert int(x.get("weight") or 99) <= 4, f"{aid} {mid}"


def test_all_non_boss_mons_in_some_pool():
    reg = DataRegistry.load(DATA_DIR)
    in_pool = set()
    for a in reg.areas.values():
        for x in a.get("monster_pools") or []:
            in_pool.add(x.get("id") if isinstance(x, dict) else x)
    for mid, m in reg.monsters.items():
        if m.get("boss"):
            continue
        assert mid in in_pool, f"orphan mon {mid}"


def test_all_drops_and_cards_resolve():
    reg = DataRegistry.load(DATA_DIR)
    for mid, m in reg.monsters.items():
        for d in m.get("drops") or []:
            assert d.get("item") in reg.items, f"{mid}->{d.get('item')}"
        cid = m.get("card_id")
        if cid:
            assert cid in reg.cards, f"{mid} card {cid}"


def test_chest_buckets_and_ranks_health():
    reg = DataRegistry.load(DATA_DIR)
    pools = yaml.safe_load(
        Path(DATA_DIR).joinpath("chests/pools.yaml").read_text(encoding="utf-8")
    )
    for name, items in (pools.get("buckets") or {}).items():
        for iid in items:
            assert iid in reg.items, f"chest {name} {iid}"
    ranks = yaml.safe_load(
        Path(DATA_DIR).joinpath("chests/ranks.yaml").read_text(encoding="utf-8")
    )
    common = next(r for r in ranks["ranks"] if r["id"] == "common")
    assert int(common["bucket_weights"]["material"]) >= 40
    assert int(common["bucket_weights"].get("soft_empty") or 0) == 0


def test_shops_no_cards_all_items_exist():
    reg = DataRegistry.load(DATA_DIR)
    shops = yaml.safe_load(
        Path(DATA_DIR).joinpath("shops/shops.yaml").read_text(encoding="utf-8")
    )
    for s in shops:
        for row in s.get("stock") or []:
            iid = row if isinstance(row, str) else (row or {}).get("id")
            if not iid:
                continue
            assert not str(iid).startswith("card_")
            assert iid in reg.items


def test_broken_unit_skills_not_absurd():
    reg = DataRegistry.load(DATA_DIR)
    for sid in (
        "unit_void_crown",
        "unit_world_pierce",
        "unit_eternal_sun",
        "unit_blood_moon",
        "unit_iron_legion",
    ):
        p = int((reg.skills.get(sid) or {}).get("power") or 0)
        assert 1 <= p <= 90, sid
    assert MAX_UNIT_CHANCE <= 0.05


def test_late_upgrade_still_expensive():
    assert upgrade_cost("main_hand", 9)["money"] > upgrade_cost("main_hand", 3)["money"]


def test_smoke_equip_and_set():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h1", "warrior", "เมษ")
    add_item(p, "titan_plate", reg, rarity="sacred")
    add_item(p, "titan_greaves", reg, rarity="rare")
    equip_item(p, "titan_plate", reg)
    equip_item(p, "titan_greaves", reg)
    recompute_stats(p, reg)
    assert int(p.get("equip_def") or 0) > 0
    assert p.get("active_sets") or p.get("partial_sets")


def test_content_scale_after_ic6_mc6():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.items) >= 145
    assert len(reg.monsters) >= 80
    assert len(reg.cards) >= 65
    assert len(reg.gear_sets) >= 10
    recipes = yaml.safe_load(
        Path(DATA_DIR).joinpath("craft/recipes.yaml").read_text(encoding="utf-8")
    )
    assert len(recipes) >= 50
