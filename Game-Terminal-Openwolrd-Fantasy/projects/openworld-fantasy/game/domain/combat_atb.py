"""
Active Time Battle (ATB) gauges — fill until ready to act.

Fill rate is derived from occupation, speed investment, blessings, statuses,
and soft luck — formulas are never shown to the player.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.bars import ratio_bar

ATB_FULL = 100.0


def init_combat_atb(
    player: MutableMapping[str, Any],
    mon: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    ambush: bool = False,
) -> None:
    """Set starting gauges. Ambush = enemy nearly full first."""
    # ensure powers exist for rate calc
    try:
        from game.domain.progression import ensure_progression, recompute_powers

        ensure_progression(player, reg)
        recompute_powers(player, reg)
    except Exception:
        pass

    if ambush:
        player["atb"] = float(rng.randint(5, 25))
        mon["atb"] = float(rng.randint(85, 100))
    else:
        # slight open roll — never explained
        player["atb"] = float(rng.randint(0, 35))
        mon["atb"] = float(rng.randint(0, 40))
        # speed edge: faster side starts a bit fuller (soft)
        pr = action_fill_rate(player, "player", reg)
        mr = action_fill_rate(mon, "monster", reg)
        if pr > mr * 1.08:
            player["atb"] = min(ATB_FULL - 1, player["atb"] + 12)
        elif mr > pr * 1.08:
            mon["atb"] = min(ATB_FULL - 1, mon["atb"] + 12)

    player["atb_rate"] = action_fill_rate(player, "player", reg)
    mon["atb_rate"] = action_fill_rate(mon, "monster", reg)


def action_fill_rate(
    entity: Mapping[str, Any],
    side: str,
    reg: Optional[DataRegistry] = None,
) -> float:
    """
    Hidden points added per ATB tick toward 100.
    Typical range ~6–18 so fights feel distinct but not glacial.
    """
    if side == "player":
        spd_power = float(entity.get("power_spd") or 5.0)
        spd_pts = int((entity.get("stats_alloc") or {}).get("speed") or 0)
        base = 7.0 + spd_power * 0.45 + spd_pts * 0.55
        # occupation latent speed soft (via recompute already in power_spd)
        # pressure slightly speeds (adrenaline)
        base += min(2.5, float(entity.get("pressure") or 0) / 20.0)
        # blessings
        flags = entity.get("blessing_flags") or []
        if "keen_edge" in flags:
            base *= 1.06
        if "soft_second_wind" in flags and int(entity.get("hp") or 0) < int(
            entity.get("max_hp") or 1
        ) * 0.35:
            base *= 1.08
        # luck slight
        luck = float(entity.get("luck_score") or 0.0)
        base *= 1.0 + luck * 0.15
        # temporary surge from spending intelligence (seize tempo)
        surge = float(entity.get("atb_intel_surge") or 0.0)
        if surge > 0:
            base += surge
        # freeze / slow statuses
        base *= _status_speed_mult(entity)
        # N2: fatigue slows ATB fill (SPD softens via needs)
        try:
            from game.domain.needs import atb_fatigue_mult

            base *= float(atb_fatigue_mult(entity))
        except Exception:
            pass
        return max(3.5, min(24.0, base))

    # monster
    mlevel = int(entity.get("level") or entity.get("level_min") or 1)
    base = 6.5 + mlevel * 0.35 + float(entity.get("atk") or entity.get("atk_base") or 8) * 0.08
    # boss slightly slower telegraphs
    if entity.get("boss"):
        base *= 0.88
    rarity = str(entity.get("rarity") or "common")
    if rarity in ("legendary", "divine", "mythic", "archdivine"):
        base *= 1.05
    base *= _status_speed_mult(entity)
    return max(3.0, min(20.0, base))


def _status_speed_mult(entity: Mapping[str, Any]) -> float:
    mult = 1.0
    for s in entity.get("statuses") or []:
        sid = s.get("id") if isinstance(s, dict) else s
        sid = str(sid or "")
        if sid in ("freeze", "stun", "shock"):
            mult *= 0.45
        elif sid in ("slow", "bind"):
            mult *= 0.7
        elif sid in ("haste", "might"):
            mult *= 1.12
    return mult


def refresh_rates(
    player: MutableMapping[str, Any],
    mon: MutableMapping[str, Any],
    reg: DataRegistry,
) -> None:
    player["atb_rate"] = action_fill_rate(player, "player", reg)
    mon["atb_rate"] = action_fill_rate(mon, "monster", reg)


def advance_until_ready(
    player: MutableMapping[str, Any],
    mon: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    max_ticks: int = 40,
) -> List[str]:
    """
    Advance ATB until at least one side is ready.
    Returns ordered list of who acts: 'player' and/or 'monster'.
    """
    refresh_rates(player, mon, reg)
    pr = float(player.get("atb_rate") or 8)
    mr = float(mon.get("atb_rate") or 8)
    pg = float(player.get("atb") or 0)
    mg = float(mon.get("atb") or 0)

    ticks = 0
    while pg < ATB_FULL and mg < ATB_FULL and ticks < max_ticks:
        pg += pr
        mg += mr
        ticks += 1

    player["atb"] = min(ATB_FULL + 20, pg)  # allow small overfill
    mon["atb"] = min(ATB_FULL + 20, mg)

    ready: List[str] = []
    p_ready = float(player.get("atb") or 0) >= ATB_FULL
    m_ready = float(mon.get("atb") or 0) >= ATB_FULL
    if p_ready and m_ready:
        # simultaneous: higher effective rate first; luck soft on player
        luck = float(player.get("luck_score") or 0)
        p_score = pr * (1.0 + luck * 0.2) + rng.random() * 0.5
        m_score = mr + rng.random() * 0.5
        if p_score >= m_score:
            ready = ["player", "monster"]
        else:
            ready = ["monster", "player"]
    elif p_ready:
        ready = ["player"]
    elif m_ready:
        ready = ["monster"]
    else:
        # safety: force player
        player["atb"] = ATB_FULL
        ready = ["player"]
    player["_atb_ticks"] = ticks
    return ready


def spend_action(entity: MutableMapping[str, Any], *, overflow_keep: float = 0.15) -> None:
    """
    After acting: drain gauge. Small leftover from overfill (soft, hidden).
    """
    g = float(entity.get("atb") or 0)
    keep = max(0.0, g - ATB_FULL) * overflow_keep
    entity["atb"] = min(25.0, keep)
    # decay intel ATB surge
    turns = int(entity.get("atb_intel_surge_turns") or 0)
    if turns > 0:
        entity["atb_intel_surge_turns"] = turns - 1
        if entity["atb_intel_surge_turns"] <= 0:
            entity["atb_intel_surge"] = 0.0
            entity["atb_intel_surge_turns"] = 0


def format_atb_bar(entity: Mapping[str, Any], width: int = 10) -> str:
    g = float(entity.get("atb") or 0)
    return ratio_bar(int(min(ATB_FULL, g)), int(ATB_FULL), width=width)


def soft_atb_label(entity: Mapping[str, Any]) -> str:
    """Player-facing readiness — no numbers of rate."""
    g = float(entity.get("atb") or 0)
    if g >= ATB_FULL:
        return "พร้อม"
    if g >= 70:
        return "เกือบเต็ม"
    if g >= 40:
        return "กำลังสะสม"
    return "ช้า"


def init_pack_atb(
    player: MutableMapping[str, Any],
    foes: Sequence[MutableMapping[str, Any]],
    reg: DataRegistry,
    rng: random.Random,
    *,
    ambush: bool = False,
) -> None:
    """Init ATB for player + multiple foes (simultaneous multi-enemy)."""
    try:
        from game.domain.progression import ensure_progression, recompute_powers

        ensure_progression(player, reg)
        recompute_powers(player, reg)
    except Exception:
        pass
    alive = [f for f in foes if int(f.get("hp") or 0) > 0]
    if ambush:
        player["atb"] = float(rng.randint(5, 22))
        for f in alive:
            f["atb"] = float(rng.randint(70, 100))
    else:
        player["atb"] = float(rng.randint(0, 35))
        for f in alive:
            f["atb"] = float(rng.randint(0, 40))
    player["atb_rate"] = action_fill_rate(player, "player", reg)
    for f in alive:
        f["atb_rate"] = action_fill_rate(f, "monster", reg)
        # slightly stagger open so not all monsters fire same tick always
        f["atb"] = min(ATB_FULL - 1, float(f.get("atb") or 0) + rng.randint(0, 15))


def advance_until_ready_multi(
    player: MutableMapping[str, Any],
    foes: Sequence[MutableMapping[str, Any]],
    reg: DataRegistry,
    rng: random.Random,
    *,
    max_ticks: int = 50,
) -> List[Tuple[str, Optional[int]]]:
    """
    Advance until player and/or any living foe is ready.
    Returns ordered acts: ("player", None) or ("monster", index_in_foes).
    """
    player["atb_rate"] = action_fill_rate(player, "player", reg)
    for f in foes:
        if int(f.get("hp") or 0) > 0:
            f["atb_rate"] = action_fill_rate(f, "monster", reg)

    ticks = 0
    while ticks < max_ticks:
        any_ready = float(player.get("atb") or 0) >= ATB_FULL
        for f in foes:
            if int(f.get("hp") or 0) > 0 and float(f.get("atb") or 0) >= ATB_FULL:
                any_ready = True
        if any_ready and ticks > 0:
            break
        # always tick at least once if nobody ready
        if any_ready and ticks == 0:
            # already ready at open — act without more fill
            break
        player["atb"] = float(player.get("atb") or 0) + float(player.get("atb_rate") or 8)
        for f in foes:
            if int(f.get("hp") or 0) > 0:
                f["atb"] = float(f.get("atb") or 0) + float(f.get("atb_rate") or 8)
        ticks += 1
        # stop when someone crosses full
        if float(player.get("atb") or 0) >= ATB_FULL:
            break
        if any(
            int(f.get("hp") or 0) > 0 and float(f.get("atb") or 0) >= ATB_FULL
            for f in foes
        ):
            break

    player["atb"] = min(ATB_FULL + 20, float(player.get("atb") or 0))
    for f in foes:
        if int(f.get("hp") or 0) > 0:
            f["atb"] = min(ATB_FULL + 20, float(f.get("atb") or 0))

    # score ready actors
    candidates: List[Tuple[float, str, Optional[int]]] = []
    luck = float(player.get("luck_score") or 0)
    if float(player.get("atb") or 0) >= ATB_FULL:
        pr = float(player.get("atb_rate") or 8)
        candidates.append((pr * (1.0 + luck * 0.2) + rng.random() * 0.5, "player", None))
    for i, f in enumerate(foes):
        if int(f.get("hp") or 0) <= 0:
            continue
        if float(f.get("atb") or 0) >= ATB_FULL:
            mr = float(f.get("atb_rate") or 8)
            candidates.append((mr + rng.random() * 0.5, "monster", i))
    if not candidates:
        player["atb"] = ATB_FULL
        candidates.append((99.0, "player", None))
    candidates.sort(key=lambda x: -x[0])
    player["_atb_ticks"] = ticks
    return [(side, idx) for _sc, side, idx in candidates]


def format_pack_atb_strip(
    player: Mapping[str, Any],
    foes: Sequence[Mapping[str, Any]],
) -> str:
    """Soft multi-foe ATB line."""
    bits = [f"คุณ {format_atb_bar(player)} {soft_atb_label(player)}"]
    for i, f in enumerate(foes):
        if int(f.get("hp") or 0) <= 0:
            bits.append(f"#{i+1} ล้ม")
            continue
        bits.append(
            f"#{i+1} {format_atb_bar(f)} {soft_atb_label(f)}"
        )
    return " · ".join(bits)


def format_atb_strip(player: Mapping[str, Any], mon: Mapping[str, Any]) -> str:
    """One soft line for combat vitals."""
    pb = format_atb_bar(player)
    mb = format_atb_bar(mon)
    pl = soft_atb_label(player)
    ml = soft_atb_label(mon)
    return f" จังหวะ คุณ [{pb}] {pl}  ·  ศัตรู [{mb}] {ml}"
