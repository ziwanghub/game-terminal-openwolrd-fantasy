"""P1–P3 party recruit, known roster, hire tier consent."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.party import (
    add_member,
    attempt_join_template,
    can_recruit_template,
    consent_chance,
    ensure_party,
    hire_cost_table,
    list_known_companions,
    member_from_template,
    reinvite_known_companion,
    remove_member,
    roll_companion_sight,
    soft_party_discovery_lines,
    template_by_id,
    template_tier,
)


def test_kinds_and_tiers():
    reg = DataRegistry.load(DATA_DIR)
    leaf = template_by_id(reg, "spirit_leaf")
    god = template_by_id(reg, "heaven_god_shard")
    assert leaf and god
    assert template_tier(leaf) <= 1
    assert template_tier(god) == 3
    costs_g = hire_cost_table(god)
    costs_l = hire_cost_table(leaf)
    assert costs_g["world"] > costs_l["world"] or costs_g["heaven"] > costs_l["heaven"]
    assert consent_chance(god, 0.9) < consent_chance(leaf, 0.9)


def test_join_marks_known_and_reinvite():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pk", "warrior", "เมษ")
    p["level"] = 10
    p["money_world"] = 500
    ensure_party(p)
    tpl = template_by_id(reg, "spirit_leaf")
    assert tpl
    # force high affinity join
    ok, notes = attempt_join_template(
        p, reg, tpl, random.Random(1), affinity=0.9
    )
    # may fail by rng once — retry
    for seed in range(30):
        p2 = create_player(reg, f"pk{seed}", "warrior", "เมษ")
        p2["level"] = 10
        p2["money_world"] = 500
        ok, notes = attempt_join_template(
            p2, reg, tpl, random.Random(seed), affinity=0.95
        )
        if ok:
            p = p2
            break
    assert ok, notes
    assert "spirit_leaf" in (p.get("party_known") or [])
    assert any(m.get("id") == "spirit_leaf" for m in (p.get("party") or []))
    # dismiss
    remove_member(p, 0)
    assert not any(m.get("id") == "spirit_leaf" for m in (p.get("party") or []))
    assert "spirit_leaf" in (p.get("party_known") or [])
    known = list_known_companions(p, reg)
    assert any(k.get("id") == "spirit_leaf" for k in known)
    # reinvite
    rejoined = False
    for seed in range(40):
        ok2, notes2 = reinvite_known_companion(p, reg, "spirit_leaf", random.Random(seed + 100))
        if ok2:
            rejoined = True
            break
        # refund money if spent on fails
        p["money_world"] = 500
    assert rejoined
    assert any(m.get("id") == "spirit_leaf" for m in (p.get("party") or []))


def test_hard_tier_needs_money():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "poor", "mage", "เมถุน")
    p["level"] = 30
    p["money_world"] = 0
    p["money_heaven"] = 0
    p["stats"] = {"boss_kills": 5, "deaths": 2}
    p["library_entries_read"] = ["a", "b", "c"]
    tpl = template_by_id(reg, "heaven_god_shard")
    ok, notes = attempt_join_template(p, reg, tpl, random.Random(1), affinity=0.99)
    assert not ok
    assert any("สวรรค์" in n or "ทรัพยากร" in n or "โลก" in n for n in notes)


def test_companion_sight_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "si", "rogue", "พิจิก")
    p["level"] = 8
    p["money_world"] = 200
    found = False
    for seed in range(80):
        s = roll_companion_sight(p, reg, random.Random(seed))
        if s:
            assert s.get("kind") == "companion"
            assert s.get("companion_template") or s.get("companion_template_id")
            found = True
            break
    assert found


def test_discovery_lines():
    lines = soft_party_discovery_lines()
    assert any("ร้าน" in x or "สำรวจ" in x for x in lines)
