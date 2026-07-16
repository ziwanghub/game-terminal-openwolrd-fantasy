"""Party relationship: auto assist chance, gifts, decay, free call."""
from __future__ import annotations

import random

from game.domain.party import (
    assist_chance_from_relationship,
    call_party_power,
    evaluate_gift,
    get_relationship,
    give_money_gift,
    party_member_turns,
    relationship_bar,
    set_relationship,
    soft_relationship_label,
    tick_relationship_decay,
)


def _player_with_member(rel: int = 50, kind: str = "beast") -> dict:
    mid = "test_m1"
    return {
        "party": [
            {
                "id": mid,
                "name": "ทดสอบ",
                "kind": kind,
                "bonus_atk": 6,
            }
        ],
        "party_bonds": {mid: rel},
        "party_known": [mid],
        "party_known_meta": {},
        "hp": 40,
        "max_hp": 50,
        "bonus_atk": 0,
        "money_world": 500,
        "money_heaven": 40,
        "money_hell": 20,
        "inventory_ids": [],
    }


def test_relationship_scale_and_labels():
    # old saves: bond 0–10 → migrate *10 onto 0–100
    p = {"party": [], "party_bonds": {"old": 8}, "party_known": [], "party_known_meta": {}}
    assert get_relationship(p, "old") == 80
    set_relationship(p, "old", 70)
    assert get_relationship(p, "old") == 70
    assert soft_relationship_label(70) == "ไว้ใจ"
    assert soft_relationship_label(10) == "ห่างเหิน"
    bar = relationship_bar(50)
    assert len(bar) == 8
    assert "█" in bar and "░" in bar


def test_assist_chance_scales_with_relationship():
    low = assist_chance_from_relationship(0)
    mid = assist_chance_from_relationship(50)
    high = assist_chance_from_relationship(100)
    assert 0.22 <= low < mid < high <= 0.96
    assert high >= 0.90


def test_high_relationship_assists_often():
    p = _player_with_member(95)
    hits = 0
    for i in range(40):
        mon = {"hp": 80, "max_hp": 80}
        notes = party_member_turns(p, mon, random.Random(i))
        text = "".join(notes)
        if any(k in text for k in ("ซุ่มโจมตี", "ซุ่มรักษา", "ซุ่มเสริม", "ปิดงาน")):
            hits += 1
    assert hits >= 28  # ~87% expected


def test_low_relationship_assists_less():
    p = _player_with_member(5)
    hits = 0
    for i in range(40):
        mon = {"hp": 80, "max_hp": 80}
        notes = party_member_turns(p, mon, random.Random(i + 100))
        text = "".join(notes)
        if any(k in text for k in ("ซุ่มโจมตี", "ซุ่มรักษา", "ซุ่มเสริม", "ปิดงาน")):
            hits += 1
    assert hits <= 28  # ~31% expected; allow seed variance


def test_call_party_power_free_no_mana():
    p = _player_with_member(50)
    p["mana"] = 0
    p["money_world"] = 0

    class _R:
        party = {}
        items = {}

    ok, msg, bonuses = call_party_power(p, _R(), 0)
    assert ok is True
    assert "มานา" in msg or "ไม่เสีย" in msg or "ซุ่ม" in msg
    # focus only once when rel >= 40
    assert bonuses.get("atk", 0) >= 1 or p.get("_party_focus_used")


def test_money_gift_raises_relationship():
    p = _player_with_member(20, kind="heaven_god")

    class _R:
        party = {}
        items = {}

    before = get_relationship(p, "test_m1")
    notes = give_money_gift(p, _R(), 0, currency="heaven", amount=10)
    after = get_relationship(p, "test_m1")
    assert after > before
    assert any("เงิน" in n for n in notes)
    assert p["money_heaven"] == 30


def test_gift_likes_hidden_soft_reaction():
    member = {"id": "spirit_a", "kind": "spirit", "name": "วิญญาณ"}
    food = {"id": "bread", "name": "ขนมปัง", "kind": "food", "tags": ["food"], "rarity": "common"}
    tier, delta, soft = evaluate_gift(member, "bread", food, None)
    assert tier in ("love", "like", "meh", "dislike")
    assert isinstance(soft, str) and soft
    # never dumps preference tags into soft message
    assert "gift_likes" not in soft
    assert "spirit" not in soft


def test_decay_slow_only_when_out_of_party():
    # not in party → decays
    p = {
        "party": [],
        "party_bonds": {"gone": 50},
        "party_known": [],
        "party_known_meta": {},
    }
    for _ in range(10):
        tick_relationship_decay(p, ticks=1)
    # ~1.2 points after 10 ticks
    assert get_relationship(p, "gone") <= 49
    assert get_relationship(p, "gone") >= 45

    # in party → no decay
    p2 = {
        "party": [{"id": "stay", "name": "X", "kind": "beast"}],
        "party_bonds": {"stay": 50},
        "party_known": [],
        "party_known_meta": {},
    }
    for _ in range(20):
        tick_relationship_decay(p2, ticks=1)
    assert get_relationship(p2, "stay") == 50


def test_decay_floor_at_five():
    p = {
        "party": [],
        "party_bonds": {"z": 6},
        "party_known": [],
        "party_known_meta": {},
    }
    for _ in range(200):
        tick_relationship_decay(p, ticks=1)
    assert get_relationship(p, "z") >= 5
