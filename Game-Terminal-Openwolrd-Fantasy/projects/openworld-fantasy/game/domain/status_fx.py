"""
Abnormal status system — data-driven catalog + apply/tick/clear.

Entity shape: entity["statuses"] = [{"id", "name", "remaining", "tick_hp", ...}, ...]
Catalog: data/statuses/statuses.yaml → reg.statuses
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Union

from game.data_load.registry import DataRegistry


# Fallback if YAML missing (keeps combat playable)
_FALLBACK: Dict[str, Dict[str, Any]] = {
    "poison": {
        "id": "poison",
        "name": "พิษ",
        "duration": 3,
        "tick_hp": 4,
        "kind": "debuff",
        "category": "ailment",
        "narrative_tick": "status_tick_poison",
        "soft_feel": "คลื่นคลื่น เลือดอุ่นผิดปกติ",
        "cleansed_by": ["antidote", "blessed_charm"],
        "cleanse_tags": ["poison", "ailment"],
    },
    "burn": {
        "id": "burn",
        "name": "ไหม้",
        "duration": 2,
        "tick_hp": 5,
        "kind": "debuff",
        "category": "ailment",
        "narrative_tick": "status_tick_burn",
        "soft_feel": "แสบร้อนเป็นระลอก",
        "cleanse_tags": ["burn", "ailment"],
    },
    "freeze": {
        "id": "freeze",
        "name": "แช่แข็ง",
        "duration": 2,
        "tick_hp": 0,
        "skip_action": True,
        "kind": "debuff",
        "category": "control",
        "narrative_tick": "status_tick_freeze",
        "soft_feel": "แข็งทื่อ เคลื่อนไหวช้า",
        "cleanse_tags": ["freeze", "control"],
    },
    "stun": {
        "id": "stun",
        "name": "มึนงง",
        "duration": 1,
        "tick_hp": 0,
        "skip_action": True,
        "kind": "debuff",
        "category": "control",
        "narrative_tick": "status_tick_stun",
        "soft_feel": "หูอื้อ จังหวะหลุด",
        "cleanse_tags": ["stun", "control"],
    },
    "shock": {
        "id": "shock",
        "name": "ช็อก",
        "duration": 2,
        "tick_hp": 3,
        "skip_action_chance": 0.3,
        "kind": "debuff",
        "category": "ailment",
        "narrative_tick": "status_tick_shock",
        "soft_feel": "กล้ามเนื้อกระตุก ฝีเท้าหลุด",
        "cleanse_tags": ["shock", "ailment"],
    },
}


@dataclass
class StatusTickResult:
    notes: List[str] = field(default_factory=list)
    damage: int = 0
    skip_action: bool = False
    expired: List[str] = field(default_factory=list)
    ticked: List[str] = field(default_factory=list)
    narrative_events: List[Dict[str, Any]] = field(default_factory=list)


def _catalog(reg: Optional[DataRegistry]) -> Dict[str, Dict[str, Any]]:
    if reg is None:
        return dict(_FALLBACK)
    cat = getattr(reg, "statuses", None) or {}
    if not cat:
        return dict(_FALLBACK)
    return cat


def _defaults(reg: Optional[DataRegistry]) -> Dict[str, Any]:
    if reg is None:
        return {"max_stacks": 1, "refresh_on_reapply": True, "on_hit_chance_cap": 0.35}
    return dict(getattr(reg, "status_defaults", None) or {})


def get_status_def(
    reg: Optional[DataRegistry], status_id: str
) -> Dict[str, Any]:
    sid = str(status_id or "").strip()
    cat = _catalog(reg)
    if sid in cat:
        d = dict(cat[sid])
        d.setdefault("id", sid)
        return d
    if sid in _FALLBACK:
        return dict(_FALLBACK[sid])
    return {
        "id": sid,
        "name": sid,
        "duration": 2,
        "tick_hp": 0,
        "kind": "debuff",
        "category": "ailment",
    }


def status_display_name(reg: Optional[DataRegistry], status_id: str) -> str:
    d = get_status_def(reg, status_id)
    name = d.get("name")
    if name:
        return str(name)
    # narrative overlay
    try:
        from game.domain.narrative import status_display_name as narr_name

        return narr_name(status_id, reg)
    except Exception:
        return str(status_id)


def status_soft_feel(reg: Optional[DataRegistry], status_id: str) -> str:
    d = get_status_def(reg, status_id)
    if d.get("soft_feel"):
        return str(d["soft_feel"])
    try:
        from game.domain.narrative import status_feel

        return status_feel(status_id, reg)
    except Exception:
        return "ความรู้สึกแปลกปลอม"


def ensure_statuses(entity: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
    st = entity.get("statuses")
    if not isinstance(st, list):
        entity["statuses"] = []
        return entity["statuses"]  # type: ignore
    # normalize entries to dicts
    norm: List[Dict[str, Any]] = []
    for s in st:
        if isinstance(s, dict):
            norm.append(dict(s))
        elif s:
            norm.append({"id": str(s), "name": str(s), "remaining": 2})
    entity["statuses"] = norm
    return norm


def list_status_ids(entity: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for s in entity.get("statuses") or []:
        if isinstance(s, dict):
            sid = s.get("id") or s.get("name")
            if sid:
                out.append(str(sid))
        elif s:
            out.append(str(s))
    return out


def has_status(entity: Mapping[str, Any], status_id: str) -> bool:
    return str(status_id) in list_status_ids(entity)


def format_status_short(
    entity: Mapping[str, Any], reg: Optional[DataRegistry] = None
) -> str:
    parts: List[str] = []
    for s in entity.get("statuses") or []:
        if not isinstance(s, dict):
            parts.append(str(s))
            continue
        sid = str(s.get("id") or s.get("name") or "?")
        nm = status_display_name(reg, sid)
        rem = s.get("remaining")
        if rem is not None:
            parts.append(f"{nm}({rem})")
        else:
            parts.append(nm)
    return ", ".join(parts) if parts else "-"


def on_hit_chance_cap(reg: Optional[DataRegistry]) -> float:
    return float(_defaults(reg).get("on_hit_chance_cap", 0.35))


def _status_element(defn: Mapping[str, Any], status_id: str) -> str:
    el = str(defn.get("element") or "").lower()
    if el:
        return el
    # soft map from id
    return {
        "burn": "fire",
        "freeze": "ice",
        "shock": "lightning",
        "poison": "nature",
        "stun": "physical",
    }.get(str(status_id), "")


def soft_resist_flavor(status_id: str, reg: Optional[DataRegistry] = None) -> str:
    """Anti-spoiler line when entity shrugs a status (DD4)."""
    sid = str(status_id or "")
    nm = status_display_name(reg, sid)
    catalog = {
        "burn": "ร่างกายชินกับเปลว",
        "freeze": "ความหนาวยังไม่เกาะ",
        "shock": "กระแสไม่จับเส้น",
        "poison": "พิษยังไม่ซึม",
        "stun": "จิตยังตั้งได้",
    }
    if sid in catalog:
        return f"「{catalog[sid]}」"
    return f"「{nm} ยังไม่ติด」"


def bump_status_familiarity(
    entity: MutableMapping[str, Any],
    status_id: str,
    *,
    amount: float = 0.04,
    cap: float = 0.22,
) -> None:
    """
    Hidden stack: after resist or after status expires, slightly harder next time.
    Not permanent farm — soft cap low, decays slowly via combat end optional.
    """
    sid = str(status_id or "")
    if not sid:
        return
    fam = dict(entity.get("status_familiarity") or {})
    cur = float(fam.get(sid) or 0)
    fam[sid] = min(cap, max(0.0, cur + float(amount)))
    entity["status_familiarity"] = fam


def decay_status_familiarity(entity: MutableMapping[str, Any], *, factor: float = 0.85) -> None:
    """Call occasionally (e.g. rest / area change) so familiarity is not permanent."""
    fam = dict(entity.get("status_familiarity") or {})
    if not fam:
        return
    out = {}
    for k, v in fam.items():
        nv = float(v) * float(factor)
        if nv >= 0.02:
            out[str(k)] = round(nv, 4)
    entity["status_familiarity"] = out


def resist_chance(
    entity: Mapping[str, Any],
    status_id: str,
    reg: Optional[DataRegistry] = None,
    *,
    aoe: bool = False,
    attack_elements: Optional[Sequence[Any]] = None,
) -> float:
    """
    Chance (0..resist_cap) that entity shrugs off the status after proc roll.
    DD4: base + gear + familiarity + elem soft + aoe resist bonus.
    """
    sid = str(status_id or "")
    defn = get_status_def(reg, sid)
    r = float(defn.get("base_resist") or 0)
    sr = entity.get("status_resist") or {}
    if isinstance(sr, dict):
        r += float(sr.get(sid, 0) or 0)
        r += float(sr.get("all", 0) or 0)
        cat = str(defn.get("category") or "")
        if cat:
            r += float(sr.get(cat, 0) or 0)
    r += float(entity.get("status_resist_all") or 0)
    r += float(entity.get("gear_status_resist") or 0)
    r += float(entity.get("climate_status_resist") or 0)

    # soft investment: defense / intelligence (hidden)
    try:
        pdef = float(entity.get("power_def") or 0)
        pint = float(entity.get("power_intel") or 0)
        r += min(0.12, pdef / 220.0 + pint / 280.0)
    except Exception:
        pass

    # WO-037: Anima resists mental / control / fear-like statuses (player only soft)
    try:
        cat = str(defn.get("category") or "").lower()
        mental_ids = ("stun", "fear", "charm", "confuse", "sleep", "horror")
        if sid in mental_ids or cat in ("control", "mental", "mind"):
            from game.domain.stat_arch import anima_mental_resist_bonus

            r += anima_mental_resist_bonus(entity)  # type: ignore[arg-type]
    except Exception:
        pass

    # familiarity stacks (hidden)
    fam = entity.get("status_familiarity") or {}
    if isinstance(fam, dict):
        r += float(fam.get(sid, 0) or 0)

    # soft gear affinities (not spoiler formulas — small nudges)
    tags = [str(t).lower() for t in (entity.get("gear_tags") or [])]
    cat = str(defn.get("category") or "")
    if "holy" in tags and cat in ("ailment", "control"):
        r += 0.08
    if "fire" in tags and sid == "burn":
        r += 0.10
    if "water" in tags and sid in ("burn", "freeze"):
        r += 0.06 if sid == "burn" else 0.05
    if "lightning" in tags and sid == "shock":
        r += 0.10
    if "shadow" in tags and sid in ("poison", "stun"):
        r += 0.05
    if "arcane" in tags and cat == "control":
        r += 0.04
    if "shield" in tags and cat in ("control", "ailment"):
        r += 0.03

    # DD4: element vs status soft (attack elements / wet vs burn etc.)
    st_el = _status_element(defn, sid)
    atk_els = {str(e).lower() for e in (attack_elements or []) if e}
    # target already wet/frozen resists burn slightly more
    target_els = set()
    for s in entity.get("statuses") or []:
        if isinstance(s, dict):
            se = str(s.get("element") or s.get("id") or "").lower()
            if se:
                target_els.add(se)
            if str(s.get("id")) == "freeze":
                target_els.add("ice")
    if sid == "burn" and ("water" in atk_els or "ice" in target_els or "water" in tags):
        r += 0.07  # เปียก/หนาว → ไฟติดยาก
    if sid == "freeze" and ("fire" in tags or "fire" in target_els):
        r += 0.06
    if sid == "shock" and ("earth" in tags or "earth" in atk_els):
        r += 0.05
    # same element attack vs familiar gear slightly
    if st_el and st_el in tags:
        r += 0.05

    # AoE soft resist bump
    if aoe:
        try:
            from game.domain.aoe_balance import aoe_status_resist_bonus

            r += float(aoe_status_resist_bonus(aoe=True))
        except Exception:
            r += 0.08

    # world / blessing soft
    if entity.get("blessing_turns") and int(entity.get("blessing_turns") or 0) > 0:
        r += 0.05
    cap = float(_defaults(reg).get("resist_cap", 0.85))
    return max(0.0, min(cap, r))


def cleanse(
    entity: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    mode: str = "all_debuffs",
    item_id: Optional[str] = None,
    clear_spec: Optional[Union[str, Sequence[str]]] = None,
) -> List[str]:
    """
    General cleanse entrypoint.
    mode:
      - all_debuffs / all / *  → every debuff
      - ailment | control     → by category tag
      - poison (or any id)    → that id + matching tags via clear_statuses
    """
    m = str(mode or "all_debuffs").strip().lower()
    if m in ("all_debuffs", "all", "*", "debuff", "debuffs"):
        return clear_all_debuffs(entity, reg)
    if m in ("ailment", "control"):
        return clear_statuses(entity, reg, tags=[m], item_id=item_id)
    # treat mode as clear_spec id/tag
    return clear_statuses(
        entity,
        reg,
        item_id=item_id,
        clear_spec=clear_spec if clear_spec is not None else mode,
    )


def apply_status(
    entity: MutableMapping[str, Any],
    status_id: str,
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
    *,
    chance: float = 1.0,
    duration: Optional[int] = None,
    tick_hp: Optional[int] = None,
    source: str = "",
    ignore_resist: bool = False,
    aoe: bool = False,
    attack_elements: Optional[Sequence[Any]] = None,
    n_targets: int = 1,
) -> Optional[str]:
    """
    Apply or refresh a status. Returns status id if applied, else None.
    chance is rolled when < 1.0 (after optional cap for on-hit callers).
    Then resist_chance may shrug it off (sets entity['_last_status_resist']).
    DD4: aoe reduces chance + bumps resist; familiarity after shrug.
    """
    rng = rng or random.Random()
    sid = str(status_id or "").strip()
    if not sid:
        return None
    entity.pop("_last_status_resist", None)
    entity.pop("_last_status_resist_flavor", None)
    entity.pop("_last_status_applied", None)

    ch = float(chance)
    if aoe or n_targets > 1:
        try:
            from game.domain.aoe_balance import aoe_status_chance_mult

            ch *= aoe_status_chance_mult(
                aoe=bool(aoe), n_targets=max(1, int(n_targets))
            )
        except Exception:
            ch *= 0.55 if aoe else 0.7

    if ch < 1.0 and rng.random() > ch:
        return None

    if not ignore_resist:
        rc = resist_chance(
            entity,
            sid,
            reg,
            aoe=bool(aoe),
            attack_elements=attack_elements,
        )
        if rc > 0 and rng.random() < rc:
            entity["_last_status_resist"] = sid
            entity["_last_status_resist_flavor"] = soft_resist_flavor(sid, reg)
            bump_status_familiarity(entity, sid, amount=0.035)
            return None

    defn = get_status_def(reg, sid)
    statuses = ensure_statuses(entity)
    # refresh: drop existing same id
    statuses = [s for s in statuses if str(s.get("id")) != sid]

    rem = int(duration if duration is not None else defn.get("duration", 2))
    rem = max(1, rem)
    thp = int(tick_hp if tick_hp is not None else defn.get("tick_hp", 0) or 0)
    entry: Dict[str, Any] = {
        "id": sid,
        "name": str(defn.get("name") or sid),
        "remaining": rem,
        "tick_hp": thp,
        "kind": defn.get("kind") or "debuff",
        "category": defn.get("category") or "ailment",
    }
    if source:
        entry["source"] = source
    if defn.get("skip_action"):
        entry["skip_action"] = True
    if defn.get("skip_action_chance"):
        entry["skip_action_chance"] = float(defn["skip_action_chance"])
    if defn.get("element"):
        entry["element"] = defn["element"]
    # copy combat modifiers onto entry for save-friendly ticks
    for key in ("atk_flat", "dmg_taken_mult", "tick_heal", "tick_mana"):
        if defn.get(key) is not None:
            entry[key] = defn[key]
    statuses.append(entry)
    entity["statuses"] = statuses
    entity["_last_status_applied"] = sid
    return sid


# Element → soft default status for monster hits without explicit profile status
_ELEMENT_STATUS = {
    "fire": "burn",
    "shadow": "poison",
    "nature": "poison",
    "lightning": "shock",
    "water": "freeze",
    "ice": "freeze",
    "holy": "stun",
}


def resolve_outgoing_status(
    attacker: Mapping[str, Any],
    profile: Optional[Mapping[str, Any]] = None,
    reg: Optional[DataRegistry] = None,
) -> Optional[Dict[str, Any]]:
    """
    Decide what status an attack may apply.
    Priority: profile.status → attacker.apply_status → element fallback.
    Returns {id, chance} or None.
    """
    profile = profile or {}
    # 1) profile explicit
    if profile.get("status"):
        return {
            "id": str(profile.get("status")),
            "chance": float(profile.get("status_chance") or profile.get("chance") or 0.25),
        }
    # 2) monster-level apply_status block
    block = attacker.get("apply_status")
    if isinstance(block, dict) and block.get("id"):
        return {
            "id": str(block.get("id")),
            "chance": float(block.get("chance") or 0.2),
        }
    if isinstance(block, str) and block:
        return {"id": block, "chance": 0.2}
    # 3) element soft fallback
    defs = _defaults(reg)
    if not defs.get("element_status_fallback", True):
        return None
    tags = list(profile.get("tags") or attacker.get("elements") or [])
    base_chance = float(defs.get("element_status_chance", 0.12))
    for t in tags:
        sid = _ELEMENT_STATUS.get(str(t))
        if sid:
            return {"id": sid, "chance": base_chance}
    return None


def try_apply_attack_status(
    target: MutableMapping[str, Any],
    attacker: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
    *,
    profile: Optional[Mapping[str, Any]] = None,
    source: str = "attack",
    aoe: bool = False,
    n_targets: int = 1,
) -> Optional[str]:
    """Roll and apply status from an attack onto target. None if fail/resist."""
    rng = rng or random.Random()
    profile = profile or {}
    spec = resolve_outgoing_status(attacker, profile, reg)
    if not spec:
        return None
    els = list(profile.get("tags") or profile.get("elements") or attacker.get("elements") or [])
    applied = apply_status(
        target,
        str(spec["id"]),
        reg,
        rng,
        chance=float(spec.get("chance") or 0),
        source=source,
        aoe=aoe,
        n_targets=n_targets,
        attack_elements=els,
    )
    return applied


def format_last_resist_note(entity: Mapping[str, Any]) -> Optional[str]:
    """Soft line if last apply was resisted (consume-friendly read)."""
    sid = entity.get("_last_status_resist")
    if not sid:
        return None
    fl = entity.get("_last_status_resist_flavor")
    if fl:
        return str(fl)
    return soft_resist_flavor(str(sid), None)


def clear_status(
    entity: MutableMapping[str, Any],
    status_id: str,
) -> bool:
    """Remove one status id. Returns True if removed."""
    statuses = ensure_statuses(entity)
    sid = str(status_id)
    new = [s for s in statuses if str(s.get("id")) != sid]
    removed = len(new) != len(statuses)
    entity["statuses"] = new
    return removed


def clear_statuses(
    entity: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    status_ids: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
    item_id: Optional[str] = None,
    clear_spec: Optional[Union[str, Sequence[str]]] = None,
    all_debuffs: bool = False,
) -> List[str]:
    """
    Clear matching statuses.
    - status_ids: exact ids
    - tags: match defn cleanse_tags / category / id
    - item_id: clear any status listing this item in cleansed_by
    - clear_spec: from item clear_status field (str or list) — id or tag
      special: all / * / debuff → all debuffs
    - all_debuffs: force full debuff cleanse
    Returns list of removed ids.
    """
    if all_debuffs:
        return clear_all_debuffs(entity, reg)
    statuses = ensure_statuses(entity)
    want_ids = {str(x) for x in (status_ids or [])}
    want_tags = {str(x) for x in (tags or [])}
    if clear_spec is not None:
        specs = [clear_spec] if isinstance(clear_spec, str) else list(clear_spec)
        for x in specs:
            xs = str(x).strip().lower()
            if xs in ("all", "*", "debuff", "debuffs", "all_debuffs"):
                return clear_all_debuffs(entity, reg)
            want_ids.add(str(x))
            want_tags.add(str(x))

    removed: List[str] = []
    kept: List[Dict[str, Any]] = []
    for s in statuses:
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        match = False
        if sid in want_ids:
            match = True
        cat = str(defn.get("category") or s.get("category") or "")
        if cat in want_tags or sid in want_tags:
            match = True
        for t in defn.get("cleanse_tags") or []:
            if str(t) in want_tags:
                match = True
                break
        if item_id:
            cleansed_by = [str(x) for x in (defn.get("cleansed_by") or [])]
            if str(item_id) in cleansed_by:
                match = True
        if match:
            removed.append(sid)
        else:
            kept.append(s)
    entity["statuses"] = kept
    return removed


def clear_all_debuffs(
    entity: MutableMapping[str, Any], reg: Optional[DataRegistry] = None
) -> List[str]:
    statuses = ensure_statuses(entity)
    removed: List[str] = []
    kept: List[Dict[str, Any]] = []
    for s in statuses:
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        kind = str(defn.get("kind") or s.get("kind") or "debuff")
        if kind == "debuff":
            removed.append(sid)
        else:
            kept.append(s)
    entity["statuses"] = kept
    return removed


def _entry_skip(
    entry: Mapping[str, Any],
    defn: Mapping[str, Any],
    rng: random.Random,
) -> bool:
    if entry.get("skip_action") or defn.get("skip_action"):
        return True
    chance = float(
        entry.get("skip_action_chance")
        if entry.get("skip_action_chance") is not None
        else defn.get("skip_action_chance") or 0
    )
    if chance > 0 and rng.random() < chance:
        return True
    return False


def active_status_mods(
    entity: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> Dict[str, float]:
    """Aggregate combat modifiers from active status entries (buffs)."""
    atk_flat = 0.0
    dmg_taken_mult = 1.0
    for s in entity.get("statuses") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        atk_flat += float(
            s.get("atk_flat")
            if s.get("atk_flat") is not None
            else defn.get("atk_flat") or 0
        )
        raw_m = s.get("dmg_taken_mult")
        if raw_m is None:
            raw_m = defn.get("dmg_taken_mult")
        if raw_m is not None:
            dmg_taken_mult *= float(raw_m)
    return {
        "atk_flat": atk_flat,
        "dmg_taken_mult": max(0.4, min(1.5, dmg_taken_mult)),
    }


def process_status_turn(
    entity: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
    *,
    apply_dot: bool = True,
    min_hp: int = 1,
    target_label: str = "",
) -> StatusTickResult:
    """
    One status resolution step (combat end of side / field tick):
    1) decide skip_action from control debuffs
    2) apply DoT (tick_hp) or buff ticks (heal / mana)
    3) decrement remaining; drop expired
    """
    rng = rng or random.Random()
    result = StatusTickResult()
    statuses = ensure_statuses(entity)
    if not statuses:
        return result

    # skip check — debuffs / control only
    for s in statuses:
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        kind = str(defn.get("kind") or s.get("kind") or "debuff")
        if kind == "buff":
            continue
        if _entry_skip(s, defn, rng):
            result.skip_action = True
            break

    kept: List[Dict[str, Any]] = []
    total_dmg = 0
    for s in statuses:
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        nm = status_display_name(reg, sid)
        kind = str(defn.get("kind") or s.get("kind") or "debuff")
        thp = int(s.get("tick_hp") if s.get("tick_hp") is not None else defn.get("tick_hp") or 0)
        theal = int(
            s.get("tick_heal")
            if s.get("tick_heal") is not None
            else defn.get("tick_heal") or 0
        )
        tmana = int(
            s.get("tick_mana")
            if s.get("tick_mana") is not None
            else defn.get("tick_mana") or 0
        )

        if apply_dot and kind != "buff" and thp > 0:
            if "hp" in entity:
                entity["hp"] = max(min_hp, int(entity.get("hp", 0)) - thp)
            total_dmg += thp
            result.ticked.append(sid)
            narr_key = str(defn.get("narrative_tick") or f"status_tick_{sid}")
            result.narrative_events.append(
                {"key": narr_key, "status": sid, "dmg": thp, "name": nm}
            )
            result.notes.append(f"[สถานะ] {nm} −{thp} HP")
        elif apply_dot and kind == "buff":
            if theal > 0 and "hp" in entity:
                max_hp = int(entity.get("max_hp") or entity.get("hp") or 1)
                entity["hp"] = min(max_hp, int(entity.get("hp", 0)) + theal)
                result.ticked.append(sid)
                narr_key = str(defn.get("narrative_tick") or f"status_tick_{sid}")
                result.narrative_events.append(
                    {"key": narr_key, "status": sid, "heal": theal, "name": nm}
                )
                result.notes.append(f"[บัฟ] {nm} +{theal} HP")
            if tmana > 0 and "mana" in entity:
                max_m = int(entity.get("max_mana") or entity.get("mana") or 1)
                entity["mana"] = min(max_m, int(entity.get("mana", 0)) + tmana)
                if sid not in result.ticked:
                    result.ticked.append(sid)
                result.notes.append(f"[บัฟ] {nm} +{tmana} MP")

        rem = int(s.get("remaining", 1)) - 1
        if rem > 0:
            kept.append({**s, "remaining": rem})
        else:
            result.expired.append(sid)
            result.narrative_events.append(
                {"key": "status_expire", "status": sid, "name": nm}
            )
            label = "บัฟ" if kind == "buff" else "สถานะ"
            result.notes.append(f"[{label}] {nm} จางลง")

    entity["statuses"] = kept
    result.damage = total_dmg
    return result


def tick_field_statuses(
    entity: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> StatusTickResult:
    """Field regen / rest — DoT + decrement, no skip_action meaning."""
    return process_status_turn(
        entity, reg, rng, apply_dot=True, min_hp=1, target_label="you"
    )


def should_skip_action(
    entity: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> bool:
    rng = rng or random.Random()
    for s in entity.get("statuses") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        defn = get_status_def(reg, sid)
        if _entry_skip(s, defn, rng):
            return True
    return False
