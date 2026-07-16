"""
WO-052 Automatic Growth after Lv30+ — cut manual P, grow from play + grade.

Early game (1–29): manual Soft P still works.
Late game (30+): no new stat_points from levels; residual converted once;
growth from grade × profile + quest/combat/anima/relic soft sources.

Soft Feel only — no raw formulas shown to player.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Soft gate — design lock
AUTO_GROWTH_LEVEL = 30

# Source weights (hidden) — relative pulse sizes
_SOURCE_BASE: Dict[str, float] = {
    "level": 1.15,
    "combat": 0.55,
    "quest": 1.35,
    "explore": 0.45,
    "anima": 0.70,
    "relic": 0.50,
    "faction": 0.40,
    "ritual": 0.90,
    "residual": 0.0,  # set per leftover points
}

# Soft labels for UI
_SOURCE_TH: Dict[str, str] = {
    "level": "เลเวล",
    "combat": "ไฟต์",
    "quest": "เควส",
    "explore": "สำรวจ",
    "anima": "จิตวิญญาณ",
    "relic": "เรลิก/พันธะ",
    "faction": "สายตาโลก",
    "ritual": "พิธี/ห้อง",
    "residual": "แต้มเก่าที่ไหลเข้า",
}

AXIS_KEYS: Tuple[str, ...] = ("atk", "defense", "magic", "speed")

AXIS_LABEL_TH: Dict[str, str] = {
    "atk": "โจมตี",
    "defense": "ป้องกัน",
    "magic": "เวท",
    "speed": "ความเร็ว",
}


def ensure_auto_growth(player: MutableMapping[str, Any]) -> None:
    player.setdefault("auto_growth_active", False)
    player.setdefault("_p_phase_out_done", False)
    player.setdefault("_auto_growth_pulses", 0)
    player.setdefault("_last_growth_source", "")
    player.setdefault("_growth_log", [])  # soft ring buffer
    try:
        from game.domain.stat_grades import ensure_grade_state

        ensure_grade_state(player)
    except Exception:
        player.setdefault("axis_progress", {})
        for k in AXIS_KEYS:
            player.setdefault("axis_progress", {}).setdefault(k, 0.0)


def auto_growth_level_gate() -> int:
    return AUTO_GROWTH_LEVEL


def is_auto_growth_mode(player: Mapping[str, Any]) -> bool:
    """True when manual P is locked (Lv ≥ 30 or forced flag)."""
    if player.get("auto_growth_active"):
        return True
    if player.get("flags") and player["flags"].get("force_auto_growth"):
        return True
    return int(player.get("level") or 1) >= AUTO_GROWTH_LEVEL


def is_manual_p_locked(player: Mapping[str, Any]) -> bool:
    return is_auto_growth_mode(player)


def soft_threshold_flag(player: Mapping[str, Any]) -> bool:
    """
    Soft Flag “พลังอั้น” near the gate (Lv 28–29) for UI foreshadow —
    does not lock P yet.
    """
    lv = int(player.get("level") or 1)
    return 28 <= lv < AUTO_GROWTH_LEVEL


def effective_growth_rate(player: Mapping[str, Any]) -> float:
    """
    Hidden overall rate from player_grade + light anima.
    Before temple: neutral-ish 1.0.
    """
    try:
        from game.domain.stat_grades import grade_revealed, player_growth_mult

        if grade_revealed(player):
            base = float(player_growth_mult(player))
        else:
            base = 0.95  # slightly slower without self-knowledge
    except Exception:
        g = str(player.get("player_grade") or "C")
        table = {
            "F": 0.55,
            "E": 0.70,
            "D": 0.85,
            "C": 1.00,
            "B": 1.12,
            "A": 1.25,
            "S": 1.40,
            "SS": 1.55,
            "SSS": 1.70,
        }
        base = float(table.get(g, 1.0)) if player.get("grade_revealed") else 0.95

    # Anima soft
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 70:
            base *= 1.06
        elif a >= 50:
            base *= 1.02
        elif a < 25:
            base *= 0.94
    except Exception:
        pass
    # relic bond soft
    try:
        if player.get("_bond_resonance_active") or float(player.get("bond_resonance") or 0) >= 0.5:
            base *= 1.03
        ba = str(player.get("_burden_active") or "")
        if ba == "crush":
            base *= 0.96
        elif ba == "strain":
            base *= 0.98
    except Exception:
        pass
    return max(0.45, min(2.0, base))


def _axis_weights(player: Mapping[str, Any]) -> Dict[str, float]:
    """Distribute growth by growth_profile (+ slight affinity)."""
    try:
        from game.domain.stat_grades import profile_tilt, grade_revealed

        if grade_revealed(player):
            w = {ax: float(profile_tilt(player, ax)) for ax in AXIS_KEYS}
        else:
            # pre-reveal: lean on existing alloc
            alloc = player.get("stats_alloc") or {}
            w = {ax: 1.0 + min(0.35, int(alloc.get(ax, 0)) * 0.04) for ax in AXIS_KEYS}
    except Exception:
        w = {ax: 1.0 for ax in AXIS_KEYS}
    # normalize-ish around mean 1
    mean = sum(w.values()) / max(1, len(w))
    if mean > 0:
        w = {k: v / mean for k, v in w.items()}
    return w


def _apply_progress_pulse(
    player: MutableMapping[str, Any],
    total_units: float,
    *,
    source: str,
    reg: Any = None,
    rng: Optional[random.Random] = None,
) -> Tuple[List[str], Dict[str, float]]:
    """
    Add hidden axis_progress + soft stats_alloc ticks; recompute powers.
    Returns soft notes + per-axis deltas (for tests).
    """
    ensure_auto_growth(player)
    rng = rng or random.Random(
        int(player.get("latent_seed") or 1)
        + int(player.get("_auto_growth_pulses") or 0) * 17
        + int(player.get("level") or 1)
    )
    rate = effective_growth_rate(player)
    weights = _axis_weights(player)
    units = max(0.0, float(total_units) * rate)
    if units <= 0:
        return [], {}

    prog = dict(player.get("axis_progress") or {})
    alloc = dict(player.get("stats_alloc") or {})
    deltas: Dict[str, float] = {}
    letter_changes: List[str] = []

    try:
        from game.domain.stat_grades import (
            axis_letter,
            axis_tier,
            grade_revealed,
            soft_desc,
            tier_label_th,
            refresh_axis_grades,
        )

        revealed = grade_revealed(player)
    except Exception:
        revealed = False

        def axis_letter(p, ax):  # type: ignore
            return "?"

        def soft_desc(ax, letter):  # type: ignore
            return ""

        def refresh_axis_grades(p):  # type: ignore
            return {}

        def axis_tier(p, ax):  # type: ignore
            return "mid"

        def tier_label_th(t):  # type: ignore
            return ""

    for ax in AXIS_KEYS:
        share = float(weights.get(ax, 1.0))
        # small noise for mystery
        noise = 0.92 + rng.random() * 0.16
        d = units * share * noise / 4.0  # split across 4 axes scale
        # focused profiles already tilt weights — extra for high weight
        d *= 0.85 + 0.3 * min(1.5, share)
        old_l = axis_letter(player, ax) if revealed else None
        old_t = axis_tier(player, ax) if revealed else None
        cur = float(prog.get(ax, alloc.get(ax, 0)))
        prog[ax] = cur + d
        deltas[ax] = d
        # soft alloc integer ticks: every ~1.0 progress ≈ +1 alloc feel
        # convert fractional to occasional whole points
        before_i = int(alloc.get(ax, 0))
        # map progress growth to alloc: +1 alloc per 1.25 progress gained this pulse accumulate
        # simpler: add floor of d * 0.55 chance-based
        add_pts = 0
        acc = float(player.get(f"_growth_alloc_acc_{ax}") or 0) + d
        while acc >= 1.15:
            acc -= 1.15
            add_pts += 1
        player[f"_growth_alloc_acc_{ax}"] = acc
        if add_pts:
            alloc[ax] = before_i + add_pts
        # temp set for letter read after
        player["axis_progress"] = prog
        player["stats_alloc"] = alloc
        if revealed and add_pts:
            new_l = axis_letter(player, ax)
            new_t = axis_tier(player, ax)
            if old_l and new_l and old_l != new_l:
                letter_changes.append(
                    f"  {AXIS_LABEL_TH[ax]} ({soft_desc(ax, old_l)}) {old_l} → "
                    f"({soft_desc(ax, new_l)}) {new_l}"
                )
            elif old_t and new_t and old_t != new_t:
                letter_changes.append(
                    f"  {AXIS_LABEL_TH[ax]} ชั้น {tier_label_th(old_t)} → {tier_label_th(new_t)}"
                )

    player["axis_progress"] = prog
    player["stats_alloc"] = alloc
    player["_auto_growth_pulses"] = int(player.get("_auto_growth_pulses") or 0) + 1
    player["_last_growth_source"] = source
    try:
        refresh_axis_grades(player)
    except Exception:
        pass

    # recompute powers
    if reg is not None:
        try:
            from game.domain.progression import recompute_powers

            recompute_powers(player, reg)
        except Exception:
            pass
        try:
            from game.domain.equipment import recompute_stats

            recompute_stats(player, reg)
        except Exception:
            pass
        try:
            from game.domain.stat_arch import recompute_anima

            recompute_anima(player, reg)
        except Exception:
            pass

    notes: List[str] = []
    src_th = _SOURCE_TH.get(source, source)
    notes.append(f"  พลังของคุณกำลังพัฒนาเอง… ({src_th})")
    if letter_changes:
        notes.append("  …รู้สึกชั้นแกนเลื่อน:")
        notes.extend(letter_changes[:3])
    else:
        # soft generic feel by dominant axis
        top = max(deltas.items(), key=lambda t: t[1])[0] if deltas else "atk"
        feel = {
            "atk": "มือหนักขึ้นเล็กน้อย",
            "defense": "ตัวถึกทนขึ้นแผ่ว",
            "magic": "เวทไหลลื่นขึ้น",
            "speed": "ก้าวเบาขึ้น",
        }.get(top, "รู้สึกหนาขึ้น")
        notes.append(f"  · {feel}")

    # ring log
    log = list(player.get("_growth_log") or [])
    log.append({"source": source, "units": round(units, 3)})
    player["_growth_log"] = log[-12:]
    # WO-053: soft personal journal (not every pulse)
    try:
        from game.domain.personal_system import note_growth_pulse_story

        note_growth_pulse_story(
            player, source, letter_changed=bool(letter_changes)
        )
    except Exception:
        pass
    return notes, deltas


def phase_out_residual_points(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    force: bool = False,
) -> List[str]:
    """
    One-time: convert leftover stat_points into growth pulse + clear pool.
    Called when entering auto mode (level-up across 30 or menu open).
    """
    ensure_auto_growth(player)
    if player.get("_p_phase_out_done") and not force:
        return []
    if not is_auto_growth_mode(player) and not force:
        return []

    pts = int(player.get("stat_points") or 0)
    player["auto_growth_active"] = True
    notes: List[str] = [
        "  …พลังอั้นแตก — แต้มไม่อยู่ในมือคุณแล้ว",
        "  จากนี้ 「พลังไหลเวียนเอง」 ตามเกรด · เควส · จิต · เรลิก",
    ]
    if pts > 0:
        # convert: each leftover point → ~0.85 growth units
        units = float(pts) * 0.85
        player["stat_points"] = 0
        gnotes, _ = _apply_progress_pulse(
            player, units, source="residual", reg=reg
        )
        notes.append(f"  แต้มเก่า {pts} จุด ไหลเข้าตัว…")
        notes.extend(gnotes)
    else:
        notes.append("  (ไม่มีแต้มค้าง — พร้อมโตเอง)")
    player["_p_phase_out_done"] = True
    player["stat_points"] = 0
    try:
        from game.domain.personal_system import note_auto_growth_story

        note_auto_growth_story(player)
    except Exception:
        pass
    return notes


def activate_auto_growth_if_needed(
    player: MutableMapping[str, Any],
    reg: Any = None,
) -> List[str]:
    """Enter auto mode when Lv crosses gate; phase out residuals."""
    ensure_auto_growth(player)
    if not is_auto_growth_mode(player):
        return []
    notes: List[str] = []
    if not player.get("auto_growth_active"):
        player["auto_growth_active"] = True
        notes.append(f"  Lv.{player.get('level')} — เข้าสู่โหมดเติบโตอัตโนมัติ")
    notes.extend(phase_out_residual_points(player, reg))
    return notes


def pulse_auto_growth(
    player: MutableMapping[str, Any],
    source: str,
    *,
    reg: Any = None,
    magnitude: float = 1.0,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Main entry for growth events. No-op before Lv30 (except residual).
    """
    ensure_auto_growth(player)
    if not is_auto_growth_mode(player):
        return []
    # ensure phase-out once
    notes = list(activate_auto_growth_if_needed(player, reg))
    base = float(_SOURCE_BASE.get(source, 0.5)) * float(magnitude)
    if base <= 0:
        return notes
    gnotes, _ = _apply_progress_pulse(
        player, base, source=source, reg=reg, rng=rng
    )
    notes.extend(gnotes)
    return notes


def on_level_up_auto_growth(
    player: MutableMapping[str, Any],
    reg: Any,
    levels: int = 1,
) -> List[str]:
    """Replace stat_points grant when in auto mode; also fire when crossing 30."""
    ensure_auto_growth(player)
    lv = int(player.get("level") or 1)
    notes: List[str] = []
    # crossing or already in
    if lv >= AUTO_GROWTH_LEVEL:
        notes.extend(activate_auto_growth_if_needed(player, reg))
        notes.extend(
            pulse_auto_growth(
                player, "level", reg=reg, magnitude=float(max(1, levels))
            )
        )
    elif soft_threshold_flag(player):
        notes.append("  …พลังเริ่มอั้น — ใกล้จังหวะที่แต้มจะไม่อยู่ในมือ")
    return notes


def should_grant_stat_points(player: Mapping[str, Any]) -> bool:
    """False after auto growth mode — levels no longer give P points."""
    return not is_auto_growth_mode(player)


def format_auto_growth_panel(player: Mapping[str, Any]) -> List[str]:
    """Soft P menu replacement after gate."""
    ensure_auto_growth(player)  # type: ignore[arg-type]
    lines: List[str] = [
        " พลังไหลเวียนเอง",
        "---",
        " หลังเลเวล 30 แต้ม P ไม่อยู่ในมือคุณแล้ว",
        " เติบโตจาก เกรด · เควส · ไฟต์ · จิตวิญญาณ · เรลิก",
        "---",
    ]
    try:
        from game.domain.stat_grades import (
            format_grade_surface_lines,
            grade_revealed,
            player_soft_desc,
            profile_label_th,
        )

        if grade_revealed(player):
            pg = str(player.get("player_grade") or "?")
            lines.append(
                f" ระดับคุณ 〔{pg}〕 {player_soft_desc(pg)} · "
                f"{profile_label_th(str(player.get('growth_profile') or 'balanced'))}"
            )
            lines.append(" (เกรดสูง = โตเร็วขึ้น · soft)")
            lines.append("---")
            for ln in format_grade_surface_lines(
                player, compact=False, include_header=False
            )[:8]:
                lines.append(ln if str(ln).startswith(" ") else f" {ln}")
        else:
            lines.append(" เกรดยังปิด — วิหารช่วยให้อ่านและโตชัดขึ้น")
    except Exception:
        lines.append(" · เกรด/แกน — กด V อ่านชั้น")

    src = str(player.get("_last_growth_source") or "")
    if src:
        lines.append("---")
        lines.append(f" ล่าสุดโตจาก 〔{_SOURCE_TH.get(src, src)}〕")
    pulses = int(player.get("_auto_growth_pulses") or 0)
    if pulses:
        lines.append(f" · รู้สึกพัฒนาแล้วหลายจังหวะ (soft)")
    lines.append("---")
    lines.append(" 0  กลับ")
    lines.append(" · ไม่มีปุ่มลงแต้ม — ไปเล่น เควส/ไฟต์/เรลิก")
    return lines


def format_p_menu_or_auto(player: Mapping[str, Any]) -> List[str]:
    """Router for P UI."""
    if is_manual_p_locked(player):
        return format_auto_growth_panel(player)
    try:
        from game.domain.stat_grades import format_grade_p_panel

        lines = list(format_grade_p_panel(player))
        if soft_threshold_flag(player):
            lines.insert(3, " …ใกล้ Lv30 — แต้มจะไหลเข้าตัวเอง")
        return lines
    except Exception:
        from game.domain.progression import format_alloc_panel

        return format_alloc_panel(player)


def refuse_manual_allocate_message(player: Mapping[str, Any]) -> str:
    return (
        "หลังเลเวล 30 แต้มไม่อยู่ในมือคุณแล้ว — "
        "พลังไหลจากเกรด · เควส · จิตวิญญาณ (กด P ดูสถานะ soft)"
    )
