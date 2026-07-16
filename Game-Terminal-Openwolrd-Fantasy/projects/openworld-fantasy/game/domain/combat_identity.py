"""
WO-054 Soft Combat Identity + Weakness Lite.

Personal System (grade · appraisal · anima · bond · faction) feels in combat
via soft flavor + tiny mult — no formula dump, no full weakness recipes.

- Pre-fight identity lines (throttled)
- Hit flavor from identity / bond / faction
- Weakness Lite after Appraisal SS+ (soft hint + optional micro mult)
- Soft journal beats (rare)
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Identity soft mult clamp (on top of grade mult — keep tiny)
ID_OUT_CLAMP = (0.94, 1.08)
WEAK_LITE_CLAMP = (1.0, 1.06)  # only when element soft-matches appraised weak

# Throttle keys on player
_PRE_FIGHT_FLAG = "_combat_id_pre_fight_done"
_HIT_FLAVOR_CD = "_combat_id_hit_cd"
_WEAK_HINT_SHOWN = "_combat_id_weak_shown"


def ensure_combat_identity(player: MutableMapping[str, Any]) -> None:
    player.setdefault(_HIT_FLAVOR_CD, 0)
    player.setdefault("_combat_id_hits", 0)


def _tick(player: Mapping[str, Any]) -> int:
    return int(
        player.get("auto_ticks")
        or player.get("_combat_round")
        or player.get("time_units")
        or 0
    )


def _player_grade_letter(player: Mapping[str, Any]) -> str:
    if not player.get("grade_revealed"):
        return ""
    return str(player.get("player_grade") or "")


def _bond_mode(player: Mapping[str, Any]) -> str:
    return str(player.get("_relic_bond_mode") or "none")


def _bond_faction(player: Mapping[str, Any]) -> str:
    return str(
        player.get("_relic_bond_faction")
        or player.get("_relic_faction_lean")
        or ""
    )


def _faction_th(fid: str) -> str:
    return {
        "divine": "เทพ/สวรรค์",
        "infernal": "มาร/นรก",
        "ancient_echo": "เงาโบราณ",
    }.get(str(fid), str(fid or ""))


def _area_faction(area_id: str) -> str:
    try:
        from game.domain.world_relations import faction_for_area

        return str(faction_for_area(area_id) or "")
    except Exception:
        return ""


def _faction_score(player: Mapping[str, Any], fid: str) -> int:
    try:
        from game.domain.world_relations import get_faction_score

        return int(get_faction_score(player, fid))
    except Exception:
        return 42


def identity_outbound_mult(
    player: Mapping[str, Any],
    *,
    mon: Optional[Mapping[str, Any]] = None,
    area_id: str = "",
) -> Tuple[float, Dict[str, Any]]:
    """
    Tiny soft mult from bond / high grade / warm faction.
    Hidden — never show numbers.
    """
    meta: Dict[str, Any] = {}
    mult = 1.0
    g = _player_grade_letter(player)
    if g in ("S", "SS", "SSS"):
        mult *= 1.02 if g == "S" else (1.03 if g == "SS" else 1.035)
        meta["grade_edge"] = g
    elif g in ("F", "E") and player.get("grade_revealed"):
        mult *= 0.98
        meta["grade_edge"] = g

    mode = _bond_mode(player)
    if mode == "chorus":
        mult *= 1.035
        meta["bond"] = "chorus"
    elif mode == "resonance":
        mult *= 1.02
        meta["bond"] = "resonance"
    elif mode == "tension":
        mult *= 0.985
        meta["bond"] = "tension"

    # warm faction lean in matching area
    fac = _area_faction(area_id) or _bond_faction(player)
    if fac:
        sc = _faction_score(player, fac)
        if sc >= 65:
            mult *= 1.015
            meta["faction_warm"] = fac
        elif sc <= 28:
            mult *= 0.99
            meta["faction_cold"] = fac

    # anima soft already in pipeline presence — light extra if deep
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 72:
            mult *= 1.01
            meta["anima"] = "deep"
        elif a < 22:
            mult *= 0.985
            meta["anima"] = "thin"
    except Exception:
        pass

    mult = max(ID_OUT_CLAMP[0], min(ID_OUT_CLAMP[1], mult))
    meta["mult"] = mult
    return mult, meta


def pre_fight_identity_lines(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    reg: Any = None,
    *,
    area_id: str = "",
    rng: Optional[random.Random] = None,
    force: bool = False,
) -> List[str]:
    """
    Soft identity block at fight open — 1–3 lines, no spam per fight.
    """
    ensure_combat_identity(player)
    if player.get(_PRE_FIGHT_FLAG) and not force:
        return []
    player[_PRE_FIGHT_FLAG] = True
    rng = rng or random.Random(
        int(player.get("latent_seed") or 1) + int(player.get("level") or 1) * 3
    )

    lines: List[str] = []
    g = _player_grade_letter(player)
    if g in ("S", "SS", "SSS"):
        lines.append("  · พลังไหลเวียนแรง — ระดับคุณกดสนาม")
    elif g in ("A", "B"):
        lines.append("  · จิตวิญญาณมั่นคง — พร้อมรับจังหวะ")
    elif g in ("F", "E") and player.get("grade_revealed"):
        lines.append("  · แรงยังแผ่ว — ต้องอ่านจังหวะให้ดี")
    elif not player.get("grade_revealed") and rng.random() < 0.35:
        lines.append("  · ยังไม่รู้ระดับตัวเอง — ต่อสู้ด้วยความรู้สึก")

    mode = _bond_mode(player)
    fac = _bond_faction(player)
    fac_th = _faction_th(fac)
    if mode == "chorus":
        lines.append(
            f"  · คณะเรลิกส่งผ่าน{(' · '+fac_th) if fac_th else ''} — เรโซแนนซ์แน่น"
        )
    elif mode == "resonance":
        lines.append(
            f"  · เรลิกเรโซแนนซ์{(' · '+fac_th) if fac_th else ''} — สั่นพ้องในมือ"
        )
    elif mode == "tension":
        lines.append("  · เรลิกตึงเครียด — สายปะทะในมือ ระวังจังหวะ")

    # faction gaze in area
    area_fac = _area_faction(area_id or str(player.get("location") or ""))
    if area_fac:
        sc = _faction_score(player, area_fac)
        if sc >= 68:
            if area_fac == "divine":
                lines.append("  · สายตาเทพจับจ้อง — อากาศอุ่นผิดปกติ")
            elif area_fac == "infernal":
                lines.append("  · เงามารแผ่ซ่าน — โลกก้มหน้าให้คุณแผ่ว")
            else:
                lines.append("  · เงา echo พยัก — โลกจดจำคุณ")
        elif sc <= 28 and rng.random() < 0.7:
            if area_fac == "divine":
                lines.append("  · เทพหันหน้า — สนามเย็นลง")
            elif area_fac == "infernal":
                lines.append("  · หมอกนรกจาง — ไม่ต้อนรับ")
            else:
                lines.append("  · เงาโบราณจ้องแข็ง")

    # Weakness lite pre-hint if already appraised SS+
    weak = weakness_lite_hint_lines(player, mon, reg, pre_fight=True, rng=rng)
    if weak:
        lines.extend(weak[:1])

    # cap lines
    if len(lines) > 3:
        rng.shuffle(lines)
        lines = lines[:3]
    return lines


def clear_fight_identity_flags(player: MutableMapping[str, Any]) -> None:
    """Call at fight end / start cleanup."""
    player.pop(_PRE_FIGHT_FLAG, None)
    player.pop(_WEAK_HINT_SHOWN, None)
    player[_HIT_FLAVOR_CD] = 0


def hit_identity_flavor(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    *,
    dmg_class: str = "physical",
    rng: Optional[random.Random] = None,
) -> Optional[str]:
    """Rare soft suffix for hit log — throttled."""
    ensure_combat_identity(player)
    rng = rng or random.Random()
    player["_combat_id_hits"] = int(player.get("_combat_id_hits") or 0) + 1
    cd = int(player.get(_HIT_FLAVOR_CD) or 0)
    if cd > 0:
        player[_HIT_FLAVOR_CD] = cd - 1
        return None
    # ~25% after throttle clear
    if rng.random() > 0.28:
        return None

    pool: List[str] = []
    g = _player_grade_letter(player)
    dc = str(dmg_class or "physical").lower()
    is_mag = dc in ("arcane", "light", "magic")
    if g in ("S", "SS", "SSS"):
        pool.append(" ·พลังไหลเวียนแรง" if not is_mag else " ·เวทไหลคมจากระดับคุณ")
    if g in ("A", "B") and rng.random() < 0.5:
        pool.append(" ·จิตวิญญาณมั่นคง")

    mode = _bond_mode(player)
    if mode == "chorus":
        pool.append(" ·คณะเรลิกส่งผ่าน")
    elif mode == "resonance":
        pool.append(" ·เรลิกเรโซแนนซ์")
    elif mode == "tension" and rng.random() < 0.4:
        pool.append(" ·เรลิกสั่นตึง")

    fac = _area_faction(str(player.get("location") or ""))
    if fac == "divine" and _faction_score(player, fac) >= 65:
        pool.append(" ·สายตาเทพจับจ้อง")
    elif fac == "infernal" and _faction_score(player, fac) >= 65:
        pool.append(" ·เงามารแผ่ซ่าน")
    elif fac == "ancient_echo" and _faction_score(player, fac) >= 65:
        pool.append(" ·เงา echo รับรู้จังหวะ")

    if not pool:
        return None
    player[_HIT_FLAVOR_CD] = 2  # skip next 2 hit rolls
    return rng.choice(pool)


def _appraised_tier(player: Mapping[str, Any], mon: Mapping[str, Any]) -> str:
    mid = str(mon.get("id") or mon.get("name") or "")
    ap = player.get("_appraised_targets") or {}
    return str(ap.get(mid) or player.get("_last_appraise_tier") or "")


def _rank_ss_or_higher(tier: str) -> bool:
    t = str(tier or "").upper()
    return t in ("SS", "SSS")


def weakness_lite_elements(
    mon: Mapping[str, Any],
    reg: Any = None,
) -> List[str]:
    """
    Hidden: attacker elements that soft-beat mon elements.
    WO-Mon-2: catalog `weak_to` / `weakness_lite` first, then matchups.
    """
    out: List[str] = []
    # explicit catalog soft weaknesses
    for key in ("weak_to", "weakness_lite", "soft_weak"):
        raw = mon.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, (list, tuple)):
            for e in raw:
                el = str(e).lower().strip()
                if el and el not in out:
                    out.append(el)
                if len(out) >= 3:
                    return out
    try:
        from game.domain.appraisal import _matchups

        defs = [str(e).lower() for e in (mon.get("elements") or mon.get("tags") or []) if e]
        if not defs:
            defs = ["physical"]
        hits: List[Tuple[float, str]] = []
        for row in _matchups(reg):
            att = str(row.get("attacker") or "").lower()
            dfn = str(row.get("defender") or "").lower()
            mult = float(row.get("mult") or 1.0)
            if dfn in defs and mult >= 1.15:
                hits.append((mult, att))
        hits.sort(key=lambda t: -t[0])
        for _, att in hits:
            if att not in out:
                out.append(att)
            if len(out) >= 3:
                break
        return out
    except Exception:
        return out


def weakness_lite_hint_lines(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    reg: Any = None,
    *,
    pre_fight: bool = False,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Soft weakness hints — WO-Mon-2:
      S: one soft band · SS+: fuller · SSS: recipe feel
    No mult numbers.
    """
    tier = _appraised_tier(player, mon)
    t = str(tier or "").upper()
    # need at least S appraisal (playable earlier than SS-only)
    if t not in ("S", "SS", "SSS") and not _rank_ss_or_higher(tier):
        return []
    if pre_fight and player.get(_WEAK_HINT_SHOWN):
        return []

    weak_els = weakness_lite_elements(mon, reg)
    if not weak_els:
        return []

    try:
        from game.domain.appraisal import el_soft
    except Exception:

        def el_soft(x: str) -> str:
            return x

    rng = rng or random.Random(hash(str(mon.get("id") or "m")) % 99991)
    lines: List[str] = []
    # primary soft band
    primary = [el_soft(e) for e in weak_els[:2]]
    if t == "S":
        # one soft line only
        if primary:
            lines.append(f"  · ใบ้ soft: แนว 〔{primary[0]}〕 อาจทะลุได้แผ่ว")
        if pre_fight:
            player[_WEAK_HINT_SHOWN] = True  # type: ignore[index]
        return lines[:1]
    if len(primary) >= 2:
        lines.append(
            f"  · ใบ้ soft: 〔{primary[0]}+{primary[1]}〕 อาจทิ่มจุดอ่อน"
        )
    elif primary:
        lines.append(f"  · ใบ้ soft: แนว 〔{primary[0]}〕 ทะลุได้แผ่ว")

    # lite recipe feel (not full fusion dump) — SS+ only, SSS can add chain
    if str(tier).upper() == "SSS" and len(weak_els) >= 1:
        # classic soft chains matching weak
        recipes = [
            (["water", "wind"], "น้ำ+ลม → หนาว/ช้าลง"),
            (["lightning", "water"], "สายฟ้า+น้ำ → กระแสวิ่ง"),
            (["fire", "wind"], "ไฟ+ลม → ลุกลาม"),
            (["holy", "fire"], "แสง+ไฟ → ชำระ"),
            (["lightning", "ice"], "สายฟ้า+น้ำแข็ง → แตกกระจาย"),
        ]
        for seq, text in recipes:
            if any(s in weak_els or s == weak_els[0] for s in seq):
                # show if overlap with weak or mon is weak to result-ish
                if seq[0] in weak_els or seq[-1] in weak_els or weak_els[0] in (
                    "fire",
                    "water",
                    "ice",
                    "shadow",
                    "dark",
                ):
                    lines.append(f"  · {text}")
                    break
        if len(lines) < 2 and rng.random() < 0.5:
            lines.append("  · จังหวะธาตุซ้อนอาจเปิดช่อง (soft · ไม่ใช่สูตรเต็ม)")

    # anima/faction clarity
    try:
        from game.domain.stat_arch import anima_value

        if float(anima_value(player)) >= 60 and lines:
            lines[0] = lines[0] + " · จิตอ่านชัดขึ้น"
    except Exception:
        pass

    if pre_fight:
        player[_WEAK_HINT_SHOWN] = True  # type: ignore[index]
    return lines[:2]


def weakness_lite_mult(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    skill_elements: Optional[Sequence[str]],
    reg: Any = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Micro mult when mon appraised S+ and attack hits soft-weak elements.
    S: +3% · SS+: up to +6%. Not full recipes.
    """
    meta: Dict[str, Any] = {"active": False}
    tier = _appraised_tier(player, mon)
    t = str(tier or "").upper()
    if t not in ("S", "SS", "SSS") and not _rank_ss_or_higher(tier):
        return 1.0, meta
    weak = set(weakness_lite_elements(mon, reg))
    if not weak:
        return 1.0, meta
    atk_els = {str(e).lower() for e in (skill_elements or []) if e}
    if not atk_els:
        return 1.0, meta
    hit = atk_els & weak
    if not hit:
        return 1.0, meta
    # S softer than SS+
    if t == "S":
        meta["active"] = True
        meta["hit"] = list(hit)
        meta["tier"] = "S"
        return 1.03, meta
    # micro: 1.03 base, +0.015 if 2+ elements
    m = 1.03 + (0.015 if len(hit) >= 2 else 0.0)
    if str(tier).upper() == "SSS":
        m += 0.01
    m = max(WEAK_LITE_CLAMP[0], min(WEAK_LITE_CLAMP[1], m))
    meta["active"] = True
    meta["hit_elements"] = list(hit)
    meta["mult"] = m
    return m, meta


def apply_identity_to_outbound(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    *,
    dmg_class: str,
    skill_elements: Optional[Sequence[str]],
    area_id: str,
    reg: Any,
    rng: random.Random,
    raw_amount: int,
) -> Tuple[int, List[str], Dict[str, Any]]:
    """
    Combine identity mult + weakness lite + flavors.
    Returns (new_amount, soft_notes, meta).
    """
    ensure_combat_identity(player)
    notes: List[str] = []
    meta: Dict[str, Any] = {}

    id_m, id_meta = identity_outbound_mult(player, mon=mon, area_id=area_id)
    meta["identity"] = id_meta
    w_m, w_meta = weakness_lite_mult(player, mon, skill_elements, reg)
    meta["weakness_lite"] = w_meta

    total = float(id_m) * float(w_m)
    total = max(0.90, min(1.12, total))
    final = max(1, int(round(int(raw_amount) * total)))
    meta["total_identity_mult"] = total

    # hit flavor
    fl = hit_identity_flavor(player, mon, dmg_class=dmg_class, rng=rng)
    if fl:
        notes.append(fl)
    # weakness soft on hit when active (rare)
    if w_meta.get("active") and rng.random() < 0.35:
        notes.append(" ·ทิ่มช่องที่อ่านไว้")

    return final, notes, meta


def on_fight_end_identity(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    *,
    victory: bool = True,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """Rare personal journal + clear flags."""
    notes: List[str] = []
    clear_fight_identity_flags(player)
    if not victory:
        return notes
    rng = rng or random.Random()
    # journal rare
    try:
        from game.domain.personal_system import append_journal

        if mon.get("boss") or mon.get("elite"):
            append_journal(
                player,
                "ชนะศัตรูหนัก — ตัวตนในไฟต์ชัดขึ้น",
                kind="milestone",
                unique_key=f"combat_win_{mon.get('id') or mon.get('name')}",
            )
        elif rng.random() < 0.12 and player.get("grade_revealed"):
            append_journal(
                player,
                "ไฟต์หนึ่งจบ — เกรด/เรลิกส่งแรงแผ่ว",
                kind="growth",
                force=True,
            )
    except Exception:
        pass
    return notes


def format_identity_debug_soft(player: Mapping[str, Any]) -> List[str]:
    """Soft-only summary for tests / god tools — still no raw mult dump to players."""
    g = _player_grade_letter(player) or "ปิด"
    mode = _bond_mode(player)
    return [
        f" · combat identity · เกรด〔{g}〕 · bond〔{mode}〕",
    ]
