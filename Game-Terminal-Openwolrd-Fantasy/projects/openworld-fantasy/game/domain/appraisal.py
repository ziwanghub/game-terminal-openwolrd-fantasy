"""
WO-051 Appraisal Skill — soft read of self & enemy in S / SS / SSS tiers.

- Soft Feel + Mystery: no raw HP/ATK/power/formula
- S: letter + tier soft
- SS: + soft weakness band (elements)
- SSS: + soft recipe (1–2 combo paths)
- Mana + cooldown; grows with use / temple / anima
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Appraisal depth tiers (skill rank feel)
TIER_BASE = "base"  # free soft glance (legacy enemy_assess depth)
TIER_S = "S"
TIER_SS = "SS"
TIER_SSS = "SSS"
TIER_ORDER: Tuple[str, ...] = (TIER_BASE, TIER_S, TIER_SS, TIER_SSS)

SKILL_ID = "soft_appraise"

# Mana / cooldown (soft — not a new resource)
MANA_COST = {
    TIER_BASE: 0,
    TIER_S: 6,
    TIER_SS: 10,
    TIER_SSS: 14,
}
# ticks between paid appraisals (auto_ticks / time_units)
COOLDOWN_TICKS = {
    TIER_BASE: 0,
    TIER_S: 2,
    TIER_SS: 3,
    TIER_SSS: 4,
}

_EL_TH: Dict[str, str] = {
    "physical": "กาย",
    "slash": "ฟัน",
    "pierce": "แทง",
    "blunt": "กระแทก",
    "nature": "ธรรมชาติ",
    "arcane": "เวท",
    "magic": "เวท",
    "fire": "ไฟ",
    "water": "น้ำ",
    "wind": "ลม",
    "earth": "ดิน",
    "ice": "น้ำแข็ง",
    "lightning": "สายฟ้า",
    "holy": "แสงศักดิ์",
    "light": "แสง",
    "shadow": "เงา",
    "dark": "มืด",
    "steam": "ไอน้ำ",
}

_EL_HINT_WEAK: Dict[str, str] = {
    "fire": "กลัวความชื้น/น้ำ",
    "water": "กลัวสายฟ้า/ความแห้ง",
    "wind": "กลัวดิน/หนัก",
    "earth": "กลัวลม/เจาะ",
    "ice": "กลัวไฟ",
    "lightning": "กลัวดิน/ฉนวน",
    "shadow": "กลัวแสงศักดิ์",
    "dark": "กลัวแสง",
    "holy": "เงาเคอะเขิน",
    "light": "เงาเคอะเขิน",
    "nature": "กลัวไฟ",
    "physical": "เวท/จุดอ่อนธาตุอาจทะลุ",
    "arcane": "กาย/ม่านบางอาจรับได้",
}


def ensure_appraisal(player: MutableMapping[str, Any]) -> None:
    player.setdefault("appraisal_tier", TIER_BASE)
    player.setdefault("appraisal_xp", 0)
    player.setdefault("_appraisal_cd_until", 0)
    player.setdefault("_appraised_targets", {})  # mon_id → tier used
    # ensure skill id present after unlock path
    skills = list(player.get("skills") or [])
    if SKILL_ID not in skills and str(player.get("appraisal_tier") or TIER_BASE) != TIER_BASE:
        skills.append(SKILL_ID)
        player["skills"] = skills


def _tick(player: Mapping[str, Any]) -> int:
    return int(
        player.get("auto_ticks")
        or player.get("time_units")
        or player.get("_care_ticks")
        or 0
    )


def _rank_index(tier: str) -> int:
    try:
        return TIER_ORDER.index(str(tier))
    except ValueError:
        return 0


def el_soft(name: str) -> str:
    return _EL_TH.get(str(name).lower(), str(name))


def resolve_appraisal_tier(player: Mapping[str, Any]) -> str:
    """
    Effective tier: max of stored appraisal_tier, skill_rank on soft_appraise,
    and soft gates (temple / level / anima / xp).
    """
    ensure_appraisal(player)  # type: ignore[arg-type]
    best = str(player.get("appraisal_tier") or TIER_BASE)

    # skill rank system if present
    try:
        ranks = player.get("skill_ranks") or {}
        r = str(ranks.get(SKILL_ID) or "").upper()
        if r in (TIER_S, TIER_SS, TIER_SSS):
            if _rank_index(r) > _rank_index(best):
                best = r
        elif r in ("N", "H", "R") and best == TIER_BASE:
            best = TIER_S  # learned skill starts at S depth
    except Exception:
        pass

    # soft auto-raise (does not write unless ensure path)
    lv = int(player.get("level") or 1)
    xp = int(player.get("appraisal_xp") or 0)
    revealed = bool(player.get("grade_revealed"))
    anima = 0.0
    try:
        from game.domain.stat_arch import anima_value

        anima = float(anima_value(player))
    except Exception:
        anima = float(player.get("anima") or 0)

    candidate = TIER_BASE
    if revealed or lv >= 8 or xp >= 3:
        candidate = TIER_S
    if (revealed and lv >= 14) or xp >= 10 or anima >= 55:
        candidate = TIER_SS
    if (revealed and lv >= 22 and xp >= 8) or xp >= 22 or anima >= 75:
        candidate = TIER_SSS

    if _rank_index(candidate) > _rank_index(best):
        best = candidate
    return best if best in TIER_ORDER else TIER_BASE


def sync_appraisal_tier(player: MutableMapping[str, Any]) -> str:
    """Write resolved tier if higher; grant skill when >= S."""
    ensure_appraisal(player)
    resolved = resolve_appraisal_tier(player)
    cur = str(player.get("appraisal_tier") or TIER_BASE)
    if _rank_index(resolved) > _rank_index(cur):
        player["appraisal_tier"] = resolved
    else:
        # keep stored if higher than soft gates
        resolved = cur if _rank_index(cur) >= _rank_index(resolved) else resolved
        player["appraisal_tier"] = resolved
    if resolved != TIER_BASE:
        skills = list(player.get("skills") or [])
        if SKILL_ID not in skills:
            skills.append(SKILL_ID)
            player["skills"] = skills
    return str(player.get("appraisal_tier") or TIER_BASE)


def on_temple_unlock_appraisal(player: MutableMapping[str, Any]) -> List[str]:
    """Call from temple unlock — seed S appraisal."""
    ensure_appraisal(player)
    notes: List[str] = []
    cur = str(player.get("appraisal_tier") or TIER_BASE)
    if _rank_index(cur) < _rank_index(TIER_S):
        player["appraisal_tier"] = TIER_S
        notes.append("  นักบวช: 「…ตาคุณเริ่มอ่านชั้นพลังได้แล้ว」")
    player["appraisal_xp"] = int(player.get("appraisal_xp") or 0) + 2
    sync_appraisal_tier(player)
    skills = list(player.get("skills") or [])
    if SKILL_ID not in skills:
        skills.append(SKILL_ID)
        player["skills"] = skills
        notes.append("  ได้ท่า 「อ่านชั้น」 (ประเมิน soft · ใช้สติ/มานา)")
    return notes


def can_appraise(
    player: Mapping[str, Any],
    *,
    paid: bool = True,
) -> Tuple[bool, str]:
    """
    paid=True: skill path with mana+cd (S+).
    paid=False: free base glance (I combat free soft).
    """
    ensure_appraisal(player)  # type: ignore[arg-type]
    tier = resolve_appraisal_tier(player)
    if not paid or tier == TIER_BASE:
        return True, ""
    now = _tick(player)
    cd_until = int(player.get("_appraisal_cd_until") or 0)
    if now < cd_until:
        return False, " …สมาธิประเมินยังไม่คืน — รอสักครู่"
    cost = int(MANA_COST.get(tier, 6))
    mana = int(player.get("mana") or 0)
    if cost > 0 and mana < cost:
        return False, " …สติ/มานาแผ่ว — ประเมินชั้นลึกไม่ได้ตอนนี้"
    return True, ""


def spend_appraise(
    player: MutableMapping[str, Any],
    *,
    paid: bool = True,
) -> Tuple[bool, str]:
    """Spend mana + set cooldown when paid appraisal."""
    ok, reason = can_appraise(player, paid=paid)
    if not ok:
        return False, reason
    tier = resolve_appraisal_tier(player)
    if paid and tier != TIER_BASE:
        cost = int(MANA_COST.get(tier, 6))
        if cost > 0:
            player["mana"] = max(0, int(player.get("mana") or 0) - cost)
        cd = int(COOLDOWN_TICKS.get(tier, 2))
        player["_appraisal_cd_until"] = _tick(player) + cd
    return True, ""


def note_appraisal_use(player: MutableMapping[str, Any], *, depth: str = TIER_S) -> Optional[str]:
    """Grow appraisal xp; may soft-raise tier."""
    ensure_appraisal(player)
    gain = 1
    if depth == TIER_SS:
        gain = 2
    elif depth == TIER_SSS:
        gain = 3
    player["appraisal_xp"] = int(player.get("appraisal_xp") or 0) + gain
    old = str(player.get("appraisal_tier") or TIER_BASE)
    new = sync_appraisal_tier(player)
    if _rank_index(new) > _rank_index(old):
        try:
            from game.domain.personal_system import note_appraisal_story

            note_appraisal_story(player, new)
        except Exception:
            pass
        return f"  …ตาคุณคมขึ้น — อ่านชั้นได้ลึกถึง 〔{new}〕"
    return None


def _matchups(reg: Any) -> List[Mapping[str, Any]]:
    if reg is not None:
        raw = getattr(reg, "matchups", None)
        if isinstance(raw, list) and raw:
            return list(raw)
    # fallback static (aligned with matchups.yaml spirit)
    return [
        {"attacker": "water", "defender": "fire", "mult": 1.4},
        {"attacker": "fire", "defender": "ice", "mult": 1.3},
        {"attacker": "lightning", "defender": "water", "mult": 1.3},
        {"attacker": "holy", "defender": "shadow", "mult": 1.35},
        {"attacker": "holy", "defender": "dark", "mult": 1.3},
        {"attacker": "fire", "defender": "nature", "mult": 1.25},
        {"attacker": "ice", "defender": "wind", "mult": 1.15},
        {"attacker": "earth", "defender": "wind", "mult": 1.15},
        {"attacker": "lightning", "defender": "earth", "mult": 1.2},
        {"attacker": "arcane", "defender": "physical", "mult": 1.15},
    ]


def _fusions(reg: Any) -> List[Mapping[str, Any]]:
    if reg is not None:
        cfg = getattr(reg, "fusions_cfg", None)
        if isinstance(cfg, dict):
            fus = cfg.get("fusions")
            if isinstance(fus, list) and fus:
                return list(fus)
        f = getattr(reg, "fusions", None)
        if isinstance(f, list) and f:
            return list(f)
    # minimal soft recipes (same spirit as fusions.yaml)
    return [
        {
            "sequence": ["water", "wind"],
            "result_elements": ["ice"],
            "flavor": "ไอน้ำเย็นจัดกลายเป็นน้ำแข็ง",
        },
        {
            "sequence": ["fire", "wind"],
            "result_elements": ["fire"],
            "flavor": "เปลวไฟลุกลามตามลม",
        },
        {
            "sequence": ["lightning", "water"],
            "result_elements": ["lightning"],
            "flavor": "กระแสไฟวิ่งในน้ำ",
        },
        {
            "sequence": ["lightning", "ice"],
            "result_elements": ["lightning", "ice"],
            "flavor": "สายฟ้าผ่าน้ำแข็ง",
        },
        {
            "sequence": ["holy", "fire"],
            "result_elements": ["holy", "fire"],
            "flavor": "แสงไฟชำระ",
        },
        {
            "sequence": ["shadow", "fire"],
            "result_elements": ["shadow", "fire"],
            "flavor": "เงาเผาไหม้",
        },
    ]


def soft_weakness_lines(
    mon: Mapping[str, Any],
    reg: Any = None,
    *,
    max_n: int = 3,
) -> List[str]:
    """SS: soft weakness bands from matchups — no mult numbers."""
    defs = [str(e).lower() for e in (mon.get("elements") or mon.get("tags") or []) if e]
    if not defs:
        defs = ["physical"]
    hits: List[Tuple[float, str, str]] = []
    for row in _matchups(reg):
        att = str(row.get("attacker") or "").lower()
        dfn = str(row.get("defender") or "").lower()
        mult = float(row.get("mult") or 1.0)
        if dfn in defs and mult >= 1.15:
            hits.append((mult, att, dfn))
    hits.sort(key=lambda t: -t[0])
    lines: List[str] = []
    seen = set()
    for mult, att, dfn in hits:
        if att in seen:
            continue
        seen.add(att)
        hint = _EL_HINT_WEAK.get(dfn, "มีช่องโหว่")
        if mult >= 1.3:
            feel = "ชัด"
        elif mult >= 1.2:
            feel = "พอเห็น"
        else:
            feel = "แผ่ว"
        lines.append(f" · แนว 〔{el_soft(att)}〕 ทะลุได้{feel} — {hint}")
        if len(lines) >= max_n:
            break
    if not lines:
        # generic soft
        for d in defs[:2]:
            lines.append(f" · ธาตุแกน 〔{el_soft(d)}〕 — {_EL_HINT_WEAK.get(d, 'ยังอ่านไม่ขาด')}")
    return lines


def soft_recipe_lines(
    mon: Mapping[str, Any],
    reg: Any = None,
    *,
    max_n: int = 2,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    SSS: soft combo recipes — element chain feel, no formula dump.
    Prefer fusions that produce elements strong vs monster.
    """
    rng = rng or random.Random(
        hash(str(mon.get("id") or mon.get("name") or "m")) % 10_000
    )
    defs = {str(e).lower() for e in (mon.get("elements") or []) if e} or {"physical"}
    weak_attackers = set()
    for row in _matchups(reg):
        if str(row.get("defender") or "").lower() in defs and float(row.get("mult") or 1) >= 1.15:
            weak_attackers.add(str(row.get("attacker") or "").lower())

    scored: List[Tuple[int, Mapping[str, Any]]] = []
    for fus in _fusions(reg):
        seq = [str(x).lower() for x in (fus.get("sequence") or [])]
        res = [str(x).lower() for x in (fus.get("result_elements") or [])]
        score = 0
        for r in res:
            if r in weak_attackers:
                score += 3
            if r not in defs:
                score += 1
        for s in seq:
            if s in weak_attackers:
                score += 2
        scored.append((score, fus))
    scored.sort(key=lambda t: (-t[0], rng.random()))
    lines: List[str] = []
    for score, fus in scored[: max(max_n, 1)]:
        seq = [el_soft(x) for x in (fus.get("sequence") or [])]
        res = [el_soft(x) for x in (fus.get("result_elements") or [])]
        chain = " + ".join(seq)
        if res:
            chain = f"{chain} → {'/'.join(res)}"
        flavor = str(fus.get("flavor") or "").strip()
        # soft: strip ! and numbers
        flavor = flavor.replace("!", "").strip()
        if flavor and len(flavor) > 36:
            flavor = flavor[:33] + "…"
        if flavor:
            lines.append(f" · สาย 〔{chain}〕 — {flavor}")
        else:
            lines.append(f" · สาย 〔{chain}〕 — ลองจังหวะนี้")
        if len(lines) >= max_n:
            break
    if not lines:
        lines.append(" · สาย 〔กาย → จังหวะ〕 — ยังไม่เห็นสูตรชัด ลองอ่านใหม่")
    return lines


def _enemy_grade_soft_band(mon: Mapping[str, Any], player: Mapping[str, Any]) -> str:
    """Hidden soft letter band for monster — not real player grade system."""
    lv = int(mon.get("level") or mon.get("lvl") or 1)
    plv = int(player.get("level") or 1)
    atk = int(mon.get("atk") or mon.get("attack") or 8)
    score = lv * 1.5 + atk * 0.4 + (4 if mon.get("boss") else 0) + (2 if mon.get("elite") else 0)
    # relative
    score += max(-4, min(6, (lv - plv) * 1.2))
    if score < 8:
        return "F"
    if score < 12:
        return "E"
    if score < 16:
        return "D"
    if score < 20:
        return "C"
    if score < 26:
        return "B"
    if score < 32:
        return "A"
    if score < 40:
        return "S"
    if score < 48:
        return "SS"
    return "SSS"


def _enemy_tier_soft(mon: Mapping[str, Any]) -> str:
    """Pseudo tier within band from hp fraction of 'typical'."""
    hp = int(mon.get("max_hp") or mon.get("hp") or 50)
    if mon.get("boss"):
        return "พิเศษ"
    if hp >= 120:
        return "ขั้นปลาย"
    if hp >= 70:
        return "ขั้นกลาง"
    if hp >= 40:
        return "ขั้นต้น"
    return "ขั้นต้น"


def appraise_self_lines(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    force_tier: Optional[str] = None,
) -> List[str]:
    """
    Self appraisal — deeper than V base when tier >= S.
    No raw numbers.
    """
    ensure_appraisal(player)
    tier = force_tier or resolve_appraisal_tier(player)
    lines: List[str] = [
        " อ่านชั้น · ตัวเอง",
        "---",
        f" ชั้นประเมิน 〔{tier if tier != TIER_BASE else 'พื้นฐาน'}〕",
    ]

    # Always soft presence
    try:
        from game.domain.stat_arch import soft_anima_label, soft_hp_condition

        lines.append(f" · ชีพ  {soft_hp_condition(player)}")
        lines.append(f" · {soft_anima_label(player)}")
    except Exception:
        lines.append(" · ชีพ/จิต — อ่านได้แผ่ว")

    if tier == TIER_BASE:
        lines.append(" · เกรดยังอ่านไม่ขาด — ไปวิหารหรือฝึกอ่านชั้น")
        lines.append("---")
        lines.append(" · ไม่โชว์ตัวเลข · soft อย่างเดียว")
        return lines

    # S+: grade surface
    try:
        from game.domain.stat_grades import format_grade_surface_lines, grade_revealed

        if grade_revealed(player):
            lines.append("---")
            lines.extend(
                format_grade_surface_lines(player, compact=False, include_header=True)
            )
        else:
            lines.append(" · เกรดยังปิด — วิหารปลดก่อนจะอ่านตัวอักษรชัด")
    except Exception:
        pass

    # SS+: soft self combat lean / weakness of build
    if _rank_index(tier) >= _rank_index(TIER_SS):
        lines.append("---")
        lines.append(" จุดที่ตัวเองเอียง (soft)")
        try:
            from game.domain.stat_grades import AXIS_KEYS, AXIS_LABEL_TH, axis_letter, axis_score

            scores = [(ax, axis_score(player, ax)) for ax in AXIS_KEYS]
            scores.sort(key=lambda t: -t[1])
            hi, lo = scores[0], scores[-1]
            lines.append(
                f" · เด่น  {AXIS_LABEL_TH[hi[0]]} 〔{axis_letter(player, hi[0])}〕"
            )
            lines.append(
                f" · บาง  {AXIS_LABEL_TH[lo[0]]} 〔{axis_letter(player, lo[0])}〕 — ระวังฝั่งนี้"
            )
        except Exception:
            lines.append(" · แนวทางยังพร่า — ลง P แล้วอ่านอีก")
        # faction / relic soft
        try:
            ba = str(player.get("_burden_active") or "")
            if ba == "crush":
                lines.append(" · เรลิกหนักมือ — อ่านศัตรูอาจสั่น")
            elif ba == "strain":
                lines.append(" · เรลิกร้อนมือ — สมาธิประเมินแผ่ว")
        except Exception:
            pass

    # SSS: soft “how you grow / fight” recipe for self
    if _rank_index(tier) >= _rank_index(TIER_SSS):
        lines.append("---")
        lines.append(" สายที่เหมาะกับคุณ (soft recipe)")
        try:
            from game.domain.stat_grades import AXIS_KEYS, AXIS_LABEL_TH, axis_score

            scores = sorted(
                ((ax, axis_score(player, ax)) for ax in AXIS_KEYS),
                key=lambda t: -t[1],
            )
            a0, a1 = scores[0][0], scores[1][0]
            recipes = {
                ("atk", "speed"): "กาย + จังหวะเร็ว — เปิดช่องแล้วทุบ",
                ("atk", "defense"): "ถึกแล้วสวน — อย่ารีบ",
                ("magic", "speed"): "เวทเร็ว — วางธาตุแล้วกด",
                ("magic", "defense"): "ม่านแล้วสาดเวท — คุมระยะ",
                ("defense", "magic"): "ตั้งมั่นแล้วปล่อยเวท",
                ("speed", "atk"): "ตัดจังหวะ — โจมตอนช่องว่าง",
            }
            key = (a0, a1)
            tip = recipes.get(key) or recipes.get((a1, a0))
            if not tip:
                tip = (
                    f"{AXIS_LABEL_TH[a0]} นำ · รอง {AXIS_LABEL_TH[a1]} — "
                    "อย่าฝืนแกนบาง"
                )
            lines.append(f" · {tip}")
            # damage pipeline soft mult feel
            try:
                from game.domain.damage_pipeline import grade_outbound_mult

                m, meta = grade_outbound_mult(player, "physical")
                if m >= 1.08:
                    lines.append(" · ตอนนี้แรงกายภาพไหลดี (soft)")
                elif m <= 0.95:
                    lines.append(" · แรงกายยังแผ่ว — เกรด/ลงแต้มช่วยได้")
                mm, _ = grade_outbound_mult(player, "arcane")
                if mm >= 1.08:
                    lines.append(" · เวทคมชัด (soft)")
            except Exception:
                pass
        except Exception:
            lines.append(" · ยังจับสายไม่ติด — ประเมินอีกหลังลง P")

    lines.append("---")
    lines.append(" · ไม่โชว์ตัวเลขดิบ · ชั้นประเมินยิ่งสูง ยิ่งอ่านลึก")
    return lines


def appraise_monster_lines(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    reg: Any = None,
    *,
    known: bool = False,
    force_tier: Optional[str] = None,
    paid: bool = False,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Enemy appraisal by tier.
    base: legacy soft assess
    S: + letter/tier band
    SS: + weakness
    SSS: + soft recipes
    """
    ensure_appraisal(player)
    tier = force_tier or resolve_appraisal_tier(player)
    # base block
    try:
        from game.domain.stat_arch import enemy_assess_lines

        lines = list(
            enemy_assess_lines(mon, player, known=known, reg=reg)
        )
        # retitle
        if lines and "ประเมินศัตรู" in lines[0]:
            lines[0] = f" อ่านชั้น · ศัตรู 〔{tier if tier != TIER_BASE else 'พื้นฐาน'}〕"
    except Exception:
        lines = [
            f" อ่านชั้น · ศัตรู 〔{tier}〕",
            "---",
            f" เป้า   {mon.get('name') or '???'}",
        ]

    if _rank_index(tier) >= _rank_index(TIER_S):
        letter = _enemy_grade_soft_band(mon, player)
        etier = _enemy_tier_soft(mon)
        lines.append("---")
        lines.append(" ชั้นพลังศัตรู (soft)")
        lines.append(f" · ระดับประมาณ 〔{letter}〕 · {etier}")
        # mark appraised for pipeline soft hint
        mid = str(mon.get("id") or mon.get("name") or "?")
        ap = dict(player.get("_appraised_targets") or {})
        ap[mid] = tier
        player["_appraised_targets"] = ap
        player["_last_appraise_mon"] = mid
        player["_last_appraise_tier"] = tier

    if _rank_index(tier) >= _rank_index(TIER_SS):
        lines.append("---")
        lines.append(" จุดอ่อน soft")
        lines.extend(soft_weakness_lines(mon, reg, max_n=3))

    if _rank_index(tier) >= _rank_index(TIER_SSS):
        lines.append("---")
        lines.append(" สายที่น่าลอง (soft recipe · ไม่ใช่สูตรเต็ม)")
        lines.extend(soft_recipe_lines(mon, reg, max_n=2, rng=rng))

    # anima / relic presence on clarity
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 65 and _rank_index(tier) >= _rank_index(TIER_S):
            lines.append(" · จิตวิญญาณมั่น — อ่านชัดขึ้น")
        elif a < 28:
            lines.append(" · จิตแผ่ว — ขอบบางของภาพพร่า")
    except Exception:
        pass

    lines.append("---")
    lines.append(" · ไม่โชว์ HP/ATK ดิบ · ไม่ dump สูตร")
    return lines


def run_appraisal(
    player: MutableMapping[str, Any],
    *,
    target: str = "self",
    mon: Optional[Mapping[str, Any]] = None,
    reg: Any = None,
    known: bool = False,
    paid: bool = True,
    rng: Optional[random.Random] = None,
) -> Tuple[List[str], Optional[str]]:
    """
    Full flow: spend → lines → growth note → soft alert.
    target: self | monster
    Returns (lines, growth_note).

    If paid path blocked (mana/cd): still show free soft read (no growth).
    """
    ensure_appraisal(player)
    sync_appraisal_tier(player)
    tier = resolve_appraisal_tier(player)

    # free base always ok; paid for S+ depth on skill path
    use_paid = paid and tier != TIER_BASE
    spent = False
    gate_note: Optional[str] = None
    if use_paid:
        ok, reason = spend_appraise(player, paid=True)
        if ok:
            spent = True
        else:
            gate_note = reason or " …สมาธิยังไม่พร้อม — อ่านแบบแผ่ว"
            # free soft still available
            use_paid = False
    else:
        spend_appraise(player, paid=False)

    if target == "monster" and mon is not None:
        # if unpaid gate, still show at least S surface if tier allows —
        # depth uses resolved tier for mystery (skill known) but no xp
        lines = appraise_monster_lines(
            player, mon, reg, known=known, paid=use_paid, rng=rng
        )
    else:
        lines = appraise_self_lines(player, reg)

    if gate_note:
        lines = [gate_note, "---"] + lines

    growth = None
    if spent:
        growth = note_appraisal_use(player, depth=tier)

    # soft alert
    try:
        from game.domain.alerts import emit_alert_lines

        alert_lines = emit_alert_lines(
            player,
            "appraisal.read",
            force=False,
            tier=tier if tier != TIER_BASE else "พื้นฐาน",
            target="ศัตรู" if target == "monster" else "ตัวเอง",
        )
        if alert_lines:
            lines = list(alert_lines) + ["---"] + lines
    except Exception:
        pass

    return lines, growth


def combat_appraise_hint(player: Mapping[str, Any], mon: Mapping[str, Any]) -> Optional[str]:
    """One-line soft for damage pipeline after appraise."""
    mid = str(mon.get("id") or mon.get("name") or "")
    ap = player.get("_appraised_targets") or {}
    tier = ap.get(mid) or player.get("_last_appraise_tier")
    if not tier or tier == TIER_BASE:
        return None
    if str(tier) == TIER_SSS:
        return " ·อ่านชั้นลึก — จังหวะชัด"
    if str(tier) == TIER_SS:
        return " ·เห็นช่องโหว่แผ่ว"
    if str(tier) == TIER_S:
        return " ·อ่านชั้นได้"
    return None


# ── WO-PARTY-6: companion soft appraisal ─────────────────────────────

_KIND_SOFT: Dict[str, str] = {
    "spirit": "เงาบาง · โทนรักษา/เวท",
    "beast": "ร่างดิบ · โทนพุ่งกาย",
    "heaven_beast": "แสงปีก · โทนคุ้ม/อุ่น",
    "hell_beast": "เงาแดง · โทนดุ/หนัก",
    "heaven_god": "รัศมี · โทนสูง/สง่างาม",
    "hell_god": "เงาโลหิต · โทนกด/คม",
    "player": "เงาผู้เดินทาง · โทนหลาก",
    "other": "รูปไม่ชัด · โทนคลุมเครือ",
}

_ROLE_SOFT: Dict[str, str] = {
    "spirit": "ในไฟต์มักเอนไปทางซ่อม/อุ้ม",
    "beast": "ในไฟต์มักเอนไปทางพุ่งปิด",
    "heaven_beast": "ในไฟต์มักเอนไปทางอุ้ม+กัดเบา",
    "hell_beast": "ในไฟต์มักเอนไปทางกดหนัก",
    "heaven_god": "ในไฟต์มักเอนไปทางรักษา/รัศมี",
    "hell_god": "ในไฟต์มักเอนไปทางปิดงานแรง",
    "player": "ในไฟต์มักเอนไปทางตามจังหวะคุณ",
    "other": "ในไฟต์ยังอ่านบทบาทไม่นิ่ง",
}


def format_companion_bond_line(rel: int, *, with_bar: bool = True) -> str:
    """
    WO-PARTY-6 UI: always say สัมพันธ์สหาย (not relic bond).
    Optional numeric for debug panels — combat can omit numbers.
    """
    from game.domain.party import relationship_bar, soft_relationship_label

    soft = soft_relationship_label(int(rel))
    if with_bar:
        return f"สัมพันธ์สหาย [{relationship_bar(int(rel))}] {soft}"
    return f"สัมพันธ์สหาย · {soft}"


def relic_vs_companion_bond_hint() -> str:
    """One-line disambiguation (soft)."""
    return " (สัมพันธ์สหาย ≠ เรโซแนนซ์เรลิก — คนละชั้น)"


def appraise_companion_soft(
    player: Mapping[str, Any],
    member: Mapping[str, Any],
    reg: Optional[Any] = None,
    *,
    show_numbers: bool = False,
) -> List[str]:
    """
    WO-PARTY-6: soft read of a party companion.

    Free (no mana) — depth scales with appraisal tier.
    Never dumps gift_likes tags, ATK numbers, or formulas.
    """
    from game.domain.party import get_relationship, kind_label

    name = str(member.get("name") or member.get("id") or "???")
    mid = str(member.get("id") or "")
    kind = str(member.get("kind") or "other")
    rel = get_relationship(player, mid, member)
    tier = resolve_appraisal_tier(player)

    kl = kind
    if reg is not None:
        try:
            kl = kind_label(reg, kind)
        except Exception:
            kl = kind

    lines: List[str] = [
        f"── อ่านสหาย · {name} ──",
        f" ชนิด soft: {kl}",
        f" {_KIND_SOFT.get(kind, _KIND_SOFT['other'])}",
        f" {format_companion_bond_line(rel, with_bar=True)}",
    ]
    if show_numbers:
        lines.append(f" (ชั้นอ่าน 〔{tier if tier != TIER_BASE else 'พื้นฐาน'}〕)")

    # S+: combat role lean
    if _rank_index(tier) >= _rank_index(TIER_S):
        lines.append(f" {_ROLE_SOFT.get(kind, _ROLE_SOFT['other'])}")
        rlab = str(member.get("rarity_label") or member.get("rarity") or "")
        if rlab:
            lines.append(f" ประกายชิ้น: 〔{rlab}〕 — อ่านได้แค่โทน")

    # SS+: gift temperament (never list tags)
    if _rank_index(tier) >= _rank_index(TIER_SS):
        if kind in ("spirit", "heaven_god", "heaven_beast"):
            lines.append(" ของขวัญ: ชอบโทนอุ่น/ศักดิ์ — หยาบๆ อาจเฉย")
        elif kind in ("hell_god", "hell_beast"):
            lines.append(" ของขวัญ: ชอบโทนมืด/คม — ของสว่างอาจไม่เข้า")
        elif kind == "beast":
            lines.append(" ของขวัญ: ชอบของกิน/วัตถุดิบดิบ — หรูอาจไม่โดน")
        else:
            lines.append(" ของขวัญ: ยังคลุม — ต้องยื่นแล้วดูปฏิกิริยา")

    # SSS: assist style + soft identity with player
    if _rank_index(tier) >= _rank_index(TIER_SSS):
        if rel >= 70:
            lines.append(" ซุ่ม: จังหวะเข้ากัน — ช่วยบ่อยเมื่อคุณลงมือ")
        elif rel >= 40:
            lines.append(" ซุ่ม: ยังรอดู — สนิทขึ้นจะถี่ขึ้น")
        else:
            lines.append(" ซุ่ม: ห่าง — อาจยืนดูมากกว่าพุ่ง")
        try:
            from game.domain.combat_identity import identity_outbound_mult

            _m, meta = identity_outbound_mult(player, mon=None, area_id="")
            if meta.get("bond") == "chorus":
                lines.append(" เรลิกของคุณร้องคอรัส — อย่าสับสนกับใจสหาย")
            elif meta.get("bond") in ("resonance", "tension"):
                lines.append(" เรโซแนนซ์เรลิกบนตัวคุณ ≠ สัมพันธ์สหายคนนี้")
        except Exception:
            pass
        lines.append(relic_vs_companion_bond_hint())

    lines.append(" (soft อ่าน — ไม่โชว์ตัวเลขพลัง/สูตร)")
    return lines


def format_party_appraisal_blurb(
    player: Mapping[str, Any],
    member: Mapping[str, Any],
    reg: Optional[Any] = None,
) -> str:
    """One-line panel blurb under companion name."""
    kind = str(member.get("kind") or "other")
    tier = resolve_appraisal_tier(player)
    base = _KIND_SOFT.get(kind, _KIND_SOFT["other"])
    # shorten for panel
    short = base.split("·")[0].strip() if "·" in base else base[:18]
    if _rank_index(tier) >= _rank_index(TIER_S):
        role = _ROLE_SOFT.get(kind, "")
        # take first clause
        if "มักเอนไปทาง" in role:
            role = role.split("มักเอนไปทาง")[-1].strip()
            return f"อ่าน: {short} · เอน{role}"
    return f"อ่าน: {short}"
