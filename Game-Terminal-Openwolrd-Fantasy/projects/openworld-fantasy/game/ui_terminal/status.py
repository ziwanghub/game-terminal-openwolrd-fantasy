"""Status rendering L0 / L1c / L1 + mode chrome (docs/UIUX_TEXT.md)."""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from game.domain.bars import ratio_bar, xp_bar
from game.ui_terminal.layout import render_box


def render_mode_chrome(mode: str, detail: str = "") -> str:
    """Zone A — one-line mode label e.g. 〔สนาม〕 โลก default."""
    label = str(mode or "").strip() or "เกม"
    d = str(detail or "").strip()
    if d:
        return f"〔{label}〕 {d}"
    return f"〔{label}〕"


def render_status_l0(player: Mapping[str, Any], current_area: str) -> str:
    """Compact single-line strip (auto / tick)."""
    name = player.get("name", "?")
    level = player.get("level", 1)
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    return (
        f"{name} Lv.{level} · "
        f"HP [{ratio_bar(hp, max_hp)}] {hp}/{max_hp} · "
        f"MP [{ratio_bar(mana, max_mana)}] {mana}/{max_mana} · "
        f"{current_area}"
    )


def render_status_l1c(player: Mapping[str, Any], current_area: str) -> str:
    """Field-compact vitals (~4 lines). Default every field turn."""
    name = player.get("name", "?")
    level = player.get("level", 1)
    occ = player.get("occupation", "-")
    rank = player.get("occ_rank_title") or ""
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    pressure = int(player.get("pressure", 0) or 0)

    mastery = 0
    loc = player.get("location")
    area_mastery = player.get("area_mastery") or {}
    if loc and loc in area_mastery:
        mastery = int(area_mastery[loc])
    elif current_area in area_mastery:
        mastery = int(area_mastery[current_area])

    party = player.get("party") or []
    party_n = len(party) if isinstance(party, list) else 0
    head = f" {name}  Lv.{level} {occ}"
    if rank:
        head += f" · {rank}"

    lines = [
        head,
        f" HP [{ratio_bar(hp, max_hp)}] {hp}/{max_hp}  "
        f"MP [{ratio_bar(mana, max_mana)}] {mana}/{max_mana}  กดดัน {pressure}",
        f" เงิน โลก {player.get('money_world', 0)} · "
        f"สวรรค์ {player.get('money_heaven', 0)} · "
        f"นรก {player.get('money_hell', 0)}   "
        f"{current_area} · ชำนาญ {mastery}%   ปาร์ตี้ {party_n}/3",
    ]
    pts = int(player.get("stat_points") or 0)
    ppts = int(player.get("personality_points") or 0)
    hints: List[str] = []
    if pts > 0:
        hints.append(f"แต้มสถานะ {pts} (P)")
    if ppts > 0:
        hints.append(f"แต้มนิสัย {ppts} (N)")
    if hints:
        lines.append(" ✦ " + " · ".join(hints))
    # compact abnormal status line (if any)
    raw_st = player.get("statuses") or []
    if raw_st:
        try:
            from game.domain.status_fx import format_status_short

            st_line = format_status_short(player, None)
            if st_line and st_line != "-":
                lines.append(f" สถานะ {st_line}")
        except Exception:
            pass
    return render_box(lines, double=False)


def render_combat_vitals(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    *,
    known: bool = True,
    situation: str = "",
    round_no: Optional[int] = None,
) -> str:
    """Combat B/C zones — multi-line strip without heavy double box."""
    php = int(player.get("hp", 0))
    pmax = max(1, int(player.get("max_hp", 1)))
    pmp = int(player.get("mana", 0))
    pmm = max(1, int(player.get("max_mana", 1)))
    mhp = int(mon.get("hp", 0))
    mmax = max(1, int(mon.get("max_hp", 1)))
    mon_st = [
        s.get("name", s.get("id", s)) if isinstance(s, dict) else str(s)
        for s in (mon.get("statuses") or [])
    ]
    st_txt = f"  [{', '.join(str(x) for x in mon_st)}]" if mon_st else ""

    show_hp = known or bool(mon.get("boss"))
    if show_hp:
        e_line = (
            f" ศัตรู {mon.get('name', '???')}  "
            f"HP [{ratio_bar(mhp, mmax)}] {mhp}/{mmax}{st_txt}"
        )
    else:
        e_line = f" ศัตรู ???  HP ???/???{st_txt}"

    phase_txt = ""
    if mon.get("boss"):
        phase_txt = f" · เฟส {mon.get('phase', 1)}/{mon.get('max_phases', 1)}"

    lines: List[str] = []
    if round_no is not None:
        lines.append(f"── จังหวะ {round_no} ──{phase_txt}")
    elif phase_txt:
        lines.append(f"── ไฟต์{phase_txt} ──")
    lines.append(
        f" คุณ  HP [{ratio_bar(php, pmax)}] {php}/{pmax}  "
        f"MP [{ratio_bar(pmp, pmm)}] {pmp}/{pmm}"
    )
    lines.append(e_line)
    # ATB gauges — fill to act (rate formula never shown)
    try:
        from game.domain.combat_atb import format_atb_strip

        lines.append(format_atb_strip(player, mon))
    except Exception:
        pass
    if situation:
        lines.append(f"  ▸ {situation}")
    return "\n".join(lines)


def render_field_actions(
    *,
    stat_points: int = 0,
    personality_points: int = 0,
    boss_line: str = "",
) -> str:
    """EXPLORE mode action block (Mode Shell Phase A)."""
    from game.domain.mode_shell import MODE_EXPLORE, render_mode_actions

    return render_mode_actions(
        MODE_EXPLORE,
        stat_points=stat_points,
        personality_points=personality_points,
        boss_line=boss_line,
    )


def render_status_l1(player: Mapping[str, Any], current_area: str) -> str:
    name = player.get("name", "?")
    level = player.get("level", 1)
    occ = player.get("occupation", "-")
    zodiac = player.get("zodiac", "-")
    hp = int(player.get("hp", 0))
    max_hp = int(player.get("max_hp", 1))
    mana = int(player.get("mana", 0))
    max_mana = int(player.get("max_mana", 1))
    pressure = player.get("pressure", 0)
    xp_pct = float(player.get("xp_percent", player.get("exp", 0)) or 0)
    xp_cur = player.get("xp", player.get("exp", 0))
    xp_need = player.get("xp_needed", "?")

    mastery = 0
    # current_area may be display name; try mastery by location id first
    loc = player.get("location")
    area_mastery = player.get("area_mastery") or {}
    if loc and loc in area_mastery:
        mastery = area_mastery[loc]
    elif current_area in area_mastery:
        mastery = area_mastery[current_area]
    else:
        # fallback any
        for k, v in area_mastery.items():
            mastery = v
            break

    skills = player.get("skills") or []
    skill_txt = ", ".join(str(s) for s in skills) if skills else "-"
    if len(skill_txt) > 48:
        skill_txt = skill_txt[:45] + "..."

    statuses = player.get("statuses") or []
    st_txt = ", ".join(
        f"{s.get('name', s)}({s.get('remaining', '?')})" if isinstance(s, dict) else str(s)
        for s in statuses
    ) or "-"

    rank = player.get("occ_rank_title") or ""
    unit = player.get("unit_class_name") or ""
    pts = int(player.get("stat_points") or 0)
    alloc = player.get("stats_alloc") or {}
    path = player.get("occ_path") or ""
    head = f" {name}   Lv.{level} {occ}"
    if rank:
        head += f" · {rank}"
    if path:
        head += f" [{path}]"
    lines = [head + f"   ราศี{zodiac}"]
    if unit:
        lines.append(f" Unit: {unit}")
    if pts > 0:
        lines.append(f" แต้มสถานะค้าง: {pts} (กด P)")
    lines.extend(
        [
            f" XP  [{xp_bar(xp_pct)}] {xp_pct:.0f}%  ({xp_cur}/{xp_need})",
            "---",
            f" HP  [{ratio_bar(hp, max_hp)}] {hp}/{max_hp}",
            f" MP  [{ratio_bar(mana, max_mana)}] {mana}/{max_mana}",
            f" กดดัน {pressure}   สถานะ: {st_txt}",
            f" ลงทุน: โจม{alloc.get('atk', 0)} กัน{alloc.get('defense', 0)} "
            f"เวท{alloc.get('magic', 0)} เร็ว{alloc.get('speed', 0)} คริ{alloc.get('crit', 0)}",
            "---",
            f" เงิน  โลก {player.get('money_world', 0)} | "
            f"สวรรค์ {player.get('money_heaven', 0)} | "
            f"นรก {player.get('money_hell', 0)}",
            f" ที่   {current_area} (ชำนาญ {mastery}%)",
            f" สกิล  {skill_txt}",
        ]
    )

    equip = player.get("equip") or {}
    if equip.get("weapon"):
        socks = (player.get("sockets") or {}).get("weapon") or []
        filled = sum(1 for s in socks if s)
        lines.append(f" อาวุธ {equip['weapon']}" + (f"  การ์ด {filled}/{len(socks)}" if socks else ""))
    if equip.get("armor"):
        socks = (player.get("sockets") or {}).get("armor") or []
        filled = sum(1 for s in socks if s)
        lines.append(f" เกราะ {equip['armor']}" + (f"  การ์ด {filled}/{len(socks)}" if socks else ""))
    bag = player.get("card_bag") or []
    if bag:
        lines.append(f" การ์ดในถุง {len(bag)} ใบ")
    if player.get("gear_tags"):
        lines.append(f" แท็ก {', '.join(str(t) for t in player['gear_tags'])}")
    if player.get("active_sets"):
        lines.append(f" เซ็ต {', '.join(str(s) for s in player['active_sets'])}")
    blessings = player.get("blessings") or []
    if blessings:
        bt = player.get("blessing_turns", 0)
        lines.append(f" พร    {', '.join(str(b) for b in blessings)} (~{bt})")
    if player.get("disciple_of"):
        lines.append(f" ศิษย์ของ {player['disciple_of']}")

    others = player.get("other_players", 0)
    lines.append(f" ผู้เล่นอื่นในพื้นที่: {others} คน")
    lines.append(" เลเวลไม่จำกัด · ยิ่งสูง ยิ่งต้องใช้ XP มากขึ้น")

    return render_box(lines, double=True)
