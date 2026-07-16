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
        "combo_mind": dict(raw.get("combo_mind") or {}),
    }


def max_combo_for_player(player: Mapping[str, Any], reg: DataRegistry) -> int:
    """
    How many skills can be chained.
    Base: level table · + focus_latent · + mind intellect · + unit mastery.
    (CM1 — formulas hidden from UI)
    """
    cfg = combo_config(reg)
    hard = int(cfg["max_combo_length"])
    # CM hard cap may be in combo_mind
    try:
        from game.domain.combo_mind import ensure_focus_latent

        ensure_focus_latent(player, reg)  # type: ignore[arg-type]
        cm = cfg.get("combo_mind") or {}
        if cm.get("hard_cap") is not None:
            hard = min(hard, int(cm["hard_cap"]))
    except Exception:
        pass
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
    # CM1: focus + intellect soft steps
    try:
        from game.domain.combo_mind import combo_step_bonuses

        fs, ms = combo_step_bonuses(player, reg)
        allowed += fs + ms
    except Exception:
        pass
    # unit mastery bonus: mastery>=3 → +1 combo length
    mastery = int(player.get("unit_mastery") or 0)
    if player.get("unit_class_id") and mastery >= 3:
        allowed += 1
    return max(1, min(hard, allowed))


def parse_combo_input(text: str, max_n: int = 3) -> List[int]:
    """
    Parse skill combo indices (1-based menu numbers).

    Preferred (UX): space-separated  ``2 1``  ``10 13 15``
    Also accepted:  commas  ``2,1`` · plus/slash  ``2+1``

    Never split glued digits: ``21`` is skill #21, not 2 then 1
    (future menus may list skills 10+).
    """
    import re

    raw = str(text or "").strip()
    if not raw:
        return []
    max_n = max(1, int(max_n or 1))

    # Split only on explicit separators (space, comma, ; + / | · -)
    # Do NOT split multi-digit numbers into single digits.
    parts = re.split(r"[\s,，;+/|·・\-–—]+", raw)
    out: List[int] = []
    for p in parts:
        if not p or not re.fullmatch(r"\d+", p):
            continue
        try:
            n = int(p)
        except ValueError:
            continue
        if n >= 1:
            out.append(n)
        if len(out) >= max_n:
            break
    return out[:max_n]


def resolve_combo(
    skill_ids: Sequence[str],
    reg: DataRegistry,
    *,
    max_n: Optional[int] = None,
    player: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build combo package: total mana, effective elements, power sum, flavor, status.
    Optional player enables SK-R2 rank scaling on skills in the chain.
    """
    cfg = combo_config(reg)
    cap = int(max_n if max_n is not None else cfg["max_combo_length"])
    ids = list(skill_ids)[:cap]
    skills: List[Dict[str, Any]] = []
    from game.domain.skill_rank import scale_skill_for_player
    from game.domain.skill_slots import is_combo_eligible, normalize_slot

    for sid in ids:
        sk = reg.skills.get(sid)
        if not sk:
            continue
        slot = normalize_slot(sk)
        if slot == "defense":
            continue
        # SK-R1: buff never chains; support heal solo only
        if not is_combo_eligible(sk) and len(ids) > 1:
            if skills:
                break
            # allow single non-combo skill alone
        if sk.get("combo_ok") is False and len(ids) > 1:
            if skills:
                break
        if player is not None:
            scaled = scale_skill_for_player(player, sk, reg, skill_id=sid)
            skills.append({**scaled, "id": sid})
        else:
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
    mind_mult = 1.0
    # CM2: intellect/focus tax × mag relief on top of length mult
    if player is not None:
        try:
            from game.domain.combo_mind import combo_mana_mind_multiplier

            mind_mult = float(combo_mana_mind_multiplier(player, reg))
            mana_mult = float(mana_mult) * mind_mult
        except Exception:
            mind_mult = 1.0

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
            "mind_mana_mult": mind_mult,
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
        "mind_mana_mult": mind_mult,
        "base_mana": base_mana,
    }


def preview_combo_mana(
    player: Mapping[str, Any],
    reg: DataRegistry,
    skill_ids: Sequence[str],
) -> Dict[str, Any]:
    """Preview cost before commit — for UI."""
    max_n = max_combo_for_player(player, reg)
    combo = resolve_combo(skill_ids, reg, max_n=max_n, player=player)
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
    """All usable defense skills (DD2 groups use guard_groups.skills_by_guard_group)."""
    from game.domain.guard_groups import defense_skills_list

    return defense_skills_list(player, reg)


def apply_defense(
    incoming: int,
    attack_tags: Sequence[str],
    guard_skill: Optional[Mapping[str, Any]],
    *,
    damage_class: Optional[str] = None,
    reg: Any = None,
) -> Tuple[int, str, str]:
    """Tag + soft guard_class match (DD2)."""
    from game.domain.guard_groups import apply_defense_with_class

    return apply_defense_with_class(
        incoming,
        attack_tags,
        guard_skill,
        damage_class=damage_class,
        reg=reg,
    )


def apply_player_defense_stat(
    incoming: int,
    player: Mapping[str, Any],
    *,
    attack_tags: Optional[Sequence[str]] = None,
    damage_class: Optional[str] = None,
    reg: Any = None,
) -> Tuple[int, str]:
    """
    Class-aware mitigation (DD1). Returns (dmg, soft_flavor).
    Legacy callers that expect int still work via first element if they unpack wrong —
    prefer the tuple form.
    """
    from game.domain.damage_class import apply_class_mitigation, resolve_damage_class

    dclass = damage_class
    if not dclass:
        dclass = resolve_damage_class(None, tags=attack_tags or [], reg=reg)
    dmg, flavor = apply_class_mitigation(incoming, player, dclass, reg)
    # ward / buff damage taken mult (soft)
    try:
        from game.domain.status_fx import active_status_mods

        mult = float(active_status_mods(player, None).get("dmg_taken_mult") or 1.0)
        if mult != 1.0:
            dmg = max(0, int(round(dmg * mult)))
    except Exception:
        pass
    return dmg, flavor
