"""P9 — Auto-farm: tick the field, auto-resolve easy fights, pause on risk."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.character import apply_field_regen
from game.domain.combat import (
    apply_status_to_monster,
    monster_raw_damage,
    pick_monster,
    pick_monster_attack,
    player_attack_damage,
    resolve_victory,
)
from game.domain.encounters import build_sights, mark_monster_seen, resolve_approach
from game.domain.leveling import grant_xp, kill_xp_reward, xp_progress
from game.ports.io import IO
from game.ui_terminal.status import render_status_l0


# XP penalty while auto-farming (manual play is more rewarding)
AUTO_XP_FACTOR = 0.55
AUTO_MAX_TICKS_DEFAULT = 12


def monster_threat(player: Dict[str, Any], mon: Dict[str, Any]) -> str:
    gap = int(mon.get("level", 1)) - int(player.get("level", 1))
    if gap >= 4:
        return "deadly"
    if gap >= 2:
        return "high"
    if gap >= 0:
        return "even"
    return "easy"


def _auto_basic_skill(player: Mapping[str, Any]) -> Tuple[Dict[str, Any], str]:
    return (
        {
            "id": "__basic__",
            "power": 8 + int(player.get("bonus_atk", 0)) // 2,
            "elements": ["physical"],
            "name": "โจมตีปกติ",
            "cost_mana": 0,
        },
        "โจมตีปกติ",
    )


def _auto_pick_skill(
    player: Dict[str, Any],
    reg: DataRegistry,
    plan: List[int],
    turn: int,
) -> Tuple[Dict[str, Any], str]:
    """Pick skill for this auto turn (before mana spend / morale checks)."""
    skill, label = _auto_basic_skill(player)
    if plan:
        try:
            from game.runtime.dungeon_auto import resolve_skill_for_auto_turn

            skill, label = resolve_skill_for_auto_turn(
                player, reg, plan, plan_step=turn - 1
            )
            if not isinstance(skill, dict):
                skill, label = _auto_basic_skill(player)
            else:
                skill = dict(skill)
        except Exception:
            skill, label = _auto_basic_skill(player)
        return skill, label
    # field auto: prefer a few elemental skills if mana allows
    for sid in player.get("skills") or []:
        sk = reg.skills.get(sid) or {}
        if sk.get("slot") == "combat" and sk.get("power") and int(
            sk.get("cost_mana", 0)
        ) <= int(player.get("mana", 0)):
            if sid in ("fire_ball", "water_bolt", "shadow_strike", "magic_missile"):
                if int(player["mana"]) >= int(sk.get("cost_mana", 0)):
                    skill = dict(sk)
                    skill["id"] = sid
                    label = str(sk.get("name") or sid)
                    break
    return skill, label


def _auto_apply_incoming(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> int:
    """
    Monster hit vs player — WO-004 P1.1: combat_needs_mults (incoming/dodge)
    + crude low-HP guard (legacy auto).
    """
    profile = pick_monster_attack(mon, rng, player=player)
    raw = monster_raw_damage(mon, profile, rng)
    try:
        from game.domain.needs import combat_needs_mults

        nm = combat_needs_mults(player)
        raw = max(1, int(round(raw * float(nm.get("incoming_mult") or 1.0))))
        dodge = float(player.get("dodge_chance") or 3.0) * float(
            nm.get("dodge_mult") or 1.0
        )
        dodge = min(40.0, max(0.0, dodge))
        roll = rng.random() * 100.0
        if roll < dodge * 0.35:
            return 0
        if roll < dodge:
            raw = max(1, int(raw * 0.55))
    except Exception:
        pass
    # crude auto-guard: half if HP low
    if int(player["hp"]) < int(player["max_hp"]) * 0.35:
        raw = max(1, raw // 2)
    return max(0, int(raw))


def _auto_fatigue_player_delayed(player: Mapping[str, Any], rng: random.Random) -> bool:
    """
    Simulate slow ATB: if fatigue mult low, chance player acts late
    (monster hits first / player skips strike this round).
    """
    try:
        from game.domain.needs import atb_fatigue_mult

        fat_m = float(atb_fatigue_mult(player))
    except Exception:
        return False
    if fat_m >= 0.95:
        return False
    # mult 0.72 → ~28% delay; mult 0.88 → ~12%
    delay_chance = max(0.0, min(0.40, (1.0 - fat_m) * 1.15))
    return rng.random() < delay_chance


def auto_fight(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    area_id: str,
    *,
    xp_factor: Optional[float] = None,
    skill_plan: Optional[List[int]] = None,
    use_regen: bool = False,
) -> List[str]:
    """
    Auto combat with Needs parity (WO-004 P1.1).
    Uses domain needs: combat tick, combat_needs_mults (via attack + incoming),
    morale skill fail/block, fatigue pacing. Win/loss apply combat_win/loss.
    xp_factor: mult on kill XP (default AUTO_XP_FACTOR for field auto; use 1.0 for full XP).
    skill_plan: 1-based skill indices (dungeon auto); mana fail → basic attack.
    use_regen: apply soft regen each round (dungeon auto advantage).
    """
    from game.domain.needs import (
        apply_needs_event,
        ensure_needs,
        skill_blocked_by_morale,
        skill_fail_chance,
    )

    ensure_needs(player)
    lines: List[str] = []
    # WO-033: soft alert before auto combat (throttled)
    try:
        from game.domain.divine_burden import pre_fight_burden_alerts

        lines.extend(pre_fight_burden_alerts(player, reg))
    except Exception:
        pass
    # WO-033.4: needs stress → Soft Alert history (throttled)
    try:
        from game.domain.needs import record_needs_soft_alerts

        lines.extend(record_needs_soft_alerts(player))
    except Exception:
        pass
    # WO-054: soft combat identity pre-fight (no spam — auto collects lines)
    try:
        from game.domain.combat_identity import (
            clear_fight_identity_flags,
            pre_fight_identity_lines,
        )

        clear_fight_identity_flags(player)
        lines.extend(
            pre_fight_identity_lines(
                player,
                mon,
                reg,
                area_id=str(player.get("location") or ""),
                rng=rng,
                force=True,
            )
        )
    except Exception:
        pass
    turn = 0
    plan = list(skill_plan or [])
    while mon["hp"] > 0 and player["hp"] > 0 and turn < 40:
        turn += 1
        # Needs tick during fight (same event table as manual combat path design)
        apply_needs_event(player, "combat", silent=True)
        # WO-023: divine burden soft drain (parity with combat_session)
        try:
            from game.domain.divine_burden import apply_burden_tick

            apply_burden_tick(player, reg, context="combat", rng=rng)
        except Exception:
            pass

        # Fatigue pacing: slow player — monster may strike before player attack
        delayed = _auto_fatigue_player_delayed(player, rng)
        if delayed:
            raw = _auto_apply_incoming(player, mon, reg, rng)
            player["hp"] = int(player["hp"]) - raw
            if int(player["hp"]) <= 0:
                break
            if turn == 1 or rng.random() < 0.35:
                lines.append("  ออโต้: ล้า — จังหวะช้า เงาขึ้นก่อน")

        skill, label = _auto_pick_skill(player, reg, plan, turn)
        # P1.3: low/passive aggression → prefer basic over costly skills
        aggr = str(player.get("_auto_aggression") or "normal")
        if aggr in ("low", "passive") and str(skill.get("id") or "") not in (
            "",
            "__basic__",
        ):
            if aggr == "passive" or rng.random() < 0.55:
                skill, label = _auto_basic_skill(player)
                if turn == 1:
                    lines.append("  ออโต้: ลดความก้าวร้าว — ใช้จังหวะเบา")
        # Morale: block focus-like skills → basic
        if skill_blocked_by_morale(player, skill):
            if str(skill.get("id") or "") not in ("", "__basic__"):
                lines.append("  ออโต้: ขวัญไม่นิ่ง — ใช้ท่าโฟกัสไม่ได้")
            skill, label = _auto_basic_skill(player)

        # Spend mana only after morale gate
        cost = int(skill.get("cost_mana") or skill.get("mana") or skill.get("mp") or 0)
        sid = str(skill.get("id") or "")
        if cost > 0 and sid != "__basic__":
            if int(player.get("mana") or 0) < cost:
                skill, label = _auto_basic_skill(player)
                cost = 0
            else:
                player["mana"] = int(player.get("mana") or 0) - cost

        if turn == 1 and plan:
            lines.append(f"  แผนสกิล: ขั้นนี้ใช้「{label}」")

        # Morale: skill fail chance (same domain as combat_session)
        failed = False
        skill_id = str(skill.get("id") or "")
        if skill_id not in ("", "__basic__") and (
            int(skill.get("cost_mana") or skill.get("mana") or skill.get("mp") or 0) > 0
            or skill.get("power")
        ):
            # basic physical spam rarely fails; skills & named attacks can
            if skill_id != "__basic__" and rng.random() < skill_fail_chance(player):
                failed = True
                lines.append("  ออโต้: มือสั่น — ท่าไม่เต็ม")

        if not failed:
            # player_attack_damage already multiplies combat_needs_mults atk
            dmg, _ = player_attack_damage(player, mon, reg, area_id, skill, rng)
            mon["hp"] = int(mon["hp"]) - dmg
        else:
            # soft fail: weak basic poke or full miss
            if rng.random() < 0.45:
                dmg, _ = player_attack_damage(
                    player, mon, reg, area_id, _auto_basic_skill(player)[0], rng
                )
                mon["hp"] = int(mon["hp"]) - max(1, dmg // 2)

        if mon["hp"] <= 0:
            break

        # If not already delayed this turn, normal monster response
        if not delayed:
            raw = _auto_apply_incoming(player, mon, reg, rng)
            player["hp"] = int(player["hp"]) - raw

        # WO-012: near-death soft log (once per fight via flags)
        try:
            from game.domain.defeat import near_death_warning_lines

            for w in near_death_warning_lines(
                player, mon=mon, enemy_name=str(mon.get("name") or "ศัตรู")
            ):
                lines.append(w)
        except Exception:
            pass

        # light mana regen (always) + optional full soft regen
        player["mana"] = min(int(player["max_mana"]), int(player.get("mana") or 0) + 1)
        if use_regen:
            try:
                from game.runtime.dungeon_auto import apply_auto_regen

                apply_auto_regen(player, reg, in_combat=True)
            except Exception:
                pass

    if player["hp"] <= 0:
        # WO-012: same soft-death pipeline as combat_session
        from game.domain.defeat import resolve_player_defeat

        enemy = str(mon.get("name") or "ศัตรู")
        result = resolve_player_defeat(
            player,
            reg,
            mon=mon,
            enemy_name=enemy,
            context="auto_fight",
            apply_needs_loss=True,
        )
        lines.append("  ออโต้: แพ้ — เข้า Soft Death (สมมาตรกับไฟต์มือ)")
        for n in result.get("narrative") or []:
            lines.append(n if str(n).startswith(" ") else f"  {n}")
        for n in result.get("needs_lines") or []:
            lines.append(n if str(n).startswith(" ") else f"  {n}")
        lines.append(f"  {result.get('death_msg')}")
        for n in (result.get("feedback") or [])[:4]:
            if n and str(n) not in (result.get("death_msg") or ""):
                lines.append(n if str(n).startswith(" ") else f"  {n}")
        # WO-015: compact fight report lines (same schema vocabulary)
        try:
            from game.domain.fight_log import format_fight_report

            # seed meta from turns
            player.setdefault("_fight_log_meta", {})
            meta = player["_fight_log_meta"]
            if isinstance(meta, dict):
                meta["attacks"] = int(meta.get("attacks") or 0) + max(1, turn)
            for ln in format_fight_report(
                player,
                outcome="loss",
                enemy_name=enemy,
                defeat_line=str((result.get("defeat") or {}).get("line") or ""),
            ):
                lines.append(ln if str(ln).startswith(" ") else f"  {ln}")
        except Exception:
            pass
        mark_monster_seen(player, mon)
        return lines

    # Victory needs (same event as combat_session)
    for n in apply_needs_event(player, "combat_win"):
        if n and not str(n).startswith("〔") and "…" in str(n):
            lines.append(n if str(n).startswith(" ") else f"  {n}")

    # Victory XP (field auto defaults reduced; callers may pass xp_factor=1.0 for full)
    xf = AUTO_XP_FACTOR if xp_factor is None else float(xp_factor)
    xf = max(0.0, min(1.0, xf))
    full_xp = kill_xp_reward(
        int(player.get("level", 1)),
        int(mon.get("level", 1)),
        float(mon.get("xp_mult", 1.0)),
        reg.levels,
    )
    xp = max(1, int(round(full_xp * xf))) if xf < 1.0 else max(1, int(full_xp))
    summary = grant_xp(player, xp, reg.levels)
    if xf >= 0.999:
        lines.append(
            f"ออโต้ชนะ {mon.get('name')} · XP +{summary['gained']} "
            f"Lv.{player['level']} {summary['xp_percent']:.0f}%"
        )
    else:
        lines.append(
            f"ออโต้ชนะ {mon.get('name')} · XP +{summary['gained']} (ลดแล้ว {int(xf * 100)}%) "
            f"Lv.{player['level']} {summary['xp_percent']:.0f}%"
        )
    for n in summary["notes"]:
        lines.append(n)
    # lighter mastery than full resolve_victory; money via WO-021 parity helper
    am = dict(player.get("area_mastery") or {})
    am[area_id] = min(100, int(am.get(area_id, 0)) + 1)
    player["area_mastery"] = am
    try:
        from game.domain.balance import grant_combat_money

        # WO-022: field auto money closer to manual (was 0.85)
        mf = 0.90 if xf < 0.999 else 1.0
        for ml in grant_combat_money(
            player, mon, rng, auto=True, money_factor=mf
        ):
            lines.append(ml if str(ml).startswith(" ") else f"  {ml}")
    except Exception:
        g = rng.randint(10, 28)
        player["money_world"] = int(player.get("money_world", 0)) + g
        lines.append(f"  เงินโลก +{g}")
    know = dict(player.get("knowledge") or {})
    mons = dict(know.get("monsters") or {})
    entry = dict(mons.get(mon["id"]) or {"seen": True, "fought": 0, "won": 0})
    entry["seen"] = True
    entry["fought"] = int(entry.get("fought", 0)) + 1
    entry["won"] = int(entry.get("won", 0)) + 1
    entry["name"] = mon.get("name")
    mons[mon["id"]] = entry
    know["monsters"] = mons
    player["knowledge"] = know
    try:
        from game.domain.quests import bump_quest

        lines.extend(bump_quest(player, reg, "kill", area_id=area_id))
    except Exception:
        pass
    if rng.random() < 0.2:
        try:
            from game.domain.equipment import add_item

            lines.append("ดรอป " + add_item(player, "upgrade_mat", reg))
        except Exception:
            pass
    return lines


def should_pause_sight(player: Dict[str, Any], sight: Dict[str, Any]) -> Tuple[bool, str]:
    kind = sight.get("kind")
    if kind == "chest":
        return True, "หีบ — เสี่ยงมอน/ของดี"
    if kind == "faction_moment":
        try:
            from game.domain.faction_moments import should_auto_pause_moment

            if should_auto_pause_moment(player, sight):
                return True, f"สายตาโลก · {sight.get('label') or 'Mini-Moment'}"
            # auto will soft-resolve without pause
            return False, "Mini-Moment · ออโต้จัดการ soft"
        except Exception:
            return True, "สายตาโลก"
    if kind == "shop_rep_event":
        # soft help by default in auto — no pause spam
        return False, "เหตุการณ์ร้าน · ออโต้ช่วย soft"
    if kind == "npc":
        return True, "คนแปลกหน้า — ต้องตัดสินใจ"
    # WO-025: player echo + Relic Aura
    if kind in ("player", "echo"):
        other = sight.get("player_echo") or sight.get("echo") or sight
        try:
            from game.domain.divine_burden import entity_has_relic_presence
            from game.runtime.dungeon_auto import ensure_auto_prefs

            prefs = ensure_auto_prefs(player)
            hot = entity_has_relic_presence(other, None)
            if hot and prefs.get("auto_avoid_relic_echo", True):
                # do not pause auto — soft-skip in run loop
                return False, "เลี่ยงเงาออร่าเรลิก"
            if hot:
                return True, "เงาแผ่ออร่าเรลิก — ตัดสินใจมือ (ถอย/นอบน้อม/ก้าวร้าว)"
        except Exception:
            pass
        return True, "เงาผู้เล่น — ต้องตัดสินใจ"
    if kind == "monster":
        mon = sight.get("monster") or {}
        threat = monster_threat(player, mon)
        if threat in ("high", "deadly"):
            return True, f"มอนอันตราย ({sight.get('label')})"
        if not sight.get("known") and threat != "easy":
            return True, f"??? ที่ยังไม่ชัวร์ ({sight.get('hint')})"
        # WO-004: low morale → do not auto-engage even easy mobs (caution/retreat)
        try:
            from game.domain.needs import get_needs
            from game.runtime.dungeon_auto import ensure_auto_prefs

            prefs = ensure_auto_prefs(player)
            mor = int(get_needs(player).get("morale") or 0)
            thr = int(prefs.get("morale") or 35)
            pol = str(prefs.get("low_morale_policy") or "caution")
            if pol != "ignore" and mor <= thr:
                return True, f"ขวัญไม่นิ่ง (ขวัญ {mor}) — เลี่ยงไฟต์ออโต้"
        except Exception:
            pass
        return False, "มอนอ่อน — ออโต้จัดการได้"
    return True, "เหตุการณ์"


def run_auto_farm(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: Optional[random.Random] = None,
    max_ticks: int = AUTO_MAX_TICKS_DEFAULT,
    continuous: bool = False,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Run auto ticks until pause event, player stops, HP critical, or max_ticks.
    continuous=True skips per-tick Enter prompt (still pauses on risk).
    Returns (reason, optional_sight_to_handle).
    WO-011: tracks Auto Run log + end-of-run summary.
    """
    rng = rng or random.Random()
    from game.ui_terminal.layout import render_box
    from game.runtime.auto_run_log import (
        auto_run_time_up,
        bump_auto_run,
        emit_auto_run_summary,
        format_god_compact_status,
        format_policy_status_line,
        is_god_compact,
        log_auto_event,
        observe_auto_lines,
        start_auto_run,
    )

    max_seconds = int(player.pop("_playtest_max_seconds", 0) or 0)
    start_auto_run(
        player,
        kind="field",
        label="Field Auto",
        max_ticks=max_ticks,
        max_seconds=max_seconds,
    )

    lines = [
        " โหมดออโต้ฟาร์ม",
        "---",
        f" สูงสุด   {max_ticks} เทิร์น",
        f" XP ออโต้  ×{AUTO_XP_FACTOR}",
        " หยุดเมื่อ  เจอความเสี่ยง / เลือดต่ำ / ครบเวลา",
        f" {format_policy_status_line(player, reg)}"[:56],
        "---",
    ]
    if max_seconds > 0:
        lines.append(f" เวลาเล่น  ≤ {max_seconds} วินาที (playtest)")
    if continuous:
        lines.append(" โหมด  ต่อเนื่อง (ไม่ถาม Enter ทุกติก)")
    else:
        lines.append(" แต่ละติก  Enter=ต่อ · s=หยุด")
    if is_god_compact(player):
        lines.append(" God Compact  เปิด — แสดงกายใจ+Policy ทุกติก")
    io.write_line()
    io.write_line(render_box(lines, double=False))

    area_id = str(player.get("location"))

    def _end(reason: str, sight: Optional[Dict[str, Any]] = None):
        emit_auto_run_summary(player, io, reason, reg=reg)
        return reason, sight

    for tick in range(1, max_ticks + 1):
        if auto_run_time_up(player):
            io.write_line(f"ออโต้หยุด: ครบเวลา playtest ({max_seconds}s)")
            return _end("time")

        area_id = str(player.get("location"))
        _, need, pct = xp_progress(player, reg.levels)
        player["xp_percent"] = round(pct, 1)
        player["xp_needed"] = need
        player["time_units"] = int(player.get("time_units", 0)) + 1
        bump_auto_run(player, "ticks")

        apply_field_regen(player, reg)
        if int(player["hp"]) < max(15, int(player["max_hp"]) * 0.2):
            io.write_line(render_status_l0(player, reg.area_name(area_id)))
            io.write_line("ออโต้หยุด: เลือดต่ำ — ควรพัก/ใช้ยา")
            log_auto_event(player, "needs", "เลือดต่ำ — หยุดออโต้", level="warn")
            return _end("hp")

        # WO-004: field auto inventory + needs care
        rested = False
        avoid_fight = False
        try:
            from game.runtime.inventory_auto import (
                auto_free_bag_space,
                ensure_inv_auto_prefs,
                format_inv_auto_hud,
                soft_stock_warnings,
            )

            # bag space here; buy/use consumables via run_auto_needs_care (avoid double)
            ip = ensure_inv_auto_prefs(player)
            bag_lines: List[str] = []
            if ip.get("inv_manage", True) and (
                ip.get("inv_sell_junk", True) or ip.get("inv_drop_junk", True)
            ):
                bag_lines.extend(
                    auto_free_bag_space(
                        player,
                        reg,
                        need_free=int(ip.get("inv_bag_free_slots") or 2),
                        max_drops=int(ip.get("inv_max_junk_drops") or 3),
                    )
                )
            bag_lines.extend(soft_stock_warnings(player, reg, ip))
            for line in bag_lines:
                io.write_line(line)
            observe_auto_lines(player, bag_lines)
            if tick == 1:
                io.write_line(f"  {format_inv_auto_hud(player, reg)}")
        except Exception:
            pass
        try:
            from game.runtime.dungeon_auto import run_auto_needs_care

            care_lines, stop_r, avoid_fight, rested = run_auto_needs_care(
                player, reg, allow_rest=True
            )
            for line in care_lines:
                io.write_line(line)
            observe_auto_lines(player, care_lines)
            if stop_r == "food":
                io.write_line("ออโต้หยุด: อาหาร/หิว")
                return _end("food")
            if stop_r == "morale":
                # WO-033: Soft Alert when stop is morale + burden
                try:
                    from game.domain.divine_burden import worst_burden_band
                    from game.domain.alerts import emit_alert

                    if worst_burden_band(player, reg) != "fit":
                        emit_alert(
                            player,
                            "relic.auto_blocked",
                            io=io,
                            force=True,
                        )
                    else:
                        io.write_line("ออโต้หยุด: ขวัญต่ำ (นโยบาย retreat)")
                except Exception:
                    io.write_line("ออโต้หยุด: ขวัญต่ำ (นโยบาย retreat)")
                return _end("morale")
        except Exception:
            pass

        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "auto_ticks", 1)
        except Exception:
            pass
        sights = build_sights(player, reg, rng, count=3)
        area_name = reg.area_name(area_id)
        if is_god_compact(player):
            io.write_line()
            io.write_line(
                format_god_compact_status(
                    player,
                    area_name,
                    reg=reg,
                    tick=tick,
                    max_ticks=max_ticks,
                )
            )
        else:
            io.write_line(
                f"\n[ออโต้ {tick}/{max_ticks}] "
                f"{render_status_l0(player, area_name)}"
            )

        if rested:
            io.write_line("ออโต้: ใช้ติกนี้พัก — ไม่ไล่เงา")
            if not continuous:
                cmd = io.read_line("(Enter=ต่อ / s=หยุดออโต้) ").strip().lower()
                if cmd in ("s", "stop", "q"):
                    io.write_line("หยุดออโต้ตามคำสั่ง")
                    return _end("stop")
            continue

        # WO-025: soft-log avoid relic-aura echoes (no pause)
        try:
            from game.domain.divine_burden import entity_has_relic_presence
            from game.runtime.dungeon_auto import ensure_auto_prefs

            ap = ensure_auto_prefs(player)
            if ap.get("auto_avoid_relic_echo", True):
                for s in sights:
                    if s.get("kind") not in ("player", "echo"):
                        continue
                    other = s.get("player_echo") or s.get("echo") or s
                    if entity_has_relic_presence(other, reg):
                        msg = (
                            f"ออโต้: เลี่ยงเงา「{s.get('label') or 'เงานิรนาม'}」"
                            " — ออร่าเรลิก"
                        )
                        io.write_line(msg)
                        bump_auto_run(player, "avoids")
                        observe_auto_lines(player, [msg])
                        log_auto_event(player, "avoid", msg[:80])
                        break
        except Exception:
            pass

        # WO-039: soft-resolve faction mini-moments (when not pausing)
        try:
            from game.domain.faction_moments import auto_resolve_moment
            from game.runtime.dungeon_auto import ensure_auto_prefs

            ap = ensure_auto_prefs(player)
            for s in sights:
                if s.get("kind") != "faction_moment":
                    continue
                pause, _ = should_pause_sight(player, s)
                if pause:
                    continue
                for ln in auto_resolve_moment(player, s, reg=reg, prefs=ap):
                    io.write_line(ln)
                    observe_auto_lines(player, [ln])
                log_auto_event(
                    player,
                    "world",
                    f"mini-moment {s.get('label') or s.get('moment_id')}",
                )
                break  # one moment per tick
        except Exception:
            pass

        # WO-Shop-5: soft-resolve shop reputation events (auto prefers help)
        try:
            from game.domain.shop_rep_content import auto_resolve_shop_rep_event

            for s in sights:
                if s.get("kind") != "shop_rep_event":
                    continue
                for ln in auto_resolve_shop_rep_event(player, s, reg=reg, prefer_help=True):
                    io.write_line(ln)
                    observe_auto_lines(player, [ln])
                log_auto_event(
                    player,
                    "world",
                    f"shop-event {s.get('label') or s.get('event_id')}",
                )
                break
        except Exception:
            pass

        paused = None
        for sight in sights:
            pause, reason = should_pause_sight(player, sight)
            if pause:
                paused = (sight, reason)
                break

        if paused:
            sight, reason = paused
            bump_auto_run(player, "pauses")
            log_auto_event(player, "pause", f"{reason}")
            io.write_line(f"⏸ หยุดออโต้: {reason}")
            io.write_line(
                f"   → [{sight.get('kind')}] {sight.get('label')} — {sight.get('hint')}"
            )
            io.write_line("1. เข้าหาเอง  2. ข้ามเป้านี้ (ออโต้ต่อ)  3. ปิดออโต้")
            ch = io.read_line("เลือก: ").strip()
            if ch == "1":
                return _end("pause", sight)
            if ch == "3":
                return _end("stop")
            io.write_line("ข้ามเป้า — เดินสำรวจต่อ")
            continue

        easy_mobs = [
            s
            for s in sights
            if s.get("kind") == "monster" and not should_pause_sight(player, s)[0]
        ]
        if easy_mobs and not avoid_fight:
            sight = easy_mobs[0]
            mon = dict(sight.get("monster") or pick_monster(reg, area_id, rng))
            if resolve_approach("monster", reg, rng) == "ambush":
                profile = pick_monster_attack(mon, rng, player=player)
                raw = monster_raw_damage(mon, profile, rng)
                player["hp"] -= max(1, raw // 2)
                io.write_line(f"ออโต้: โดนซุ่มเบาๆ -{max(1, raw // 2)} HP")
            logs = auto_fight(player, mon, reg, rng, area_id)
            for line in logs:
                io.write_line(line)
            # WO-017 R3: 1 fight outcome = 1 counter (not per log line)
            bump_auto_run(player, "fights")
            observe_auto_lines(player, logs)  # log only
            try:
                from game.domain.needs import apply_needs_event

                apply_needs_event(player, "explore", silent=True)
            except Exception:
                pass
        else:
            if avoid_fight and easy_mobs:
                msg = "ออโต้: ขวัญไม่นิ่ง — เลี่ยงมอน เดินสำรวจแทน"
                io.write_line(msg)
                bump_auto_run(player, "avoids")
                observe_auto_lines(player, [msg])
            am = dict(player.get("area_mastery") or {})
            am[area_id] = min(100, int(am.get(area_id, 0)) + 1)
            player["area_mastery"] = am
            grant_xp(player, max(1, int(2 * AUTO_XP_FACTOR)), reg.levels)
            io.write_line("ออโต้: สำรวจสงบ ชำนาญ+1 · XP นิดหน่อย")
            try:
                from game.domain.needs import apply_needs_event

                apply_needs_event(player, "explore", silent=True)
            except Exception:
                pass

        if not continuous:
            cmd = io.read_line("(Enter=ต่อ / s=หยุดออโต้) ").strip().lower()
            if cmd in ("s", "stop", "q"):
                io.write_line("หยุดออโต้ตามคำสั่ง")
                return _end("stop")

        if int(player["hp"]) <= 0:
            player["hp"] = max(8, int(player["max_hp"]) // 2)
            return _end("hp")

    io.write_line(f"ออโต้ครบ {max_ticks} เทิร์น")
    return _end("done")

