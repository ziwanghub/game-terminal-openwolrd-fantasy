"""World help board + assist flow (H1–H4)."""
from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry
from game.domain.boss import spawn_boss
from game.domain.party import member_from_player_echo
from game.domain.situation import (
    apply_assist_failure,
    apply_assist_victory,
    claim_help_for_helper,
    format_board_lines,
    format_helper_badge,
    format_inbox_preview,
    format_world_signal_log_lines,
    list_open_help_signals,
    load_world_signal_log,
    pop_inbox_detail,
)
from game.ports.io import IO
from game.services.save_service import load_player, save_player


def run_help_board(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: Optional[random.Random] = None,
) -> None:
    """Explore-mode: list SOS signals; optionally assist; world log; inbox."""
    rng = rng or random.Random()
    world_id = str(player.get("world_id") or "default")
    badge = format_helper_badge(player)
    if badge:
        io.write_line(f" ฉายาผู้ช่วยของคุณ: {badge}")
    while True:
        signals = list_open_help_signals(
            world_id,
            exclude_player_id=str(player.get("id") or ""),
            viewer=player,
        )
        for line in format_board_lines(signals):
            io.write_line(line)
        io.write_line(" หมายเลข = ดู/ยื่นมือ · I จดหมาย · L บันทึกโลก · 0 กลับ")
        ch = io.read_line("สัญญาณ> ").strip()
        if ch in ("0", "q", "Q", ""):
            return
        if ch in ("i", "I"):
            _inbox_menu(player, io)
            continue
        if ch in ("l", "L"):
            msgs = load_world_signal_log(world_id)
            for line in format_world_signal_log_lines(msgs):
                io.write_line(line)
            io.read_line("Enter...")
            continue
        try:
            idx = int(ch) - 1
        except ValueError:
            io.write_line("?")
            continue
        if idx < 0 or idx >= len(signals):
            io.write_line("ไม่มีหมายเลขนั้น")
            continue
        sig = signals[idx]
        _signal_detail_and_assist(player, reg, io, rng, sig)


def _inbox_menu(player: Dict[str, Any], io: IO) -> None:
    for line in format_inbox_preview(player):
        io.write_line(line)
    box = list(player.get("world_inbox") or [])
    if not box:
        io.read_line("Enter...")
        return
    io.write_line(" หมายเลข = อ่านละเอียด · 0 กลับ")
    ch = io.read_line("จดหมาย> ").strip()
    if ch in ("0", ""):
        return
    try:
        idx = int(ch) - 1
    except ValueError:
        return
    _, lines = pop_inbox_detail(player, idx)
    for line in lines:
        io.write_line(line)
    io.read_line("Enter...")


def _signal_detail_and_assist(
    helper: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    sig: Dict[str, Any],
) -> None:
    io.write_line(f"\n── สัญญาณของ {sig.get('owner_name')} ──")
    io.write_line(f" {sig.get('label')} · {sig.get('severity_label')}")
    io.write_line(f" ตอบแทน: {sig.get('offer_line')}")
    if sig.get("presence_label"):
        io.write_line(f" ร่องรอย: 〔{sig.get('presence_label')}〕")
    if sig.get("note"):
        io.write_line(f" 「{sig.get('note')}」")
    if not sig.get("claimable"):
        io.write_line(" (มีผู้ช่วย claim แล้วหรือรับไม่ได้)")
        io.read_line("Enter...")
        return
    io.write_line("1. ยื่นมือช่วย (ร่วมทีมเงา · สู้ฝ่าสถานการณ์)")
    io.write_line("0. กลับ")
    ch = io.read_line("ช่วย> ").strip()
    if ch != "1":
        return
    try:
        owner = load_player(str(sig["path"]))
    except Exception as exc:
        io.write_line(f"โหลดเซฟเจ้าของไม่ได้: {exc}")
        return
    # H5 lite: soft presence note (not realtime multiplayer)
    try:
        from game.domain.situation import presence_soft_for_player

        pres = presence_soft_for_player(owner)
        if pres.get("id") == "fresh":
            io.write_line(" …ร่องรอยสด — เงาเจ้าของตอบสนองชัดขึ้นเล็กน้อย (async soft)")
            helper["_assist_fresh_presence"] = True
        elif pres.get("id") == "warm":
            io.write_line(" …เพิ่งผ่าน — เงายังอุ่น")
    except Exception:
        pass
    # re-check after load
    ok, notes = claim_help_for_helper(owner, helper)
    for n in notes:
        io.write_line(n)
    if not ok:
        return
    save_player(owner, world_id=str(owner.get("world_id") or "default"))

    won = _run_assist_combat(helper, owner, reg, io, rng)
    if won:
        result_notes = apply_assist_victory(owner, helper, reg)
        if helper.pop("_assist_fresh_presence", None):
            # soft rep nudge for helping a "fresh" signal
            helper["help_rep"] = int(helper.get("help_rep") or 0) + 1
            result_notes = list(result_notes) + ["「ช่วยตอนร่องรอยสด — ชื่อเสียงซ่อนขยับ」"]
    else:
        result_notes = apply_assist_failure(owner, helper)
        helper.pop("_assist_fresh_presence", None)
    for n in result_notes:
        io.write_line(n)
    save_player(owner, world_id=str(owner.get("world_id") or "default"))
    save_player(helper, world_id=str(helper.get("world_id") or "default"))
    io.write_line(" บันทึกทั้งสองฝั่งแล้ว")
    io.read_line("Enter...")


def _run_assist_combat(
    helper: Dict[str, Any],
    owner: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
) -> bool:
    """Fight dungeon boss as helper with owner echo in party. Returns True if helper wins."""
    from game.services.combat_session import _run_combat

    run = owner.get("dungeon_run") or {}
    area = str(run.get("area_id") or owner.get("location_before_dungeon") or "dark_forest")
    boss_id = run.get("boss_id")
    boss = spawn_boss(reg, area, rng)
    if not boss and boss_id:
        base = reg.monsters.get(str(boss_id)) or {}
        if base:
            boss = {
                "id": boss_id,
                "name": base.get("name") or boss_id,
                "level": int(base.get("level_min") or 10),
                "hp": int(base.get("hp_base") or 200),
                "max_hp": int(base.get("hp_base") or 200),
                "atk": int(base.get("atk_base") or 20),
                "elements": list(base.get("elements") or ["physical"]),
                "xp_mult": float(base.get("xp_mult") or 3),
                "attack_profiles": [],
                "statuses": [],
                "boss": True,
                "dungeon_boss": True,
            }
    if not boss:
        # soft auto-success if no boss data
        io.write_line(" …เงาจาง — วิกฤตคลายโดยไม่ต้องสู้หนัก")
        return True

    boss["dungeon_boss"] = True
    boss["boss"] = True
    try:
        from game.domain.dungeon import apply_dungeon_enemy_mods

        boss = apply_dungeon_enemy_mods(boss, owner)
    except Exception:
        pass

    # temporary party: keep helper party, add owner echo
    saved_party = copy.deepcopy(helper.get("party") or [])
    try:
        echo = member_from_player_echo(owner, affinity=0.55, reg=reg, rng=rng)
        echo["name"] = f"เงา·{owner.get('name')}"
        party = list(helper.get("party") or [])
        if len(party) < 3:
            party.append(echo)
        else:
            party[-1] = echo
        helper["party"] = party
        io.write_line(f"\n☠ ช่วย「{owner.get('name')}」ท้า: {boss.get('name')}")
        io.write_line(f" เงาเจ้าของร่วมทีม: {echo.get('name')}")
        _run_combat(helper, reg, io, rng, mon=boss, ambush=False)
        won = int(boss.get("hp") or 0) <= 0 and int(helper.get("hp") or 0) > 0
        return won
    finally:
        helper["party"] = saved_party
