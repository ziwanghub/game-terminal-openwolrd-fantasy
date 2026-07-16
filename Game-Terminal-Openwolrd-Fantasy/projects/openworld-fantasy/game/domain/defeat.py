"""
WO-012: Soft Death & Defeat Experience — shared path for manual + auto.

Soft death only (no permadeath). God-readable cause + near-death warnings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from game.data_load.registry import DataRegistry

# Near-death HP ratio bands
NEAR_DEATH_WARN = 0.25
NEAR_DEATH_CRIT = 0.15


def hp_ratio(player: Mapping[str, Any]) -> float:
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    return float(hp) / float(mhp)


def is_near_death(player: Mapping[str, Any], *, crit: bool = False) -> bool:
    r = hp_ratio(player)
    if int(player.get("hp") or 0) <= 0:
        return False
    return r <= (NEAR_DEATH_CRIT if crit else NEAR_DEATH_WARN)


def near_death_warning_lines(
    player: Mapping[str, Any],
    *,
    mon: Optional[Mapping[str, Any]] = None,
    enemy_name: str = "ศัตรู",
    force: bool = False,
) -> List[str]:
    """
    Soft near-death warnings (WO-012). Dedup via player flags per fight.
    """
    if int(player.get("hp") or 0) <= 0:
        return []
    r = hp_ratio(player)
    out: List[str] = []
    # crit band first
    if r <= NEAR_DEATH_CRIT:
        if force or not player.get("_near_death_crit_warned"):
            if isinstance(player, dict):
                player["_near_death_crit_warned"] = True  # type: ignore[index]
            out.append(
                f" ⚠ ใกล้สลบ (HP {int(player.get('hp') or 0)}/"
                f"{int(player.get('max_hp') or 1)}) — หนึ่งหมัดอาจจบ"
            )
            # needs pressure if stressed
            try:
                from game.domain.needs import band, get_needs

                n = get_needs(player)
                bits = []
                if band("hunger", n["hunger"]) in ("bad", "crit"):
                    bits.append("หิวถ่วงร่าง")
                if band("fatigue", n["fatigue"]) in ("bad", "crit"):
                    bits.append("ล้าหนัก")
                if band("morale", n["morale"]) in ("low", "crit"):
                    bits.append("ขวัญไม่นิ่ง")
                if bits:
                    out.append("   · " + " · ".join(bits))
            except Exception:
                pass
        return out
    if r <= NEAR_DEATH_WARN:
        if force or not player.get("_near_death_warned"):
            if isinstance(player, dict):
                player["_near_death_warned"] = True  # type: ignore[index]
            out.append(
                f" …เลือดบาง (HP ≤25%) — ระวัง{enemy_name if enemy_name else 'ศัตรู'}"
            )
    _ = mon
    return out


def clear_near_death_flags(player: MutableMapping[str, Any]) -> None:
    player.pop("_near_death_warned", None)
    player.pop("_near_death_crit_warned", None)


def explain_defeat(
    player: Mapping[str, Any],
    mon: Optional[Mapping[str, Any]] = None,
    *,
    context: str = "combat",
) -> Dict[str, Any]:
    """
    Primary defeat cause for God log.
    Returns {primary, label_th, detail, tags[]}.
    """
    tags: List[str] = []
    scores: Dict[str, int] = {
        "hunger": 0,
        "fatigue": 0,
        "morale": 0,
        "fight": 0,
    }
    try:
        from game.domain.needs import band, get_needs

        n = get_needs(player)
        hb = band("hunger", int(n["hunger"]))
        fb = band("fatigue", int(n["fatigue"]))
        mb = band("morale", int(n["morale"]))
        if hb == "crit":
            scores["hunger"] = 3
            tags.append("หิววิกฤต")
        elif hb == "bad":
            scores["hunger"] = 2
            tags.append("หิว")
        if fb == "crit":
            scores["fatigue"] = 3
            tags.append("ล้าวิกฤต")
        elif fb == "bad":
            scores["fatigue"] = 2
            tags.append("ล้า")
        if mb == "crit":
            scores["morale"] = 3
            tags.append("ขวัญย่ำแย่")
        elif mb == "low":
            scores["morale"] = 2
            tags.append("ขวัญหด")
    except Exception:
        pass

    # fight weight: level gap / boss / low hp entry
    fight_score = 1
    if mon:
        try:
            gap = int(mon.get("level") or 1) - int(player.get("level") or 1)
            if gap >= 4 or mon.get("boss") or mon.get("dungeon_boss"):
                fight_score = 3
                tags.append("ไฟต์หนัก")
            elif gap >= 2:
                fight_score = 2
                tags.append("ศัตรูแข็ง")
            else:
                tags.append("ปะทะ")
        except Exception:
            tags.append("ปะทะ")
    else:
        tags.append("ปะทะ")
    scores["fight"] = fight_score

    # pick primary
    primary = max(scores.items(), key=lambda kv: kv[1])[0]
    # if all weak, default fight
    if scores[primary] <= 1 and scores["fight"] >= 1:
        primary = "fight"

    labels = {
        "hunger": "หิวถ่วง — ร่างไม่ไหว",
        "fatigue": "ล้าหนัก — จังหวะพัง",
        "morale": "ขวัญแตก — มือไม่นิ่ง",
        "fight": "ไฟต์หนัก — รับไม่ไหว",
    }
    label = labels.get(primary, "พ่ายแพ้")
    detail_bits = tags[:3] if tags else [label]
    detail = " · ".join(detail_bits)

    return {
        "primary": primary,
        "label_th": label,
        "detail": detail,
        "tags": tags,
        "context": context,
        "line": f"สาเหตุหลัก: {label} ({detail})",
    }


def defeat_narrative_lines(
    player: Mapping[str, Any],
    mon: Optional[Mapping[str, Any]] = None,
    *,
    enemy_name: str = "ศัตรู",
    context: str = "combat",
    rng: Any = None,
) -> List[str]:
    """1–3 soft flavor lines when falling."""
    info = explain_defeat(player, mon, context=context)
    primary = str(info.get("primary") or "fight")
    # fixed soft lines (no RNG required for tests) — optional spice
    openings = {
        "hunger": "คุณสลบลงกับพื้น… ท้องร้องจนหมดสติ",
        "fatigue": "ขาทรุด — ลมหายใจขาด โลกหมุน…",
        "morale": "คุณสลบลง… ขวัญแตกสลาย มือไม่ยอมขยับอีก",
        "fight": f"คุณล้มลงต่อหน้า{enemy_name}… แรงสุดท้ายหมดลง",
    }
    lines = [
        f" {openings.get(primary, openings['fight'])}",
        f" {info['line']}",
    ]
    _ = rng
    return lines


def format_soft_death_feedback(
    summary: str,
    defeat_info: Optional[Mapping[str, Any]] = None,
    *,
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """Lines for soft_death_panel extra + God summary."""
    lines: List[str] = []
    if defeat_info:
        lines.append(str(defeat_info.get("line") or ""))
        tags = defeat_info.get("tags") or []
        if tags:
            lines.append(" ปัจจัย: " + " · ".join(str(t) for t in tags[:4]))
    lines.append(f" ผลกระทบ: {summary}")
    lines.append(" (Soft Death — ยังเล่นต่อได้ · ไม่ใช่จบเกม)")
    for e in extra or []:
        if e:
            lines.append(str(e))
    return [x for x in lines if x]


def resolve_player_defeat(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    mon: Optional[Mapping[str, Any]] = None,
    enemy_name: str = "ศัตรู",
    context: str = "combat",
    apply_needs_loss: bool = True,
) -> Dict[str, Any]:
    """
    Canonical soft-defeat pipeline (manual + auto_fight).
    Order: explain → combat_loss needs → apply_soft_death → feedback lines.
    """
    from game.domain.balance import apply_soft_death
    from game.domain.needs import apply_needs_event

    clear_near_death_flags(player)
    info = explain_defeat(player, mon, context=context)
    narrative = defeat_narrative_lines(
        player, mon, enemy_name=enemy_name, context=context
    )
    needs_lines: List[str] = []
    if apply_needs_loss:
        for n in apply_needs_event(player, "combat_loss"):
            if n and not str(n).startswith("〔"):
                needs_lines.append(str(n))

    death_msg = apply_soft_death(player, reg)
    feedback = format_soft_death_feedback(death_msg, info)
    player["_last_defeat"] = {
        **info,
        "summary": death_msg,
        "enemy": enemy_name,
        "context": context,
    }

    # optional auto-run log hook
    try:
        from game.runtime.auto_run_log import log_auto_event

        if (player.get("_auto_run") or {}).get("active") or player.get(
            "_combat_auto_play"
        ):
            log_auto_event(
                player,
                "stop",
                f"แพ้/สลบ · {info.get('line')}",
                level="warn",
            )
    except Exception:
        pass

    return {
        "defeat": info,
        "narrative": narrative,
        "needs_lines": needs_lines,
        "death_msg": death_msg,
        "feedback": feedback,
        "panel_extra": feedback,
    }
