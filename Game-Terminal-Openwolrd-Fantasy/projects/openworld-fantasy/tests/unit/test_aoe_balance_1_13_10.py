"""1.13.10: AoE / pack balance."""
from __future__ import annotations

from game.domain.aoe_balance import (
    pack_size_roll,
    pack_spawn_chance,
    soft_splash_kill_xp_mult,
    splash_damage_mult,
)


def test_splash_diminishes_with_more_targets():
    m1 = splash_damage_mult(n_splash=1, aoe_skill=False)
    m2 = splash_damage_mult(n_splash=2, aoe_skill=False)
    m3 = splash_damage_mult(n_splash=3, aoe_skill=False)
    assert m1 > m2 > m3
    assert m3 >= 0.26


def test_aoe_skill_stronger_than_cleave_but_capped():
    cleave = splash_damage_mult(n_splash=2, aoe_skill=False)
    aoe = splash_damage_mult(n_splash=2, aoe_skill=True)
    assert aoe >= cleave
    assert aoe <= 0.64


def test_pack_spawn_rarer_early():
    assert pack_spawn_chance(1) < pack_spawn_chance(10)
    assert pack_spawn_chance(1) <= 0.12


def test_pack_size_mostly_one_early():
    # many rolls at lv1 should be mostly 1
    ones = sum(1 for i in range(100) if pack_size_roll(1, i / 100.0) == 1)
    assert ones >= 80


def test_soft_splash_xp():
    assert 0.3 <= soft_splash_kill_xp_mult() <= 0.55
