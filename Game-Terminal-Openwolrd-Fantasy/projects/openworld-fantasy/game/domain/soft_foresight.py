"""
WO-015: Soft foresight — light pre-checks before dungeon / long auto.
WO-044: Soft world-gaze + Mini-Moment hints per area (no block · no UI).

Not a planner. Soft warnings / presence only for feel + God playtest.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

# Soft gaze lines by faction lean (no raw scores)
_GAZE_LINES = {
    "divine": "คุณรู้สึกสายตาจากเทพวายุ… อบอุ่นจากที่สูง",
    "infernal": "เงามารแผ่ซ่านเบา ๆ… ความร้อนคุ้นเคย",
    "ancient_echo": "เสียงกระซิบจาก echo… เงาโบราณเหลือบมอง",
}

_GAZE_ALERT = {
    "divine": "world.foresight_divine_gaze",
    "infernal": "world.foresight_infernal_haze",
    "ancient_echo": "world.foresight_echo_whisper",
}


def area_faction_lean(area_id: str = "", reg: Any = None) -> str:
    """Primary faction lean for an area (world_relations map)."""
    try:
        from game.domain.world_relations import FACTION_ECHO, faction_for_area

        return str(faction_for_area(str(area_id or "")) or FACTION_ECHO)
    except Exception:
        return "ancient_echo"


def area_world_gaze_lines(
    player: Mapping[str, Any],
    reg: Any,
    *,
    area_id: str = "",
    force: bool = False,
    include_moment_hint: bool = True,
    brief: bool = False,
) -> List[str]:
    """
    WO-044/045: Soft Foresight — feel world eyes + optional moment chance hint.
    Soft only · does not block · throttled per area unless force.
    WO-045: brief=True → one soft line only (re-visit travel · less spam).
    """
    lines: List[str] = []
    try:
        aid = str(area_id or player.get("location") or "")
        if not aid:
            return lines
        # throttle: once per area visit key unless force/brief
        if not force and not brief:
            seen = dict(player.get("_area_world_gaze_seen") or {})  # type: ignore[arg-type]
            if seen.get(aid):
                return lines

        # WO-045: brief re-visit — soft tick gate (avoid every hop spam)
        if brief and isinstance(player, dict):
            tick = int(
                player.get("auto_ticks")
                or player.get("time_units")
                or player.get("_care_ticks")
                or 0
            )
            last = int(player.get("_area_gaze_brief_tick") or -99)
            last_aid = str(player.get("_area_gaze_brief_aid") or "")
            if last_aid == aid and tick - last < 2:
                return lines
            player["_area_gaze_brief_tick"] = tick  # type: ignore[index]
            player["_area_gaze_brief_aid"] = aid  # type: ignore[index]

        fac = area_faction_lean(aid, reg)
        gaze = _GAZE_LINES.get(fac) or _GAZE_LINES["ancient_echo"]
        lines.append(f"  …{gaze}")

        # Soft Alert only on full (first) foresight — not every brief hop
        if not brief:
            try:
                from game.domain.alerts import emit_alert_lines

                code = _GAZE_ALERT.get(fac) or _GAZE_ALERT["ancient_echo"]
                for al in emit_alert_lines(
                    player,  # type: ignore[arg-type]
                    code,
                    force=False,
                ):
                    if al not in lines:
                        lines.append(al)
            except Exception:
                pass

        if include_moment_hint and not brief:
            try:
                from game.domain.faction_moments import moments_for_area

                pool = moments_for_area(aid)
                if pool:
                    labels = [str(m.get("label") or m.get("id") or "") for m in pool[:2]]
                    lab = " · ".join(x for x in labels if x)
                    # soft chance wording — not a guarantee
                    lines.append(
                        f"  ใบ้สายตาโลก  อาจเจอ Mini-Moment"
                        + (f" 〔{lab}〕" if lab else "")
                        + " · ช่วย/ปฏิเสธ/หลบได้"
                    )
                else:
                    lines.append("  ใบ้สายตาโลก  พื้นที่เงียบกว่า — ยังมี lean แผ่ว")
            except Exception:
                pass
        elif include_moment_hint and brief:
            # one short hint without listing every moment name
            lines.append("  …สายตาโลกยังอยู่ — อาจเจอ Mini-Moment ถ้าสำรวจ")

        # WO-046: relic × area synergy soft foresight
        try:
            from game.data_load.registry import get_registry
            from game.domain.relic_anima import synergy_foresight_lines

            reg_syn = reg if reg is not None else get_registry()
            if reg_syn is not None:
                for sl in synergy_foresight_lines(
                    player, reg_syn, area_id=aid, brief=brief
                ):
                    if sl not in lines:
                        lines.append(sl)
        except Exception:
            pass

        # cache for non-force full callers
        if not force and not brief and isinstance(player, dict):
            seen = dict(player.get("_area_world_gaze_seen") or {})
            seen[aid] = True
            player["_area_world_gaze_seen"] = seen  # type: ignore[index]
    except Exception:
        pass
    return lines


def soft_dungeon_entry_warnings(
    player: Mapping[str, Any],
    reg: Any,
    *,
    dungeon: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    """
    Returns soft warning lines (may be empty). Does not block entry.
    """
    lines: List[str] = []
    try:
        from game.domain.needs import band, get_needs, soft_label
        from game.runtime.dungeon_auto import count_food, count_potions, ensure_auto_prefs

        n = get_needs(player)
        prefs = ensure_auto_prefs(player)  # type: ignore[arg-type]
        food_n = int(count_food(player, reg))
        hp_n = int(count_potions(player, reg, kind="hp"))
        min_food = int(prefs.get("inv_min_food") or 2)

        hb = band("hunger", int(n["hunger"]))
        fb = band("fatigue", int(n["fatigue"]))
        mb = band("morale", int(n["morale"]))

        hun_th = int(prefs.get("hunger") or 58)
        fat_th = int(prefs.get("fatigue") or 67)
        # rough burn estimate from R1/R2 (dungeon ~0.5–1 food / few ticks when fighting)
        est_ticks = max(1, food_n * 2) if food_n else 0

        lines.append(" ── ก่อนลงดัน · Soft Foresight ──")
        lines.append(
            f"  กายใจ  หิว {soft_label('hunger', int(n['hunger']))} · "
            f"ล้า {soft_label('fatigue', int(n['fatigue']))} · "
            f"ขวัญ {soft_label('morale', int(n['morale']))}"
        )
        money = int(player.get("money_world") or 0)
        buy_on = bool(prefs.get("auto_buy_supplies", True))
        reserve = int(prefs.get("auto_buy_reserve") or 50)
        lines.append(
            f"  เสบียง  อาหาร {food_n} · ยา HP {hp_n} · "
            f"นโยบาย {prefs.get('low_morale_policy')} · "
            f"เกณฑ์กิน≥{hun_th}/พัก≥{fat_th}"
        )
        lines.append(
            f"  เงิน    โลก {money} · ซื้อเสบียงอัตโนมัติ="
            f"{'เปิด' if buy_on else 'ปิด'} (สำรอง {reserve}G)"
        )
        # WO-024/033: divine burden + Soft Alert catalog
        try:
            from game.domain.divine_burden import (
                burden_summary_for_log,
                soft_burden_status_line,
                worst_burden_band,
            )
            from game.domain.alerts import emit_alert_lines

            bb = worst_burden_band(player, reg)  # type: ignore[arg-type]
            if bb != "fit":
                lines.append(f"  {burden_summary_for_log(player, reg)}")  # type: ignore[arg-type]
                sl = soft_burden_status_line(player, reg)  # type: ignore[arg-type]
                if sl:
                    lines.append(f"  {sl}")
                # Soft Alert Bus (throttled) — same wording as pre-dungeon
                try:
                    for al in emit_alert_lines(
                        player,  # type: ignore[arg-type]
                        "relic.pre_dungeon",
                        band=bb,
                    ):
                        if al not in lines:
                            lines.append(al)
                except Exception:
                    pass
        except Exception:
            pass
        if food_n > 0:
            lines.append(
                f"  ประมาณ  อาหารพอออโต้สั้น ~{est_ticks} ติก "
                f"(หยาบ · ไฟต์ถี่จะหมดเร็วกว่า)"
            )
        else:
            if buy_on and money > reserve + 10:
                lines.append(
                    "  ประมาณ  ไม่มีอาหาร — ออโต้อาจซื้อเสบียงเบา ๆ ถ้าเงินพอ"
                )
            else:
                lines.append("  ประมาณ  ไม่มีอาหาร — ออโต้จะหยุดที่หิวเร็ว")

        risks: List[str] = []
        score = 0
        if food_n <= 0:
            if buy_on and money > reserve + 10:
                risks.append("ไม่มีอาหาร — พึ่งออโต้ซื้อ (เงินพอประมาณ)")
                score += 1
            else:
                risks.append("ไม่มีอาหาร — ลงแล้วหิว/หยุดออโต้เร็ว")
                score += 3
        elif food_n < min_food:
            risks.append(f"อาหารน้อยกว่าเกณฑ์เตือน ({food_n} < {min_food})")
            score += 2
        if hp_n <= 0:
            risks.append("ไม่มียา HP — เลือดบางเสี่ยงสลบ")
            score += 2
        if money < 25:
            risks.append("เงินโลกน้อย — ซื้อเสบียง/ยาลำบาก")
            score += 1
        try:
            from game.domain.divine_burden import worst_burden_band

            bb = worst_burden_band(player, reg)
            if bb == "crush":
                risks.append("ภาระเรลิกหนักเกินตัว — ขวัญจะร่วงในดัน")
                score += 2
            elif bb == "strain":
                risks.append("เรลิกร้อนมือ — ภาระเบาในดัน")
                score += 1
        except Exception:
            pass
        if hb in ("bad", "crit"):
            risks.append("หิวอยู่แล้ว — ควรกินก่อนลง")
            score += 2 if hb == "crit" else 1
        if fb in ("bad", "crit"):
            risks.append("ล้าอยู่แล้ว — ควรพักก่อนลง")
            score += 2 if fb == "crit" else 1
        if mb in ("low", "crit"):
            pol = str(prefs.get("low_morale_policy") or "caution")
            risks.append(f"ขวัญไม่นิ่ง — ออโต้ ({pol}) เลี่ยง/ถอยง่าย")
            score += 2 if mb == "crit" else 1
        hp = int(player.get("hp") or 0)
        mhp = max(1, int(player.get("max_hp") or 1))
        if 100.0 * hp / mhp <= 40:
            risks.append("เลือดไม่เต็ม — ไฟต์แรกเสี่ยง")
            score += 1

        if score >= 5:
            rank = "สูง"
        elif score >= 2:
            rank = "ปานกลาง"
        else:
            rank = "ต่ำ"

        if risks:
            lines.append(f"  ⚠ ความเสี่ยงรวม 〔{rank}〕 (ไม่บังคับหยุด)")
            for r in risks[:5]:
                lines.append(f"   · {r}")
        else:
            lines.append("  · ความเสี่ยงรวม 〔ต่ำ〕 — พอเดินหน้าได้")

        if dungeon and dungeon.get("name"):
            lines.append(f"  เป้า  {dungeon.get('name')}")
        # WO-029: soft area loop tip when player location known
        try:
            loc = str(player.get("location") or "")
            area = (getattr(reg, "areas", None) or {}).get(loc) or {}
            tips = list(area.get("loop_soft") or [])
            if tips:
                lines.append(f"  ลูปพื้นที่  {tips[0]}")
        except Exception:
            pass
        # WO-044: world gaze + moment hint (force once in foresight panel)
        try:
            loc = str(player.get("location") or "")
            for gl in area_world_gaze_lines(
                player, reg, area_id=loc, force=True, include_moment_hint=True
            ):
                if gl not in lines:
                    lines.append(gl)
        except Exception:
            pass
    except Exception as exc:
        lines = [f"  (foresight ข้าม: {exc})"]
    return lines


def area_loop_soft_lines(player: Mapping[str, Any], reg: Any) -> List[str]:
    """
    WO-029: short lines for field when entering / first tick in area.
    WO-044: + Soft world gaze + Mini-Moment hint.
    """
    lines: List[str] = []
    try:
        loc = str(player.get("location") or "")
        area = (getattr(reg, "areas", None) or {}).get(loc) or {}
        tips = list(area.get("loop_soft") or [])
        for t in tips[:2]:
            lines.append(f"  …{t}")
        # Soft Foresight world eyes (throttled per area via cache)
        for gl in area_world_gaze_lines(
            player, reg, area_id=loc, force=False, include_moment_hint=True
        ):
            if gl not in lines:
                lines.append(gl)
    except Exception:
        pass
    return lines


def explore_soft_gaze_tick(
    player: MutableMapping[str, Any],
    reg: Any,
    rng: Any = None,
    *,
    area_id: str = "",
) -> List[str]:
    """
    WO-044: rare soft gaze while exploring (not every tick).
    ~12% if area has lean; skips if already shown this visit.
    """
    import random

    lines: List[str] = []
    try:
        aid = str(area_id or player.get("location") or "")
        if not aid:
            return lines
        rng = rng or random.Random(
            int(player.get("latent_seed") or 1)
            + int(player.get("time_units") or 0)
            + int(player.get("auto_ticks") or 0)
        )
        # already shown this visit → skip tick spam
        seen = dict(player.get("_area_world_gaze_seen") or {})
        if seen.get(aid):
            return lines
        if rng.random() > 0.12:
            return lines
        lines.extend(
            area_world_gaze_lines(
                player, reg, area_id=aid, force=False, include_moment_hint=True
            )
        )
    except Exception:
        pass
    return lines


def should_soft_block_dungeon(player: Mapping[str, Any], reg: Any) -> bool:
    """True only for extreme underprep — caller may still allow with confirm."""
    try:
        from game.domain.needs import band, get_needs
        from game.runtime.dungeon_auto import count_food

        n = get_needs(player)
        food_n = int(count_food(player, reg))
        # extreme: no food AND (hunger crit or morale crit)
        if food_n <= 0 and (
            band("hunger", int(n["hunger"])) == "crit"
            or band("morale", int(n["morale"])) == "crit"
        ):
            return True
    except Exception:
        pass
    return False
