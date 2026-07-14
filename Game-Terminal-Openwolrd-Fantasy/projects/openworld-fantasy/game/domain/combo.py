"""Skill combo resolution — Combo 2.0: length by level, steep mana, fusions."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry


def combo_config(reg: DataRegistry) -> Dict[str, Any]:
    raw = getattr(reg, "fusions_cfg", None) or {}
    return {
        "max_combo_length": int(raw.get("max_combo_length", 6)),
        "mana_mult": list(raw.get("mana_mult") or [1.0, 1.12, 1.28, 1.48, 1.75, 2.10]),
        "power_mult": list(raw.get("power_mult") or [1.0, 1.10, 1.22, 1.38, 1.58, 1.85]),
        "fusions": list(raw.get("fusions") or []),
        "combo_length_by_level": list(raw.get("combo_length_by_level") or []),
        "pressure_per_long_combo": int(raw.get("pressure_per_long_combo") or 1),
    }


def max_combo_for_player(player: Mapping[str, Any], reg: DataRegistry) -> int:
    """How many skills can be chained — scales with level (+ unit mastery soft)."""
    cfg = combo_config(reg)
    hard = int(cfg["max_combo_length"])
    lv = int(player.get("level", 1))
    rows = list(cfg.get("combo_length_by_level") or [])
    allowed = 3
    if rows:
        for row in sorted(rows, key=lambda r: int(r.get("max_level", 999))):
            if lv <= int(row.get("max_level", 999)):
                allowed = int(row.get("max_combo", 3))
                break
        else:
            allowed = int(rows[-1].get("max_combo", hard))
    else:
        # fallback tiers
        if lv <= 9:
            allowed = 2
        elif lv <= 19:
            allowed = 3
        elif lv <= 34:
            allowed = 4
        elif lv <= 49:
            allowed = 5
        else:
            allowed = 6
    # unit mastery bonus: mastery>=3 → +1 combo length
    mastery = int(player.get("unit_mastery") or 0)
    if player.get("unit_class_id") and mastery >= 3:
        allowed += 1
    return max(1, min(hard, allowed))


def parse_combo_input(text: str, max_n: int = 3) -> List[int]:
    """Parse '1,2,3' or '1 2' into 1-based indices list."""
    text = text.replace(" ", ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    out: List[int] = []
    for p in parts[:max_n]:
        try:
            out.append(int(p))
        except ValueError:
            continue
    return out


def resolve_combo(
    skill_ids: Sequence[str],
    reg: DataRegistry,
    *,
    max_n: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build combo package: total mana, effective elements, power sum, flavor, status.
    """
    cfg = combo_config(reg)
    cap = int(max_n if max_n is not None else cfg["max_combo_length"])
    ids = list(skill_ids)[:cap]
    skills: List[Dict[str, Any]] = []
    for sid in ids:
        sk = reg.skills.get(sid)
        if not sk:
            continue
        if sk.get("slot") == "defense":
            continue
        if sk.get("combo_ok") is False and len(ids) > 1:
            if skills:
                break
        skills.append({**sk, "id": sid})

    if not skills:
        return {"ok": False, "reason": "no_skills"}

    n = len(skills)
    mana_table = cfg["mana_mult"]
    power_table = cfg["power_mult"]
    # extend tables if shorter than n
    while len(mana_table) < n:
        mana_table = list(mana_table) + [float(mana_table[-1]) * 1.15]
    while len(power_table) < n:
        power_table = list(power_table) + [float(power_table[-1]) * 1.12]
    mana_mult = float(mana_table[n - 1])
    power_mult = float(power_table[n - 1])

    base_mana = sum(int(s.get("cost_mana", 0)) for s in skills)
    total_mana = int(round(base_mana * mana_mult))

    if n == 1 and skills[0].get("heal"):
        return {
            "ok": True,
            "skills": skills,
            "total_mana": total_mana,
            "heal": int(skills[0]["heal"]),
            "power": 0,
            "elements": list(skills[0].get("elements") or []),
            "flavor": f"ใช้ {skills[0].get('name')}",
            "status": None,
            "status_chance": 0.0,
            "length": 1,
            "mana_mult": mana_mult,
        }

    power = sum(int(s.get("power", 0)) for s in skills if not s.get("heal"))
    power = int(round(power * power_mult))
    elements: List[str] = []
    for s in skills:
        for e in s.get("elements") or []:
            if e not in elements:
                elements.append(str(e))

    flavor_parts = [str(s.get("name")) for s in skills]
    flavor = " → ".join(flavor_parts)
    status = None
    status_chance = 0.0
    power_bonus = 0.0

    elem_seq = []
    for s in skills:
        el = list(s.get("elements") or [])
        if el:
            elem_seq.append(str(el[0]))

    # prefer longer fusion matches
    best_len = 0
    for fusion in cfg["fusions"]:
        seq = [str(x) for x in (fusion.get("sequence") or [])]
        if not seq:
            continue
        if _is_consecutive_subseq(elem_seq, seq) or elem_seq[: len(seq)] == seq:
            if len(seq) < best_len:
                continue
            best_len = len(seq)
            flavor = str(fusion.get("flavor") or flavor)
            result_el = list(fusion.get("result_elements") or [])
            if result_el:
                elements = result_el + [e for e in elements if e not in result_el]
            if fusion.get("result_status"):
                status = fusion.get("result_status")
                status_chance = float(fusion.get("status_chance") or 0.4)
            power_bonus = max(power_bonus, float(fusion.get("power_bonus") or 0))

    power = int(round(power * (1.0 + power_bonus)))

    return {
        "ok": True,
        "skills": skills,
        "total_mana": total_mana,
        "heal": 0,
        "power": power,
        "elements": elements,
        "flavor": flavor,
        "status": status,
        "status_chance": status_chance,
        "length": n,
        "mana_mult": mana_mult,
        "base_mana": base_mana,
    }


def preview_combo_mana(
    player: Mapping[str, Any],
    reg: DataRegistry,
    skill_ids: Sequence[str],
) -> Dict[str, Any]:
    """Preview cost before commit — for UI."""
    max_n = max_combo_for_player(player, reg)
    combo = resolve_combo(skill_ids, reg, max_n=max_n)
    if not combo.get("ok"):
        return combo
    have = int(player.get("mana") or 0)
    need = int(combo.get("total_mana") or 0)
    combo["can_afford"] = have >= need
    combo["mana_have"] = have
    return combo


def _is_consecutive_subseq(hay: Sequence[str], needle: Sequence[str]) -> bool:
    if len(needle) > len(hay):
        return False
    for i in range(len(hay) - len(needle) + 1):
        if list(hay[i : i + len(needle)]) == list(needle):
            return True
    return False


def defense_skills(player: Mapping[str, Any], reg: DataRegistry) -> List[Tuple[str, Dict[str, Any]]]:
    from game.domain.skill_charges import is_skill_usable

    out = []
    owned = set(player.get("skills") or [])
    for sid in ["guard_basic", "guard_water_veil", "guard_earth", "guard_shadow"]:
        if sid in reg.skills and (sid == "guard_basic" or sid in owned):
            if sid == "guard_basic" or is_skill_usable(player, sid):
                out.append((sid, reg.skills[sid]))
    for sid in player.get("skills") or []:
        sk = reg.skills.get(sid)
        if (
            sk
            and sk.get("slot") == "defense"
            and sid not in {x[0] for x in out}
            and is_skill_usable(player, sid)
        ):
            out.append((sid, sk))
    return out


def apply_defense(
    incoming: int,
    attack_tags: Sequence[str],
    guard_skill: Optional[Mapping[str, Any]],
) -> Tuple[int, str, str]:
    if not guard_skill:
        return incoming, "none", "ไม่ป้องกัน"

    tags = {str(t).lower() for t in attack_tags}
    strong = {str(t).lower() for t in (guard_skill.get("strong_vs") or [])}
    weak = {str(t).lower() for t in (guard_skill.get("weak_vs") or [])}

    if tags & strong:
        mult = float(guard_skill.get("damage_mult_strong", 0.1))
        grade = "strong"
        msg = f"★ {guard_skill.get('name')} ได้ผลดี!"
    elif tags & weak:
        mult = float(guard_skill.get("damage_mult_weak", 0.9))
        grade = "weak"
        msg = f"✗ {guard_skill.get('name')} แทบไม่มีผล..."
    else:
        mult = float(guard_skill.get("damage_mult_neutral", 0.55))
        grade = "neutral"
        msg = f"· {guard_skill.get('name')} กันได้บางส่วน"

    final = max(0, int(round(incoming * mult)))
    if grade == "strong" and final <= 2 and incoming > 0:
        final = 0 if mult <= 0.1 else final
    return final, grade, msg


def apply_player_defense_stat(incoming: int, player: Mapping[str, Any]) -> int:
    pdef = float(player.get("power_def", 5.0))
    reduce = pdef / (pdef + 45.0)
    dmg = max(0, int(round(incoming * (1.0 - min(0.55, reduce)))))
    # ward / buff damage taken mult (soft)
    try:
        from game.domain.status_fx import active_status_mods

        mult = float(active_status_mods(player, None).get("dmg_taken_mult") or 1.0)
        if mult != 1.0:
            dmg = max(0, int(round(dmg * mult)))
    except Exception:
        pass
    return dmg
