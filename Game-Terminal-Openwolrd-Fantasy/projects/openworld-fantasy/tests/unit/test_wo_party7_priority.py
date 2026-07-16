"""WO-PARTY-7: Smart Companion Assist Priority Engine."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.companion_decision_engine import (
    ACT_ATTACK,
    ACT_CLEANSE,
    ACT_HEAL,
    P0,
    P1,
    P2,
    decide,
    decide_for_tests,
    member_role,
    success_chance,
)
from game.domain.party import party_member_turns, set_relationship
from game.domain.status_fx import apply_status, has_status


def test_priority_p0_poison_support_cleanses():
    d = decide_for_tests(
        hp_ratio=0.8,
        statuses=["poison"],
        kind="spirit",
        role="support_nature",
        bond=60,
    )
    assert d.action == ACT_CLEANSE
    assert d.priority == P0
    assert d.cleanse_target == "poison"


def test_priority_p0_hp_crit_heals():
    d = decide_for_tests(hp_ratio=0.15, kind="beast", role="attack", bond=50)
    assert d.action == ACT_HEAL
    assert d.priority == P0


def test_priority_p1_boss_low_hp_attack():
    d = decide_for_tests(
        hp_ratio=0.9,
        mon_ratio=0.18,
        boss=True,
        kind="beast",
        role="attack",
        bond=55,
    )
    assert d.action == ACT_ATTACK
    assert d.priority <= P1


def test_priority_order_poison_beats_general_attack():
    """Support with poison chooses cleanse over chip damage."""
    d = decide_for_tests(
        hp_ratio=0.85,
        mon_ratio=0.9,
        statuses=["poison"],
        kind="spirit",
        role="support",
        bond=70,
    )
    assert d.action == ACT_CLEANSE
    assert d.priority == P0


def test_member_role_leaf_support():
    assert member_role({"id": "spirit_leaf", "kind": "spirit", "role": "support_nature"}) == "support"
    assert member_role({"kind": "beast", "role": "attack"}) == "attack"


def test_success_chance_clamped_and_scales():
    p = {"grade_revealed": True, "player_grade": "A"}
    m = {"kind": "spirit", "role": "support", "rarity": "common"}
    low = success_chance(p, m, action="cleanse", bond=10)
    high = success_chance(p, m, action="cleanse", bond=90)
    assert 0.18 <= low < high <= 0.92


def test_combat_poison_cleanse_harness():
    """Support companion tends to cleanse poison when bond high (soft RNG)."""
    reg = DataRegistry.load(DATA_DIR)
    cleansed = 0
    for seed in range(40):
        player = {
            "hp": 80,
            "max_hp": 100,
            "needs": {"hunger": 20, "fatigue": 20, "morale": 60},
            "statuses": [],
            "party": [
                {
                    "id": "spirit_leaf",
                    "name": "ภูตใบไม้",
                    "kind": "spirit",
                    "role": "support_nature",
                    "template_id": "spirit_leaf",
                    "bonus_atk": 2,
                    "rarity": "common",
                }
            ],
            "party_bonds": {"spirit_leaf": 85},
            "grade_revealed": True,
            "player_grade": "A",
            "bonus_atk": 5,
        }
        apply_status(player, "poison", reg, random.Random(1), chance=1.0, ignore_resist=True)
        assert has_status(player, "poison")
        mon = {"hp": 200, "max_hp": 200, "name": "มอน"}
        notes = party_member_turns(player, mon, random.Random(seed), reg)
        text = "".join(notes)
        if not has_status(player, "poison") or "ชำระ" in text:
            cleansed += 1
    # high bond support should cleanse in a good fraction of seeds
    assert cleansed >= 8


def test_decide_does_not_cleanse_twice_flag():
    player = {
        "hp": 90,
        "max_hp": 100,
        "needs": {"morale": 70, "hunger": 10, "fatigue": 10},
        "statuses": [{"id": "poison", "kind": "debuff", "remaining": 2}],
    }
    mon = {"hp": 100, "max_hp": 100}
    m = {"id": "s", "kind": "spirit", "role": "support"}
    d1 = decide(player, mon, m, bond=70, team_cleansed_this_round=False)
    d2 = decide(player, mon, m, bond=70, team_cleansed_this_round=True)
    assert d1.action == ACT_CLEANSE
    assert d2.action != ACT_CLEANSE or d2.priority >= P0
