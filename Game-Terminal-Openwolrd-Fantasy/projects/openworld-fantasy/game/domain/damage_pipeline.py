"""
WO-050 Damage Pipeline v1 — single adapter entry for outbound/inbound damage.

- Does not rewrite combat: wraps legacy formula + soft grade mult
- No raw numbers shown to player; soft flavor only
- No SSS high volatility / weakness recipes (deferred)
- Physical + magic (arcane/light/dark) share this path

Future hooks: elemental fusion, weakness recipes, appraisal (WO-051+)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# Soft outbound mult from player_grade (after temple). S ≈ +12%, SSS soft-capped.
_PLAYER_OUT_MULT: Dict[str, float] = {
    "F": 0.90,
    "E": 0.93,
    "D": 0.96,
    "C": 1.00,
    "B": 1.04,
    "A": 1.08,
    "S": 1.12,
    "SS": 1.14,
    "SSS": 1.15,
}

# Soft mult from axis letter (atk / magic / defense)
_AXIS_MULT: Dict[str, float] = {
    "F": 0.92,
    "E": 0.95,
    "D": 0.97,
    "C": 1.00,
    "B": 1.03,
    "A": 1.06,
    "S": 1.09,
    "SS": 1.11,
    "SSS": 1.12,
}

_TIER_DELTA: Dict[str, float] = {
    "early": -0.01,
    "mid": 0.0,
    "late": 0.015,
    "special": 0.025,
}

# Inbound: defense axis reduces incoming slightly
_DEF_IN_MULT: Dict[str, float] = {
    "F": 1.06,  # take more
    "E": 1.03,
    "D": 1.01,
    "C": 1.00,
    "B": 0.97,
    "A": 0.94,
    "S": 0.91,
    "SS": 0.89,
    "SSS": 0.88,
}

OUT_CLAMP = (0.85, 1.18)
IN_CLAMP = (0.82, 1.12)


@dataclass
class DamageResult:
    """Adapter result — amount + soft flavor; meta for tests only."""

    amount: int
    flavor: str = ""
    soft_notes: List[str] = field(default_factory=list)
    damage_class: str = "physical"
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_tuple(self) -> Tuple[int, str]:
        return int(self.amount), str(self.flavor or "")


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _axis_for_class(dmg_class: str, *, outbound: bool) -> str:
    """Which axis grade feeds this damage class."""
    dc = str(dmg_class or "physical").lower()
    if not outbound:
        return "defense"
    if dc in ("arcane", "light", "magic"):
        return "magic"
    if dc in ("dark",):
        # dark blends atk-leaning in damage_class outbound
        return "atk"
    return "atk"


def grade_outbound_mult(
    player: Mapping[str, Any],
    dmg_class: str = "physical",
) -> Tuple[float, Dict[str, Any]]:
    """
    Soft mult from player_grade + axis grade (+ tier).
    Before temple: player_grade neutral; axis still from hidden progress.
    """
    meta: Dict[str, Any] = {"revealed": False, "player_part": 1.0, "axis_part": 1.0}
    try:
        from game.domain.stat_grades import (
            axis_letter,
            axis_tier,
            grade_revealed,
        )

        revealed = grade_revealed(player)
        meta["revealed"] = revealed
        if revealed:
            pg = str(player.get("player_grade") or "C")
            p_m = float(_PLAYER_OUT_MULT.get(pg, 1.0))
            meta["player_grade"] = pg
            meta["player_part"] = p_m
        else:
            p_m = 1.0

        ax = _axis_for_class(dmg_class, outbound=True)
        letter = axis_letter(player, ax)
        tier = axis_tier(player, ax)
        a_m = float(_AXIS_MULT.get(letter, 1.0)) + float(_TIER_DELTA.get(tier, 0.0))
        meta["axis"] = ax
        meta["axis_letter"] = letter
        meta["axis_tier"] = tier
        meta["axis_part"] = a_m

        # blend: player identity + axis specialty
        if revealed:
            combined = p_m * 0.55 + a_m * 0.45
        else:
            # pre-temple: axis invest still soft-feeds damage slightly
            combined = 1.0 * 0.7 + a_m * 0.3
        combined = _clamp(combined, *OUT_CLAMP)
        meta["mult"] = combined
        return combined, meta
    except Exception:
        meta["mult"] = 1.0
        return 1.0, meta


def grade_inbound_mult(
    player: Mapping[str, Any],
    dmg_class: str = "physical",
) -> Tuple[float, Dict[str, Any]]:
    """Soft mult on damage taken from defense axis (+ light player_grade)."""
    meta: Dict[str, Any] = {"revealed": False}
    try:
        from game.domain.stat_grades import axis_letter, axis_tier, grade_revealed

        letter = axis_letter(player, "defense")
        tier = axis_tier(player, "defense")
        d_m = float(_DEF_IN_MULT.get(letter, 1.0))
        d_m += float(_TIER_DELTA.get(tier, 0.0)) * -0.5  # high tier = take less
        meta["axis_letter"] = letter
        meta["axis_tier"] = tier
        if grade_revealed(player):
            meta["revealed"] = True
            pg = str(player.get("player_grade") or "C")
            # slight toughness from overall grade
            p_tough = {
                "F": 1.03,
                "E": 1.02,
                "D": 1.01,
                "C": 1.00,
                "B": 0.98,
                "A": 0.96,
                "S": 0.94,
                "SS": 0.93,
                "SSS": 0.92,
            }.get(pg, 1.0)
            combined = d_m * 0.65 + p_tough * 0.35
            meta["player_grade"] = pg
        else:
            combined = d_m
        combined = _clamp(combined, *IN_CLAMP)
        meta["mult"] = combined
        return combined, meta
    except Exception:
        meta["mult"] = 1.0
        return 1.0, meta


def soft_presence_mult(player: Mapping[str, Any]) -> Tuple[float, Optional[str]]:
    """
    Light Anima / Relic soft presence on outbound damage.
    Returns (mult, optional soft log). Never large swings.
    """
    mult = 1.0
    note: Optional[str] = None
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 70:
            mult *= 1.03
            note = " ·จิตลึกมั่น"
        elif a >= 50:
            mult *= 1.01
        elif a < 25:
            mult *= 0.97
            note = " ·จิตแผ่ว"
    except Exception:
        pass
    # relic burden soft (existing flags)
    try:
        ba = str(player.get("_burden_active") or "")
        if ba == "crush":
            mult *= 0.96
            note = " ·ภาระหนักมือ"
        elif ba == "strain":
            mult *= 0.98
    except Exception:
        pass
    # soft bond resonance flag if present
    try:
        if player.get("_bond_resonance_active") or float(player.get("bond_resonance") or 0) >= 0.5:
            mult *= 1.02
            if note is None:
                note = " ·เรลิกร้องแผ่ว"
    except Exception:
        pass
    return _clamp(mult, 0.92, 1.06), note


def soft_outbound_log(
    meta: Mapping[str, Any],
    dmg_class: str,
    *,
    rng: Optional[random.Random] = None,
) -> Optional[str]:
    """Rare soft combat feel line — no numbers."""
    rng = rng or random.Random()
    m = float(meta.get("mult") or 1.0)
    dc = str(dmg_class or "physical").lower()
    is_magic = dc in ("arcane", "light", "magic")
    # only when meaningfully off-neutral or lucky soft
    if abs(m - 1.0) < 0.04 and rng.random() > 0.12:
        return None
    if m >= 1.08:
        return " ·พลังกายภาพไหลเวียนแรง" if not is_magic else " ·เวทไหลคมชัด"
    if m >= 1.04:
        return " ·คมขึ้นเล็กน้อย" if not is_magic else " ·เวทมั่นขึ้น"
    if m <= 0.93:
        return " ·แรงแผ่ว" if not is_magic else " ·เวทพร่า"
    if m <= 0.97:
        return " ·ยังไม่เต็มแรง"
    # slight chance flavor when near neutral but high letter
    letter = str(meta.get("axis_letter") or "")
    if letter in ("S", "SS", "SSS") and rng.random() < 0.2:
        return " ·เหนือมนุษย์แผ่ว"
    return None


def soft_inbound_log(meta: Mapping[str, Any], *, rng: Optional[random.Random] = None) -> Optional[str]:
    rng = rng or random.Random()
    m = float(meta.get("mult") or 1.0)
    if m <= 0.93 and rng.random() < 0.4:
        return " ·เกราะในตนรับได้"
    if m >= 1.04 and rng.random() < 0.35:
        return " ·ตัวบางต่อแรงนี้"
    return None


def _legacy_player_attack_core(
    player: Mapping[str, Any],
    monster: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
    skill: Optional[Mapping[str, Any]],
    rng: random.Random,
    power_override: Optional[int] = None,
    elements_override: Optional[Sequence[str]] = None,
) -> Tuple[int, str, str]:
    """
    Existing combat formula backend (moved from combat.player_attack_damage).
    Returns (dmg, flavor, damage_class).
    """
    if skill and not skill.get("_skill_rank") and skill.get("id"):
        try:
            from game.domain.skill_rank import scale_skill_for_player

            skill = scale_skill_for_player(
                player, skill, reg, skill_id=str(skill.get("id"))
            )
        except Exception:
            pass
    if skill and skill.get("heal") and power_override is None:
        return 0, "heal", "physical"
    try:
        from game.domain.skill_slots import normalize_slot

        if skill and normalize_slot(skill) == "buff" and power_override is None:
            return 0, "buff", "physical"
    except Exception:
        pass

    base = int(power_override if power_override is not None else (skill or {}).get("power", 8))
    base += int(player.get("bonus_atk", 0))
    try:
        from game.domain.status_fx import active_status_mods

        base += int(active_status_mods(player, reg).get("atk_flat") or 0)
    except Exception:
        pass

    sk_elems = list(
        elements_override
        if elements_override is not None
        else (skill or {}).get("elements")
        or ["physical"]
    )
    dclass = "physical"
    try:
        from game.domain.damage_class import outbound_power_bonus, resolve_damage_class

        dclass = resolve_damage_class(skill, elements=sk_elems, reg=reg)
        base += int(outbound_power_bonus(player, dclass, reg))
    except Exception:
        if any(
            e in sk_elems
            for e in ("arcane", "fire", "water", "holy", "lightning", "shadow")
        ):
            base += int(float(player.get("power_mag", 0)) * 0.35)
            dclass = "arcane"

    base += rng.randint(0, 5)
    elems = list(sk_elems)
    for t in player.get("gear_tags") or []:
        if t not in elems:
            elems.append(str(t))
    em = reg.element_mult(elems, list(monster.get("elements") or []))
    mon_st = [s.get("id") if isinstance(s, dict) else s for s in (monster.get("statuses") or [])]
    if "freeze" in mon_st and ("lightning" in elems or "fire" in elems):
        em *= 1.35

    # mastery mult (same formula as combat._mastery_mult — avoid circular import)
    mastery = (player.get("area_mastery") or {}).get(area_id, 10)
    mastery_m = 0.65 + (float(mastery) / 100.0) * 0.75
    mult = mastery_m * em
    if player.get("blessing_turns", 0) > 0:
        mult += 0.12
    mult += min(0.12, float(player.get("power_spd", 5)) / 200.0)
    try:
        from game.domain.needs import combat_needs_mults

        mult *= float(combat_needs_mults(player).get("atk_mult") or 1.0)
    except Exception:
        pass
    try:
        from game.domain.status_fx import active_status_mods

        am = active_status_mods(player, reg)
        mult *= float(am.get("atk_mult") or 1.0)
    except Exception:
        pass

    dmg = max(1, int(base * mult))
    crit_chance = float(player.get("crit_chance", 5))
    luck = float(player.get("luck_score") or 0.0)
    crit_chance = min(55.0, crit_chance * (1.0 + luck * 0.3))
    flavor = ""
    if rng.random() * 100 < crit_chance:
        dmg = int(dmg * 1.45)
        flavor = " (คริ!)"
    if em >= 1.25:
        flavor += " (ได้ผลดี!)"
    elif em <= 0.85:
        flavor += " (ต้านทาน...)"
    try:
        from game.domain.damage_class import resolve_damage_class, soft_class_label

        dc = resolve_damage_class(skill, elements=elems, reg=reg)
        dclass = dc or dclass
        if dc and flavor.count("(") < 2 and rng.random() < 0.35:
            sn = soft_class_label(dc, reg)
            if sn:
                flavor += f" ·{sn}"
    except Exception:
        pass
    return max(0, int(dmg)), flavor, dclass


def _legacy_incoming_core(
    player: MutableMapping[str, Any],
    raw_dmg: int,
    rng: random.Random,
) -> Tuple[int, str]:
    """Existing apply_incoming_damage body."""
    dmg = max(0, int(raw_dmg))
    if dmg <= 0:
        return 0, ""
    dodge = float(player.get("dodge_chance") or 3.0)
    luck = float(player.get("luck_score") or 0.0)
    dodge = min(40.0, max(0.0, dodge * (1.0 + luck * 0.25)))
    try:
        from game.domain.needs import combat_needs_mults

        nm = combat_needs_mults(player)
        dodge *= float(nm.get("dodge_mult") or 1.0)
        dmg = max(0, int(round(dmg * float(nm.get("incoming_mult") or 1.0))))
    except Exception:
        pass
    roll = rng.random() * 100
    if roll < dodge * 0.35:
        return 0, " (หลบพ้น!)"
    if roll < dodge:
        reduced = max(1, int(dmg * 0.55))
        return reduced, " (รับได้เบาลง)"
    def_b = int(player.get("alloc_def_bonus") or 0)
    dmg = max(1, dmg - def_b // 8)
    return dmg, ""


def resolve_player_outbound(
    player: Mapping[str, Any],
    monster: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
    skill: Optional[Mapping[str, Any]],
    rng: random.Random,
    power_override: Optional[int] = None,
    elements_override: Optional[Sequence[str]] = None,
) -> DamageResult:
    """
    Single entry: player → monster damage (physical / magic / hybrid classes).
    """
    raw, flavor, dclass = _legacy_player_attack_core(
        player,
        monster,
        reg,
        area_id,
        skill,
        rng,
        power_override=power_override,
        elements_override=elements_override,
    )
    if flavor in ("heal", "buff") or raw <= 0:
        return DamageResult(amount=raw, flavor=flavor, damage_class=dclass, meta={"skipped": True})

    g_mult, g_meta = grade_outbound_mult(player, dclass)
    p_mult, p_note = soft_presence_mult(player)
    total_mult = _clamp(g_mult * p_mult, *OUT_CLAMP)
    final = max(1, int(round(raw * total_mult)))

    soft_notes: List[str] = []
    slog = soft_outbound_log(g_meta, dclass, rng=rng)
    if slog:
        soft_notes.append(slog)
    if p_note and (abs(p_mult - 1.0) >= 0.02) and rng.random() < 0.45:
        soft_notes.append(p_note)

    # WO-051: soft appraisal combat hint (no numbers)
    try:
        from game.domain.appraisal import combat_appraise_hint

        ah = combat_appraise_hint(player, monster)
        if ah and rng.random() < 0.4:
            soft_notes.append(ah)
    except Exception:
        pass

    # WO-054: Soft Combat Identity + Weakness Lite (tiny mult + flavor)
    id_meta: Dict[str, Any] = {}
    try:
        from game.domain.combat_identity import apply_identity_to_outbound

        sk_els = list(
            elements_override
            if elements_override is not None
            else (skill or {}).get("elements")
            or []
        )
        final2, id_notes, id_meta = apply_identity_to_outbound(
            player,  # type: ignore[arg-type]
            monster,
            dmg_class=dclass,
            skill_elements=sk_els,
            area_id=area_id,
            reg=reg,
            rng=rng,
            raw_amount=final,
        )
        final = final2
        soft_notes.extend(id_notes)
    except Exception:
        id_meta = {}

    # keep flavor free of numbers; merge one soft note into flavor occasionally
    out_flavor = flavor
    if soft_notes and rng.random() < 0.55:
        out_flavor = flavor + soft_notes[0]

    return DamageResult(
        amount=final,
        flavor=out_flavor,
        soft_notes=soft_notes,
        damage_class=dclass,
        meta={
            "raw": raw,
            "grade_mult": g_mult,
            "presence_mult": p_mult,
            "total_mult": total_mult,
            "grade": g_meta,
            "identity": id_meta,
        },
    )


def resolve_player_inbound(
    player: MutableMapping[str, Any],
    raw_dmg: int,
    rng: random.Random,
    *,
    dmg_class: str = "physical",
    reg: Any = None,
    use_class_mitigation: bool = False,
) -> DamageResult:
    """
    Single entry: monster → player damage after dodge/def soft + grade defense.

    Class mitigation stays optional (combo path already uses damage_class
    separately — avoid double-mitigate by default).
    """
    pre = max(0, int(raw_dmg))
    class_fl = ""
    if use_class_mitigation:
        try:
            from game.domain.damage_class import apply_class_mitigation

            pre, class_fl = apply_class_mitigation(pre, player, dmg_class, reg)
        except Exception:
            pass

    mid, dodge_fl = _legacy_incoming_core(player, pre, rng)
    if mid <= 0:
        return DamageResult(
            amount=0,
            flavor=(class_fl or "") + (dodge_fl or ""),
            damage_class=dmg_class,
            meta={"dodged": True},
        )

    g_mult, g_meta = grade_inbound_mult(player, dmg_class)
    final = max(0, int(round(mid * g_mult)))
    if mid >= 1 and final == 0:
        final = 1

    soft_notes: List[str] = []
    ilog = soft_inbound_log(g_meta, rng=rng)
    if ilog:
        soft_notes.append(ilog)

    flavor = (class_fl or "") + (dodge_fl or "")
    if soft_notes and rng.random() < 0.4:
        flavor = flavor + soft_notes[0]

    return DamageResult(
        amount=final,
        flavor=flavor,
        soft_notes=soft_notes,
        damage_class=dmg_class,
        meta={
            "raw": raw_dmg,
            "after_class": pre,
            "after_dodge": mid,
            "grade_mult": g_mult,
            "grade": g_meta,
        },
    )


def resolve_monster_outbound(
    monster: Mapping[str, Any],
    profile: Mapping[str, Any],
    rng: random.Random,
) -> DamageResult:
    """
    Monster raw power path (backend). Grade not applied here —
    player inbound path applies defense grade.
    """
    power = int(profile.get("power") or monster.get("atk", 8))
    dmg = max(1, power + rng.randint(-2, 4))
    tags = list(profile.get("tags") or monster.get("elements") or ["physical"])
    dclass = "physical"
    try:
        from game.domain.damage_class import resolve_damage_class

        dclass = resolve_damage_class(profile, elements=tags, tags=tags)
    except Exception:
        pass
    return DamageResult(amount=dmg, flavor="", damage_class=dclass, meta={"monster": True})
