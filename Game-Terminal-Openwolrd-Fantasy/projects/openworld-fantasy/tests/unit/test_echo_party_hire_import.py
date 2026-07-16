"""Regression: hiring player-echo into party must import passives/recompute."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.party import (
    add_member,
    apply_party_passives_to_player,
    member_from_player_echo,
    try_consent_player_hire,
)
from game.domain.progression import init_progression
from game.domain.world_social import build_echo_snapshot
from game.services import field_encounters as fe


def test_field_encounters_imports_party_passives():
    assert hasattr(fe, "apply_party_passives_to_player")
    assert hasattr(fe, "recompute_stats")
    assert hasattr(fe, "apply_world_enemy_mods")


def test_echo_hire_applies_passives_without_nameerror():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Hirer", "vagabond", "เมษ")
    init_progression(p, reg)
    other = build_echo_snapshot(p)
    other["id"] = "echo_hire_1"
    other["name"] = "เงานิรนาม"
    other["bonus_atk"] = 16
    other["max_hp"] = 120
    other["max_mana"] = 50
    ok = False
    why = ""
    for seed in range(40):
        ok, why = try_consent_player_hire(
            p, other, reg, affinity=0.95, rng=random.Random(seed)
        )
        if ok:
            break
    assert ok, why
    mem = member_from_player_echo(other, 0.95, reg, random.Random(1))
    msg = add_member(p, mem, reg)
    assert "ร่วมทาง" in msg
    # same sequence as field_encounters after hire (must not NameError)
    fe.apply_party_passives_to_player(p, reg)
    fe.recompute_stats(p, reg)
    assert len(p.get("party") or []) == 1
    assert "party_bonus_atk" in p
