"""
EQ soft context layers (anti-theorycraft diversity):

  EQ-W  weight class (light/medium/heavy)
  EQ-G  grip stance affinity (shield / dual / two_hand meters)
  EQ-A  area climate × gear material
  EQ-N  needs × weight (hooks into needs mults)

All soft — no kg, no %, no meter bars in UI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

STANCE_KEYS = ("one_hand_shield", "dual", "two_hand", "one_hand", "focus")

# material weight points per piece (soft)
_MATERIAL_WEIGHT = {
    "cloth": 1.0,
    "leather": 1.5,
    "wood": 1.8,
    "bone": 2.0,
    "crystal": 1.6,
    "metal": 3.2,
    "iron": 3.2,
    "steel": 3.5,
    "plate": 4.0,
}

_GRIP_WEIGHT = {
    "one_hand": 1.0,
    "two_hand": 2.8,
    "shield": 2.2,
    "focus": 0.8,
}

# climate tags on areas
_DEFAULT_AREA_CLIMATE: Dict[str, List[str]] = {
    "dark_forest": ["temperate", "dark", "wet"],
    "mist_marsh": ["wet", "cold", "dark"],
    "cave_shadow": ["dark", "cold"],
    "desert_heat": ["hot", "arid"],
    "mountain_rock": ["cold", "windy"],
    "crystal_peak": ["cold", "crystal", "holy_ground"],
    "ancient_city": ["temperate", "holy_ground"],
    "void_rift": ["dark", "void", "hot"],
}


def ensure_loadout_context(player: MutableMapping[str, Any]) -> None:
    player.setdefault("weight_class", "medium")
    player.setdefault("weight_score", 0.0)
    player.setdefault("stance_meters", {k: 25.0 for k in STANCE_KEYS})
    sm = dict(player.get("stance_meters") or {})
    for k in STANCE_KEYS:
        sm.setdefault(k, 25.0)
    player["stance_meters"] = sm
    player.setdefault("current_stance", "one_hand")
    player.setdefault("loadout_context_notes", [])
    player.setdefault("climate_soft_notes", [])
    player.setdefault("stance_soft_penalty", 0.0)


def item_material(it: Mapping[str, Any]) -> str:
    raw = str(it.get("material") or "").strip().lower()
    if raw in _MATERIAL_WEIGHT:
        return raw
    tags = {str(t).lower() for t in (it.get("tags") or [])}
    for m in ("cloth", "leather", "wood", "bone", "crystal", "metal", "plate", "iron"):
        if m in tags:
            return "metal" if m in ("iron", "plate") else m
    # id heuristics
    iid = str(it.get("id") or "").lower()
    name = str(it.get("name") or "").lower()
    blob = iid + " " + name
    if any(x in blob for x in ("robe", "cloth", "veil", "cloak", "คลุม", "ผ้า")):
        return "cloth"
    if any(x in blob for x in ("leather", "หนัง", "boots", "greaves")):
        return "leather"
    if any(x in blob for x in ("wood", "oak", "ไม้", "staff")):
        return "wood"
    if any(x in blob for x in ("crystal", "focus", "ผลึก", "arcane")):
        return "crystal"
    if any(x in blob for x in ("iron", "steel", "plate", "helm", "shield", "เหล็ก", "โล่")):
        return "metal"
    slot = str(it.get("slot") or "")
    if slot in ("main_hand", "weapon", "off_hand"):
        return "metal"
    if slot in ("body", "armor", "head", "legs", "feet"):
        return "leather"
    return "leather"


def detect_stance(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> str:
    """Current grip loadout mode id."""
    from game.domain.equipment import (
        GRIP_FOCUS,
        GRIP_ONE_HAND,
        GRIP_SHIELD,
        GRIP_TWO_HAND,
        item_grip,
    )

    eq = player.get("equip_ids") or {}
    main = eq.get("main_hand")
    off = eq.get("off_hand")
    main_it = (reg.items.get(main) if reg and main else None) or {}
    off_it = (reg.items.get(off) if reg and off else None) or {}
    mg = item_grip(main_it) if main else None
    og = item_grip(off_it) if off else None
    if mg == GRIP_TWO_HAND:
        return "two_hand"
    if mg == GRIP_ONE_HAND and og == GRIP_SHIELD:
        return "one_hand_shield"
    if mg == GRIP_ONE_HAND and og == GRIP_ONE_HAND:
        return "dual"
    if og == GRIP_FOCUS or mg == GRIP_FOCUS:
        return "focus"
    if mg == GRIP_ONE_HAND:
        return "one_hand"
    return "one_hand"


def _weight_score(player: Mapping[str, Any], reg: DataRegistry) -> float:
    from game.domain.equipment import EQUIP_SLOTS, item_grip

    score = 0.0
    eq = player.get("equip_ids") or {}
    for slot in EQUIP_SLOTS:
        eid = eq.get(slot)
        if not eid:
            continue
        it = reg.items.get(eid) or {}
        mat = item_material(it)
        score += float(_MATERIAL_WEIGHT.get(mat, 1.5))
        if slot in ("main_hand", "off_hand"):
            score += float(_GRIP_WEIGHT.get(item_grip(it), 1.0))
        # explicit weight_class on item
        wc = str(it.get("weight_class") or "").lower()
        if wc == "heavy":
            score += 1.5
        elif wc == "light":
            score -= 0.5
    return max(0.0, score)


def weight_class_from_score(score: float) -> str:
    if score < 8.0:
        return "light"
    if score < 14.0:
        return "medium"
    return "heavy"


def area_climates(
    reg: Optional[DataRegistry],
    area_id: Optional[str],
) -> List[str]:
    aid = str(area_id or "")
    if reg and aid and aid in (reg.areas or {}):
        area = reg.areas[aid] or {}
        cl = area.get("climate") or area.get("climates") or area.get("tags")
        if isinstance(cl, list) and cl:
            return [str(x).lower() for x in cl]
        if isinstance(cl, str) and cl:
            return [cl.lower()]
    return list(_DEFAULT_AREA_CLIMATE.get(aid, ["temperate"]))


def climate_material_effects(
    player: Mapping[str, Any],
    reg: DataRegistry,
    area_id: Optional[str],
) -> Tuple[Dict[str, float], List[str]]:
    """
    Returns mults {atk, def, mdef, atb, incoming, status_resist} and soft notes.
    """
    mults = {
        "atk": 1.0,
        "def": 1.0,
        "mdef": 1.0,
        "atb": 1.0,
        "incoming": 1.0,
        "status_resist": 0.0,
    }
    notes: List[str] = []
    climates = set(area_climates(reg, area_id))
    if not climates:
        return mults, notes

    from game.domain.equipment import EQUIP_SLOTS

    mats: List[str] = []
    eq = player.get("equip_ids") or {}
    for slot in EQUIP_SLOTS:
        eid = eq.get(slot)
        if not eid:
            continue
        mats.append(item_material(reg.items.get(eid) or {}))
    if not mats:
        return mults, notes

    n_metal = sum(1 for m in mats if m in ("metal", "iron", "steel", "plate"))
    n_cloth = sum(1 for m in mats if m == "cloth")
    n_leather = sum(1 for m in mats if m == "leather")
    n_crystal = sum(1 for m in mats if m == "crystal")
    n_wood = sum(1 for m in mats if m == "wood")

    # wet + metal → rust soft
    if climates & {"wet", "marsh"} and n_metal >= 2:
        mults["def"] *= 0.94
        mults["atb"] *= 0.93
        notes.append("สนิมในใจ — โลหะกับความชื้นไม่เข้ากัน")
    # cold + cloth → chill
    if climates & {"cold"} and n_cloth >= 2 and n_metal == 0:
        mults["incoming"] *= 1.06
        mults["status_resist"] -= 0.04
        notes.append("ผ้าบางในความเย็น — หนาวแทรก")
    # cold + metal/leather ok slightly
    if climates & {"cold"} and n_metal + n_leather >= 2:
        mults["incoming"] *= 0.98
    # hot + metal heavy
    if climates & {"hot", "arid"} and n_metal >= 2:
        mults["atb"] *= 0.92
        mults["atk"] *= 0.97
        notes.append("โลหะร้อนแผด — ย่างตัวเอง")
    # hot + cloth ok
    if climates & {"hot", "arid"} and n_cloth >= 1 and n_metal <= 1:
        mults["atb"] *= 1.03
    # dark + crystal
    if climates & {"dark", "void"} and n_crystal >= 1:
        mults["mdef"] *= 1.06
        mults["atk"] *= 1.03
        notes.append("ผลึกดูดเงา — เวทตอบสนอง")
    # holy_ground + shadow tags handled elsewhere; crystal in holy soft
    if climates & {"holy_ground"} and n_crystal >= 1:
        mults["mdef"] *= 1.04
    # wood in wet slightly bad
    if climates & {"wet"} and n_wood >= 2:
        mults["atk"] *= 0.97
        notes.append("ไม้ชื้น — ด้ามลื่น")

    return mults, notes


def stance_affinity_mult(player: Mapping[str, Any], stance: str) -> Tuple[float, str]:
    """
    Low meter for current stance → soft penalty on atk/def (single mult).
    Returns (mult 0.88..1.05, soft note or "").
    """
    ensure_loadout_context(player)  # type: ignore
    meters = player.get("stance_meters") or {}
    m = float(meters.get(stance) or 25.0)
    if m >= 55:
        return 1.03, ""
    if m >= 35:
        return 1.0, ""
    if m >= 20:
        return 0.96, "มือยังจำท่าเดิมเล็กน้อย"
    return 0.90, "มือยังจำท่าเดิม — ยังไม่ชินชุดนี้"


def bump_stance_meter(
    player: MutableMapping[str, Any],
    stance: str,
    *,
    amount: float = 6.0,
) -> None:
    ensure_loadout_context(player)
    meters = dict(player.get("stance_meters") or {})
    for k in STANCE_KEYS:
        meters.setdefault(k, 25.0)
    cur = float(meters.get(stance) or 25.0)
    meters[stance] = min(100.0, cur + float(amount))
    # slight decay of others (not hard lock)
    for k in STANCE_KEYS:
        if k != stance:
            meters[k] = max(5.0, float(meters[k]) - 1.2)
    player["stance_meters"] = meters


def recompute_loadout_context(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    area_id: Optional[str] = None,
) -> None:
    """Refresh weight/stance/climate soft fields on player."""
    ensure_loadout_context(player)
    aid = area_id or str(player.get("location") or "")
    score = _weight_score(player, reg)
    wc = weight_class_from_score(score)
    player["weight_score"] = round(score, 2)
    player["weight_class"] = wc
    stance = detect_stance(player, reg)
    player["current_stance"] = stance
    aff_m, aff_note = stance_affinity_mult(player, stance)
    player["stance_soft_penalty"] = round(1.0 - aff_m, 4) if aff_m < 1.0 else 0.0
    player["stance_combat_mult"] = round(aff_m, 4)

    clim_m, clim_notes = climate_material_effects(player, reg, aid)
    player["climate_mults"] = {k: round(v, 4) for k, v in clim_m.items()}
    player["climate_soft_notes"] = clim_notes

    notes: List[str] = []
    if wc == "light":
        notes.append("ตัวเบา — ก้าวคล่อง")
    elif wc == "heavy":
        notes.append("ก้าวหนัก — เกราะทับตัว")
    if aff_note:
        notes.append(aff_note)
    notes.extend(clim_notes[:2])
    player["loadout_context_notes"] = notes

    # climate → status resist delta (absolute, not stacked every recompute)
    base_sr = float(player.get("gear_status_resist") or 0)
    # store climate-only delta separately so recompute is stable
    clim_sr = float(clim_m.get("status_resist") or 0)
    player["climate_status_resist"] = round(clim_sr, 4)
    # effective used by resist_chance via gear_status_resist + climate field
    # keep gear_status_resist as gear-only (set in equipment.recompute before us)
    _ = base_sr  # climate applied in resist via climate_status_resist


def loadout_combat_mults(player: Mapping[str, Any]) -> Dict[str, float]:
    """
    Combined hidden mults for combat from weight + stance + climate + needs×weight.
    """
    wc = str(player.get("weight_class") or "medium")
    stance_m = float(player.get("stance_combat_mult") or 1.0)
    clim = player.get("climate_mults") or {}

    atk = 1.0 * stance_m * float(clim.get("atk") or 1.0)
    incoming = 1.0 * float(clim.get("incoming") or 1.0)
    atb = 1.0 * float(clim.get("atb") or 1.0)
    # weight base
    if wc == "light":
        atk *= 0.98
        incoming *= 1.04
        atb *= 1.06
    elif wc == "heavy":
        atk *= 1.02
        incoming *= 0.96
        atb *= 0.90

    # EQ-N: heavy + hungry/tired hurts more
    try:
        from game.domain.needs import band, get_needs

        n = get_needs(player)
        hb = band("hunger", n["hunger"])
        fb = band("fatigue", n["fatigue"])
        if wc == "heavy":
            if hb in ("bad", "crit"):
                atk *= 0.94 if hb == "bad" else 0.88
                atb *= 0.92 if hb == "bad" else 0.85
                incoming *= 1.05 if hb == "bad" else 1.10
            if fb in ("bad", "crit"):
                atb *= 0.90 if fb == "bad" else 0.82
                incoming *= 1.04 if fb == "bad" else 1.08
        elif wc == "light":
            if hb == "crit":
                atk *= 0.95  # light still suffers but less armor crush
            if fb == "crit":
                atb *= 0.92
    except Exception:
        pass

    return {
        "atk_mult": max(0.72, min(1.18, atk)),
        "incoming_mult": max(0.88, min(1.22, incoming)),
        "atb_mult": max(0.70, min(1.15, atb)),
        "def_mult": max(0.90, min(1.12, float(clim.get("def") or 1.0))),
        "mdef_mult": max(0.90, min(1.12, float(clim.get("mdef") or 1.0))),
    }


def soft_weight_label(player: Mapping[str, Any]) -> str:
    wc = str(player.get("weight_class") or "medium")
    return {
        "light": "ตัวเบา",
        "medium": "สมดุล",
        "heavy": "ก้าวหนัก",
    }.get(wc, "สมดุล")


def on_combat_victory_stance(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> List[str]:
    """Call after win — train current stance meter. Occasional soft note."""
    ensure_loadout_context(player)
    stance = str(player.get("current_stance") or detect_stance(player, reg))
    before = float((player.get("stance_meters") or {}).get(stance) or 25)
    bump_stance_meter(player, stance, amount=5.5 + (2.0 if stance in ("dual", "two_hand") else 0))
    after = float((player.get("stance_meters") or {}).get(stance) or 25)
    notes: List[str] = []
    # rare soft hint when crossing thresholds
    if before < 35 <= after:
        notes.append("「มือเริ่มจำท่านี้」")
    elif before < 55 <= after:
        notes.append("「ท่านี้ชินขึ้น」")
    return notes
