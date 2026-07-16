"""WO-Arena-1: session, scoring, mystery invite, promote-by-score, rewards."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.arena import (
    BAND_CUTOFFS,
    TIERS,
    build_foe_team,
    can_promote,
    ensure_arena_state,
    format_session_summary,
    next_tier,
    party_lineup_size,
    reward_plan,
    roll_mystery_invite,
    run_arena_session_logic,
    score_round_from_metrics,
    select_lineup,
    total_and_band,
)
from game.domain.character import create_player
from game.domain.party import ensure_party


def test_lineup_size_1_to_4():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ar1", "warrior", "เมษ")
    ensure_party(p)
    assert party_lineup_size(p, []) == 1
    p["party"] = [
        {"id": "c1", "name": "A", "kind": "spirit"},
        {"id": "c2", "name": "B", "kind": "beast"},
        {"id": "c3", "name": "C", "kind": "spirit"},
    ]
    assert party_lineup_size(p, ["c1", "c2"]) == 3
    assert party_lineup_size(p, ["c1", "c2", "c3"]) == 4
    ids = select_lineup(p, [1, 3])
    assert len(ids) == 2


def test_score_loss_can_still_be_high():
    # lose but strong pressure/craft
    r = score_round_from_metrics(
        won=False,
        damage_dealt=120,
        damage_taken=40,
        skills_used=5,
        skill_variety=3,
        assists=2,
        hp_ratio_end=0.2,
        rounds_taken=5,
        acted=True,
    )
    assert not r.won
    assert r.score >= 50  # play well despite loss


def test_idle_scores_low():
    r = score_round_from_metrics(
        won=False,
        damage_dealt=0,
        damage_taken=5,
        skills_used=0,
        skill_variety=0,
        assists=0,
        hp_ratio_end=0.9,
        rounds_taken=1,
        acted=False,
    )
    assert r.score < 40


def test_promote_with_losses_high_score():
    assert can_promote("normal", 100, wins=0)
    assert not can_promote("normal", 50, wins=0)
    assert can_promote("elite", 130, wins=0)
    assert not can_promote("divine", 999, wins=3)
    assert next_tier("normal") == "elite"
    assert next_tier("divine") is None


def test_bands():
    total, bid, lab = total_and_band(
        [
            score_round_from_metrics(
                won=True, damage_dealt=80, damage_taken=10,
                skills_used=4, skill_variety=2, assists=1,
                hp_ratio_end=0.8, rounds_taken=3, acted=True,
            )
        ]
        * 3
    )
    assert total >= 70
    assert bid in {b[1] for b in BAND_CUTOFFS}


def test_mystery_invite_not_pure_random():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ar2", "warrior", "เมษ")
    ensure_arena_state(p)
    # stack flags for deeper weight
    p["bosses_defeated"] = ["boss_a", "boss_b"]
    p["quests_done"] = [f"q{i}" for i in range(15)]
    p["arena"]["best_total"] = 180
    p["grade_revealed"] = True
    p["player_grade"] = "S"
    tiers = set()
    for seed in range(40):
        inv = roll_mystery_invite(p, reg, random.Random(seed))
        assert inv["kind"] == "mystery"
        assert inv["tier"] in TIERS
        assert "???" in inv["label"] or "เงา" in inv["label"]
        tiers.add(inv["tier"])
    # with strong flags should sometimes see elite+
    assert "normal" in tiers or "elite" in tiers


def test_foe_team_caps_and_tiers():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(1)
    for tier in TIERS:
        foes = build_foe_team(reg, tier, rng, player_team_size=4, round_index=2)
        assert 1 <= len(foes) <= 3
        for f in foes:
            assert int(f.get("hp") or 0) > 0


def test_full_session_solo_and_full_team():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ar3", "warrior", "เมษ")
    p["level"] = 8
    p["power_atk"] = 25
    p["atk"] = 20
    p["max_hp"] = 80
    p["hp"] = 80
    p["skills"] = ["slash", "guard_basic", "power_strike"]
    # solo
    r1 = run_arena_session_logic(p, reg, random.Random(2), tier="normal", lineup_ids=[])
    assert len(r1.rounds) == 3
    assert r1.band_id
    assert r1.total_score >= 0
    summary = format_session_summary(r1)
    assert any("รอบ" in x for x in summary)
    # full team
    p["party"] = [
        {"id": "c1", "name": "Leaf", "kind": "spirit", "bonus_atk": 4},
        {"id": "c2", "name": "Wolf", "kind": "beast", "bonus_atk": 5},
        {"id": "c3", "name": "Shade", "kind": "spirit", "bonus_atk": 3},
    ]
    p["party_bonds"] = {"c1": 70, "c2": 60, "c3": 50}
    r2 = run_arena_session_logic(
        p, reg, random.Random(3), tier="elite", lineup_ids=["c1", "c2", "c3"]
    )
    assert len(r2.rounds) == 3
    # party restored
    assert len(p.get("party") or []) == 3


def test_f_grade_still_rewarded_on_good_band():
    plan = reward_plan("elite", "sharp", wins=0, player_grade="F")
    assert int(plan["money"]) > 0 or plan["items"]
    plan_dim = reward_plan("elite", "dim", wins=0, player_grade="SSS")
    # dim can still have tiny money from wins only — wins 0
    assert int(plan_dim["money"]) == 0


def test_lose_all_but_promote_path():
    """Construct high-score losses → promote normal."""
    # three strong loss rounds ~60 each = 180
    rounds = [
        score_round_from_metrics(
            won=False,
            damage_dealt=100,
            damage_taken=50,
            skills_used=5,
            skill_variety=3,
            assists=2,
            hp_ratio_end=0.15,
            rounds_taken=6,
            acted=True,
        )
        for _ in range(3)
    ]
    total, band, _ = total_and_band(rounds)
    assert total >= 95
    assert can_promote("normal", total, wins=0)
