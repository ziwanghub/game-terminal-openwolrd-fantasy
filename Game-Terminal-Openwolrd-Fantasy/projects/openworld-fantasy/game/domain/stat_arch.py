"""
WO-035 Stat & Relationship Architecture helpers.

3 layers: Needs (L1) → Core facets Physical/Magical/Spirit (L2) → Derivatives (L3).
Spirit core value is stored as **anima** (not morale, not relic.spirit_* alerts).

Soft DNA: no formula dump in player UI; soft bands only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

# ── locked names (see docs/STAT_ARCHITECTURE.md) ─────────────────────────

FACET_PHYSICAL = "physical"
FACET_MAGICAL = "magical"
FACET_SPIRIT = "spirit"  # facet id only — value lives in player["anima"]

ANIMA_KEY = "anima"  # 0–100 soft internal; never show raw in normal UI

# UI: hide raw invest counts on P / status when True
SOFT_INVEST_UI = True


def ensure_stat_arch(player: MutableMapping[str, Any]) -> None:
    """Init anima + world_relations axes."""
    if player.get(ANIMA_KEY) is None:
        # soft start from morale + mind hints (not a copy of morale)
        try:
            from game.domain.needs import get_needs, ensure_needs

            ensure_needs(player)
            mor = int(get_needs(player).get("morale") or 50)
        except Exception:
            mor = 50
        mind = float(player.get("mind_growth") or 0)
        focus = float(player.get("focus_latent") or 0)
        base = 40.0 + (mor - 50) * 0.15 + min(12.0, mind * 0.4) + min(8.0, focus * 0.3)
        player[ANIMA_KEY] = max(5.0, min(95.0, base))
    player.setdefault("world_relations", {})  # "axis:id" -> 0..100
    player.setdefault("_self_assess_tick", -999)


# ── Layer 2 soft scores (derived, not new invest rows) ───────────────────

def physical_score(player: Mapping[str, Any]) -> float:
    """Hidden soft 0–100-ish from existing powers / alloc."""
    alloc = player.get("stats_alloc") or {}
    atk = float(player.get("power_atk") or 0) + int(alloc.get("atk") or 0) * 1.2
    de = float(player.get("power_def") or 0) + int(alloc.get("defense") or 0) * 1.1
    spd = float(player.get("power_spd") or 0) + int(alloc.get("speed") or 0) * 1.0
    raw = atk * 0.4 + de * 0.35 + spd * 0.25
    return max(0.0, min(100.0, raw * 1.8))


def magical_score(player: Mapping[str, Any]) -> float:
    alloc = player.get("stats_alloc") or {}
    mag = float(player.get("power_mag") or 0) + int(alloc.get("magic") or 0) * 1.2
    mdef = float(player.get("power_mdef") or 0)
    mp = float(player.get("max_mana") or 50) / 10.0
    raw = mag * 0.5 + mdef * 0.3 + mp * 0.2
    return max(0.0, min(100.0, raw * 1.7))


def anima_value(player: Mapping[str, Any]) -> float:
    try:
        return float(player.get(ANIMA_KEY) or 40.0)
    except Exception:
        return 40.0


def recompute_anima(player: MutableMapping[str, Any], reg: Any = None) -> float:
    """
    Soft recompute anima from mind / focus / intel / blessings — not morale copy.
    Call after level-up, library, rest-ish.
    """
    ensure_stat_arch(player)
    cur = anima_value(player)
    mind = float(player.get("mind_growth") or 0)
    focus = float(player.get("focus_latent") or 0)
    intel_p = float(player.get("power_intel") or 3)
    learn = int(player.get("learn_points") or 0)
    target = 38.0 + min(20.0, mind * 0.9) + min(15.0, focus * 1.1) + min(12.0, intel_p * 0.8)
    target += min(8.0, learn * 0.35)
    if "quiet_mind" in (player.get("blessing_flags") or []) or "grace_mind" in (
        player.get("blessing_flags") or []
    ):
        target += 4.0
    # blend toward target (soft, not snap)
    nxt = cur * 0.72 + target * 0.28
    player[ANIMA_KEY] = max(5.0, min(99.0, nxt))
    return float(player[ANIMA_KEY])


def soft_facet_label(score: float) -> str:
    s = float(score)
    if s >= 75:
        return "โดดเด่น"
    if s >= 55:
        return "มั่น"
    if s >= 35:
        return "พอใช้"
    if s >= 18:
        return "แผ่ว"
    return "อ่อน"


def soft_anima_label(player: Mapping[str, Any]) -> str:
    a = anima_value(player)
    if a >= 75:
        return "จิตวิญญาณลึก"
    if a >= 55:
        return "จิตวิญญาณมั่น"
    if a >= 35:
        return "จิตวิญญาณพอใช้"
    if a >= 18:
        return "จิตวิญญาณแผ่ว"
    return "จิตวิญญาณพร่า"


def soft_hp_condition(player: Mapping[str, Any]) -> str:
    """Phase 1: soft HP wording (optional alongside bar)."""
    hp = int(player.get("hp") or 0)
    mx = max(1, int(player.get("max_hp") or 1))
    r = hp / mx
    if r >= 0.85:
        return "ร่างกายแข็งแรง"
    if r >= 0.60:
        return "บาดเจ็บเล็กน้อย"
    if r >= 0.35:
        return "เจ็บหนัก"
    if r >= 0.15:
        return "อาการสาหัส"
    if r > 0:
        return "ใกล้ตาย"
    return "สลบ"


# ── Needs soft resist from core (phase 2 lite) ───────────────────────────

def core_needs_soft_mults(player: Mapping[str, Any]) -> Dict[str, float]:
    """
    Hidden mults for needs tick / care (caller optional).
    Physical → less fatigue gain; Magical unused here; Anima → morale drain resist.
    """
    ensure_stat_arch(player)  # type: ignore[arg-type]
    phy = physical_score(player) / 100.0
    mag = magical_score(player) / 100.0
    ani = anima_value(player) / 100.0
    return {
        # <1 = slower bad gain / less drain
        "fatigue_gain_mult": max(0.82, 1.0 - phy * 0.14),
        "hunger_gain_mult": max(0.88, 1.0 - phy * 0.08),
        "morale_drain_mult": max(0.75, 1.0 - ani * 0.22),
        "intel_recover_mult": 1.0 + mag * 0.12,
    }


def apply_anima_to_burden_resist(player: Mapping[str, Any]) -> float:
    """0..0.2 extra soft resist chance for relic aura (caller adds)."""
    return min(0.20, max(0.0, (anima_value(player) - 40.0) / 100.0 * 0.35))


def anima_band(player: Mapping[str, Any]) -> str:
    """deep | steady | thin | frail — for soft moments."""
    a = anima_value(player)
    if a >= 70:
        return "deep"
    if a >= 45:
        return "steady"
    if a >= 25:
        return "thin"
    return "frail"


# ── WO-037 Anima Presence (soft moments) ─────────────────────────────────

# reason -> preferred alert code + small anima nudge (hidden)
_ANIMA_MOMENT_META: Dict[str, Dict[str, Any]] = {
    "relic_equip": {
        "code": "anima.relic_touch",
        "nudge": 0.35,
        "throttle": 2,
    },
    "chamber_spar": {
        "code": "anima.chamber_echo",
        "nudge": 0.55,
        "throttle": 1,
    },
    "library": {
        "code": "anima.learn_glow",
        "nudge": 0.8,
        "throttle": 3,
    },
    "learn_skill": {
        "code": "anima.learn_glow",
        "nudge": 0.65,
        "throttle": 2,
    },
    "magic_combo": {
        "code": "anima.mana_flow",
        "nudge": 0.4,
        "throttle": 2,
    },
    "thin_warn": {
        "code": "anima.thin",
        "nudge": 0.0,
        "throttle": 5,
    },
    "deep_calm": {
        "code": "anima.deep",
        "nudge": 0.0,
        "throttle": 6,
    },
}


def _nudge_anima(player: MutableMapping[str, Any], delta: float) -> None:
    if abs(delta) < 0.01:
        return
    ensure_stat_arch(player)
    cur = anima_value(player)
    player[ANIMA_KEY] = max(5.0, min(99.0, cur + float(delta)))


def anima_presence_lines(
    player: MutableMapping[str, Any],
    reason: str,
    *,
    force: bool = False,
    item: str = "",
    reg: Any = None,
) -> List[str]:
    """
    Soft moment when Anima is felt — Soft Alert bus + optional nudge.
    reason: relic_equip | chamber_spar | library | learn_skill | magic_combo | thin_warn | deep_calm
    Never shows raw anima number.
    """
    ensure_stat_arch(player)
    meta = _ANIMA_MOMENT_META.get(str(reason) or "")
    if not meta:
        return []
    code = str(meta["code"])
    # auto-pick thin/deep presence on low/high when asked generically
    band = anima_band(player)
    if reason == "relic_equip" and band == "frail":
        code = "anima.thin"
    elif reason == "relic_equip" and band == "deep":
        code = "anima.deep"

    try:
        from game.domain.alerts import emit_alert_lines

        lines = emit_alert_lines(
            player,
            code,
            force=force,
            item=item or "เรลิก",
            band=band,
        )
    except Exception:
        lines = [f"  · จิตวิญญาณสั่นไหว… ({reason})"]

    if lines:
        _nudge_anima(player, float(meta.get("nudge") or 0))
        # mark that player has "felt" anima without needing V first
        player["_anima_presence_felt"] = True
        if band in ("deep", "steady"):
            player["_self_assess_done"] = True  # allow soft status line
        # WO-052: anima moment can soft-fuel auto growth (Lv30+)
        try:
            from game.domain.auto_growth import is_auto_growth_mode, pulse_auto_growth

            if is_auto_growth_mode(player) and float(meta.get("nudge") or 0) > 0:
                extra = pulse_auto_growth(
                    player, "anima", reg=reg, magnitude=0.55
                )
                if extra:
                    lines = list(lines) + extra[:2]
        except Exception:
            pass
        # WO-053: personal journal anima beat
        try:
            from game.domain.personal_system import note_anima_story

            note_anima_story(player, str(reason or ""))
        except Exception:
            pass
    return lines


def anima_morale_drain_factor(player: Mapping[str, Any]) -> float:
    """
    WO-037.2: mult on negative morale deltas.
    High anima → slower drain; low → faster (soft).
    """
    a = anima_value(player)
    if a >= 70:
        return 0.72
    if a >= 55:
        return 0.85
    if a >= 40:
        return 0.95
    if a >= 25:
        return 1.08
    return 1.18


def anima_mental_resist_bonus(player: Mapping[str, Any]) -> float:
    """Extra resist chance vs mental/ailment statuses (0..0.18)."""
    a = anima_value(player)
    if a >= 70:
        return 0.16
    if a >= 50:
        return 0.10
    if a >= 35:
        return 0.04
    return 0.0


def anima_skill_soft_fail_chance(player: Mapping[str, Any]) -> float:
    """
    Soft fail chance for focus/magic skills when anima frail + morale low.
    Auto should rarely hit this (only frail).
    """
    a = anima_value(player)
    if a >= 35:
        return 0.0
    try:
        from game.domain.needs import get_needs

        mor = int(get_needs(player).get("morale") or 50)  # type: ignore[arg-type]
    except Exception:
        mor = 50
    if mor >= 40:
        return 0.04 if a < 25 else 0.02
    if mor >= 20:
        return 0.10 if a < 25 else 0.06
    return 0.16 if a < 25 else 0.10


def try_anima_skill_soft_fail(
    player: MutableMapping[str, Any],
    *,
    skill_name: str = "",
    rng: Any = None,
) -> Tuple[bool, List[str]]:
    """
    Returns (failed, lines). On fail: skill fizzles soft, no crash.
    """
    import random as _rnd

    rng = rng or _rnd
    ch = anima_skill_soft_fail_chance(player)
    if ch <= 0:
        return False, []
    roll = rng.random() if hasattr(rng, "random") else _rnd.random()
    if roll >= ch:
        return False, []
    lines: List[str] = []
    try:
        from game.domain.alerts import emit_alert_lines

        lines = emit_alert_lines(
            player,
            "anima.skill_waver",
            force=True,
            item=skill_name or "สกิล",
        )
    except Exception:
        lines = ["  …จิตวิญญาณสั่น — ท่าหลุดจังหวะเล็กน้อย"]
    return True, lines


# ── Self assess (phase 1) ────────────────────────────────────────────────

def self_assess_lines(
    player: MutableMapping[str, Any],
    *,
    force: bool = False,
    reg: Any = None,
) -> List[str]:
    """
    Soft self-read of core facets — no power numbers.
    Throttle by auto_ticks unless force.
    WO-036: clearer sections · Anima ≠ ขวัญ.
    """
    ensure_stat_arch(player)
    recompute_anima(player, reg)
    tick = int(player.get("auto_ticks") or player.get("time_units") or 0)
    last = int(player.get("_self_assess_tick") or -999)
    if not force and tick - last < 2 and last >= 0:
        return [
            " ประเมินตัวเอง",
            "---",
            "  …เพิ่งสำรวจใจไป — รอสักครู่แล้วค่อยประเมินอีกครั้ง",
        ]

    player["_self_assess_tick"] = tick
    player["_self_assess_done"] = True
    phy = physical_score(player)
    mag = magical_score(player)
    lines = [
        " ประเมินตัวเอง",
        "---",
        " ① ชีพ",
        f"  · {soft_hp_condition(player)}",
        "---",
        " ② แกนพลัง (soft · ไม่ใช่ตัวเลข)",
        f"  · กายภาพ   〔{soft_facet_label(phy)}〕  ← โจม/กัน/เร็วที่ลง P",
        f"  · เวทมนตร์  〔{soft_facet_label(mag)}〕  ← เวท/มานา",
        f"  · {soft_anima_label(player)}  ← ลึกในใจ · โตจากเรียน/เรลิก",
        "---",
        " ③ กายใจ (Needs · คนละชั้นกับจิตวิญญาณ)",
    ]
    try:
        from game.domain.needs import get_needs, soft_label, ensure_needs

        ensure_needs(player)
        n = get_needs(player)
        lines.append(
            f"  · หิว  {soft_label('hunger', int(n['hunger']))}"
        )
        lines.append(
            f"  · ล้า  {soft_label('fatigue', int(n['fatigue']))}"
        )
        lines.append(
            f"  · ขวัญ {soft_label('morale', int(n['morale']))}  ← กำลังใจวันนี้"
        )
    except Exception:
        lines.append("  · (กายใจยังไม่อ่านได้)")
    lines.append("---")
    lines.append(" ใบ้แยกชั้น")
    lines.append("  · ขวัญ = อารมณ์/กำลังใจตอนนี้ (กินพักได้)")
    lines.append("  · จิตวิญญาณ = แกนลึก ซ่อน · ไม่ใช่แต้ม P")
    try:
        ba = str(player.get("_burden_active") or "")
        if ba in ("strain", "crush"):
            lab = "ร้อนมือ" if ba == "strain" else "หนักเกินตัว"
            lines.append(f"  · ภาระเรลิก〔{lab}〕กดขวัญ — ไม่ลดจิตวิญญาณตรง ๆ")
    except Exception:
        pass
    # WO-048/049: grade surface (letter + tier soft after temple)
    try:
        from game.domain.stat_grades import grade_self_assess_extra

        lines.append("---")
        lines.append(" ④ เกรด (soft surface · หลังปลดวิหาร)")
        for ln in grade_self_assess_extra(player):
            lines.append(ln if str(ln).startswith(" ") else f" {ln}")
    except Exception:
        pass
    # WO-038: world relations soft block
    try:
        from game.domain.world_relations import format_world_relations_soft

        lines.append("---")
        lines.extend(format_world_relations_soft(player))
    except Exception:
        pass
    lines.append("---")
    lines.append(" ลงแต้ม P แล้วรู้สึก “หนาขึ้น” · ไม่โชว์พลังดิบ")
    return lines


def enemy_assess_lines(
    mon: Mapping[str, Any],
    player: Optional[Mapping[str, Any]] = None,
    *,
    known: bool = False,
    reg: Any = None,
) -> List[str]:
    """
    WO-036.3: soft enemy read — bands only, no exact stats.
    """
    name = str(mon.get("name") or "???")
    if not known and not mon.get("boss"):
        name = "???"
    mhp = max(1, int(mon.get("max_hp") or mon.get("hp") or 1))
    hp = max(0, int(mon.get("hp") or mhp))
    hr = hp / mhp
    if hr >= 0.85:
        cond = "ยังเต็มแรง"
    elif hr >= 0.55:
        cond = "เริ่มถูกรอย"
    elif hr >= 0.30:
        cond = "บาดเจ็บชัด"
    elif hr > 0:
        cond = "ใกล้หมดแรง"
    else:
        cond = "ล้มแล้ว"

    lv = int(mon.get("level") or mon.get("lvl") or 1)
    plv = int((player or {}).get("level") or 1) if player else 1
    gap = lv - plv
    if gap >= 4:
        threat = "อันตรายมาก"
    elif gap >= 2:
        threat = "แข็งกว่าเรา"
    elif gap >= -1:
        threat = "คู่ควร"
    elif gap >= -3:
        threat = "อ่อนกว่าเรา"
    else:
        threat = "แผ่วมาก"

    atk = int(mon.get("atk") or mon.get("attack") or 0)
    # soft offense band from absolute atk (hidden thresholds)
    if atk >= 28:
        off = "คมกริบ"
    elif atk >= 16:
        off = "คม"
    elif atk >= 8:
        off = "พอใช้"
    elif atk > 0:
        off = "แผ่ว"
    else:
        off = "ไม่แน่ชัด"

    # Proportional soft panel sections (WO combat UI)
    lines = [
        " ประเมินศัตรู (soft)",
        "---",
        " เป้า / สภาพ",
        f"  ชื่อ    {name}",
        f"  อาการ  {cond}",
        f"  ภัย    〔{threat}〕    คม  〔{off}〕",
    ]
    notes: List[str] = []
    if mon.get("boss"):
        notes.append("บอส — อย่าประมาท · ดูจังหวะ")
    if mon.get("rarity"):
        notes.append(f"เรืองรองแปลก ๆ ({mon.get('rarity')})")
    # player anima soft: high anima slightly clearer read
    if player is not None:
        try:
            a = anima_value(player)
            if a >= 60:
                notes.append("จิตวิญญาณมั่น — อ่านเจตนาชัดขึ้นเล็กน้อย")
            elif a < 30:
                notes.append("จิตวิญญาณแผ่ว — อ่านศัตรูพร่า")
        except Exception:
            pass
    if notes:
        lines.append("---")
        lines.append(" ร่องรอย")
        for n in notes:
            lines.append(f"  · {n}")
    return lines


# ── Soft invest UI (phase 1) ─────────────────────────────────────────────

def format_soft_invest_lines(player: Mapping[str, Any]) -> List[str]:
    """WO-048/049: Soft P + grade letters/tiers after temple (panel already surfaces)."""
    try:
        from game.domain.stat_grades import format_grade_p_panel

        lines = list(format_grade_p_panel(player))
    except Exception:
        from game.domain.progression import ALLOCATE_KEYS, STAT_LABELS

        pts = int(player.get("stat_points") or 0)
        lines = [
            " แจกแต้มสถานะ",
            "---",
            f" แต้มที่ใช้ได้  {pts}",
            "---",
            " ลงแต้มแล้ว “รู้สึก” หนาขึ้น — ไม่โชว์ตัวเลขพลัง",
        ]
        for i, k in enumerate(ALLOCATE_KEYS, 1):
            lines.append(f"  {i}. {STAT_LABELS[k]}")
    lines.append("---")
    lines.append("  · จิตวิญญาณไม่ได้อยู่ในเมนูนี้ (กด V)")
    lines.append("  · โชค = ดวงแผ่ว · แจกตรงไม่ได้")
    try:
        ensure_stat_arch(player)  # type: ignore[arg-type]
        lines.append("---")
        lines.append(
            f"  กาย 〔{soft_facet_label(physical_score(player))}〕 · "
            f"เวท 〔{soft_facet_label(magical_score(player))}〕 · "
            f"{soft_anima_label(player)}"
        )
    except Exception:
        pass
    return lines


def format_soft_invest_menu_lines(player: Mapping[str, Any]) -> List[str]:
    try:
        from game.domain.stat_grades import format_grade_p_menu

        return format_grade_p_menu(player)
    except Exception:
        from game.domain.progression import ALLOCATE_KEYS, STAT_LABELS

        nkeys = len(ALLOCATE_KEYS)
        lines = [" ลงทุนที่ (soft)", "---"]
        for i, k in enumerate(ALLOCATE_KEYS, 1):
            lines.append(f"  {i}  {STAT_LABELS[k]:<8}")
        lines.append("---")
        lines.append("  0  กลับ")
        lines.append(f" พิมพ์ 1–{nkeys} แล้วใส่จำนวนแต้ม")
        return lines


# ── World relations (phase 3 lite) ───────────────────────────────────────

def relation_key(axis: str, actor_id: str) -> str:
    return f"{str(axis).strip().lower()}:{str(actor_id).strip()}"


def get_world_relation(
    player: Mapping[str, Any],
    axis: str,
    actor_id: str,
    *,
    default: int = 40,
) -> int:
    wr = player.get("world_relations") or {}
    k = relation_key(axis, actor_id)
    if k in wr:
        return max(0, min(100, int(wr[k])))
    # party bonds stay source of truth for companions
    if axis in ("companion", "party"):
        try:
            from game.domain.party import get_relationship

            return int(get_relationship(player, actor_id))
        except Exception:
            pass
    return max(0, min(100, int(default)))


def set_world_relation(
    player: MutableMapping[str, Any],
    axis: str,
    actor_id: str,
    value: int,
) -> int:
    ensure_stat_arch(player)
    wr = dict(player.get("world_relations") or {})
    v = max(0, min(100, int(value)))
    wr[relation_key(axis, actor_id)] = v
    player["world_relations"] = wr
    if axis in ("companion", "party"):
        try:
            from game.domain.party import set_relationship

            set_relationship(player, actor_id, v)
        except Exception:
            pass
    return v


def adjust_world_relation(
    player: MutableMapping[str, Any],
    axis: str,
    actor_id: str,
    delta: float,
) -> int:
    cur = get_world_relation(player, axis, actor_id)
    return set_world_relation(player, axis, actor_id, int(round(cur + delta)))


def soft_relation_label(score: int) -> str:
    s = int(score)
    if s >= 85:
        return "สนิทสนม"
    if s >= 65:
        return "ชอบ"
    if s >= 45:
        return "เป็นกลาง"
    if s >= 25:
        return "ไม่ชอบ"
    return "ศัตรู"


# Axes reserved for expansion (npc / divine / infernal)
RELATION_AXES = ("companion", "npc", "divine", "infernal")
