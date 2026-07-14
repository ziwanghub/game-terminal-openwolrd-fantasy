"""
AoE / multi-target balance — soft formulas, no UI spoilers of exact rates.

Splash hits more foes → each secondary takes less (diminishing).
Splash kills give thinner rewards than a focused kill.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping


# Base secondary multiplier before pack-size diminishing
BASE_CLEAVE_MULT = 0.52
BASE_AOE_SKILL_MULT = 0.62
# Hard caps so multi never out-damages single-target focus too hard
SPLASH_MULT_MIN = 0.26
SPLASH_MULT_MAX = 0.64


def splash_damage_mult(
    *,
    n_splash: int,
    aoe_skill: bool = False,
) -> float:
    """
    Damage fraction for each secondary target.
    n_splash = number of secondary foes (not counting primary).
    """
    n = max(0, int(n_splash))
    base = BASE_AOE_SKILL_MULT if aoe_skill else BASE_CLEAVE_MULT
    # 1 secondary ≈ full base; 2 → /1.22; 3 → /1.44
    dim = 1.0 / (1.0 + 0.22 * max(0, n - 1))
    m = base * dim
    # slight soft floor when only one splash
    if n <= 1 and not aoe_skill:
        m = min(m, 0.55)
    return max(SPLASH_MULT_MIN, min(SPLASH_MULT_MAX, m))


def pack_spawn_chance(player_level: int) -> float:
    """Explore: chance a fight is multi-foe (2+). Lower early game."""
    lv = max(1, int(player_level or 1))
    if lv <= 2:
        return 0.10
    if lv <= 4:
        return 0.16
    if lv <= 8:
        return 0.22
    if lv <= 14:
        return 0.28
    return 0.32


def pack_size_roll(player_level: int, rng_random: float) -> int:
    """
    1, 2, or rarely 3 foes. rng_random in [0,1).
    """
    lv = max(1, int(player_level or 1))
    r = float(rng_random)
    chance2 = pack_spawn_chance(lv)
    if r >= chance2:
        return 1
    # among multi: mostly 2, rare 3 at mid+
    chance3 = 0.0
    if lv >= 8:
        chance3 = 0.12
    if lv >= 14:
        chance3 = 0.20
    # r is already < chance2; use secondary roll via fractional part
    # caller should pass a second random for 3 — we use r/chance2
    inner = r / max(1e-6, chance2)
    if inner < chance3:
        return 3
    return 2


def soft_splash_kill_xp_mult() -> float:
    """Splash kills yield thinner XP (anti farm pack with one cleave)."""
    return 0.42


def apply_soft_splash_kill_flag(mon: MutableMapping[str, Any]) -> None:
    mon["_killed_by_splash"] = True


def is_soft_splash_kill(mon: Mapping[str, Any]) -> bool:
    return bool(mon.get("_killed_by_splash"))
