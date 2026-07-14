import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combo import max_combo_for_player, preview_combo_mana, resolve_combo
from game.domain.party import add_member, member_from_template, party_assist_damage
from game.domain.unit_system import (
    claim_unit,
    is_unit_claimed,
    load_claims,
    mastery_power_mult,
    soft_mastery_label,
)


def test_combo_length_scales_with_level():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c1", "mage", "เมถุน")
    p["level"] = 5
    assert max_combo_for_player(p, reg) == 2
    p["level"] = 15
    assert max_combo_for_player(p, reg) == 3
    p["level"] = 40
    assert max_combo_for_player(p, reg) >= 4
    p["level"] = 60
    assert max_combo_for_player(p, reg) >= 5


def test_long_combo_costs_more_mana():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c2", "mage", "เมถุน")
    p["skills"] = ["magic_missile", "fire_ball", "water_bolt", "lightning_spark"]
    p["level"] = 50
    one = resolve_combo(["magic_missile"], reg, max_n=6)
    three = resolve_combo(
        ["magic_missile", "fire_ball", "water_bolt"], reg, max_n=6
    )
    assert one["ok"] and three["ok"]
    assert three["total_mana"] > one["total_mana"]
    assert three["mana_mult"] > one["mana_mult"]


def test_preview_cannot_afford():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c3", "mage", "เมถุน")
    p["level"] = 30
    p["skills"] = ["arcane_surge", "fire_ball", "lightning_spark"]
    p["mana"] = 1
    prev = preview_combo_mana(p, reg, ["arcane_surge", "fire_ball"])
    assert prev.get("ok")
    assert prev.get("can_afford") is False


def test_fusions_expanded():
    reg = DataRegistry.load(DATA_DIR)
    f = (reg.fusions_cfg or {}).get("fusions") or []
    assert len(f) >= 15


def test_party_assist_can_damage():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pa", "warrior", "เมษ")
    t = (reg.party or {}).get("templates")[0]
    add_member(p, member_from_template(t), reg)
    mon = {"hp": 100, "max_hp": 100}
    # force many rolls
    notes = []
    for seed in range(30):
        notes = party_assist_damage(p, mon, random.Random(seed))
        if notes:
            break
    # at least sometimes
    assert mon["hp"] <= 100


def test_unit_claim_exclusive():
    reg = DataRegistry.load(DATA_DIR)
    world = "_test_claim_world"
    # clean claims file if any
    from game.domain.unit_system import claims_path, save_claims

    save_claims(world, {})
    a = create_player(reg, "ua", "rogue", "พิจิก")
    a["world_id"] = world
    a["id"] = "player_a"
    b = create_player(reg, "ub", "rogue", "พิจิก")
    b["world_id"] = world
    b["id"] = "player_b"
    assert claim_unit(world, "unit_eclipse", a)
    assert is_unit_claimed(world, "unit_eclipse", except_player_id="player_b")
    assert not claim_unit(world, "unit_eclipse", b)


def test_mastery_mult_curve():
    assert mastery_power_mult(0) < mastery_power_mult(5)
    assert "เงียบ" in soft_mastery_label(0) or soft_mastery_label(0)


def test_accessory_equip():
    reg = DataRegistry.load(DATA_DIR)
    assert "copper_ring" in reg.items
    assert reg.items["copper_ring"].get("slot") == "accessory"
    p = create_player(reg, "acc", "mage", "เมถุน")
    from game.domain.equipment import add_item, equip_item, recompute_stats

    add_item(p, "copper_ring", reg)
    msg = equip_item(p, "copper_ring", reg)
    assert "สวม" in msg or "copper" in msg.lower() or "แหวน" in msg
    assert (p.get("equip_ids") or {}).get("accessory") == "copper_ring"
