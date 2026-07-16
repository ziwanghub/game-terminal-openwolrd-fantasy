"""
WO-053 Personal System — "เรื่องของฉัน"

Unifies grade · appraisal · auto growth · anima · relic bond · faction
into one soft narrative surface + soft journal.

No raw numbers. Mystery + Soft Feel DNA.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

# Soft journal entry kinds
KIND_TEMPLE = "temple"
KIND_GRADE = "grade"
KIND_GROWTH = "growth"
KIND_ANIMA = "anima"
KIND_RELIC = "relic"
KIND_FACTION = "faction"
KIND_APPRAISAL = "appraisal"
KIND_MILESTONE = "milestone"
KIND_BOND = "bond"

JOURNAL_MAX = 24


def ensure_personal_system(player: MutableMapping[str, Any]) -> None:
    player.setdefault("personal_journal", [])
    player.setdefault("_personal_milestones", [])
    player.setdefault("_personal_seen_v", False)
    # reuse growth log if present
    player.setdefault("_growth_log", [])
    try:
        from game.domain.stat_grades import ensure_grade_state

        ensure_grade_state(player)
    except Exception:
        pass
    try:
        from game.domain.appraisal import ensure_appraisal

        ensure_appraisal(player)
    except Exception:
        pass
    try:
        from game.domain.auto_growth import ensure_auto_growth

        ensure_auto_growth(player)
    except Exception:
        pass


def _tick(player: Mapping[str, Any]) -> int:
    return int(
        player.get("auto_ticks")
        or player.get("time_units")
        or player.get("level")
        or 0
    )


def append_journal(
    player: MutableMapping[str, Any],
    text: str,
    *,
    kind: str = KIND_MILESTONE,
    unique_key: str = "",
    force: bool = False,
) -> bool:
    """
    Soft journal line. unique_key prevents spam of same story beat.
    Returns True if recorded.
    """
    ensure_personal_system(player)
    text = str(text or "").strip()
    if not text:
        return False
    # de-dupe by unique_key among milestones set
    if unique_key and not force:
        seen = list(player.get("_personal_milestones") or [])
        if unique_key in seen:
            return False
        seen.append(unique_key)
        player["_personal_milestones"] = seen[-48:]

    entry = {
        "kind": str(kind or KIND_MILESTONE),
        "text": text if not text.startswith(" ") else text.strip(),
        "lv": int(player.get("level") or 1),
        "tick": _tick(player),
    }
    journal = list(player.get("personal_journal") or [])
    # avoid consecutive identical text
    if journal and journal[-1].get("text") == entry["text"] and not force:
        return False
    journal.append(entry)
    player["personal_journal"] = journal[-JOURNAL_MAX:]
    return True


def journal_lines(
    player: Mapping[str, Any],
    *,
    limit: int = 6,
) -> List[str]:
    """Newest-first soft journal for UI."""
    ensure_personal_system(player)  # type: ignore[arg-type]
    journal = list(player.get("personal_journal") or [])
    if not journal:
        return [" · (ยังว่าง — วิหาร · เรลิก · โต · สายตาโลก จะเติมเรื่อง)"]
    lines: List[str] = []
    for ent in reversed(journal[-limit:]):
        t = str(ent.get("text") or "")
        lv = ent.get("lv")
        if lv:
            lines.append(f" · Lv.{lv}  {t}")
        else:
            lines.append(f" · {t}")
    return lines


def _growth_mode_soft(player: Mapping[str, Any]) -> str:
    try:
        from game.domain.auto_growth import is_auto_growth_mode, soft_threshold_flag

        if is_auto_growth_mode(player):
            return "พลังไหลเวียนเอง (หลัง Lv30)"
        if soft_threshold_flag(player):
            return "ใกล้ไหลเอง — แต้มยังอยู่ในมือ"
        return "ลงแต้ม P soft ได้"
    except Exception:
        lv = int(player.get("level") or 1)
        return "พลังไหลเอง" if lv >= 30 else "ลงแต้ม P ได้"


def _appraisal_soft(player: Mapping[str, Any]) -> str:
    try:
        from game.domain.appraisal import resolve_appraisal_tier, TIER_BASE

        t = resolve_appraisal_tier(player)
        if t == TIER_BASE:
            return "พื้นฐาน — ยังอ่านชั้นไม่ขาด"
        return f"ชั้น 〔{t}〕 — อ่านตัวเอง/ศัตรู soft"
    except Exception:
        return "ยังไม่ชัด"


def _anima_soft_block(player: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    try:
        from game.domain.stat_arch import soft_anima_label, soft_hp_condition

        lines.append(f" · ชีพ  {soft_hp_condition(player)}")
        lines.append(f" · {soft_anima_label(player)}")
    except Exception:
        lines.append(" · จิตวิญญาณ — ยังอ่านพร่า")
    if player.get("_anima_presence_felt"):
        lines.append(" · เคยรู้สึก Anima ชัด (เรลิก/ห้อง/เรียน)")
    return lines


def _relic_bond_soft(player: Mapping[str, Any], reg: Any = None) -> List[str]:
    lines: List[str] = []
    try:
        if reg is not None:
            from game.domain.relic_anima import evaluate_relic_bonds, sync_bond_state

            try:
                st = sync_bond_state(player, reg)  # type: ignore[arg-type]
            except Exception:
                st = evaluate_relic_bonds(player, reg)
        else:
            st = {
                "mode": player.get("_relic_bond_mode") or "none",
                "faction": player.get("_relic_faction_lean"),
            }
        mode = str(st.get("mode") or "none")
        fac = st.get("faction")
        fac_th = {
            "divine": "สวรรค์/เทพ",
            "infernal": "มาร/นรก",
            "ancient_echo": "เงาโบราณ",
        }.get(str(fac or ""), str(fac or "—"))
        if mode == "chorus":
            lines.append(f" · พันธะเรลิก 〔คอรัส〕 — {fac_th} ร้องพร้อมกัน")
        elif mode == "resonance":
            lines.append(f" · พันธะเรลิก 〔เรโซแนนซ์〕 — {fac_th} สั่นพ้อง")
        elif mode == "tension":
            lines.append(" · พันธะเรลิก 〔ตึงเครียด〕 — สายปะทะกันแผ่ว")
        else:
            lines.append(" · พันธะเรลิก — ยังเงียบ หรือชิ้นเดียว")
        ba = str(player.get("_burden_active") or "")
        if ba == "crush":
            lines.append(" · ภาระเรลิก 〔หนักเกินตัว〕")
        elif ba == "strain":
            lines.append(" · ภาระเรลิก 〔ร้อนมือ〕")
    except Exception:
        lines.append(" · เรลิก/พันธะ — ยังไม่แตะชั้นนี้")
    return lines


def _faction_soft_block(player: Mapping[str, Any]) -> List[str]:
    try:
        from game.domain.world_relations import format_world_relations_soft

        # reuse but retitle for personal panel
        raw = format_world_relations_soft(player)
        out: List[str] = []
        for ln in raw:
            if "④" in ln or ln.strip() == "---":
                continue
            out.append(ln if str(ln).startswith(" ") else f" {ln}")
        return out[:6] if out else [" · สายตาโลก — ยังเงียบ"]
    except Exception:
        return [" · สายตาโลก — ยังไม่อ่านได้"]


def _grade_block(player: Mapping[str, Any]) -> List[str]:
    try:
        from game.domain.stat_grades import (
            format_grade_surface_lines,
            grade_revealed,
            player_soft_desc,
            profile_label_th,
        )

        if not grade_revealed(player):
            return [
                " · เกรดยังปิด — วิหารปลดเมื่อตัน",
                " · แกนโจม/กัน/เวท/เร็ว — soft อย่างเดียวจนกว่าจะปลด",
            ]
        lines = list(
            format_grade_surface_lines(player, compact=False, include_header=False)
        )
        return [ln if str(ln).startswith(" ") else f" {ln}" for ln in lines]
    except Exception:
        return [" · เกรด — กด W วิหาร"]


def _growth_block(player: Mapping[str, Any]) -> List[str]:
    lines = [f" · โหมด  {_growth_mode_soft(player)}"]
    try:
        from game.domain.auto_growth import _SOURCE_TH

        src = str(player.get("_last_growth_source") or "")
        if src:
            lines.append(f" · ล่าสุดโตจาก 〔{_SOURCE_TH.get(src, src)}〕")
        pulses = int(player.get("_auto_growth_pulses") or 0)
        if pulses > 0:
            lines.append(" · รู้สึกพัฒนาแล้วหลายจังหวะ (soft)")
    except Exception:
        src = str(player.get("_last_growth_source") or "")
        if src:
            lines.append(f" · ล่าสุดโตจาก 〔{src}〕")
    # fold recent growth log soft
    glog = list(player.get("_growth_log") or [])
    if glog:
        last = glog[-1]
        lines.append(f" · บันทึกโตแผ่ว · แหล่ง {last.get('source', '?')}")
    return lines


def format_personal_narrative_panel(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    journal_limit: int = 6,
) -> List[str]:
    """
    Full 「เรื่องของฉัน」 panel — primary Personal System surface.
    """
    ensure_personal_system(player)
    name = str(player.get("name") or "???")
    lv = int(player.get("level") or 1)
    occ = str(player.get("occupation") or player.get("occ_rank_title") or "")

    lines: List[str] = [
        " เรื่องของฉัน",
        "---",
        f" {name}  ·  Lv.{lv}" + (f"  ·  {occ}" if occ else ""),
        "---",
        " ① เกรด · ตัวตน",
    ]
    lines.extend(_grade_block(player))
    lines.append("---")
    lines.append(" ② อ่านชั้น (Appraisal)")
    lines.append(f" · {_appraisal_soft(player)}")
    lines.append("---")
    lines.append(" ③ ชีพ · จิตวิญญาณ (Anima)")
    lines.extend(_anima_soft_block(player))
    lines.append("---")
    lines.append(" ④ เรลิก · พันธะ")
    lines.extend(_relic_bond_soft(player, reg))
    lines.append("---")
    lines.append(" ⑤ สายตาโลก (Faction)")
    lines.extend(_faction_soft_block(player))
    lines.append("---")
    lines.append(" ⑥ การเติบโต")
    lines.extend(_growth_block(player))
    lines.append("---")
    lines.append(" ⑦ บันทึกจังหวะ (Soft Journal)")
    lines.extend(journal_lines(player, limit=journal_limit))
    lines.append("---")
    lines.append(" · ไม่โชว์ตัวเลขดิบ · นี่คือเรื่องของคุณ")
    return lines


def format_personal_compact_lines(player: Mapping[str, Any]) -> List[str]:
    """2–3 lines for hub chrome."""
    ensure_personal_system(player)  # type: ignore[arg-type]
    bits: List[str] = []
    try:
        from game.domain.stat_grades import grade_revealed, player_soft_desc

        if grade_revealed(player):
            pg = str(player.get("player_grade") or "?")
            bits.append(f"เกรด〔{pg}〕{player_soft_desc(pg)}")
        else:
            bits.append("เกรดปิด")
    except Exception:
        bits.append("เกรด?")
    try:
        from game.domain.appraisal import resolve_appraisal_tier

        bits.append(f"อ่านชั้น〔{resolve_appraisal_tier(player)}〕")
    except Exception:
        pass
    bits.append(_growth_mode_soft(player).split("—")[0].strip()[:18])
    return [" เรื่องของฉัน · " + " · ".join(bits)]


# ── Story hooks (call from domain events) ───────────────────────────────


def note_temple_story(player: MutableMapping[str, Any], grade: str = "") -> None:
    g = str(grade or player.get("player_grade") or "")
    append_journal(
        player,
        f"วิหารปลด — รู้ระดับตัวเอง 〔{g or '?'}〕",
        kind=KIND_TEMPLE,
        unique_key="temple_unlock",
    )
    append_journal(
        player,
        "ตาเริ่มอ่านชั้นพลังได้",
        kind=KIND_APPRAISAL,
        unique_key="appraisal_seed",
    )


def note_auto_growth_story(player: MutableMapping[str, Any]) -> None:
    append_journal(
        player,
        "แต้มไม่อยู่ในมือ — พลังเริ่มไหลเอง",
        kind=KIND_GROWTH,
        unique_key="auto_growth_gate",
    )


def note_growth_pulse_story(
    player: MutableMapping[str, Any],
    source: str,
    *,
    letter_changed: bool = False,
) -> None:
    """Occasional soft journal from growth (not every pulse)."""
    ensure_personal_system(player)
    pulses = int(player.get("_auto_growth_pulses") or 0)
    # every 3rd pulse or letter change
    if letter_changed:
        append_journal(
            player,
            "ชั้นแกนเลื่อน — รู้สึกตัวเองเปลี่ยน",
            kind=KIND_GROWTH,
            unique_key="",
            force=True,
        )
        return
    if pulses > 0 and pulses % 3 == 0:
        src_th = {
            "quest": "เควส",
            "combat": "ไฟต์",
            "level": "เลเวล",
            "anima": "จิตวิญญาณ",
            "relic": "เรลิก",
            "faction": "สายตาโลก",
            "residual": "แต้มเก่า",
        }.get(source, source)
        append_journal(
            player,
            f"พัฒนาจาก 〔{src_th}〕 — เรื่องของคุณยาวขึ้น",
            kind=KIND_GROWTH,
            unique_key=f"growth_pulse_{pulses // 3}",
        )


def note_anima_story(player: MutableMapping[str, Any], reason: str = "") -> None:
    r = str(reason or "")
    if "relic" in r or r == "relic_equip":
        if not player.get("_journal_anima_relic"):
            append_journal(
                player,
                "ครั้งแรกที่ Anima สั่นกับเรลิก",
                kind=KIND_ANIMA,
                unique_key="anima_relic_first",
            )
            player["_journal_anima_relic"] = True
        else:
            append_journal(
                player,
                "Anima เรโซแนนซ์กับเรลิกอีกครั้ง",
                kind=KIND_ANIMA,
                unique_key="",
                force=True,
            )
    elif "chamber" in r:
        append_journal(
            player,
            "ในห้องเรลิก — จิตก้องลึก",
            kind=KIND_ANIMA,
            unique_key="anima_chamber",
        )
    elif r in ("deep_calm", "thin_warn"):
        append_journal(
            player,
            "จิตวิญญาณลึกมั่น" if r == "deep_calm" else "จิตวิญญาณแผ่ว — ระวังขวัญ",
            kind=KIND_ANIMA,
            unique_key=f"anima_{r}",
        )


def note_bond_story(player: MutableMapping[str, Any], mode: str, faction: str = "") -> None:
    fac_th = {
        "divine": "สวรรค์",
        "infernal": "นรก",
        "ancient_echo": "เงาโบราณ",
    }.get(str(faction or ""), "")
    if mode == "resonance":
        append_journal(
            player,
            f"เรลิกเรโซแนนซ์{(' · '+fac_th) if fac_th else ''}",
            kind=KIND_BOND,
            unique_key=f"bond_res_{faction}",
        )
    elif mode == "chorus":
        append_journal(
            player,
            f"คอรัสเรลิก — {fac_th or 'หลายชิ้น'} ร้องพร้อม",
            kind=KIND_BOND,
            unique_key=f"bond_chorus_{faction}",
        )
    elif mode == "tension":
        append_journal(
            player,
            "เรลิกตึงเครียด — สายปะทะในมือ",
            kind=KIND_BOND,
            unique_key="bond_tension",
        )


def note_faction_story(
    player: MutableMapping[str, Any],
    faction: str,
    *,
    warm: bool = True,
) -> None:
    meta = {
        "divine": ("สายตาเทพเริ่มจับจ้องคุณ", "เทพหันหน้าหนีแผ่ว"),
        "infernal": ("พลังมารส่งสายตา…", "หมอกนรกจางลง"),
        "ancient_echo": ("เงา echo พยัก…", "เงาโบราณจ้องแข็ง"),
    }
    warm_t, cold_t = meta.get(str(faction), ("สายตาโลกเปลี่ยน", "สายตาโลกเย็นลง"))
    append_journal(
        player,
        warm_t if warm else cold_t,
        kind=KIND_FACTION,
        unique_key=f"faction_{faction}_{'w' if warm else 'c'}",
    )


def note_appraisal_story(player: MutableMapping[str, Any], tier: str) -> None:
    if str(tier) in ("SS", "SSS"):
        append_journal(
            player,
            f"ตาคมขึ้น — อ่านชั้นถึง 〔{tier}〕",
            kind=KIND_APPRAISAL,
            unique_key=f"appraisal_tier_{tier}",
        )


def maybe_seed_opening_journal(player: MutableMapping[str, Any]) -> None:
    """First open of personal panel — soft prologue."""
    ensure_personal_system(player)
    if player.get("_personal_prologue"):
        return
    player["_personal_prologue"] = True
    append_journal(
        player,
        "เริ่มต้นเส้นทาง — ยังไม่รู้ว่าตัวเองเป็นใคร",
        kind=KIND_MILESTONE,
        unique_key="prologue",
    )
