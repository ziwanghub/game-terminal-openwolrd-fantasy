"""Unlimited levels — XP requirement grows with level (harder to level up high)."""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping, MutableMapping, Tuple


DEFAULT_CURVE = {
    "base": 100,
    "exponent": 1.42,
    "linear": 25,
    "xp_kill_base": 18,
    "xp_kill_per_monster_level": 4,
    "xp_gap_bonus": 2.5,
    "xp_overlevel_factor": 0.55,
}


def curve_params(levels_cfg: Mapping[str, Any] | None) -> Dict[str, float]:
    cfg = {**DEFAULT_CURVE, **(dict(levels_cfg) if levels_cfg else {})}
    return {
        "base": float(cfg.get("base", 100)),
        "exponent": float(cfg.get("exponent", 1.42)),
        "linear": float(cfg.get("linear", 25)),
        "xp_kill_base": float(cfg.get("xp_kill_base", 18)),
        "xp_kill_per_monster_level": float(cfg.get("xp_kill_per_monster_level", 4)),
        "xp_gap_bonus": float(cfg.get("xp_gap_bonus", 2.5)),
        "xp_overlevel_factor": float(cfg.get("xp_overlevel_factor", 0.55)),
    }


def xp_to_next(level: int, levels_cfg: Mapping[str, Any] | None = None) -> int:
    """XP needed to go from `level` -> `level+1`. No level cap."""
    level = max(1, int(level))
    p = curve_params(levels_cfg)
    raw = p["base"] * (level ** p["exponent"]) + level * p["linear"]
    return max(1, int(math.floor(raw)))


def xp_progress(player: Mapping[str, Any], levels_cfg: Mapping[str, Any] | None = None) -> Tuple[int, int, float]:
    """Return (xp_current, xp_needed, percent 0-100)."""
    level = int(player.get("level", 1))
    needed = xp_to_next(level, levels_cfg)
    cur = int(player.get("xp", 0))
    cur = max(0, cur)
    pct = min(100.0, (cur / needed) * 100.0) if needed else 100.0
    return cur, needed, pct


def grant_xp(
    player: MutableMapping[str, Any],
    amount: int,
    levels_cfg: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Add XP; level up repeatedly with no max level. Returns summary."""
    amount = max(0, int(amount))
    player["xp"] = int(player.get("xp", 0)) + amount
    levels_gained = 0
    notes = []
    # Safety: allow multi-level but cap loops per grant (anti-runaway)
    for _ in range(100):
        need = xp_to_next(int(player["level"]), levels_cfg)
        if player["xp"] < need:
            break
        player["xp"] -= need
        player["level"] = int(player["level"]) + 1
        levels_gained += 1
        notes.append(f"LEVEL UP! → Lv.{player['level']}")
    # Stat points + hidden rank/unit checks (no free atk every level — player allocates)
    if levels_gained > 0:
        try:
            from game.data_load.registry import get_registry
            from game.domain.progression import on_level_up_points
            from game.domain.equipment import recompute_stats

            reg = get_registry()
            notes.extend(on_level_up_points(player, reg, levels_gained))
            recompute_stats(player, reg)
            player["hp"] = min(int(player["max_hp"]), int(player.get("hp", 0)) + 4 * levels_gained)
            player["mana"] = min(int(player["max_mana"]), int(player.get("mana", 0)) + 2 * levels_gained)
        except Exception:
            player["max_hp"] = int(player.get("max_hp", 100)) + 6 * levels_gained
            player["hp"] = min(int(player["max_hp"]), int(player.get("hp", 0)) + 6 * levels_gained)
    cur, need, pct = xp_progress(player, levels_cfg)
    player["xp_percent"] = round(pct, 1)
    return {
        "gained": amount,
        "levels_gained": levels_gained,
        "xp": cur,
        "xp_needed": need,
        "xp_percent": pct,
        "notes": notes,
    }


def kill_xp_reward(
    player_level: int,
    monster_level: int,
    monster_xp_mult: float = 1.0,
    levels_cfg: Mapping[str, Any] | None = None,
) -> int:
    """XP for a kill — higher monster level pays more; overlevel reduces XP."""
    p = curve_params(levels_cfg)
    base = p["xp_kill_base"] + monster_level * p["xp_kill_per_monster_level"]
    gap = monster_level - player_level
    if gap >= 0:
        base += gap * p["xp_gap_bonus"]
    else:
        # overleveled: still some XP but reduced
        base *= p["xp_overlevel_factor"] ** min(5, -gap)
    base *= max(0.2, float(monster_xp_mult))
    # High-level players need more absolute XP; slight level scaling on rewards
    base *= 1.0 + (player_level - 1) * 0.03
    return max(1, int(round(base)))
