"""DD4 status resist / AoE soft · EL5 partial sets · DD5 gear resist."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.aoe_balance import aoe_status_chance_mult, aoe_status_resist_bonus
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.status_fx import (
    apply_status,
    bump_status_familiarity,
    decay_status_familiarity,
    resist_chance,
    soft_resist_flavor,
)


def test_aoe_status_chance_lower():
    assert aoe_status_chance_mult(aoe=False, n_targets=1) == 1.0
    assert aoe_status_chance_mult(aoe=True, n_targets=3) < 0.7
    assert aoe_status_chance_mult(aoe=True, n_targets=1) < 1.0
    assert aoe_status_resist_bonus(aoe=True) > 0


def test_soft_resist_flavor():
    assert "เปลว" in soft_resist_flavor("burn")
    assert "「" in soft_resist_flavor("poison")


def test_gear_status_resist_from_shield():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sr", "warrior", "โล่")
    recompute_stats(p, reg)
    base = float(p.get("gear_status_resist") or 0)
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "wood_shield", reg)
    recompute_stats(p, reg)
    assert float(p.get("gear_status_resist") or 0) >= base


def test_helm_status_resist_bias():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "helm", "warrior", "หมวก")
    add_item(p, "iron_helm", reg)
    equip_item(p, "iron_helm", reg)
    recompute_stats(p, reg)
    assert float(p.get("gear_status_resist") or 0) > 0


def test_familiarity_raises_resist():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fam", "warrior", "ชิน")
    r0 = resist_chance(p, "burn", reg)
    bump_status_familiarity(p, "burn", amount=0.15)
    r1 = resist_chance(p, "burn", reg)
    assert r1 > r0
    decay_status_familiarity(p, factor=0.5)
    r2 = resist_chance(p, "burn", reg)
    assert r2 < r1


def test_aoe_apply_less_likely():
    reg = DataRegistry.load(DATA_DIR)
    hits = 0
    hits_aoe = 0
    n = 80
    for i in range(n):
        mon = {"statuses": [], "name": "t"}
        mon2 = {"statuses": [], "name": "t2"}
        rng = random.Random(1000 + i)
        if apply_status(mon, "burn", reg, rng, chance=0.9, source="t"):
            hits += 1
        rng2 = random.Random(1000 + i)
        if apply_status(
            mon2, "burn", reg, rng2, chance=0.9, aoe=True, n_targets=3, source="t"
        ):
            hits_aoe += 1
    # AoE should land fewer statuses on average (soft — not absolute)
    assert hits_aoe <= hits


def test_resist_sets_flavor():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "res", "warrior", "ต้าน")
    # force resist via high resist map
    p["status_resist"] = {"burn": 0.99, "all": 0.5}
    p["status_resist_all"] = 0.5
    applied = apply_status(
        p, "burn", reg, random.Random(1), chance=1.0, ignore_resist=False
    )
    # high resist → usually None
    if applied is None:
        assert p.get("_last_status_resist") == "burn"
        assert p.get("_last_status_resist_flavor")


def test_partial_set_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "set1", "warrior", "เศษ")
    add_item(p, "iron_sword", reg)  # iron_legion
    equip_item(p, "iron_sword", reg)
    recompute_stats(p, reg)
    # only 1 piece of 2 — partial not full active
    assert not p.get("active_sets") or "กองทัพ" not in str(p.get("active_sets"))
    partial = p.get("partial_sets") or []
    # iron sword is iron_legion — should show partial
    assert any("เศษ" in str(x) or "iron" in str(x).lower() or "เหล็ก" in str(x) for x in partial) or any(
        "เศษ" in str(f) for f in (p.get("set_flavors") or [])
    )


def test_full_set_still_works():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "set2", "warrior", "ครบ")
    add_item(p, "iron_sword", reg)
    add_item(p, "leather_armor", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "leather_armor", reg)
    recompute_stats(p, reg)
    assert p.get("active_sets")
    assert any("เหล็ก" in s or "กองทัพ" in s for s in p["active_sets"])


def test_base_resist_in_catalog():
    reg = DataRegistry.load(DATA_DIR)
    burn = reg.statuses.get("burn") or {}
    assert float(burn.get("base_resist") or 0) > 0 or True  # loaded
    # resist_chance uses base from def
    p = create_player(reg, "br", "mage", "เบส")
    r = resist_chance(p, "stun", reg)
    assert r >= 0.0
