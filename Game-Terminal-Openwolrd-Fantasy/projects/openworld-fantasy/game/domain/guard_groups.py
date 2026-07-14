"""
DD2 — guard skill groups for soft combat UI.

Players pick: กันกาย · กันเวท · กันธาตุ · ไม่กัน
Real skill ids stay hidden; engine maps group → owned defense skills.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# UI group order (menu 1..3)
GUARD_GROUPS: Tuple[str, ...] = ("physical", "arcane", "elemental")

GUARD_GROUP_LABELS: Dict[str, str] = {
    "physical": "กันกาย",
    "arcane": "กันเวท",
    "elemental": "กันธาตุ",
    "universal": "กันรอบด้าน",
}

GUARD_GROUP_HINTS: Dict[str, str] = {
    "physical": "รับแรงกระแทก · ดาบ ธนู กระแทก",
    "arcane": "ม่านเวท · ลูกไฟ กระสุนเวท",
    "elemental": "ธาตุ/แสง-มืด · น้ำ ดิน เงา",
    "universal": "รับได้หลายชั้น (แผ่ว)",
}

# Heuristic: map strong_vs tags → default guard_class when YAML omits it
_PHYSICAL_TAGS = frozenset(
    {"physical", "slash", "pierce", "blunt", "wind", "nature"}
)
_ARCANE_TAGS = frozenset(
    {"arcane", "magic", "fire", "lightning", "ice", "water"}
)
_ELEMENTAL_TAGS = frozenset(
    {
        "fire",
        "water",
        "wind",
        "earth",
        "ice",
        "lightning",
        "heat",
        "burn",
        "shadow",
        "holy",
        "light",
        "dark",
        "nature",
    }
)


def resolve_guard_class(skill: Optional[Mapping[str, Any]]) -> str:
    """physical | arcane | elemental | universal."""
    if not skill:
        return "physical"
    raw = str(skill.get("guard_class") or "").strip().lower()
    if raw in ("physical", "arcane", "elemental", "universal", "magic"):
        return "arcane" if raw == "magic" else raw
    strong = {str(t).lower() for t in (skill.get("strong_vs") or [])}
    if not strong:
        return "physical"
    # pure physical
    if strong <= _PHYSICAL_TAGS and not (strong & {"arcane", "magic", "fire", "lightning", "shadow", "holy"}):
        return "physical"
    # pure arcane/magic channel
    if strong & {"arcane", "magic"} and not (strong & {"physical", "shadow", "holy", "earth"}):
        return "arcane"
    # many element-ish or light/dark
    if strong & {"shadow", "holy", "earth", "water", "fire", "lightning"}:
        # if also lots of physical + elements → physical-leaning hybrid
        if strong & {"physical"} and len(strong & _ELEMENTAL_TAGS) <= 1:
            return "physical"
        if strong & {"arcane", "magic", "fire", "lightning"} and not (strong & {"earth", "water", "shadow"}):
            return "arcane"
        return "elemental"
    if strong & _ARCANE_TAGS:
        return "arcane"
    if strong & _ELEMENTAL_TAGS:
        return "elemental"
    if len(strong) >= 4:
        return "universal"
    return "physical"


def defense_skills_list(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Tuple[str, Dict[str, Any]]]:
    """All usable defense skills (guard_basic always if in catalog)."""
    from game.domain.skill_charges import is_skill_usable

    out: List[Tuple[str, Dict[str, Any]]] = []
    owned = set(player.get("skills") or [])
    seen = set()
    # prioritize known guards first
    preferred = [
        "guard_basic",
        "guard_water_veil",
        "guard_earth",
        "guard_shadow",
        "counter_guard",
        "blessing_ward",
        "mage_mana_shield",
        "archer_evade_veil",
        "warrior_bastion",
        "priest_sanctuary",
        "unit_aegis_wall",
    ]
    for sid in preferred:
        if sid not in reg.skills:
            continue
        if sid != "guard_basic" and sid not in owned:
            continue
        if sid != "guard_basic" and not is_skill_usable(player, sid):
            continue
        sk = dict(reg.skills[sid])
        sk.setdefault("id", sid)
        out.append((sid, sk))
        seen.add(sid)
    for sid in player.get("skills") or []:
        if sid in seen:
            continue
        sk = reg.skills.get(sid)
        if not sk or sk.get("slot") != "defense":
            continue
        if not is_skill_usable(player, sid):
            continue
        skd = dict(sk)
        skd.setdefault("id", sid)
        out.append((sid, skd))
        seen.add(sid)
    return out


def skills_by_guard_group(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
    """Map guard group → list of (id, skill). Universal appears in all three UI groups softly."""
    groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {
        g: [] for g in GUARD_GROUPS
    }
    for sid, sk in defense_skills_list(player, reg):
        gclass = resolve_guard_class(sk)
        if gclass == "universal":
            for g in GUARD_GROUPS:
                groups[g].append((sid, sk))
        elif gclass in groups:
            groups[gclass].append((sid, sk))
        else:
            groups["physical"].append((sid, sk))
    return groups


def group_menu_rows(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """
    Soft rows for combat UI.
    Each: {key, label, hint, count, skills}
    Only groups with at least 1 skill (physical always has guard_basic).
    """
    by = skills_by_guard_group(player, reg)
    rows: List[Dict[str, Any]] = []
    for g in GUARD_GROUPS:
        skills = by.get(g) or []
        if not skills:
            continue
        rows.append(
            {
                "key": g,
                "label": GUARD_GROUP_LABELS.get(g, g),
                "hint": GUARD_GROUP_HINTS.get(g, ""),
                "count": len(skills),
                "skills": skills,
            }
        )
    return rows


def pick_skill_in_group(
    player: Mapping[str, Any],
    reg: DataRegistry,
    group: str,
    *,
    skill_index: Optional[int] = None,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Choose one skill from group. Default: lowest mana cost that player can pay.
    skill_index: 0-based into group's skill list (after filter affordable prefer).
    """
    by = skills_by_guard_group(player, reg)
    g = str(group or "physical").lower()
    if g == "magic":
        g = "arcane"
    skills = list(by.get(g) or [])
    if not skills:
        return None
    mana = int(player.get("mana") or 0)
    affordable = [
        (sid, sk)
        for sid, sk in skills
        if int(sk.get("cost_mana") or 0) <= mana
    ]
    pool = affordable if affordable else skills  # show fail later on mana
    # unique by sid preserve order
    seen = set()
    uniq: List[Tuple[str, Dict[str, Any]]] = []
    for sid, sk in pool:
        if sid in seen:
            continue
        seen.add(sid)
        uniq.append((sid, sk))
    uniq.sort(key=lambda x: (int(x[1].get("cost_mana") or 0), x[0]))
    if skill_index is not None and 0 <= skill_index < len(uniq):
        return uniq[skill_index]
    return uniq[0] if uniq else None


def apply_defense_with_class(
    incoming: int,
    attack_tags: Sequence[str],
    guard_skill: Optional[Mapping[str, Any]],
    *,
    damage_class: Optional[str] = None,
    reg: Any = None,
) -> Tuple[int, str, str]:
    """
    Tag matchups (strong/weak) + soft guard_class vs damage_class (DD2).
    Returns (final_dmg, grade, soft_msg).
    """
    if not guard_skill:
        return incoming, "none", "ไม่ป้องกัน"

    from game.domain.damage_class import resolve_damage_class

    tags = {str(t).lower() for t in attack_tags}
    strong = {str(t).lower() for t in (guard_skill.get("strong_vs") or [])}
    weak = {str(t).lower() for t in (guard_skill.get("weak_vs") or [])}
    gclass = resolve_guard_class(guard_skill)
    aclass = damage_class or resolve_damage_class(
        None, tags=list(attack_tags), reg=reg
    )
    name = str(guard_skill.get("name") or "การป้องกัน")

    if tags & strong:
        mult = float(guard_skill.get("damage_mult_strong", 0.1))
        grade = "strong"
        msg = f"★ {name} ได้ผลดี!"
    elif tags & weak:
        mult = float(guard_skill.get("damage_mult_weak", 0.9))
        grade = "weak"
        msg = f"✗ {name} แทบไม่มีผล..."
    else:
        mult = float(guard_skill.get("damage_mult_neutral", 0.55))
        grade = "neutral"
        msg = f"· {name} กันได้บางส่วน"
        # class soft adjust
        if gclass == "universal":
            mult = min(mult, mult * 0.92)
            msg = f"· {name} รับรอบด้าน (แผ่ว)"
            grade = "class_soft"
        elif gclass == aclass or (
            gclass == "elemental"
            and aclass in ("arcane", "light", "dark", "physical")
            and tags & _ELEMENTAL_TAGS
        ):
            # class match → better than neutral
            mult = max(
                float(guard_skill.get("damage_mult_strong", 0.15)),
                mult * 0.72,
            )
            grade = "class_match"
            if gclass == "physical":
                msg = f"★ เกราะรับชั้นกาย — {name}"
            elif gclass == "arcane":
                msg = f"★ ม่านกลืนเวท — {name}"
            else:
                msg = f"★ กันธาตุสัมผัส — {name}"
        elif (
            (gclass == "physical" and aclass in ("arcane", "light", "dark"))
            or (gclass == "arcane" and aclass == "physical")
            or (gclass == "elemental" and aclass == "physical" and not (tags & _ELEMENTAL_TAGS))
        ):
            mult = min(
                0.95,
                max(float(guard_skill.get("damage_mult_weak", 0.9)), mult * 1.35),
            )
            grade = "class_miss"
            if gclass == "physical":
                msg = f"✗ เกราะไม่ช่วยชั้นนั้น — {name}"
            elif gclass == "arcane":
                msg = f"✗ ม่านไม่รับกาย — {name}"
            else:
                msg = f"✗ กันธาตุไม่ตรงจังหวะ — {name}"

    final = max(0, int(round(incoming * mult)))
    if grade in ("strong", "class_match") and final <= 2 and incoming > 0:
        final = 0 if mult <= 0.12 else final
    return final, grade, msg


def format_guard_group_box_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Sectioned lines for render_box."""
    rows = group_menu_rows(player, reg)
    lines = [
        " ป้องกัน",
        "---",
        " ศัตรูจะโจมตี — เลือกชั้นการกัน (ไม่โชว์สูตร)",
        "---",
    ]
    for i, row in enumerate(rows, 1):
        n = int(row["count"])
        hint = str(row.get("hint") or "")
        # compact: count soft, not skill ids
        extra = f"  ·{n} ท่า" if n > 1 else ""
        lines.append(f"  {i}  {row['label']:<8}{extra}")
        if hint:
            lines.append(f"       {hint}")
    lines.extend(["---", "  0  ไม่ป้องกัน"])
    return lines
