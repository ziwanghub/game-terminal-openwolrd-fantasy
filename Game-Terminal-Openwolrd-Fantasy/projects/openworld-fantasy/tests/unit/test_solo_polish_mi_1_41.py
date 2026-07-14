"""Solo polish 1.41 — MI onboarding · situation · party finish · talk gates."""
from __future__ import annotations

import random

from game.domain.monster_ai import talk_eligible
from game.domain.narrative import situation_strip
from game.domain.party import party_member_turns
from game.ui_terminal.help import CITY_ONBOARD_TIPS, HELP_LINES, TUTORIAL_PAGES


def test_help_covers_parley_and_smart_monsters():
    blob = "\n".join("\n".join(p) for p in TUTORIAL_PAGES) + "\n" + "\n".join(HELP_LINES)
    assert "เจรจา" in blob or "7" in blob
    assert "ฉลาด" in blob or "ถอย" in blob
    tip_blob = "\n".join(CITY_ONBOARD_TIPS)
    assert "elite" in tip_blob.lower() or "ฉลาด" in tip_blob or "เจรจา" in tip_blob


def test_situation_strip_mentions_smart_and_maybe_flee():
    mon = {
        "elite": True,
        "intel_tier": 2,
        "hp": 10,
        "max_hp": 100,
        "name": "อัลฟา",
        "boss": False,
    }
    player = {"hp": 50, "max_hp": 100, "statuses": [], "blessings": []}
    s = situation_strip(player, mon, known=True)
    assert "ฉลาด" in s or "ถอย" in s or "คุย" in s


def test_situation_boss_no_flee_hint():
    mon = {
        "boss": True,
        "intel_tier": 3,
        "hp": 5,
        "max_hp": 200,
        "never_flee": True,
    }
    player = {"hp": 80, "max_hp": 100}
    s = situation_strip(player, mon, known=True)
    assert "อาจถอย" not in s
    assert "คิดเป็น" in s or "ฉลาด" in s or "ศัตรู" in s


def test_party_prefers_finish_on_low_elite():
    player = {
        "hp": 80,
        "max_hp": 100,
        "party": [
            {"id": "c1", "name": "เพื่อน", "kind": "beast", "bonus_atk": 8, "bond": 5}
        ],
        "party_bonds": {"c1": 5},
    }
    mon = {"hp": 8, "max_hp": 100, "elite": True, "name": "elite"}
    # high bond always acts; attack path should reduce mon hp
    notes = party_member_turns(player, mon, random.Random(1))
    assert notes
    assert int(mon["hp"]) < 8 or any("โจมตี" in n or "ปิด" in n or "→" in n for n in notes)


def test_talk_eligible_unchanged_for_polish():
    assert talk_eligible({"elite": True, "intel_tier": 2})
    assert not talk_eligible({"boss": True})
