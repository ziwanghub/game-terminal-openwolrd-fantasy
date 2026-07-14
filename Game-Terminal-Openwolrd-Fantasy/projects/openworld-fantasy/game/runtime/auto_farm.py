"""P9 — Auto-farm: tick the field, auto-resolve easy fights, pause on risk."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

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


def auto_fight(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    area_id: str,
) -> List[str]:
    """Resolve a simple auto combat (attack spam + crude defend). Returns log lines."""
    lines: List[str] = []
    turn = 0
    while mon["hp"] > 0 and player["hp"] > 0 and turn < 40:
        turn += 1
        skill = {"power": 8 + int(player.get("bonus_atk", 0)) // 2, "elements": ["physical"]}
        # Prefer elemental starter skill if owned
        for sid in player.get("skills") or []:
            sk = reg.skills.get(sid) or {}
            if sk.get("slot") == "combat" and sk.get("power") and int(sk.get("cost_mana", 0)) <= int(player.get("mana", 0)):
                if sid in ("fire_ball", "water_bolt", "shadow_strike", "magic_missile"):
                    if int(player["mana"]) >= int(sk.get("cost_mana", 0)):
                        player["mana"] = int(player["mana"]) - int(sk.get("cost_mana", 0))
                        skill = sk
                        break
        dmg, _ = player_attack_damage(player, mon, reg, area_id, skill, rng)
        mon["hp"] -= dmg
        if mon["hp"] <= 0:
            break
        profile = pick_monster_attack(mon, rng, player=player)
        raw = monster_raw_damage(mon, profile, rng)
        # crude auto-guard: half if HP low
        if int(player["hp"]) < int(player["max_hp"]) * 0.35:
            raw = max(1, raw // 2)
        player["hp"] -= raw
        # light mana regen
        player["mana"] = min(int(player["max_mana"]), int(player["mana"]) + 1)

    if player["hp"] <= 0:
        player["hp"] = max(8, int(player["max_hp"]) // 2)
        lines.append("ออโต้: แพ้ — ฟื้นครึ่งเลือด (soft)")
        mark_monster_seen(player, mon)
        return lines

    # Victory with reduced XP
    full_xp = kill_xp_reward(
        int(player.get("level", 1)),
        int(mon.get("level", 1)),
        float(mon.get("xp_mult", 1.0)),
        reg.levels,
    )
    xp = max(1, int(full_xp * AUTO_XP_FACTOR))
    summary = grant_xp(player, xp, reg.levels)
    lines.append(
        f"ออโต้ชนะ {mon.get('name')} · XP +{summary['gained']} (ลดแล้ว {int(AUTO_XP_FACTOR*100)}%) "
        f"Lv.{player['level']} {summary['xp_percent']:.0f}%"
    )
    for n in summary["notes"]:
        lines.append(n)
    # lighter mastery/money than full resolve_victory
    am = dict(player.get("area_mastery") or {})
    am[area_id] = min(100, int(am.get(area_id, 0)) + 1)
    player["area_mastery"] = am
    player["money_world"] = int(player.get("money_world", 0)) + rng.randint(3, 12)
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
    if kind == "npc":
        return True, "คนแปลกหน้า — ต้องตัดสินใจ"
    if kind == "monster":
        mon = sight.get("monster") or {}
        threat = monster_threat(player, mon)
        if threat in ("high", "deadly"):
            return True, f"มอนอันตราย ({sight.get('label')})"
        if not sight.get("known") and threat != "easy":
            return True, f"??? ที่ยังไม่ชัวร์ ({sight.get('hint')})"
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
    """
    rng = rng or random.Random()
    from game.ui_terminal.layout import render_box

    lines = [
        " โหมดออโต้ฟาร์ม",
        "---",
        f" สูงสุด   {max_ticks} เทิร์น",
        f" XP ออโต้  ×{AUTO_XP_FACTOR}",
        " หยุดเมื่อ  เจอความเสี่ยง / เลือดต่ำ",
        "---",
    ]
    if continuous:
        lines.append(" โหมด  ต่อเนื่อง (ไม่ถาม Enter ทุกติก)")
    else:
        lines.append(" แต่ละติก  Enter=ต่อ · s=หยุด")
    io.write_line()
    io.write_line(render_box(lines, double=False))

    area_id = str(player.get("location"))

    for tick in range(1, max_ticks + 1):
        area_id = str(player.get("location"))
        _, need, pct = xp_progress(player, reg.levels)
        player["xp_percent"] = round(pct, 1)
        player["xp_needed"] = need
        player["time_units"] = int(player.get("time_units", 0)) + 1

        apply_field_regen(player, reg)
        if int(player["hp"]) < max(15, int(player["max_hp"]) * 0.2):
            io.write_line(render_status_l0(player, reg.area_name(area_id)))
            io.write_line("ออโต้หยุด: เลือดต่ำ — ควรพัก/ใช้ยา")
            return "hp", None

        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "auto_ticks", 1)
        except Exception:
            pass
        sights = build_sights(player, reg, rng, count=3)
        io.write_line(f"\n[ออโต้ {tick}/{max_ticks}] {render_status_l0(player, reg.area_name(area_id))}")

        paused = None
        for sight in sights:
            pause, reason = should_pause_sight(player, sight)
            if pause:
                paused = (sight, reason)
                break

        if paused:
            sight, reason = paused
            io.write_line(f"⏸ หยุดออโต้: {reason}")
            io.write_line(
                f"   → [{sight.get('kind')}] {sight.get('label')} — {sight.get('hint')}"
            )
            io.write_line("1. เข้าหาเอง  2. ข้ามเป้านี้ (ออโต้ต่อ)  3. ปิดออโต้")
            ch = io.read_line("เลือก: ").strip()
            if ch == "1":
                return "pause", sight
            if ch == "3":
                return "stop", None
            io.write_line("ข้ามเป้า — เดินสำรวจต่อ")
            continue

        easy_mobs = [
            s
            for s in sights
            if s.get("kind") == "monster" and not should_pause_sight(player, s)[0]
        ]
        if easy_mobs:
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
        else:
            am = dict(player.get("area_mastery") or {})
            am[area_id] = min(100, int(am.get(area_id, 0)) + 1)
            player["area_mastery"] = am
            grant_xp(player, max(1, int(2 * AUTO_XP_FACTOR)), reg.levels)
            io.write_line("ออโต้: สำรวจสงบ ชำนาญ+1 · XP นิดหน่อย")

        if not continuous:
            cmd = io.read_line("(Enter=ต่อ / s=หยุดออโต้) ").strip().lower()
            if cmd in ("s", "stop", "q"):
                io.write_line("หยุดออโต้ตามคำสั่ง")
                return "stop", None

        if int(player["hp"]) <= 0:
            player["hp"] = max(8, int(player["max_hp"]) // 2)
            return "hp", None

    io.write_line(f"ออโต้ครบ {max_ticks} เทิร์น")
    return "done", None

