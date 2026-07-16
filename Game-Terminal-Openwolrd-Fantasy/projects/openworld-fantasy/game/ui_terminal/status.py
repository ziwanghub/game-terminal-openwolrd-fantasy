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


def resolve_area_mastery(player: Mapping[str, Any], current_area: str = "") -> int:
    """
    Mastery % for status bars.
    In dungeon: prefer dungeon:id, then host area_id, then display name.
    """
    area_mastery = player.get("area_mastery") or {}
    if not isinstance(area_mastery, dict):
        return 0
    loc = str(player.get("location") or "")
    # dungeon run → host area + dungeon key
    run = player.get("dungeon_run")
    if isinstance(run, dict) and run.get("dungeon_id"):
        did = str(run.get("dungeon_id"))
        dkey = f"dungeon:{did}"
        if dkey in area_mastery:
            return int(area_mastery.get(dkey) or 0)
        aid = str(run.get("area_id") or "")
        if aid and aid in area_mastery:
            return int(area_mastery.get(aid) or 0)
    if loc and loc in area_mastery:
        return int(area_mastery.get(loc) or 0)
    if current_area and current_area in area_mastery:
        return int(area_mastery.get(current_area) or 0)
    return 0


def render_status_l0(player: Mapping[str, Any], current_area: str) -> str:
    """Compact single-line strip (auto / tick). God compact adds needs."""
    name = player.get("name", "?")
    level = player.get("level", 1)
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    base = (
        f"{name} Lv.{level} · "
        f"HP [{ratio_bar(hp, max_hp)}] {hp}/{max_hp} · "
        f"MP [{ratio_bar(mana, max_mana)}] {mana}/{max_mana} · "
        f"{current_area}"
    )
    try:
        from game.runtime.auto_run_log import is_god_compact

        if is_god_compact(player):
            from game.domain.needs import format_combat_needs_compact

            return f"{base} · {format_combat_needs_compact(player)}"
    except Exception:
        pass
    return base


def format_personal_hub_lines(
    player: Mapping[str, Any],
    current_area: str,
    *,
    mission_line: str = "",
) -> List[str]:
    """
    Single PERSONAL hub frame — no duplicated vitals/Tama/money/points.
    Sections: identity · vitals · place/money · tama · menu hints.
    """
    name = player.get("name", "?")
    level = player.get("level", 1)
    occ = player.get("occupation", "-")
    rank = player.get("occ_rank_title") or ""
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    pressure = int(player.get("pressure", 0) or 0)

    mastery = resolve_area_mastery(player, current_area)

    party = player.get("party") or []
    party_n = len(party) if isinstance(party, list) else 0
    head = f" {name}   Lv.{level}  {occ}"
    if rank:
        head += f" · {rank}"

    lines: List[str] = [
        " ตัวละคร",
        "---",
        head,
        "---",
    ]
    # WO-035: soft HP condition + compact vitals (visible shell)
    try:
        from game.domain.stat_arch import soft_hp_condition, ensure_stat_arch

        ensure_stat_arch(player)  # type: ignore[arg-type]
        lines.append(f" ชีพ  {soft_hp_condition(player)}")
        lines.append(
            f" HP  [{ratio_bar(hp, max_hp, width=8)}] {hp}/{max_hp}"
            f"   MP  [{ratio_bar(mana, max_mana, width=8)}] {mana}/{max_mana}"
        )
    except Exception:
        lines.append(
            f" HP  [{ratio_bar(hp, max_hp, width=8)}] {hp}/{max_hp}"
            f"   MP  [{ratio_bar(mana, max_mana, width=8)}] {mana}/{max_mana}"
        )
    if pressure:
        lines.append(f" กดดัน {pressure}")
    lines.append("---")
    # WO-006/007 + 035: Needs first (primary visible stats)
    try:
        from game.domain.needs import format_field_needs_block, format_tama_ascii

        lines.extend(format_field_needs_block(player, width=6, show_values=True))
        lines.append("---")
        lines.append(" Tama")
        for ln in format_tama_ascii(player, with_identity=False)[:6]:
            lines.append(ln)
    except Exception:
        try:
            from game.domain.needs import ensure_needs, format_needs_bar_line

            ensure_needs(player)  # type: ignore
            lines.append(" 【สถานะกายใจ】")
            lines.append(f" {format_needs_bar_line(player, width=6)}")
        except Exception:
            pass
    lines.append("---")
    lines.append(
        f" พื้นที่  {current_area}   ·  ชำนาญ {mastery}%   ·  ปาร์ตี้ {party_n}/3"
    )
    lines.append(
        f" เงิน     โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}"
    )
    # WO-024: soft divine burden
    try:
        ba = str(player.get("_burden_active") or "")
        if ba in ("strain", "crush"):
            lab = "ร้อนมือ" if ba == "strain" else "หนักเกินตัว"
            lines.append(f" ภาระเรลิก  {lab}")
    except Exception:
        pass
    # WO-038: one soft world-presence line
    try:
        from game.domain.world_relations import soft_world_presence_line

        loc = str(player.get("location") or "")
        lines.append(soft_world_presence_line(player, loc))
    except Exception:
        pass

    if mission_line:
        lines.append("---")
        lines.append(f" {str(mission_line).strip()}")

    pts = int(player.get("stat_points") or 0)
    ppts = int(player.get("personality_points") or 0)
    # WO-052: auto growth soft instead of "แต้ม → P"
    try:
        from game.domain.auto_growth import is_auto_growth_mode, soft_threshold_flag

        if is_auto_growth_mode(player):
            lines.append("---")
            bits = ["พลังไหลเอง → P"]
            if ppts > 0:
                bits.append(f"แต้มนิสัย {ppts} → N")
            lines.append(" ✦ " + "  ·  ".join(bits))
        elif pts > 0 or ppts > 0:
            lines.append("---")
            bits = []
            if pts > 0:
                bits.append(f"แต้มสถานะ {pts} → P")
            if ppts > 0:
                bits.append(f"แต้มนิสัย {ppts} → N")
            if soft_threshold_flag(player):
                bits.append("ใกล้ไหลเอง")
            lines.append(" ✦ " + "  ·  ".join(bits))
    except Exception:
        if pts > 0 or ppts > 0:
            lines.append("---")
            bits = []
            if pts > 0:
                bits.append(f"แต้มสถานะ {pts} → P")
            if ppts > 0:
                bits.append(f"แต้มนิสัย {ppts} → N")
            lines.append(" ✦ " + "  ·  ".join(bits))

    # WO-049/053: Grade Surface + Personal compact on hub
    try:
        from game.domain.stat_grades import grade_hub_compact_lines

        lines.append("---")
        lines.extend(grade_hub_compact_lines(player))
    except Exception:
        pass
    try:
        from game.domain.personal_system import format_personal_compact_lines

        lines.append("---")
        lines.extend(format_personal_compact_lines(player))
        lines.append("  (V = เรื่องของฉัน)")
    except Exception:
        pass

    raw_st = player.get("statuses") or []
    if raw_st:
        try:
            from game.domain.status_fx import format_status_short

            st_line = format_status_short(player, None)
            if st_line and st_line != "-":
                lines.append(f" สถานะ  {st_line}")
        except Exception:
            pass
    return lines


def render_status_l1c(player: Mapping[str, Any], current_area: str) -> str:
    """
    WO-006 Field Status Layout — scan order:
      ตัวตน → ชีพ (HP/MP) → 【สถานะกายใจ】 → ที่/เงิน/ปาร์ตี้ → แต้ม
    Needs (หิว/ล้า/ขวัญ) prominent for God / auto playtest.
    """
    name = player.get("name", "?")
    level = player.get("level", 1)
    occ = player.get("occupation", "-")
    rank = player.get("occ_rank_title") or ""
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    pressure = int(player.get("pressure", 0) or 0)

    mastery = resolve_area_mastery(player, current_area)

    party = player.get("party") or []
    party_n = len(party) if isinstance(party, list) else 0
    head = f" {name}   Lv.{level}  {occ}"
    if rank:
        head += f" · {rank}"

    # status debuff short on same band as HP
    st_bit = ""
    raw_st = player.get("statuses") or []
    if raw_st:
        try:
            from game.domain.status_fx import format_status_short

            st_line = format_status_short(player, None)
            if st_line and st_line != "-":
                st_bit = f"   ·  {st_line}"
        except Exception:
            pass

    lines: List[str] = [
        " ตัวตน",
        "---",
        head,
        "---",
    ]
    # WO-035 visible shell: soft HP + needs first
    try:
        from game.domain.stat_arch import soft_hp_condition, ensure_stat_arch

        ensure_stat_arch(player)  # type: ignore[arg-type]
        lines.append(f" ชีพ  {soft_hp_condition(player)}")
    except Exception:
        pass
    lines.append(
        f" HP  [{ratio_bar(hp, max_hp, width=8)}] {hp}/{max_hp}"
        f"   MP  [{ratio_bar(mana, max_mana, width=8)}] {mana}/{max_mana}"
        f"{st_bit}"
    )
    if pressure:
        lines.append(f" กดดัน {pressure}")

    lines.append("---")
    try:
        from game.domain.needs import format_field_needs_block

        lines.extend(format_field_needs_block(player, width=6, show_values=True))
    except Exception:
        try:
            from game.domain.needs import ensure_needs, format_needs_bar_line

            ensure_needs(player)  # type: ignore
            lines.append(" 【สถานะกายใจ】")
            lines.append(f" {format_needs_bar_line(player, width=6)}")
        except Exception:
            pass

    lines.append("---")
    lines.append(
        f" พื้นที่  {current_area}   ·  ชำนาญ {mastery}%   ·  ปาร์ตี้ {party_n}/3"
    )
    lines.append(
        f" เงิน     โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}"
    )

    pts = int(player.get("stat_points") or 0)
    ppts = int(player.get("personality_points") or 0)
    hints: List[str] = []
    if pts > 0:
        hints.append(f"แต้มสถานะ {pts} → P")
    if ppts > 0:
        hints.append(f"แต้มนิสัย {ppts} → N")
    if hints:
        lines.append("---")
        lines.append(" ✦ " + "  ·  ".join(hints))
    # WO-049: compact grade surface on overview status
    try:
        from game.domain.stat_grades import grade_hub_compact_lines

        lines.append("---")
        lines.extend(grade_hub_compact_lines(player))
    except Exception:
        pass
    return render_box(lines, double=False)


def _sight_kind_th(kind: str) -> str:
    k = str(kind or "").lower()
    return {
        "chest": "หีบ",
        "monster": "มอน",
        "npc": "คน",
        "event": "เหตุ",
        "dungeon": "ดัน",
        "companion": "เงา",
        "boss": "บอส",
        "faction_moment": "โลก",
        "shop_rep_event": "ร้าน",
    }.get(k, k or "?")


def format_sights_panel_lines(
    sights: Sequence[Mapping[str, Any]],
    *,
    flavor: str = "",
) -> List[str]:
    """
    Zone B — things you notice (separate from vitals / needs).
    Flavor stays in this box only — does not mix into status layout.
    """
    lines: List[str] = [
        " สิ่งที่สังเกต",
        "---",
        " ในระยะสายตา มีสิ่งที่ดึงความสนใจ...",
        "---",
    ]
    if flavor:
        # short flavor under header, not inside identity block
        fl = flavor.strip()
        if len(fl) > 52:
            fl = fl[:49] + "..."
        lines.append(f" …{fl}")
        lines.append("---")
    if not sights:
        lines.append(" (ยังไม่เห็นเป้าชัด — ลอง 2 สำรวจ)")
        lines.append("---")
        lines.append(" เข้าหา: 3 แล้วเลข")
        return lines
    for i, s in enumerate(sights, 1):
        h = str(s.get("handle") or f"#{i}")
        kind_th = _sight_kind_th(str(s.get("kind") or ""))
        label = str(s.get("label") or "???")
        hint = str(s.get("hint") or "").strip()
        risk = s.get("risk", "?")
        lines.append(f" {i}.  {h:<6}  [{kind_th}]  {label}")
        detail = []
        if hint:
            detail.append(hint)
        detail.append(f"เสี่ยง {risk}")
        lines.append(f"      {' · '.join(detail)}")
        if i < len(sights):
            lines.append("")
    lines.append("---")
    lines.append(" เข้าหา: 3 แล้วเลข  หรือ  f_mn01 / o_ch01 / talk_np01")
    return lines


def render_combat_vitals(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    *,
    known: bool = True,
    situation: str = "",
    round_no: Optional[int] = None,
    banner: str = "",
) -> str:
    """
    Combat vitals — sectioned box:
      header · you · foe · ATB · situation
    """
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
    mon_name = str(mon.get("name") or "???")

    show_hp = known or bool(mon.get("boss"))
    phase_txt = ""
    if mon.get("boss"):
        phase_txt = f" · เฟส {mon.get('phase', 1)}/{mon.get('max_phases', 1)}"

    head = " ไฟต์"
    if round_no is not None:
        head = f" จังหวะ {round_no}{phase_txt}"
    elif phase_txt:
        head = f" ไฟต์{phase_txt}"
    if banner:
        head = f" {banner.strip()}"

    lines: List[str] = [head, "---", " คุณ"]
    try:
        from game.domain.stat_arch import soft_hp_condition

        lines.append(f"  ชีพ  {soft_hp_condition(player)}")
    except Exception:
        pass
    lines.append(
        f"  HP  [{ratio_bar(php, pmax, width=8)}] {php}/{pmax}"
    )
    lines.append(
        f"  MP  [{ratio_bar(pmp, pmm, width=8)}] {pmp}/{pmm}"
    )
    # player status short
    try:
        from game.domain.status_fx import format_status_short

        pst = format_status_short(player, None)
        if pst and pst != "-":
            lines.append(f"  สถานะ  {pst}")
    except Exception:
        pass

    # WO-005 / P1.5: compact needs (หิว · ล้า · ขวัญ) — soft, not formula
    try:
        from game.domain.needs import (
            combat_needs_soft_warnings,
            ensure_needs,
            format_combat_needs_compact,
        )

        ensure_needs(player)  # type: ignore
        lines.append(f"  กายใจ  {format_combat_needs_compact(player)}")
        for w in combat_needs_soft_warnings(player):
            lines.append(f"  {w}")
    except Exception:
        pass

    # party roster in combat (who fights with you)
    party = list(player.get("party") or [])
    if party:
        lines.append("---")
        lines.append(f" ทีมร่วม  {len(party)}/3")
        try:
            from game.domain.party import kind_label
            from game.data_load.registry import get_registry

            reg = None
            try:
                reg = get_registry()
            except Exception:
                reg = None
            from game.domain.party import (
                get_relationship,
                relationship_bar,
                soft_relationship_label,
            )

            for i, m in enumerate(party, 1):
                nm = str(m.get("name") or m.get("id") or "?")
                kd = str(m.get("kind") or "other")
                kl = kind_label(reg, kd) if reg else kd
                mid = str(m.get("id") or "")
                rel = get_relationship(player, mid, m)
                soft = soft_relationship_label(rel)
                lines.append(
                    f"  {i}. {nm} · {kl} · สัมพันธ์สหาย "
                    f"[{relationship_bar(rel)}] {soft}"
                )
        except Exception:
            for i, m in enumerate(party, 1):
                lines.append(f"  {i}. {m.get('name') or m.get('id') or '?'}")

    lines.append("---")
    lines.append(" ศัตรู")
    if show_hp:
        lines.append(f"  {mon_name}")
        lines.append(f"  HP  [{ratio_bar(mhp, mmax, width=8)}] {mhp}/{mmax}{st_txt}")
    else:
        lines.append(f"  {mon_name if known else '???'}")
        lines.append(f"  HP  ???/???{st_txt}")

    lines.append("---")
    lines.append(" จังหวะ (แท่งเต็ม = ลงมือ)")
    try:
        from game.domain.combat_atb import format_atb_bar, soft_atb_label

        pb = format_atb_bar(player)
        mb = format_atb_bar(mon)
        pl = soft_atb_label(player)
        ml = soft_atb_label(mon)
        lines.append(f"  คุณ    [{pb}]  {pl}")
        lines.append(f"  ศัตรู   [{mb}]  {ml}")
        # fatigue soft next to ATB when lagging (P1.5)
        try:
            from game.domain.needs import band, get_needs

            fb = band("fatigue", int(get_needs(player).get("fatigue") or 0))
            if fb in ("bad", "crit"):
                lines.append(
                    "  …ล้ากระทบจังหวะ — แท่งคุณเติมช้า"
                    if fb == "bad"
                    else "  …ล้าวิกฤต — จังหวะหนักมาก"
                )
        except Exception:
            pass
    except Exception:
        try:
            from game.domain.combat_atb import format_atb_strip

            lines.append(format_atb_strip(player, mon))
        except Exception:
            pass

    if situation:
        lines.append("---")
        lines.append(f" ▸ {situation}")

    return render_box(lines, double=False)


def render_field_actions(
    *,
    stat_points: int = 0,
    personality_points: int = 0,
    boss_line: str = "",
    player: Any = None,
    reg: Any = None,
) -> str:
    """EXPLORE mode action block (Mode Shell Phase A + care band)."""
    from game.domain.mode_shell import MODE_EXPLORE, render_mode_actions

    return render_mode_actions(
        MODE_EXPLORE,
        stat_points=stat_points,
        personality_points=personality_points,
        boss_line=boss_line,
        player=player,
        reg=reg,
    )


def render_status_l1(player: Mapping[str, Any], current_area: str) -> str:
    """
    Full status (S) — sectioned for scanability / proportion:
      ตัวตน · ชีพ · ลงทุน·จิต · ที่·เงิน·สกิล · เกียร์ · หมายเหตุ
    """
    name = player.get("name", "?")
    level = player.get("level", 1)
    occ = player.get("occupation", "-")
    zodiac = player.get("zodiac", "-")
    hp = int(player.get("hp", 0))
    max_hp = max(1, int(player.get("max_hp", 1)))
    mana = int(player.get("mana", 0))
    max_mana = max(1, int(player.get("max_mana", 1)))
    pressure = int(player.get("pressure", 0) or 0)
    xp_pct = float(player.get("xp_percent", player.get("exp", 0)) or 0)
    xp_cur = player.get("xp", player.get("exp", 0))
    xp_need = player.get("xp_needed", "?")

    mastery = resolve_area_mastery(player, current_area)
    if mastery == 0:
        # fallback any known mastery (legacy)
        area_mastery = player.get("area_mastery") or {}
        if isinstance(area_mastery, dict):
            for _k, v in area_mastery.items():
                mastery = int(v or 0)
                break

    skills = player.get("skills") or []
    skill_txt = " · ".join(str(s) for s in skills) if skills else "-"
    if len(skill_txt) > 42:
        skill_txt = skill_txt[:39] + "..."

    # soft status line (prefer short formatter)
    st_txt = "-"
    try:
        from game.domain.status_fx import format_status_short

        st_line = format_status_short(player, None)
        if st_line and st_line != "-":
            st_txt = st_line
    except Exception:
        statuses = player.get("statuses") or []
        if statuses:
            st_txt = ", ".join(
                f"{s.get('name', s)}({s.get('remaining', '?')})"
                if isinstance(s, dict)
                else str(s)
                for s in statuses
            ) or "-"

    rank = player.get("occ_rank_title") or ""
    unit = player.get("unit_class_name") or ""
    pts = int(player.get("stat_points") or 0)
    ppts = int(player.get("personality_points") or 0)
    alloc = player.get("stats_alloc") or {}
    path = player.get("occ_path") or ""

    # ── 1. ตัวตน ──────────────────────────────────────────
    lines: List[str] = [" ตัวตน"]
    lines.append(f" {name}  ·  Lv.{level}")
    id_bits = [str(occ)]
    if rank:
        id_bits.append(str(rank))
    if path:
        id_bits.append(f"[{path}]")
    id_bits.append(f"ราศี{zodiac}")
    lines.append(" " + "  ·  ".join(id_bits))
    if unit:
        lines.append(f" อาชีพลับ  {unit}")
    if pts > 0 or ppts > 0:
        wait_bits = []
        if pts > 0:
            wait_bits.append(f"แต้มสถานะ {pts} → P")
        if ppts > 0:
            wait_bits.append(f"แต้มนิสัย {ppts} → N")
        lines.append(" ✦ " + "  ·  ".join(wait_bits))
    if (player.get("flags") or {}).get("class_offer_pending"):
        try:
            from game.domain.class_paths import list_available_class_paths
            from game.data_load.registry import get_registry

            if list_available_class_paths(player, get_registry()):
                lines.append(" …มีข้อเสนออาชีพ (กด C · รับหรือปฏิเสธ)")
            else:
                player.setdefault("flags", {})["class_offer_pending"] = False
        except Exception:
            lines.append(" …มีข้อเสนออาชีพ (กด C)")
    lines.append(f" XP  [{xp_bar(xp_pct)}] {xp_pct:.0f}%  ({xp_cur}/{xp_need})")

    # ── 2. ชีพ ────────────────────────────────────────────
    lines.append("---")
    lines.append(" ชีพ")
    lines.append(f" HP  [{ratio_bar(hp, max_hp)}] {hp}/{max_hp}")
    lines.append(f" MP  [{ratio_bar(mana, max_mana)}] {mana}/{max_mana}")
    lines.append(f" กดดัน {pressure}  ·  สถานะ {st_txt}")

    # ── 3. ลงทุน · Core soft (WO-035: no raw ×N) ─────────
    lines.append("---")
    lines.append(" ลงทุน · Core (soft)")
    try:
        from game.domain.stat_arch import (
            soft_facet_label,
            soft_anima_label,
            physical_score,
            magical_score,
            ensure_stat_arch,
            recompute_anima,
        )

        ensure_stat_arch(player)  # type: ignore[arg-type]
        recompute_anima(player)  # type: ignore[arg-type]
        lines.append(
            f" กาย 〔{soft_facet_label(physical_score(player))}〕 · "
            f"เวท 〔{soft_facet_label(magical_score(player))}〕"
        )
        # Anima after assess OR soft presence felt (WO-037)
        if player.get("_self_assess_done") or player.get("_anima_presence_felt"):
            lines.append(f" {soft_anima_label(player)}")
            if player.get("_anima_presence_felt") and not player.get("_self_assess_done"):
                lines.append("  (รู้สึกจากเรลิก/ห้อง/เรียน · V=อ่านชัดขึ้น)")
            else:
                lines.append("  (จากประเมิน V · คนละชั้นกับขวัญ)")
        else:
            lines.append(" จิตวิญญาณ  ···  กด V หรือสัมผัสเรลิก/ห้อง G")
        lines.append(" P=ลงแต้ม soft · V=ประเมินตัวเอง")
    except Exception:
        a = int(alloc.get("atk", 0) or 0)
        d = int(alloc.get("defense", 0) or 0)
        m = int(alloc.get("magic", 0) or 0)
        s = int(alloc.get("speed", 0) or 0)
        lines.append(f" โจม/กัน/เวท/เร็ว  (soft · ไม่โชว์ดิบ)")
    # WO-049: Grade Surface on full Status
    try:
        from game.domain.stat_grades import format_grade_surface_lines

        lines.append("---")
        lines.extend(format_grade_surface_lines(player, compact=False, include_header=True))
    except Exception:
        pass
    try:
        from game.domain.combo_mind import soft_combo_mind_hint

        lines.append(f" {soft_combo_mind_hint(player)}")
    except Exception:
        pass

    # ── 4. ที่ · เงิน · สกิล ───────────────────────────────
    lines.append("---")
    lines.append(" ที่ · เงิน · สกิล")
    lines.append(f" ที่   {current_area}  ·  ชำนาญ {mastery}%")
    lines.append(
        f" เงิน  โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}"
    )
    lines.append(f" สกิล  {skill_txt}")

    # ── 5. เกียร์ (เฉพาะที่มี) ─────────────────────────────
    gear_lines: List[str] = []
    equip = player.get("equip") or {}
    from game.domain.equipment import EQUIP_SLOT_UI

    for slot, lab in EQUIP_SLOT_UI:
        shown = equip.get(slot)
        if not shown:
            continue
        socks = (player.get("sockets") or {}).get(slot) or []
        filled = sum(1 for x in socks if x)
        card_bit = f"  การ์ด {filled}/{len(socks)}" if socks else ""
        gear_lines.append(f" {lab:<6}  {shown}{card_bit}")
    bag = player.get("card_bag") or []
    if bag:
        gear_lines.append(f" การ์ดในถุง  {len(bag)} ใบ")
    if player.get("gear_tags"):
        gear_lines.append(
            f" แท็ก   {', '.join(str(t) for t in player['gear_tags'])}"
        )
    if player.get("active_sets"):
        gear_lines.append(
            f" เซ็ต   {', '.join(str(x) for x in player['active_sets'])}"
        )
    blessings = player.get("blessings") or []
    if blessings:
        bt = player.get("blessing_turns", 0)
        gear_lines.append(
            f" พร     {', '.join(str(b) for b in blessings)} (~{bt})"
        )
    if player.get("disciple_of"):
        gear_lines.append(f" ศิษย์ของ  {player['disciple_of']}")

    if gear_lines:
        lines.append("---")
        lines.append(" เกียร์")
        lines.extend(gear_lines)

    # ── 6. หมายเหตุ ───────────────────────────────────────
    lines.append("---")
    others = int(player.get("other_players", 0) or 0)
    lines.append(f" ผู้เล่นอื่นในพื้นที่  {others} คน")
    lines.append(" เลเวลไม่จำกัด · ยิ่งสูง ยิ่งต้องใช้ XP มากขึ้น")

    return render_box(lines, double=True)
