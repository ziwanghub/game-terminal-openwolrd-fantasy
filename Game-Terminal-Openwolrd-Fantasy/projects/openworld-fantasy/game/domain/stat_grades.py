"""
WO-048/049 Hidden Grade System — player_grade + axis grades + temple unlock.

WO-049: Grade Surface UI + tier soft (ต้น/กลาง/ปลาย/พิเศษ).
True numbers stay hidden. Player sees soft labels + letter (+ tier) after temple.
Anima is NOT a grade axis (separate Spirit facet).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Axes that receive P invest + grades
AXIS_KEYS: Tuple[str, ...] = ("atk", "defense", "magic", "speed")

AXIS_LABEL_TH: Dict[str, str] = {
    "atk": "โจมตี",
    "defense": "ป้องกัน",
    "magic": "เวท",
    "speed": "ความเร็ว",
}

GRADE_ORDER: Tuple[str, ...] = (
    "F",
    "E",
    "D",
    "C",
    "B",
    "A",
    "S",
    "SS",
    "SSS",
)

# WO-049: soft tier within a letter band
TIER_EARLY = "early"
TIER_MID = "mid"
TIER_LATE = "late"
TIER_SPECIAL = "special"
TIER_ORDER: Tuple[str, ...] = (TIER_EARLY, TIER_MID, TIER_LATE, TIER_SPECIAL)

TIER_LABEL_TH: Dict[str, str] = {
    TIER_EARLY: "ขั้นต้น",
    TIER_MID: "ขั้นกลาง",
    TIER_LATE: "ขั้นปลาย",
    TIER_SPECIAL: "พิเศษ",
}

# Soft flavor for tier (shorter, for compact UI)
TIER_SOFT_TH: Dict[str, str] = {
    TIER_EARLY: "เริ่ม",
    TIER_MID: "มั่น",
    TIER_LATE: "เต็มช่วง",
    TIER_SPECIAL: "เหนือขอบ",
}

# axis_score thresholds (inclusive lower) — locked docs/STAT_GRADES_LOCK.md
# Ordered high→low for letter_from_axis_score
_AXIS_THRESHOLDS: Tuple[Tuple[str, float], ...] = (
    ("SSS", 57.0),
    ("SS", 47.0),
    ("S", 37.0),
    ("A", 27.0),
    ("B", 20.0),
    ("C", 15.0),
    ("D", 10.0),
    ("E", 5.0),
    ("F", 0.0),
)

# band [lo, hi) per letter — hi exclusive except SSS open
_AXIS_BAND: Dict[str, Tuple[float, Optional[float]]] = {
    "F": (0.0, 5.0),
    "E": (5.0, 10.0),
    "D": (10.0, 15.0),
    "C": (15.0, 20.0),
    "B": (20.0, 27.0),
    "A": (27.0, 37.0),
    "S": (37.0, 47.0),
    "SS": (47.0, 57.0),
    "SSS": (57.0, None),  # open-ended; special from 80+
}

# player_grade → base growth mult
_PLAYER_GROWTH: Dict[str, float] = {
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

# player_grade soft description (รวม · นักฝึก → เสี้ยวเทพ)
_PLAYER_SOFT_DESC: Dict[str, str] = {
    "F": "นักฝึก",
    "E": "อดทนได้",
    "D": "เริ่มมีแวว",
    "C": "จิตต้น",
    "B": "โดดเด่น",
    "A": "ยอดเยี่ยม",
    "S": "ตำนานแผ่ว",
    "SS": "ใกล้เทพ",
    "SSS": "เสี้ยวเทพ",
}

# soft description per axis per grade (locked)
_SOFT_DESC: Dict[str, Dict[str, str]] = {
    "atk": {
        "F": "นักฝึก",
        "E": "มือเริ่มหนัก",
        "D": "คมเริ่มชัด",
        "C": "นักรบฝึกหัด",
        "B": "คมโดดเด่น",
        "A": "คมยอด",
        "S": "คมตำนานแผ่ว",
        "SS": "คมใกล้เทพ",
        "SSS": "เสี้ยวคมเทพ",
    },
    "defense": {
        "F": "ยังบาง",
        "E": "อดทนได้",
        "D": "ถึกขึ้น",
        "C": "เกราะในใจ",
        "B": "ถึกแน่น",
        "A": "เกราะในตน",
        "S": "ถึกเหนือคน",
        "SS": "เกราะใกล้เทพ",
        "SSS": "เสี้ยวเกราะเทพ",
    },
    "magic": {
        "F": "จิตฝุ่น",
        "E": "จิตต้น",
        "D": "เวทแผ่วมั่น",
        "C": "จิตมั่นต้น",
        "B": "เวทไหล",
        "A": "เวทยอด",
        "S": "เวทตำนานแผ่ว",
        "SS": "เวทใกล้เทพ",
        "SSS": "เสี้ยวเวทเทพ",
    },
    "speed": {
        "F": "ก้าวลัง",
        "E": "พอเลื่อน",
        "D": "เบาขึ้น",
        "C": "ไร้เงาแผ่ว",
        "B": "ไร้เงา",
        "A": "ว่องไว",
        "S": "เหนือเงา",
        "SS": "เกินคน",
        "SSS": "เสี้ยวความเร็วเทพ",
    },
}

# invest soft feel line (direction)
_INVEST_FEEL: Dict[str, str] = {
    "atk": "รู้สึกมือเริ่มหนักขึ้น",
    "defense": "รู้สึกตัวถึกทนขึ้นเล็กน้อย",
    "magic": "เวทย์ไหลลื่นขึ้น",
    "speed": "รู้สึกตัวเบาขึ้น",
}

PROFILE_BALANCED = "balanced"
PROFILE_FOCUSED = "focused"
PROFILE_MIXED = "mixed"
PROFILES = (PROFILE_BALANCED, PROFILE_FOCUSED, PROFILE_MIXED)

TEMPLE_MIN_LEVEL = 10


def ensure_grade_state(player: MutableMapping[str, Any]) -> None:
    player.setdefault("grade_revealed", False)
    player.setdefault("player_grade", None)
    player.setdefault("growth_profile", PROFILE_BALANCED)
    player.setdefault("axis_grades", {})
    player.setdefault("axis_tiers", {})
    player.setdefault("_grade_pressure", 0)
    # hidden float progress per axis (grows with invest × growth)
    player.setdefault("axis_progress", {})
    for k in AXIS_KEYS:
        player["axis_progress"].setdefault(k, float((player.get("stats_alloc") or {}).get(k, 0)))


def grade_revealed(player: Mapping[str, Any]) -> bool:
    return bool(player.get("grade_revealed"))


def soft_desc(axis: str, letter: str) -> str:
    return (_SOFT_DESC.get(axis) or {}).get(letter) or "ยังไม่ชัด"


def player_soft_desc(letter: str) -> str:
    """Soft description for player_grade (รวม)."""
    return _PLAYER_SOFT_DESC.get(str(letter or ""), "ยังไม่ชัด")


def tier_label_th(tier: str) -> str:
    return TIER_LABEL_TH.get(tier, "ขั้นกลาง")


def tier_soft_th(tier: str) -> str:
    return TIER_SOFT_TH.get(tier, "มั่น")


def invest_feel(axis: str) -> str:
    return _INVEST_FEEL.get(axis) or "รู้สึกหนาขึ้นเล็กน้อย"


def letter_from_axis_score(score: float) -> str:
    s = max(0.0, float(score))
    for letter, thr in _AXIS_THRESHOLDS:
        if s >= thr:
            return letter
    return "F"


def tier_from_axis_score(score: float) -> str:
    """
    Soft tier within the letter band: early / mid / late / special.
    No raw scores exposed — internal only.
    SSS special starts at 80 (hidden).
    """
    s = max(0.0, float(score))
    letter = letter_from_axis_score(s)
    lo, hi = _AXIS_BAND.get(letter, (0.0, 5.0))
    if letter == "SSS" or hi is None:
        # open band: early 57–66 · mid 67–79 · late 80–99 · special 100+
        # special also at late high of open (80+) for SSS mystery edge
        if s >= 100.0:
            return TIER_SPECIAL
        if s >= 80.0:
            return TIER_LATE
        if s >= 67.0:
            return TIER_MID
        return TIER_EARLY
    span = max(0.001, float(hi) - float(lo))
    # position in band [0, 1)
    t = (s - float(lo)) / span
    if t >= 0.92:
        return TIER_SPECIAL  # top edge of band = พิเศษ
    if t >= 0.66:
        return TIER_LATE
    if t >= 0.33:
        return TIER_MID
    return TIER_EARLY


def player_growth_mult(player: Mapping[str, Any]) -> float:
    if not grade_revealed(player):
        return 1.0  # before unlock: neutral invest (true growth still via alloc)
    g = str(player.get("player_grade") or "C")
    return float(_PLAYER_GROWTH.get(g, 1.0))


def _ranked_axes_by_alloc(player: Mapping[str, Any]) -> List[str]:
    alloc = player.get("stats_alloc") or {}
    scored = [(k, int(alloc.get(k, 0))) for k in AXIS_KEYS]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return [k for k, _ in scored]


def profile_tilt(player: Mapping[str, Any], axis: str) -> float:
    """Direction mult from growth_profile."""
    if not grade_revealed(player):
        return 1.0
    prof = str(player.get("growth_profile") or PROFILE_BALANCED)
    if prof == PROFILE_BALANCED:
        return 1.0
    order = _ranked_axes_by_alloc(player)
    if prof == PROFILE_FOCUSED:
        if order and axis == order[0]:
            return 1.25
        return 0.75
    if prof == PROFILE_MIXED:
        top2 = set(order[:2])
        if axis in top2:
            return 1.15
        return 0.85
    return 1.0


def effective_growth(player: Mapping[str, Any], axis: str) -> float:
    return player_growth_mult(player) * profile_tilt(player, axis)


def axis_score(player: Mapping[str, Any], axis: str) -> float:
    """Hidden score used for letter grade (= axis_progress)."""
    ensure_grade_state(player)  # type: ignore[arg-type]
    prog = player.get("axis_progress") or {}
    if axis in prog:
        return float(prog[axis])
    return float((player.get("stats_alloc") or {}).get(axis, 0))


def axis_letter(player: Mapping[str, Any], axis: str) -> str:
    return letter_from_axis_score(axis_score(player, axis))


def axis_tier(player: Mapping[str, Any], axis: str) -> str:
    return tier_from_axis_score(axis_score(player, axis))


def refresh_axis_grades(player: MutableMapping[str, Any]) -> Dict[str, str]:
    ensure_grade_state(player)
    out: Dict[str, str] = {}
    tiers: Dict[str, str] = {}
    for ax in AXIS_KEYS:
        out[ax] = axis_letter(player, ax)
        tiers[ax] = axis_tier(player, ax)
    player["axis_grades"] = out
    player["axis_tiers"] = tiers
    return out


def format_axis_surface(
    player: Mapping[str, Any],
    axis: str,
    *,
    with_feel: bool = False,
    compact: bool = False,
) -> str:
    """
    Soft surface for one axis after unlock.
    Example: โจมตี · นักรบฝึกหัด E · ขั้นต้น
    Before unlock: label + feel only.
    """
    lab = AXIS_LABEL_TH.get(axis, axis)
    if not grade_revealed(player):
        if with_feel:
            return f"{lab}  ·  {invest_feel(axis)}"
        return f"{lab}  ·  ยังปิดเกรด"
    letter = axis_letter(player, axis)
    tier = axis_tier(player, axis)
    desc = soft_desc(axis, letter)
    tlab = tier_label_th(tier)
    if compact:
        # compact: โจม E·ต้น
        short = tlab.replace("ขั้น", "")
        return f"{lab[:2] if len(lab) >= 2 else lab} {letter}·{short}"
    base = f"{lab} ({desc}) {letter} · {tlab}"
    if with_feel:
        return f"{base}  ·  {invest_feel(axis)}"
    return base


def format_axis_line(player: Mapping[str, Any], axis: str) -> str:
    """One soft line for P menu (with tier after unlock)."""
    return format_axis_surface(player, axis, with_feel=True, compact=False)


def note_grade_pressure(player: MutableMapping[str, Any], amount: int = 1) -> None:
    """Call from level-up / heavy play to build temple soft flag."""
    ensure_grade_state(player)
    if player.get("grade_revealed"):
        return
    player["_grade_pressure"] = int(player.get("_grade_pressure") or 0) + max(0, int(amount))


def soft_bottleneck(player: Mapping[str, Any]) -> bool:
    """Soft flag: รู้สึกตัน — ready for temple (with level gate)."""
    if grade_revealed(player):
        return False
    lv = int(player.get("level") or 1)
    if lv < TEMPLE_MIN_LEVEL:
        return False
    pts = int(player.get("stat_points") or 0)
    kills = int((player.get("stats") or {}).get("kills") or player.get("kills") or 0)
    pressure = int(player.get("_grade_pressure") or 0)
    if pts >= 5:
        return True
    if kills >= 8:
        return True
    if pressure >= 3:
        return True
    if lv >= TEMPLE_MIN_LEVEL + 2:
        return True
    return False


def can_temple_unlock(player: Mapping[str, Any]) -> bool:
    if grade_revealed(player):
        return False
    if int(player.get("level") or 1) < TEMPLE_MIN_LEVEL:
        return False
    return soft_bottleneck(player)


def temple_hint_lines(player: Mapping[str, Any]) -> List[str]:
    if grade_revealed(player):
        return []
    lv = int(player.get("level") or 1)
    if lv < TEMPLE_MIN_LEVEL:
        return []
    if soft_bottleneck(player):
        return [
            "  …พลังในตัวอั้น — รู้สึกตัน",
            "  ใบ้: หาวิหารในเมืองโบราณ · หรือเมนูตัวละคร → วิหาร (เมื่อถึงเกณฑ์)",
        ]
    if lv >= TEMPLE_MIN_LEVEL:
        return ["  …บางครั้งพลังอั้น — ยังไม่ถึงจังหวะปลด"]
    return []


def _roll_player_grade(player: Mapping[str, Any], rng: random.Random) -> str:
    """Mystery assign — player does not learn the formula."""
    lv = int(player.get("level") or 1)
    alloc = player.get("stats_alloc") or {}
    total = sum(int(alloc.get(k, 0)) for k in AXIS_KEYS)
    kills = int((player.get("stats") or {}).get("kills") or 0)
    # seed-ish score
    score = lv * 1.2 + total * 0.8 + kills * 0.15 + rng.random() * 8
    if score < 14:
        return "F"
    if score < 18:
        return "E"
    if score < 22:
        return "D"
    if score < 26:
        return "C"
    if score < 30:
        return "B"
    if score < 35:
        return "A"
    if score < 40:
        return "S"
    if score < 45:
        return "SS"
    return "SSS"


def _roll_profile(player: Mapping[str, Any], rng: random.Random) -> str:
    order = _ranked_axes_by_alloc(player)
    alloc = player.get("stats_alloc") or {}
    if not order:
        return PROFILE_BALANCED
    top = int(alloc.get(order[0], 0))
    rest = sum(int(alloc.get(k, 0)) for k in order[1:]) / max(1, len(order) - 1)
    if top >= rest + 4 and top >= 3:
        return PROFILE_FOCUSED if rng.random() < 0.65 else PROFILE_MIXED
    if top >= rest + 2:
        return PROFILE_MIXED if rng.random() < 0.5 else PROFILE_BALANCED
    return PROFILE_BALANCED


def temple_unlock(
    player: MutableMapping[str, Any],
    reg: Any = None,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Temple ritual: reveal player_grade + growth_profile + axis letters.
    """
    ensure_grade_state(player)
    if player.get("grade_revealed"):
        return _already_unlocked_lines(player)
    if not can_temple_unlock(player):
        lv = int(player.get("level") or 1)
        if lv < TEMPLE_MIN_LEVEL:
            return [
                "  นักบวชส่ายหน้าแผ่ว",
                "  「ยังเร็ว… พลังในตัวยังไม่ตันพอจะปลด」",
            ]
        return [
            "  นักบวชมองทะลุ",
            "  「ยังไม่ตัน — เล่นไปอีก เก็บแต้มหรือออกไปเผชิญโลก แล้วค่อยกลับ」",
        ]

    rng = rng or random.Random(
        int(player.get("latent_seed") or 1)
        + int(player.get("level") or 1) * 17
        + sum(int((player.get("stats_alloc") or {}).get(k, 0)) for k in AXIS_KEYS)
    )
    pg = _roll_player_grade(player, rng)
    prof = _roll_profile(player, rng)
    player["player_grade"] = pg
    player["growth_profile"] = prof
    player["grade_revealed"] = True
    player["_grade_unlocked_at_level"] = int(player.get("level") or 1)
    # re-weight existing progress with growth so grades reflect unlock state
    alloc = player.get("stats_alloc") or {}
    prog: Dict[str, float] = {}
    for ax in AXIS_KEYS:
        base = float(alloc.get(ax, 0))
        # convert historical invest into progress units with current growth
        prog[ax] = base * effective_growth(player, ax)
    player["axis_progress"] = prog
    refresh_axis_grades(player)

    lines = [
        "  วิหารเงียบ — แสงอ่อนตกลงบนไหล่คุณ",
        "  นักบวชกระซิบ: 「…ปลดแล้ว」",
        f"  ระดับของคุณ 〔{pg}〕 {player_soft_desc(pg)} — (ไม่รู้ได้มายังไง รู้แค่นี้)",
        f"  แนวทางเติบโต 〔{_profile_label_th(prof)}〕",
        "---",
        "  ตอนนี้คุณอ่านแกนตัวเองได้เป็นตัวอักษร + ชั้น soft:",
    ]
    for ax in AXIS_KEYS:
        lines.append(f"   · {format_axis_surface(player, ax)}")
    lines.append("---")
    lines.append("  แต้ม P ยังใช้ได้ — ลงแล้วเกรด/ชั้นแกนอาจเลื่อน")
    # WO-051: seed appraisal skill on temple unlock
    try:
        from game.domain.appraisal import on_temple_unlock_appraisal

        for ln in on_temple_unlock_appraisal(player):
            lines.append(ln)
    except Exception:
        pass
    # WO-053: personal journal temple beat
    try:
        from game.domain.personal_system import note_temple_story

        note_temple_story(player, str(pg))
    except Exception:
        pass
    return lines


def _profile_label_th(prof: str) -> str:
    return {
        PROFILE_BALANCED: "สมดุล",
        PROFILE_FOCUSED: "เฉพาะทาง",
        PROFILE_MIXED: "ผสม",
    }.get(prof, prof)


def profile_label_th(prof: str) -> str:
    """Public alias for UI."""
    return _profile_label_th(prof)


def _already_unlocked_lines(player: Mapping[str, Any]) -> List[str]:
    pg = str(player.get("player_grade") or "?")
    lines = [
        "  นักบวชพยัก: 「ปลดไปแล้ว」",
        f"  ระดับของคุณ 〔{pg}〕 {player_soft_desc(pg)} · "
        f"แนวทาง 〔{_profile_label_th(str(player.get('growth_profile')))}〕",
        "---",
    ]
    for ax in AXIS_KEYS:
        lines.append(f"   · {format_axis_surface(player, ax)}")
    return lines


def apply_invest_to_grades(
    player: MutableMapping[str, Any],
    axis: str,
    points: int,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    After stats_alloc increased: advance hidden progress by points × growth.
    Returns (old_letter, new_letter, old_tier, new_tier) if revealed else Nones.
    """
    ensure_grade_state(player)
    if axis not in AXIS_KEYS:
        return None, None, None, None
    revealed = grade_revealed(player)
    old_l = axis_letter(player, axis) if revealed else None
    old_t = axis_tier(player, axis) if revealed else None
    prog = dict(player.get("axis_progress") or {})
    cur = float(prog.get(axis, (player.get("stats_alloc") or {}).get(axis, 0) - points))
    # growth applies after unlock; before unlock 1:1 with invest points
    g = effective_growth(player, axis) if revealed else 1.0
    prog[axis] = cur + float(points) * g
    player["axis_progress"] = prog
    refresh_axis_grades(player)
    new_l = axis_letter(player, axis) if revealed else None
    new_t = axis_tier(player, axis) if revealed else None
    return old_l, new_l, old_t, new_t


def format_grade_p_panel(player: Mapping[str, Any]) -> List[str]:
    """Soft P overview with optional grades + tiers."""
    ensure_grade_state(player)  # type: ignore[arg-type]
    pts = int(player.get("stat_points") or 0)
    lines = [
        " ลงแต้มสถานะ",
        "---",
        f" แต้มคงเหลือ  {pts}",
        "---",
    ]
    if grade_revealed(player):
        pg = str(player.get("player_grade") or "?")
        lines.append(
            f" ระดับคุณ 〔{pg}〕 {player_soft_desc(pg)} · "
            f"{_profile_label_th(str(player.get('growth_profile')))}"
        )
        lines.append(" (เกรดแกน + ชั้น soft · ไม่โชว์ตัวเลข)")
        lines.append("---")
    else:
        lines.append(" เกรดยังถูกปิด — soft อย่างเดียว")
        if can_temple_unlock(player):
            lines.append(" …พลังตัน · ไปวิหารเพื่อปลด")
        elif int(player.get("level") or 1) >= TEMPLE_MIN_LEVEL:
            lines.append(" …ใกล้ตัน · เล่นต่อแล้วไปวิหาร")
        lines.append("---")
    for i, ax in enumerate(AXIS_KEYS, 1):
        lines.append(f"  {i}. {format_axis_line(player, ax)}")
    lines.append("---")
    lines.append(" 0  กลับ")
    lines.append(" พิมพ์ 1–4 แล้วใส่จำนวนแต้ม")
    return lines


def format_grade_p_menu(player: Mapping[str, Any]) -> List[str]:
    lines = [" ลงทุนที่", "---"]
    for i, ax in enumerate(AXIS_KEYS, 1):
        lines.append(f"  {i}  {format_axis_line(player, ax)}")
    lines.append("---")
    lines.append("  0  กลับ")
    return lines


def format_grade_surface_lines(
    player: Mapping[str, Any],
    *,
    compact: bool = False,
    include_header: bool = True,
) -> List[str]:
    """
    WO-049 Grade Surface — for Status / Personal hub / V.
    Before temple: soft closed line only.
    After: player_grade + 4 axes with soft desc + letter + tier.
    Never shows raw scores.
    """
    ensure_grade_state(player)  # type: ignore[arg-type]
    lines: List[str] = []
    if include_header:
        lines.append(" เกรด (soft surface)")
    if not grade_revealed(player):
        lines.append(" · ยังปิด — soft อย่างเดียว · วิหารเมื่อตัน (W)")
        if can_temple_unlock(player):
            lines.append(" · …พลังตัน · กด W เข้าวิหาร")
        return lines

    refresh_axis_grades(player)  # type: ignore[arg-type]
    pg = str(player.get("player_grade") or "?")
    prof = _profile_label_th(str(player.get("growth_profile") or PROFILE_BALANCED))
    pdesc = player_soft_desc(pg)
    if compact:
        lines.append(f" · ระดับ 〔{pg}〕 {pdesc} · {prof}")
        compact_axes = " · ".join(
            format_axis_surface(player, ax, compact=True) for ax in AXIS_KEYS
        )
        lines.append(f" · แกน  {compact_axes}")
        return lines

    lines.append(f" · เกรดรวม  〔{pg}〕 {pdesc}")
    lines.append(f" · แนวเติบโต  {prof}  (ส่งผลอัตรา/สมดุลเมื่อลง P)")
    lines.append(" · เกรดแกน")
    for ax in AXIS_KEYS:
        lines.append(f"    {format_axis_surface(player, ax)}")
    return lines


def grade_self_assess_extra(player: Mapping[str, Any]) -> List[str]:
    """Lines for V / status when revealed — full surface (WO-049)."""
    # skip duplicate header; V section already has ④ เกรด
    return format_grade_surface_lines(
        player, compact=False, include_header=False
    )


def grade_hub_compact_lines(player: Mapping[str, Any]) -> List[str]:
    """Compact block for Personal hub frame."""
    return format_grade_surface_lines(player, compact=True, include_header=True)


def invest_feedback_message(
    player: Mapping[str, Any],
    axis: str,
    *,
    old_letter: Optional[str],
    new_letter: Optional[str],
    points_left: int,
    old_tier: Optional[str] = None,
    new_tier: Optional[str] = None,
) -> str:
    lab = AXIS_LABEL_TH.get(axis, axis)
    feel = invest_feel(axis)
    if not grade_revealed(player):
        return (
            f"「{lab}」{feel} · แต้มเหลือ {points_left} · "
            f"(เกรดยังปิด · V/วิหาร)"
        )
    letter = str(new_letter or axis_letter(player, axis))
    tier = str(new_tier or axis_tier(player, axis))
    desc_new = soft_desc(axis, letter)
    tlab = tier_label_th(tier)
    letter_changed = bool(old_letter and new_letter and old_letter != new_letter)
    tier_changed = bool(old_tier and new_tier and old_tier != new_tier)
    if letter_changed:
        desc_old = soft_desc(axis, str(old_letter))
        old_t = tier_label_th(str(old_tier or TIER_MID))
        return (
            f"คุณรู้สึกพลังไหลเวียนแรงขึ้น\n"
            f"  {lab} ({desc_old}) {old_letter} · {old_t}"
            f" → ({desc_new}) {letter} · {tlab}\n"
            f"  แต้มเหลือ {points_left}"
        )
    if tier_changed:
        return (
            f"「{lab}」ชั้นเลื่อน · ({desc_new}) {letter} · "
            f"{tier_label_th(str(old_tier))} → {tlab}\n"
            f"  {feel} · แต้มเหลือ {points_left}"
        )
    return (
        f"「{lab}」({desc_new}) {letter} · {tlab} · {feel} · "
        f"แต้มเหลือ {points_left}"
    )
