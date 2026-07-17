"""
WO-013: Structured combat turn log (T# ▸ / ◂) + short Fight Report.

Compact default for Continuous Auto; dense for Step/debug.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

# damage class → short God tag
CLASS_TAGS = {
    "physical": "กาย",
    "arcane": "เวท",
    "light": "แสง",
    "dark": "มืด",
    "poison": "พิษ",
    "true": "แท้",
}

ELEMENT_TAGS = {
    "physical": "กาย",
    "fire": "ไฟ",
    "water": "น้ำ",
    "ice": "น้ำแข็ง",
    "lightning": "สายฟ้า",
    "wind": "ลม",
    "earth": "ดิน",
    "shadow": "เงา",
    "holy": "ศักดิ์สิทธิ์",
    "arcane": "เวท",
    "nature": "ธรรมชาติ",
    "poison": "พิษ",
}


def clear_fight_log(player: MutableMapping[str, Any]) -> None:
    player["_fight_log"] = []
    player["_fight_log_meta"] = {
        "attacks": 0,
        "skills": 0,
        "potions": 0,
        "party": 0,
        "incoming": 0,
        "guards": 0,
    }


def ensure_fight_log(player: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
    raw = player.get("_fight_log")
    if not isinstance(raw, list):
        player["_fight_log"] = []
        return player["_fight_log"]  # type: ignore[return-value]
    return raw  # type: ignore[return-value]


def _meta(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    m = player.get("_fight_log_meta")
    if not isinstance(m, dict):
        m = {
            "attacks": 0,
            "skills": 0,
            "potions": 0,
            "party": 0,
            "incoming": 0,
            "guards": 0,
        }
        player["_fight_log_meta"] = m
    return m


def damage_tag(
    *,
    damage_class: Optional[str] = None,
    elements: Optional[Sequence[str]] = None,
    reg: Any = None,
) -> str:
    """〔กาย〕〔เวท〕… from damage_class or first element."""
    dc = str(damage_class or "").lower()
    if not dc and elements:
        el0 = str(elements[0]).lower()
        try:
            from game.domain.damage_class import resolve_damage_class

            dc = str(
                resolve_damage_class({"elements": list(elements)}, tags=list(elements), reg=reg)
                or ""
            )
        except Exception:
            dc = ""
        if not dc:
            return ELEMENT_TAGS.get(el0, el0[:4] if el0 else "?")
    if dc in CLASS_TAGS:
        return CLASS_TAGS[dc]
    if elements:
        return ELEMENT_TAGS.get(str(elements[0]).lower(), str(elements[0])[:4])
    return "?"


def format_turn_line(
    turn: int,
    *,
    outbound: bool,
    actor: str,
    action: str,
    target: str = "",
    dmg: Optional[int] = None,
    tag: str = "",
    note: str = "",
) -> str:
    """
    T3 ▸ คุณ 「Fire Ball」→ ??? 〔เวท〕24
    T3 ◂ ??? 「กรงเล็บ」→ คุณ 〔กาย〕18 (กัน −35%)
    """
    arrow = "▸" if outbound else "◂"
    act = str(action or "").strip()
    if act and not act.startswith("「"):
        act = f"「{act}」"
    bits = [f"T{int(turn)} {arrow} {actor}"]
    if act:
        bits.append(act)
    if target:
        bits.append(f"→ {target}" if outbound or dmg is not None else target)
    if dmg is not None:
        tag_s = f"〔{tag}〕" if tag else ""
        bits.append(f"{tag_s}{int(dmg)}")
    line = " ".join(bits)
    if note:
        line = f"{line}  ({note})"
    return line


def log_fight_event(
    player: MutableMapping[str, Any],
    turn: int,
    *,
    outbound: bool,
    actor: str,
    action: str,
    target: str = "",
    dmg: Optional[int] = None,
    tag: str = "",
    note: str = "",
    kind: str = "hit",
) -> str:
    """Append structured event; return formatted line."""
    line = format_turn_line(
        turn,
        outbound=outbound,
        actor=actor,
        action=action,
        target=target,
        dmg=dmg,
        tag=tag,
        note=note,
    )
    buf = ensure_fight_log(player)
    buf.append(
        {
            "t": int(turn),
            "out": bool(outbound),
            "actor": actor,
            "action": action,
            "target": target,
            "dmg": dmg,
            "tag": tag,
            "note": note,
            "kind": kind,
            "line": line,
        }
    )
    # cap ring
    if len(buf) > 80:
        player["_fight_log"] = buf[-80:]
    meta = _meta(player)
    if kind == "potion":
        meta["potions"] = int(meta.get("potions") or 0) + 1
    elif kind == "party":
        meta["party"] = int(meta.get("party") or 0) + 1
    elif kind == "guard":
        meta["guards"] = int(meta.get("guards") or 0) + 1
    elif outbound and dmg is not None:
        if kind == "skill":
            meta["skills"] = int(meta.get("skills") or 0) + 1
        else:
            meta["attacks"] = int(meta.get("attacks") or 0) + 1
    elif not outbound and dmg is not None:
        meta["incoming"] = int(meta.get("incoming") or 0) + 1
    return line


def recent_fight_lines(player: Mapping[str, Any], *, limit: int = 8) -> List[str]:
    buf = list(player.get("_fight_log") or [])
    return [str(e.get("line") or "") for e in buf[-limit:] if e.get("line")]


def _soft_enemy_short(name: str, *, max_w: int = 28) -> str:
    """
    Shorten long floor-boss display names for vitals / Auto / report.

    Prefer Thai title; strip rarity glyphs and (ระดับ).
    e.g. "ผู้เฝ้าชั้น · ◇Ruins Specter (สูง)" → "ผู้เฝ้าชั้น · Specter"
    """
    from game.ui_terminal.layout import display_width

    s = str(name or "???").strip()
    # drop rarity / tier parens first
    if "(" in s and s.rstrip().endswith(")"):
        s = s.rsplit("(", 1)[0].strip()
    # strip diamond / star rarity glyphs
    for g in ("◇", "◆", "★", "☆", "✦", "✧", "●", "○"):
        s = s.replace(g, "")
    s = " ".join(s.split())
    if "·" in s:
        left, right = s.split("·", 1)
        left = left.strip()
        right = right.strip()
        # English multi-word class → keep last token (Ruins Specter → Specter)
        if right and all((ord(c) < 128) or c.isspace() or c in "-'_" for c in right):
            words = right.split()
            if len(words) > 1:
                right = words[-1]
        if right and display_width(f"{left} · {right}") > max_w:
            s = left or right
        else:
            s = f"{left} · {right}" if left and right else (left or right)
        if left and display_width(s) > max_w:
            s = left
    if display_width(s) <= max_w:
        return s
    out: List[str] = []
    w = 0
    for ch in s:
        cw = display_width(ch)
        if w + cw > max_w - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def _trunc_log_line(ln: str, *, max_w: int = 52) -> str:
    from game.ui_terminal.layout import display_width

    s = str(ln or "").strip()
    # compress party assist headers
    if "ซุ่มช่วย" in s and "→" in s:
        s = s.split("→")[0].strip() + " → …"
    if display_width(s) <= max_w:
        return s
    out: List[str] = []
    w = 0
    for ch in s:
        cw = display_width(ch)
        if w + cw > max_w - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def format_fight_report(
    player: Mapping[str, Any],
    *,
    outcome: str,
    enemy_name: str = "???",
    defeat_line: str = "",
    dense: bool = False,
) -> List[str]:
    """
    5–8 line Fight Report for end of combat (WO-013).
    outcome: win | loss | flee
    """
    meta = player.get("_fight_log_meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    oc = str(outcome or "").lower()
    oc_th = {
        "win": "ชนะ",
        "loss": "แพ้ — สลบ (Soft Death)",
        "flee": "หนีสำเร็จ",
    }.get(oc, oc or "?")
    en = _soft_enemy_short(enemy_name)

    lines: List[str] = [
        " สรุปไฟต์",
        "---",
        f" ผล      {oc_th}",
        f" ศัตรู    {en}",
        "---",
        " แอคชัน",
        f"  โจมตี {int(meta.get('attacks', 0) or 0)}   "
        f"สกิล {int(meta.get('skills', 0) or 0)}   "
        f"ยา {int(meta.get('potions', 0) or 0)}   "
        f"ปาร์ตี้ {int(meta.get('party', 0) or 0)}",
    ]
    try:
        from game.domain.needs import format_combat_needs_compact

        lines.append("---")
        lines.append(" กายใจ")
        lines.append(f"  {format_combat_needs_compact(player)}")  # type: ignore[arg-type]
    except Exception:
        pass
    if oc == "loss" and defeat_line:
        lines.append("---")
        lines.append(f" {defeat_line}")
    elif player.get("_last_defeat") and oc == "loss":
        lines.append("---")
        lines.append(f" {player['_last_defeat'].get('line', '')}")

    log_n = 6 if dense else 4
    recent = recent_fight_lines(player, limit=log_n)
    if recent:
        lines.append("---")
        lines.append(" บันทึกย่อ (ล่าสุด)")
        for ln in recent:
            lines.append(f"  {_trunc_log_line(ln)}")
    return lines


def emit_fight_report(
    player: Mapping[str, Any],
    io: Any,
    *,
    outcome: str,
    enemy_name: str = "???",
    defeat_line: str = "",
    dense: bool = False,
) -> List[str]:
    from game.ui_terminal.layout import render_box

    lines = format_fight_report(
        player,
        outcome=outcome,
        enemy_name=enemy_name,
        defeat_line=defeat_line,
        dense=dense,
    )
    io.write_line()
    io.write_line(render_box(lines, double=False))
    return lines
