"""
DD0–DD1: damage classes (physical / arcane / light / dark) + mitigation.

Soft UI only — never expose % or raw power_def/mdef to players.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

DAMAGE_CLASSES = ("physical", "arcane", "light", "dark")

_DEFAULT_CFG: Dict[str, Any] = {
    "element_to_class": {
        "physical": "physical",
        "slash": "physical",
        "pierce": "physical",
        "blunt": "physical",
        "nature": "physical",
        "arcane": "arcane",
        "magic": "arcane",
        "fire": "arcane",
        "water": "arcane",
        "wind": "arcane",
        "earth": "arcane",
        "ice": "arcane",
        "lightning": "arcane",
        "holy": "light",
        "light": "light",
        "shadow": "dark",
        "dark": "dark",
    },
    "mitigation": {
        "k": 45.0,
        "cap": 0.55,
        "light_dark_def_weight": 0.45,
        "light_dark_mdef_weight": 0.55,
    },
    "outbound": {
        "physical": "power_atk",
        "arcane": "power_mag",
        "light": "power_mag",
        "dark": "power_atk",
        "secondary_frac": 0.15,
    },
    "classes": {
        "physical": {
            "soft_name": "กายภาพ",
            "soft_guard_ok": "เกราะรับแรงกระแทก",
            "soft_guard_miss": "เกราะไม่ช่วยชั้นนี้",
        },
        "arcane": {
            "soft_name": "เวทมนต์",
            "soft_guard_ok": "ม่านกลืนเวท",
            "soft_guard_miss": "ม่านไม่รับกาย",
        },
        "light": {
            "soft_name": "แสง",
            "soft_guard_ok": "แสงถูกกลืนบางส่วน",
            "soft_guard_miss": "แสงทะลุเกราะ",
        },
        "dark": {
            "soft_name": "มืด",
            "soft_guard_ok": "เงาถูกกลืนบางส่วน",
            "soft_guard_miss": "เงาทะลุเกราะ",
        },
    },
}


def damage_class_cfg(reg: Optional[Any] = None) -> Dict[str, Any]:
    cfg = getattr(reg, "damage_classes_cfg", None) if reg is not None else None
    if isinstance(cfg, dict) and cfg:
        # shallow merge defaults for missing keys
        out = dict(_DEFAULT_CFG)
        out.update(cfg)
        if "element_to_class" in cfg:
            m = dict(_DEFAULT_CFG["element_to_class"])
            m.update(cfg.get("element_to_class") or {})
            out["element_to_class"] = m
        if "mitigation" in cfg:
            mit = dict(_DEFAULT_CFG["mitigation"])
            mit.update(cfg.get("mitigation") or {})
            out["mitigation"] = mit
        if "outbound" in cfg:
            ob = dict(_DEFAULT_CFG["outbound"])
            ob.update(cfg.get("outbound") or {})
            out["outbound"] = ob
        if "classes" in cfg:
            cl = dict(_DEFAULT_CFG["classes"])
            for k, v in (cfg.get("classes") or {}).items():
                base = dict(cl.get(k) or {})
                if isinstance(v, dict):
                    base.update(v)
                cl[str(k)] = base
            out["classes"] = cl
        return out
    return dict(_DEFAULT_CFG)


def normalize_damage_class(raw: Optional[str]) -> str:
    s = str(raw or "").strip().lower()
    if s in DAMAGE_CLASSES:
        return s
    if s in ("magic",):
        return "arcane"
    if s in ("holy",):
        return "light"
    if s in ("shadow",):
        return "dark"
    return "physical"


def infer_damage_class_from_elements(
    elements: Sequence[Any],
    reg: Optional[Any] = None,
) -> str:
    cfg = damage_class_cfg(reg)
    mapping = cfg.get("element_to_class") or {}
    # priority: explicit class-like elements first
    priority = ("physical", "arcane", "magic", "holy", "light", "shadow", "dark")
    elems = [str(e).lower() for e in (elements or []) if e]
    if not elems:
        return "physical"
    for p in priority:
        if p in elems:
            return normalize_damage_class(mapping.get(p, p))
    # first element wins
    e0 = elems[0]
    return normalize_damage_class(mapping.get(e0, "physical"))


def resolve_damage_class(
    skill_or_profile: Optional[Mapping[str, Any]] = None,
    *,
    elements: Optional[Sequence[Any]] = None,
    reg: Optional[Any] = None,
    tags: Optional[Sequence[Any]] = None,
) -> str:
    """
    Prefer explicit damage_class on skill/profile;
    else infer from elements / attack tags.
    """
    src = skill_or_profile or {}
    if src.get("damage_class"):
        return normalize_damage_class(str(src.get("damage_class")))
    els: List[Any] = []
    if elements is not None:
        els = list(elements)
    elif src.get("elements"):
        els = list(src.get("elements") or [])
    elif tags is not None:
        els = list(tags)
    elif src.get("tags"):
        els = list(src.get("tags") or [])
    return infer_damage_class_from_elements(els, reg)


def mitigation_power_for_class(
    player: Mapping[str, Any],
    dmg_class: str,
    reg: Optional[Any] = None,
) -> float:
    """Which defensive power reduces this damage class."""
    cfg = damage_class_cfg(reg)
    mit = cfg.get("mitigation") or {}
    # power_def / power_mdef already include gear bias after recompute_powers
    pdef = float(player.get("power_def") or 5.0)
    pmdef = float(player.get("power_mdef") or player.get("power_mag") or 5.0)
    dc = normalize_damage_class(dmg_class)
    if dc == "physical":
        return max(0.0, pdef)
    if dc == "arcane":
        return max(0.0, pmdef)
    # light / dark blend
    w_d = float(mit.get("light_dark_def_weight") or 0.45)
    w_m = float(mit.get("light_dark_mdef_weight") or 0.55)
    # normalize weights soft
    s = max(0.01, w_d + w_m)
    return max(0.0, pdef * (w_d / s) + pmdef * (w_m / s))


def class_mitigation_mult(
    player: Mapping[str, Any],
    dmg_class: str,
    reg: Optional[Any] = None,
) -> float:
    """Return damage multiplier after class mitigation (0.45..1.0 soft)."""
    cfg = damage_class_cfg(reg)
    mit = cfg.get("mitigation") or {}
    k = float(mit.get("k") or 45.0)
    cap = float(mit.get("cap") or 0.55)
    pwr = mitigation_power_for_class(player, dmg_class, reg)
    reduce = pwr / (pwr + k) if (pwr + k) > 0 else 0.0
    reduce = min(cap, max(0.0, reduce))
    return 1.0 - reduce


def apply_class_mitigation(
    incoming: int,
    player: Mapping[str, Any],
    dmg_class: str,
    reg: Optional[Any] = None,
) -> Tuple[int, str]:
    """
    Reduce incoming damage by class. Returns (final_dmg, soft_flavor).
    Flavor only when mitigation is noticeable.
    """
    dmg = max(0, int(incoming))
    if dmg <= 0:
        return 0, ""
    mult = class_mitigation_mult(player, dmg_class, reg)
    final = max(0, int(round(dmg * mult)))
    # soft floor: at least 0, keep some chip if huge hit
    if dmg >= 3 and final == 0 and mult > 0.15:
        final = 1
    cfg = damage_class_cfg(reg)
    cl = (cfg.get("classes") or {}).get(normalize_damage_class(dmg_class)) or {}
    flavor = ""
    reduced = dmg - final
    if reduced >= max(2, int(dmg * 0.18)):
        flavor = f" ({cl.get('soft_guard_ok') or 'รับได้'})"
    elif mult > 0.92 and normalize_damage_class(dmg_class) in ("arcane", "light", "dark"):
        # weak mdef vs magic-ish — rare soft hint
        if float(player.get("power_mdef") or 0) + float(player.get("gear_mdef_bias") or 0) < 8:
            flavor = f" ({cl.get('soft_guard_miss') or 'ทะลุ...'})"
    return final, flavor


def outbound_power_bonus(
    player: Mapping[str, Any],
    dmg_class: str,
    reg: Optional[Any] = None,
) -> float:
    """Extra power from class-linked stats (hidden)."""
    cfg = damage_class_cfg(reg)
    ob = cfg.get("outbound") or {}
    dc = normalize_damage_class(dmg_class)
    primary_key = str(ob.get(dc) or "power_atk")
    primary = float(player.get(primary_key) or 0.0)
    # gear atk already in bonus_atk; here we add soft power_* feed
    frac = 0.28 if dc in ("arcane", "light") else 0.22
    bonus = primary * frac
    sec_frac = float(ob.get("secondary_frac") or 0.15)
    if dc == "physical":
        bonus += float(player.get("power_mag") or 0) * sec_frac * 0.4
    elif dc == "arcane":
        bonus += float(player.get("power_atk") or 0) * sec_frac * 0.35
    elif dc == "light":
        bonus += float(player.get("power_def") or 0) * sec_frac * 0.25
    elif dc == "dark":
        bonus += float(player.get("power_mag") or 0) * sec_frac * 0.4
    # gear bias soft (EL3)
    if dc == "physical":
        bonus += float(player.get("gear_atk_bias") or 0) * 0.5
    if dc in ("arcane", "light"):
        bonus += float(player.get("gear_mag_bias") or 0) * 0.55
    return max(0.0, bonus)


def soft_class_label(dmg_class: str, reg: Optional[Any] = None) -> str:
    cfg = damage_class_cfg(reg)
    cl = (cfg.get("classes") or {}).get(normalize_damage_class(dmg_class)) or {}
    return str(cl.get("soft_name") or dmg_class)


def ensure_damage_fields(player: MutableMapping[str, Any]) -> None:
    player.setdefault("power_def", 5.0)
    player.setdefault("power_mdef", float(player.get("power_mag") or 5.0))
    player.setdefault("gear_def_bias", 0.0)
    player.setdefault("gear_mdef_bias", 0.0)
    player.setdefault("gear_atk_bias", 0.0)
    player.setdefault("gear_mag_bias", 0.0)
    player.setdefault("gear_atb_bias", 0.0)
    player.setdefault("loadout_soft_notes", [])
