"""
Intelligence as a spendable mental resource (hidden formulas).

- Invest in ความฉลาด (stats_alloc) raises max capacity.
- Current pool (intel_current) is spent for ATB boost / special choices.
- Recovers via rest, time, items — never exact formula shown.
- Luck soft-biases success of intel-gated options (never shown).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def ensure_intelligence(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> None:
    """Init / clamp intel pool after alloc or load."""
    if reg is not None:
        try:
            from game.domain.progression import recompute_powers

            # recompute sets power_intel; avoid full recursion if already mid-recompute
            if "power_intel" not in player:
                recompute_powers(player, reg)
        except Exception:
            pass
    alloc = int((player.get("stats_alloc") or {}).get("intelligence") or 0)
    learn = int(player.get("learn_points") or 0)
    power = float(player.get("power_intel") or 3.0)
    # max capacity: soft from investment + latent power + learn (hidden)
    imax = max(3, int(round(3 + alloc * 1.4 + power * 0.35 + learn * 0.5)))
    # temporary boost from items
    imax += int(player.get("intel_max_boost") or 0)
    player["intel_max"] = imax
    cur = player.get("intel_current")
    if cur is None:
        player["intel_current"] = imax
    else:
        player["intel_current"] = max(0, min(imax, int(cur)))
    # soft flag for "any special option UI" — still need enough current for each option
    player["intel_options"] = (
        alloc + learn >= 2
        or power >= 6
        or "quiet_mind" in (player.get("blessing_flags") or [])
        or imax >= 6
    )


def recompute_intel_max(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> None:
    ensure_intelligence(player, reg)


def intel_current(player: Mapping[str, Any]) -> int:
    return int(player.get("intel_current") or 0)


def intel_max(player: Mapping[str, Any]) -> int:
    return max(1, int(player.get("intel_max") or 3))


def soft_intel_label(player: Mapping[str, Any]) -> str:
    """UI soft — never show exact formula."""
    c, m = intel_current(player), intel_max(player)
    if m <= 0:
        return "จิตว่าง"
    r = c / m
    if r >= 0.85:
        return "จิตแจ่มใส"
    if r >= 0.5:
        return "จิตพอใช้"
    if r >= 0.25:
        return "จิตล้า"
    return "จิตมืดมัว"


def can_afford_intel(player: Mapping[str, Any], cost: int) -> bool:
    return intel_current(player) >= max(0, int(cost))


def spend_intelligence(
    player: MutableMapping[str, Any],
    cost: int,
    *,
    reason: str = "",
) -> Tuple[bool, str]:
    """Spend current intel. Returns (ok, soft message)."""
    cost = max(0, int(cost))
    if cost <= 0:
        return True, ""
    ensure_intelligence(player)
    cur = intel_current(player)
    if cur < cost:
        return False, "ความฉลาดไม่พอสำหรับทางเลือกนี้… (จิตยังไม่พร้อม)"
    player["intel_current"] = cur - cost
    # track fatigue for recovery soft
    player["intel_spent_total"] = int(player.get("intel_spent_total") or 0) + cost
    soft = {
        "atb": "ใช้สติเร่งจังหวะ — จิตอ่อนลงเล็กน้อย",
        "choice": "ตัดสินใจพิเศษ — ใช้สติไปกับทางนั้น",
        "insight": "มองเห็นทางแปลก — จิตเปลืองไปกับการคิด",
    }.get(reason, "ใช้ความฉลาดไปกับสิ่งหนึ่ง…")
    return True, soft


def restore_intelligence(
    player: MutableMapping[str, Any],
    amount: int,
    *,
    reason: str = "rest",
) -> str:
    """Restore current toward max. Soft message only."""
    ensure_intelligence(player)
    amount = max(0, int(amount))
    if amount <= 0:
        return ""
    cur = intel_current(player)
    mx = intel_max(player)
    if cur >= mx:
        return "จิตเต็มอยู่แล้ว"
    player["intel_current"] = min(mx, cur + amount)
    labels = {
        "rest": "พักผ่อน — จิตค่อยๆ กลับมา",
        "time": "เวลาผ่านไป — หัวโล่งขึ้นเล็กน้อย",
        "item": "ใช้ของ — ความคิดคมขึ้นชั่วขณะ",
        "learn": "เรียนรู้ — ช่องว่างในจิตกว้างขึ้น",
    }
    return labels.get(reason, "จิตฟื้นขึ้นบ้าง")


def tick_intel_recovery(
    player: MutableMapping[str, Any],
    *,
    ticks: int = 1,
) -> Optional[str]:
    """
    Passive field time_units: slow passive recovery (hidden rate).
    Call occasionally from field loop.
    """
    ensure_intelligence(player)
    if intel_current(player) >= intel_max(player):
        return None
    # very slow: every few ticks chance to +1
    acc = int(player.get("_intel_tick_acc") or 0) + max(1, int(ticks))
    player["_intel_tick_acc"] = acc
    need = 4  # hidden
    if acc < need:
        return None
    player["_intel_tick_acc"] = acc % need
    return restore_intelligence(player, 1, reason="time")


def rest_intel_recovery(player: MutableMapping[str, Any]) -> str:
    """Field rest — solid restore (still soft)."""
    ensure_intelligence(player)
    mx = intel_max(player)
    cur = intel_current(player)
    # restore ~30–50% of missing + flat 1
    missing = mx - cur
    gain = 1 + max(0, missing // 3)
    # speed investment slightly helps mental rest? no — defense soft
    return restore_intelligence(player, gain, reason="rest")


def apply_intel_item(
    player: MutableMapping[str, Any],
    item: Mapping[str, Any],
) -> List[str]:
    """Item fields: restore_intel, boost_intel_max (temp), fill_intel."""
    notes: List[str] = []
    ensure_intelligence(player)
    if item.get("fill_intel"):
        player["intel_current"] = intel_max(player)
        notes.append(restore_intelligence(player, 0, reason="item") or "จิตเต็มทันที")
        player["intel_current"] = intel_max(player)
        notes = ["ใช้ของ — จิตกลับมาเต็ม"]
    if item.get("restore_intel"):
        msg = restore_intelligence(player, int(item["restore_intel"]), reason="item")
        if msg:
            notes.append(msg)
    if item.get("boost_intel_max"):
        player["intel_max_boost"] = int(player.get("intel_max_boost") or 0) + int(
            item["boost_intel_max"]
        )
        ensure_intelligence(player)
        # also fill a bit of the new room
        restore_intelligence(player, int(item["boost_intel_max"]), reason="item")
        notes.append("ขอบเขตความคิดกว้างขึ้นชั่วคราว… (ไม่รู้ว่านานแค่ไหน)")
    return notes


def spend_intel_for_atb(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> Tuple[bool, str]:
    """
    Spend intel to seize tempo:
    - If ATB not full: surge fill toward full.
    - If already full: bank rate surge for next cycle after you act.
    Cost 1–3 (hidden). Luck soft-biases fill amount (never shown).
    """
    ensure_intelligence(player, reg)
    rng = rng or random.Random()
    atb = float(player.get("atb") or 0)
    luck = float(player.get("luck_score") or 0.0)

    if atb >= 100:
        # bank next-cycle acceleration
        cost = 2
        ok, msg = spend_intelligence(player, cost, reason="atb")
        if not ok:
            return False, msg
        player["atb_intel_surge"] = float(player.get("atb_intel_surge") or 0) + 2.2 + luck
        player["atb_intel_surge_turns"] = max(
            int(player.get("atb_intel_surge_turns") or 0), 3
        )
        return True, msg + " · เตรียมชิงจังหวะรอบถัดไป (แท่งจะเต็มเร็วขึ้น)"

    missing = max(0.0, 100.0 - atb)
    cost = 1 if missing < 40 else (2 if missing < 75 else 3)
    if intel_max(player) <= 4 and cost < 3:
        cost = min(3, cost + (1 if missing > 50 else 0))
    ok, msg = spend_intelligence(player, cost, reason="atb")
    if not ok:
        return False, msg
    surge = 28 + missing * 0.35 + luck * 25 + rng.randint(0, 8)
    player["atb"] = min(100.0, atb + surge)
    player["atb_intel_surge"] = float(player.get("atb_intel_surge") or 0) + 1.5
    player["atb_intel_surge_turns"] = 2
    return True, msg + " · จังหวะพุ่งขึ้น!"


def can_use_special_option(
    player: Mapping[str, Any],
    need: int,
) -> Tuple[bool, str]:
    """Gate a special decision option by current intel."""
    need = max(0, int(need))
    if need <= 0:
        return True, ""
    if not can_afford_intel(player, need):
        return (
            False,
            f"ทางเลือกพิเศษนี้ต้องการสติมากกว่านี้ (ตอนนี้จิต{soft_intel_label(player)})",
        )
    return True, ""


def try_special_option(
    player: MutableMapping[str, Any],
    need: int,
    rng: random.Random,
    *,
    base_success: float = 0.72,
    reason: str = "choice",
) -> Tuple[bool, str, bool]:
    """
    Spend intel and roll success (luck hidden).
    Returns (spent_ok, message, success).
    If cannot afford: (False, msg, False).
    """
    can, why = can_use_special_option(player, need)
    if not can:
        return False, why, False
    ok, msg = spend_intelligence(player, need, reason=reason)
    if not ok:
        return False, msg, False
    luck = float(player.get("luck_score") or 0.0)
    # success never shown as %
    chance = max(0.15, min(0.95, base_success + luck * 0.35))
    success = rng.random() < chance
    if success:
        return True, msg + " · ทางนั้น… ไปได้", True
    return True, msg + " · ทำแล้ว แต่ผลไม่เป็นดั่งใจ (โชค/จังหวะ?)", False


def format_intel_status_line(player: Mapping[str, Any]) -> str:
    """Soft line for status panels — no exact combat formulas."""
    ensure_intelligence(player)  # type: ignore
    c, m = intel_current(player), intel_max(player)
    return f" จิต [{soft_intel_label(player)}] {c}/{m}  (ใช้เร่งจังหวะ/ทางเลือกพิเศษ)"
