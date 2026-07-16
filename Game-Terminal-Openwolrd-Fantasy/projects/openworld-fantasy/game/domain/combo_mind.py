"""
Combo Mind (CM1–CM2): hidden focus + intellect band + mag mana relief.

- focus_latent (hidden): more combo steps; slight mana tax when high
- mind_intellect (shown as soft band only): more steps + mana tax
- power_mag (hidden): reduces combo mana multiplier (capped)

Formulas never exposed as raw % in UI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry


def _combo_mind_cfg(reg: Optional[DataRegistry]) -> Dict[str, Any]:
    raw = {}
    if reg is not None:
        raw = dict((getattr(reg, "fusions_cfg", None) or {}).get("combo_mind") or {})
    # defaults match COMBO_MIND_VISION + CM5 balance
    return {
        "hard_cap": int(raw.get("hard_cap") or 6),
        "focus_steps": list(raw.get("focus_steps") or [[0, 0], [8, 1], [20, 2]]),
        "intellect_steps": list(raw.get("intellect_steps") or [[0, 0], [6, 1], [15, 2]]),
        "intellect_mana_tax": list(
            raw.get("intellect_mana_tax") or [[0, 1.0], [6, 1.06], [15, 1.14], [25, 1.22]]
        ),
        "focus_mana_tax": list(
            raw.get("focus_mana_tax") or [[0, 1.0], [12, 1.04], [24, 1.08]]
        ),
        "mag_mana_relief": list(
            raw.get("mag_mana_relief") or [[0, 1.0], [8, 0.96], [16, 0.90], [28, 0.82]]
        ),
        "relief_floor": float(raw.get("relief_floor") or 0.75),
        "mult_ceil": float(raw.get("mult_ceil") or 2.8),
        "focus_base": float(raw.get("focus_base") or 5.0),
        "focus_ceil": float(raw.get("focus_ceil") or 40.0),
        # CM5: soft ceiling by level — early game cannot bank endless focus
        "focus_ceil_by_level": list(
            raw.get("focus_ceil_by_level")
            or [
                [9, 14.0],
                [19, 22.0],
                [34, 30.0],
                [49, 36.0],
                [999, 40.0],
            ]
        ),
        # mind_growth soft soft-cap contribution
        "mind_growth_soft_cap": float(raw.get("mind_growth_soft_cap") or 18.0),
    }


def focus_ceil_for_level(level: int, reg: Optional[DataRegistry] = None) -> float:
    """Effective max focus_latent for player level (CM5 anti early-stack)."""
    cfg = _combo_mind_cfg(reg)
    abs_ceil = float(cfg["focus_ceil"])
    lv = max(1, int(level or 1))
    rows = list(cfg.get("focus_ceil_by_level") or [])
    eff = abs_ceil
    parsed: List[Tuple[int, float]] = []
    for row in rows:
        try:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                parsed.append((int(row[0]), float(row[1])))
            elif isinstance(row, dict):
                parsed.append(
                    (
                        int(row.get("max_level") or 999),
                        float(row.get("ceil") or abs_ceil),
                    )
                )
        except Exception:
            continue
    parsed.sort(key=lambda x: x[0])
    for max_lv, ceil in parsed:
        if lv <= max_lv:
            eff = ceil
            break
    return max(6.0, min(abs_ceil, eff))


def _table_bonus(table: Sequence[Any], value: float) -> float:
    """Ascending [threshold, bonus] rows — last threshold <= value wins."""
    best = 0.0
    rows: List[Tuple[float, float]] = []
    for row in table:
        try:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                rows.append((float(row[0]), float(row[1])))
            elif isinstance(row, dict):
                rows.append((float(row.get("at") or row.get("threshold") or 0), float(row.get("bonus") or row.get("mult") or 0)))
        except Exception:
            continue
    rows.sort(key=lambda x: x[0])
    for thr, bonus in rows:
        if value >= thr:
            best = bonus
    return best


def ensure_focus_latent(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> float:
    """Init hidden focus if missing; clamp to level soft ceil (CM5)."""
    cfg = _combo_mind_cfg(reg)
    lv = int(player.get("level") or 1)
    ceil = focus_ceil_for_level(lv, reg)
    if player.get("focus_latent") is None:
        # soft seed from level — never start near +2 step band early
        base = float(cfg["focus_base"]) + min(6.0, lv * 0.22)
        player["focus_latent"] = min(base, ceil * 0.85)
    try:
        fl = float(player.get("focus_latent") or 0)
    except Exception:
        fl = float(cfg["focus_base"])
    fl = max(0.0, min(ceil, fl))
    player["focus_latent"] = fl
    return fl


def get_focus_latent(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> float:
    if player.get("focus_latent") is None and isinstance(player, dict):
        return ensure_focus_latent(player, reg)  # type: ignore[arg-type]
    try:
        return max(0.0, float(player.get("focus_latent") or 0))
    except Exception:
        return 0.0


def mind_intellect(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> float:
    """
    Shown as soft band only — derive from power_intel + legacy alloc int + learn + mind_growth.
    Not the same as intel_current (spendable pool). CM3: not freely P-allocated.
    CM5: mind_growth soft-caps (diminishing).
    """
    cfg = _combo_mind_cfg(reg)
    pint = float(player.get("power_intel") or 0)
    alloc = int((player.get("stats_alloc") or {}).get("intelligence") or 0)
    learn = int(player.get("learn_points") or 0)
    growth = float(player.get("mind_growth") or 0)
    gcap = float(cfg.get("mind_growth_soft_cap") or 18.0)
    # diminishing after soft cap
    if growth <= gcap:
        g_eff = growth
    else:
        g_eff = gcap + (growth - gcap) * 0.35
    # light level soft
    lv = int(player.get("level") or 1)
    return max(0.0, pint + alloc * 0.85 + learn * 0.35 + g_eff * 0.4 + lv * 0.05)


def note_mind_growth(
    player: MutableMapping[str, Any],
    amount: float = 0.35,
    *,
    reason: str = "learn",
) -> Optional[str]:
    """Soft intellect growth (hidden). Rare soft line."""
    player["mind_growth"] = float(player.get("mind_growth") or 0) + max(0.0, float(amount))
    # also tiny learn_points for intel pool capacity coupling
    if reason in ("learn", "library", "master"):
        player["learn_points"] = int(player.get("learn_points") or 0) + (
            1 if amount >= 0.5 else 0
        )
    labels = {
        "learn": "คิดเกี่ยวกับท่าใหม่… ความคิดคมขึ้นนิด",
        "library": "อ่านแล้ว หัวโล่งขึ้นเล็กน้อย",
        "master": "คำสอนซึม… เข้าใจโครงท่าง่ายขึ้น",
        "fusion": "หลอมธาตุสำเร็จ — เห็นแพทเทิร์นชัดขึ้น",
        "combo": "เรียงท่าได้ดี — เข้าใจจังหวะขึ้น",
    }
    # don't spam: only sometimes surface
    import random

    if random.Random(int(player.get("mind_growth") or 0) * 10).random() < 0.45:
        return labels.get(reason)
    return None


def soft_focus_label(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> str:
    f = get_focus_latent(player, reg)
    if f < 6:
        return "จิตกระจัด"
    if f < 12:
        return "จิตพอตั้ง"
    if f < 20:
        return "จิตนิ่ง"
    if f < 28:
        return "สมาธิลึก"
    return "จิตสงบแน่น"


def soft_intellect_label(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> str:
    m = mind_intellect(player, reg)
    if m < 5:
        return "เลือน"
    if m < 9:
        return "พอใช้"
    if m < 15:
        return "คม"
    if m < 22:
        return "แจ่ม"
    return "เฉียบ"


def combo_step_bonuses(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> Tuple[int, int]:
    """Returns (focus_steps, intellect_steps)."""
    cfg = _combo_mind_cfg(reg)
    f = get_focus_latent(player, reg)
    m = mind_intellect(player, reg)
    fs = int(_table_bonus(cfg["focus_steps"], f))
    ms = int(_table_bonus(cfg["intellect_steps"], m))
    return max(0, fs), max(0, ms)


def combo_mana_mind_multiplier(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> float:
    """
    Tax from intellect/focus × relief from power_mag.
    Applied on top of length-based mana_mult.
    """
    cfg = _combo_mind_cfg(reg)
    f = get_focus_latent(player, reg)
    m = mind_intellect(player, reg)
    mag = float(player.get("power_mag") or 0)
    tax_i = float(_table_bonus(cfg["intellect_mana_tax"], m) or 1.0)
    tax_f = float(_table_bonus(cfg["focus_mana_tax"], f) or 1.0)
    # tax tables store absolute mult at threshold; use as product factors if >=1
    if tax_i < 0.5:
        tax_i = 1.0
    if tax_f < 0.5:
        tax_f = 1.0
    relief = float(_table_bonus(cfg["mag_mana_relief"], mag) or 1.0)
    if relief <= 0:
        relief = 1.0
    # if table used "bonus style" 0 for low mag, treat as 1.0
    if relief > 1.0:
        relief = 1.0
    mult = tax_i * tax_f * relief
    floor = float(cfg["relief_floor"])
    ceil = float(cfg["mult_ceil"])
    return max(floor, min(ceil, mult))


def soft_combo_mind_hint(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> str:
    """One line for combat meta — no numbers of latent."""
    fl = soft_focus_label(player, reg)
    il = soft_intellect_label(player, reg)
    return f"จิต〔{fl}〕 · ฉลาด〔{il}〕"


def adjust_focus_latent(
    player: MutableMapping[str, Any],
    delta: float,
    reg: Optional[DataRegistry] = None,
    *,
    reason: str = "",
) -> Optional[str]:
    """Change hidden focus; optional soft message (no formula)."""
    ensure_focus_latent(player, reg)
    before = float(player["focus_latent"])
    lv = int(player.get("level") or 1)
    ceil = focus_ceil_for_level(lv, reg)
    # CM5: diminishing rest gains near ceiling
    d = float(delta)
    if d > 0 and before >= ceil * 0.88:
        d *= 0.35
    player["focus_latent"] = max(0.0, min(ceil, before + d))
    after = float(player["focus_latent"])
    if abs(after - before) < 0.05:
        if d > 0 and before >= ceil * 0.95:
            return "จิตนิ่งเต็มที่ในระดับตอนนี้… ยังไม่ลึกกว่านี้"
        return None
    if d > 0:
        labels = {
            "rest": "จิตค่อยสงบขึ้น…",
            "victory": "หลังชนะ จิตตั้งได้ดีขึ้นนิด",
            "single_skill": "ฝึกทีละท่า — มือคุ้น จิตนิ่งขึ้น",
            "item": "ของช่วยให้จิตนิ่งชั่วขณะ",
        }
        return labels.get(reason, "จิตนิ่งขึ้นเล็กน้อย…")
    labels = {
        "long_combo": "เรียงท่ามากไป — จิตกระจัดชั่วคราว",
        "flee": "หนีแล้ว จิตยังสั่น",
        "defeat": "จิตกระจัดจากความพ่าย",
        "needs": "ร่างกายไม่พร้อม — จิตตั้งยาก",
    }
    return labels.get(reason, "จิตกระจัดลงนิด…")


def soft_combo_too_long_message(
    player: Mapping[str, Any],
    wanted: int,
    allowed: int,
    reg: Optional[DataRegistry] = None,
) -> str:
    """Player tried more steps than mind allows — soft, no formulas."""
    fl = soft_focus_label(player, reg)
    il = soft_intellect_label(player, reg)
    if wanted > allowed + 1:
        return (
            f"เรียง {wanted} ท่า — จิต/ความคิดยังไม่รับ (สูงสุด {allowed} · "
            f"〔{fl}〕/〔{il}〕)"
        )
    return f"ตอนนี้เรียงได้สูงสุด {allowed} ขั้น (จิต〔{fl}〕· ฉลาด〔{il}〕)"


def soft_combo_mana_fail_message(
    player: Mapping[str, Any],
    need: int,
    have: int,
    reg: Optional[DataRegistry] = None,
    *,
    length: int = 1,
) -> str:
    """
    Soft line when combo MP not enough — no mind formula, optional band.
    Still shows need/have as soft numbers (player already sees MP).
    """
    fl = soft_focus_label(player, reg)
    il = soft_intellect_label(player, reg)
    mag = float(player.get("power_mag") or 0)
    if length >= 3 and mag < 10:
        tip = "โซ่ยาวหนัก — เวท/มานาอาจยังไม่พอรองรับ"
    elif length >= 2:
        tip = f"โซ่นี้หนักเกินไปตอนนี้ (จิต〔{fl}〕· ฉลาด〔{il}〕)"
    else:
        tip = "มานาไม่พอสำหรับท่านั้น"
    return f"{tip} · ต้องการ ~{need} · มี {have}"


def on_combo_resolved(
    player: MutableMapping[str, Any],
    length: int,
    reg: Optional[DataRegistry] = None,
) -> Optional[str]:
    """After a successful multi-skill chain — fatigue if long."""
    if length <= 2:
        # small train focus
        if length == 1:
            return adjust_focus_latent(player, 0.15, reg, reason="single_skill")
        return adjust_focus_latent(player, 0.05, reg, reason="single_skill")
    if length >= 4:
        return adjust_focus_latent(player, -0.8 - 0.25 * (length - 4), reg, reason="long_combo")
    if length == 3:
        return adjust_focus_latent(player, -0.25, reg, reason="long_combo")
    return None


def on_rest_focus(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> Optional[str]:
    return adjust_focus_latent(player, 1.2, reg, reason="rest")


def on_victory_focus(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> Optional[str]:
    return adjust_focus_latent(player, 0.4, reg, reason="victory")
