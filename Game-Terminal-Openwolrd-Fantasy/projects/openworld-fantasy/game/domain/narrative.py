"""
Narrative / atmosphere lines for combat and field situations.
Data-driven templates so players feel what is happening (damage, buffs, skills).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Union

from game.data_load.registry import DataRegistry


def _cfg(reg: Optional[DataRegistry]) -> Dict[str, Any]:
    if reg is None:
        return {}
    return dict(getattr(reg, "narrative", None) or {})


def narrative_enabled(reg: Optional[DataRegistry]) -> bool:
    cfg = _cfg(reg)
    return bool(cfg.get("enabled", True))


def status_display_name(status_id: str, reg: Optional[DataRegistry] = None) -> str:
    names = (_cfg(reg).get("status_names") or {}) if reg else {}
    return str(names.get(status_id) or status_id)


def status_feel(status_id: str, reg: Optional[DataRegistry] = None) -> str:
    feels = (_cfg(reg).get("status_feel") or {}) if reg else {}
    return str(feels.get(status_id) or feels.get("default") or "ความรู้สึกแปลกปลอม")


def damage_band(dmg: int, max_hp: int, reg: Optional[DataRegistry] = None) -> str:
    cfg = _cfg(reg)
    bands = cfg.get("damage_bands") or {
        "scratch": 0.05,
        "light": 0.12,
        "solid": 0.25,
        "heavy": 0.45,
        "devastating": 1.01,
    }
    ratio = float(dmg) / max(1, int(max_hp))
    order = ["scratch", "light", "solid", "heavy", "devastating"]
    for key in order:
        if ratio < float(bands.get(key, 1.0)):
            return key
    return "devastating"


def _pick(lines: Sequence[str], rng: Optional[random.Random] = None) -> str:
    if not lines:
        return ""
    rng = rng or random
    return str(rng.choice(list(lines)))


def _format(template: str, ctx: Mapping[str, Any]) -> str:
    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_Safe(**{k: ctx.get(k, "") for k in ctx}))
    except Exception:
        return template


def narrate(
    reg: Optional[DataRegistry],
    key: str,
    rng: Optional[random.Random] = None,
    **ctx: Any,
) -> List[str]:
    """
    Return 0–n narrative lines for event key.
    Always safe if data missing.
    """
    if reg is not None and not narrative_enabled(reg):
        return []
    cfg = _cfg(reg)
    pool = cfg.get(key)
    if not pool:
        return []
    if isinstance(pool, str):
        pool = [pool]
    if not isinstance(pool, list):
        return []
    # enrich status
    if "status" in ctx and "status_name" not in ctx:
        ctx = dict(ctx)
        ctx["status_name"] = status_display_name(str(ctx["status"]), reg)
        ctx["status_feel"] = status_feel(str(ctx["status"]), reg)
    line = _pick([str(x) for x in pool if x], rng)
    if not line:
        return []
    text = _format(line, ctx)
    prefix = str(cfg.get("prefix") or "  ")
    return [prefix + text]


def narrate_many(
    reg: Optional[DataRegistry],
    keys: Sequence[str],
    rng: Optional[random.Random] = None,
    **ctx: Any,
) -> List[str]:
    out: List[str] = []
    for k in keys:
        out.extend(narrate(reg, k, rng, **ctx))
    return out


def narrate_damage_out(
    reg: Optional[DataRegistry],
    dmg: int,
    enemy_max_hp: int,
    enemy_name: str,
    rng: Optional[random.Random] = None,
    *,
    elements: Optional[Sequence[str]] = None,
    crit: bool = False,
) -> List[str]:
    lines: List[str] = []
    if crit:
        lines.extend(narrate(reg, "player_crit", rng, enemy=enemy_name, dmg=dmg))
    band = damage_band(dmg, enemy_max_hp, reg)
    lines.extend(
        narrate(
            reg,
            f"damage_out_{band}",
            rng,
            dmg=dmg,
            enemy=enemy_name,
        )
    )
    if elements:
        el = str(elements[0]).lower()
        el_key = f"element_{el}"
        if el_key in _cfg(reg):
            lines.extend(narrate(reg, el_key, rng, enemy=enemy_name, dmg=dmg))
    return lines


def narrate_damage_in(
    reg: Optional[DataRegistry],
    dmg: int,
    player_max_hp: int,
    enemy_name: str,
    rng: Optional[random.Random] = None,
    *,
    guard_grade: Optional[str] = None,
    guard_skill_name: Optional[str] = None,
) -> List[str]:
    lines: List[str] = []
    if guard_grade == "strong":
        lines.extend(
            narrate(
                reg,
                "guard_strong",
                rng,
                skill=guard_skill_name or "ป้องกัน",
                grade=guard_grade,
                enemy=enemy_name,
                dmg=dmg,
            )
        )
    elif guard_grade == "weak":
        lines.extend(
            narrate(
                reg,
                "guard_weak",
                rng,
                skill=guard_skill_name or "ป้องกัน",
                grade=guard_grade,
                enemy=enemy_name,
                dmg=dmg,
            )
        )
    elif guard_grade == "neutral":
        lines.extend(
            narrate(
                reg,
                "guard_neutral",
                rng,
                skill=guard_skill_name or "ป้องกัน",
                grade=guard_grade,
                enemy=enemy_name,
                dmg=dmg,
            )
        )
    elif guard_grade in (None, "none"):
        lines.extend(narrate(reg, "guard_none", rng, enemy=enemy_name, dmg=dmg))

    band = damage_band(dmg, player_max_hp, reg)
    lines.extend(
        narrate(
            reg,
            f"damage_in_{band}",
            rng,
            dmg=dmg,
            enemy=enemy_name,
        )
    )
    return lines


def narrate_battle_open(
    reg: Optional[DataRegistry],
    enemy_name: str,
    rng: Optional[random.Random] = None,
    *,
    ambush: bool = False,
    boss: bool = False,
    known: bool = True,
) -> List[str]:
    lines: List[str] = []
    if ambush:
        lines.extend(narrate(reg, "battle_start_ambush", rng, enemy=enemy_name))
    elif boss:
        lines.extend(narrate(reg, "battle_start_boss", rng, enemy=enemy_name))
    else:
        lines.extend(narrate(reg, "battle_start", rng, enemy=enemy_name))
    if not known:
        lines.extend(narrate(reg, "unknown_foe", rng, enemy=enemy_name))
    return lines


def narrate_player_action(
    reg: Optional[DataRegistry],
    kind: str,
    rng: Optional[random.Random] = None,
    **ctx: Any,
) -> List[str]:
    """kind: basic | skill | combo | heal"""
    key = {
        "basic": "player_basic_attack",
        "skill": "player_skill",
        "combo": "player_combo",
        "heal": "player_heal",
    }.get(kind, "player_basic_attack")
    return narrate(reg, key, rng, **ctx)


def narrate_low_hp_warnings(
    reg: Optional[DataRegistry],
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    enemy_name: str,
    rng: Optional[random.Random] = None,
) -> List[str]:
    lines: List[str] = []
    php = int(player.get("hp") or 0)
    pmax = max(1, int(player.get("max_hp") or 1))
    if php / pmax <= 0.25 and php > 0:
        lines.extend(narrate(reg, "low_hp_player", rng, enemy=enemy_name))
    mhp = int(mon.get("hp") or 0)
    mmax = max(1, int(mon.get("max_hp") or 1))
    if mhp / mmax <= 0.3 and mhp > 0:
        lines.extend(narrate(reg, "low_hp_enemy", rng, enemy=enemy_name))
    return lines


def situation_strip(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    *,
    known: bool = True,
    reg: Optional[DataRegistry] = None,
) -> str:
    """One-line HUD atmosphere under HP bar."""
    bits: List[str] = []
    php = int(player.get("hp") or 0)
    pmax = max(1, int(player.get("max_hp") or 1))
    ratio = php / pmax
    if ratio <= 0.2:
        bits.append("คุณใกล้สิ้นแรง")
    elif ratio <= 0.5:
        bits.append("คุณบาดเจ็บ")
    else:
        bits.append("คุณยังมั่น")

    mhp = int(mon.get("hp") or 0)
    mmax = max(1, int(mon.get("max_hp") or 1))
    if known or mon.get("boss"):
        mr = mhp / mmax
        if mr <= 0.25:
            bits.append("ศัตรูใกล้พัง")
        elif mr <= 0.5:
            bits.append("ศัตรูสะเทือน")
        else:
            bits.append("ศัตรูยังแข็ง")
    else:
        bits.append("ศัตรูอ่านไม่ออก")

    mon_st = [
        (s.get("id") if isinstance(s, dict) else s) for s in (mon.get("statuses") or [])
    ]
    if mon_st:
        names = [status_display_name(str(s), reg) for s in mon_st if s]
        bits.append("ศัตรู:" + "/".join(names))
    p_st = [
        (s.get("id") if isinstance(s, dict) else s) for s in (player.get("statuses") or [])
    ]
    if p_st:
        names = [status_display_name(str(s), reg) for s in p_st if s]
        bits.append("คุณ:" + "/".join(names))
    if player.get("blessings"):
        bits.append("บัฟ:" + ",".join(str(x) for x in (player.get("blessings") or [])[:2]))
    if player.get("party_call_active"):
        bits.append("ปาร์ตี้ถูกเรียก")
    return " · ".join(bits)


def emit_narrative(
    io: Any,
    lines: Sequence[str],
    *,
    max_lines: int = 3,
) -> None:
    """Write narrative lines with a soft cap (UIUX density P3/P5)."""
    n = 0
    cap = max(0, int(max_lines))
    for line in lines:
        if not line:
            continue
        if n >= cap:
            break
        io.write_line(line)
        n += 1


def area_mood(reg: Optional[DataRegistry], area_id: str, rng: Optional[random.Random] = None) -> List[str]:
    """Soft area atmosphere line."""
    key = f"area_mood_{area_id}"
    lines = narrate(reg, key, rng, area=area_id)
    if lines:
        return lines
    return narrate(reg, "field_night_feel", rng, area=area_id)


def narrate_field(
    reg: Optional[DataRegistry],
    event: str,
    rng: Optional[random.Random] = None,
    **ctx: Any,
) -> List[str]:
    """
    Field events: rest, explore, travel, library, party, loot, npc_*, etc.
    Keys are field_* or passed with field_ prefix auto.
    """
    key = event if event.startswith("field_") or event.startswith("npc_") or event.startswith("area_") or event.startswith("blessing_") else f"field_{event}"
    # area name resolve if area_id given
    if reg is not None and ctx.get("area_id") and not ctx.get("area"):
        ctx = dict(ctx)
        ctx["area"] = reg.area_name(str(ctx["area_id"])) if hasattr(reg, "area_name") else str(ctx["area_id"])
    return narrate(reg, key, rng, **ctx)


def field_enter_area(
    reg: Optional[DataRegistry],
    area_id: str,
    rng: Optional[random.Random] = None,
) -> List[str]:
    lines = narrate_field(reg, "travel", rng, area_id=area_id)
    lines.extend(area_mood(reg, area_id, rng))
    return lines
