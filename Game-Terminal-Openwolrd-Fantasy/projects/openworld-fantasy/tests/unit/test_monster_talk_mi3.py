"""MI3 soft talk / negotiate with smart monsters."""
from __future__ import annotations

import random

from game.domain.monster_ai import (
    apply_talk_rewards,
    bias_monster_approach,
    resolve_monster_talk,
    talk_eligible,
)


def test_talk_eligible_elite_not_boss_by_default():
    assert talk_eligible({"elite": True, "intel_tier": 2}) is True
    assert talk_eligible({"boss": True, "intel_tier": 3}) is False
    assert talk_eligible({"boss": True, "can_talk": True}) is True
    assert talk_eligible({"rarity": "common"}) is False
    assert talk_eligible({"can_talk": False, "elite": True}) is False


def test_bias_can_promote_rare_talk_for_elite():
    mon = {"elite": True, "intel_tier": 2, "level": 8, "can_flee": True}
    player = {"level": 5, "hp": 80, "max_hp": 100}
    # many seeds: at least some rare_talk promotions from fair_combat base
    talks = 0
    for seed in range(80):
        out = bias_monster_approach("fair_combat", mon, player, random.Random(seed))
        if out == "rare_talk":
            talks += 1
    assert talks >= 5


def test_walk_style_always_walk():
    mon = {"name": "หมาป่า", "elite": True, "intel_tier": 2, "level": 5}
    player = {"level": 5, "hp": 50, "max_hp": 100, "money_world": 100}
    out, lines = resolve_monster_talk(mon, player, "walk", random.Random(1))
    assert out == "walk"
    assert lines


def test_threaten_smart_often_combat_or_ambush_or_flee():
    mon = {
        "name": "หัวหน้า",
        "elite": True,
        "intel_tier": 2,
        "level": 10,
        "can_flee": True,
    }
    player = {
        "level": 3,
        "hp": 90,
        "max_hp": 100,
        "money_world": 0,
        "stats_alloc": {"intelligence": 0},
        "personality": {"courage": 50},
    }
    ends = set()
    for seed in range(40):
        m = dict(mon)
        p = dict(player)
        out, _ = resolve_monster_talk(m, p, "threaten", random.Random(seed))
        ends.add(out)
    # threaten vs smart should not only ever be truce
    assert ends & {"combat", "ambush", "flee", "truce", "walk"}
    assert len(ends) >= 2


def test_gift_spends_money_when_possible():
    mon = {"name": "จอมเวทย์", "elite": True, "intel_tier": 2, "level": 5}
    player = {
        "level": 8,
        "hp": 80,
        "max_hp": 100,
        "money_world": 200,
        "stats_alloc": {"intelligence": 5},
        "luck_score": 0.5,
        "personality": {"caution": 20},
    }
    before = player["money_world"]
    # force gift path
    out, lines = resolve_monster_talk(mon, player, "gift", random.Random(0))
    assert player["money_world"] < before or "เงิน" in " ".join(lines)
    assert out in ("truce", "tip", "tribute", "walk", "combat", "ambush", "flee")


def test_apply_talk_rewards_mastery():
    player = {"location": "dark_forest", "area_mastery": {}, "action_counts": {}}
    mon = {"id": "elite_forest_alpha_wolf", "name": "อัลฟา"}
    notes = apply_talk_rewards(player, mon, "truce", random.Random(1))
    assert int(player["area_mastery"].get("dark_forest", 0)) >= 1
    assert notes
    assert int((player.get("action_counts") or {}).get("monster_talk", 0)) >= 1
