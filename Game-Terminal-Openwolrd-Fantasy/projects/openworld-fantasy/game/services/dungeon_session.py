"""Dungeon field session — enter, floor turns, boss, escape, help signal (H0–H2)."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional, Union

from game.data_load.registry import DataRegistry
from game.domain.dungeon import (
    advance_floor,
    begin_dungeon,
    dungeon_by_id,
    dungeon_menu_actions,
    exit_dungeon,
    explore_floor_event,
    format_dungeon_panel,
    get_run,
    in_dungeon,
    soft_difficulty_text,
    tick_dungeon_time,
    try_escape,
)
from game.domain.party import format_party_panel
from game.domain.situation import (
    POLICY_FRIENDS,
    POLICY_PUBLIC,
    close_help_request,
    consent_warning_lines,
    format_help_status_lines,
    help_is_open,
    open_help_request,
    sync_situation_from_dungeon,
)
from game.ports.io import IO
from game.services.combat_session import _run_combat
from game.services.field_menus import _party_menu
from game.services.save_service import save_player


def _help_signal_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> Optional[str]:
    """
    H0–H2: open/close help + offer escrow.
    Returns 'quit_save' if owner wants to save & wait for help (leave field).
    """
    sync_situation_from_dungeon(player, preserve_help=True)
    for line in format_help_status_lines(player):
        io.write_line(line)
    if help_is_open(player):
        io.write_line("1. ปิดสัญญาณขอแรง (คืนของล็อก)")
        io.write_line("2. ดูสถานะ")
        io.write_line("3. บันทึกและพักรอแรง (ออกเมนูหลัก — ดันยังค้าง)")
        io.write_line("0. กลับ")
        ch = io.read_line("สัญญาณ> ").strip()
        if ch == "1":
            ok, notes = close_help_request(player, reg, reason="owner_cancel")
            for n in notes:
                io.write_line(n)
        elif ch == "2":
            for line in format_help_status_lines(player):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch == "3":
            path = save_player(player)
            io.write_line(f"บันทึกพักรอแรง → {path}")
            io.write_line("สัญญาณยังเปิดในโลก — ผู้เล่นอื่นเปิดกระดาน G เพื่อยื่นมือ")
            return "quit_save"
        return None

    for line in consent_warning_lines():
        io.write_line(line)
    io.write_line("1. เปิดสัญญาณ (อาสา — ไม่ล็อกของ)")
    io.write_line("2. เปิดพร้อมข้อความสั้น")
    io.write_line("3. เปิดพร้อมเงินตอบแทน")
    io.write_line("4. เปิดพร้อมไอเทมตอบแทน (id แรกในกระเป๋าที่พิมพ์)")
    io.write_line("0. ยังไม่ขอ")
    ch = io.read_line("ขอแรง> ").strip()
    if ch in ("0", ""):
        io.write_line("ยังไม่เปิดสัญญาณ")
        return None
    note = ""
    gold = 0
    item_ids: list = []
    if ch == "2":
        note = io.read_line("ข้อความ (สั้น): ").strip()[:80]
    elif ch == "3":
        note = io.read_line("ข้อความ (Enter=ว่าง): ").strip()[:80]
        try:
            gold = int(io.read_line(f"เงินตอบแทน (มี {player.get('money_world', 0)}G): ").strip() or "0")
        except ValueError:
            gold = 0
    elif ch == "4":
        note = io.read_line("ข้อความ (Enter=ว่าง): ").strip()[:80]
        bag = list(player.get("inventory_ids") or [])
        io.write_line(" กระเป๋า (id): " + ", ".join(bag[:12]) + ("…" if len(bag) > 12 else ""))
        raw = io.read_line("ไอเทม id (คั่นด้วยช่องว่าง ถ้าหลายชิ้น): ").strip()
        item_ids = [x for x in raw.split() if x]
        try:
            gold = int(io.read_line("เงินเพิ่ม (0=ไม่มี): ").strip() or "0")
        except ValueError:
            gold = 0
    elif ch != "1":
        io.write_line("ยกเลิก")
        return None
    io.write_line(" ขอบเขตผู้รับสัญญาณ:")
    io.write_line(" 1 สาธารณะในโลก  2 เฉพาะสายสัมพันธ์ (เพื่อน)")
    pol_ch = io.read_line("ขอบเขต> ").strip()
    policy = POLICY_FRIENDS if pol_ch == "2" else POLICY_PUBLIC
    ok, notes = open_help_request(
        player, reg, note=note, gold=gold, item_ids=item_ids, policy=policy
    )
    for n in notes:
        io.write_line(n)
    if ok:
        io.write_line(" เปิดแล้ว — เลือก 6→3 เพื่อบันทึกพักรอแรง หรือเล่นต่อ")
    return None


def _enter_dungeon_flow(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    dungeon_id: str,
) -> None:
    """Confirm party prep then enter — difficulty unknown."""
    d = dungeon_by_id(reg, dungeon_id)
    if not d:
        io.write_line("ทางเข้าจางหาย...")
        return
    soft = soft_difficulty_text(player, reg, d)
    from game.ui_terminal.layout import render_box

    lines = [
        f" ปากดันเจียน · {d.get('name')}",
        "---",
        f" สัญญาณ   {soft}",
        " ความยาก  ซ่อน (สังเกต / หาข้อมูลเอง)",
        f" ปาร์ตี้   {len(player.get('party') or [])}/3",
        "---",
    ]
    for line in format_party_panel(player, reg):
        if "ปาร์ตี้" in line or "·" in line:
            lines.append(f" {line.strip()}")
    lines.extend(
        [
            "---",
            "  1  เข้าไปเคลียร์ (ทางออกอาจล็อก)",
            "  2  จัดปาร์ตี้ก่อน",
            "  0  ถอย",
        ]
    )
    io.write_line()
    io.write_line(render_box(lines, double=False))
    ch = io.read_line("\n  เลือก (1/2/0): ").strip()
    if ch == "2":
        _party_menu(player, reg, io)
        conf = io.read_line("เข้าดันเจียนเลย? (1=ใช่): ").strip()
        if conf != "1":
            io.write_line("คุณถอยจากปากถ้ำ")
            return
    elif ch != "1":
        io.write_line("คุณถอยจากปากถ้ำ")
        return
    for line in begin_dungeon(player, reg, dungeon_id, rng):
        io.write_line(line)


def _dungeon_field_turn(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
) -> Union[bool, str]:
    """
    Restricted loop while locked in dungeon.
    Returns True to continue field, 'quit_save' to leave field after save.
    """
    run = get_run(player)
    if not run:
        return True
    from game.ui_terminal.layout import render_box

    io.write_line()
    io.write_line(render_box(format_dungeon_panel(player, reg), double=False))
    acts = dungeon_menu_actions(player)
    if acts:
        io.write_line()
        io.write_line(render_box(acts, double=False))
    ch = io.read_line("\n  ในดัน เลือก (1–6 · Y · 0): ").strip()
    acted = False
    if ch == "1":
        io.write_line("สำรวจชั้นนี้...")
        ev = explore_floor_event(player, reg, rng)
        for line in ev.get("notes") or []:
            io.write_line(line)
        if ev.get("trigger_combat"):
            _run_combat(player, reg, io, rng)
        acted = True
    elif ch == "2":
        for line in advance_floor(player, reg, rng):
            io.write_line(line)
        acted = True
    elif ch == "3":
        run = get_run(player) or {}
        floor = int(run.get("floor") or 1)
        floors = int(run.get("floors") or 1)
        if floor < floors and not run.get("boss_defeated"):
            io.write_line("บอสยังอยู่ชั้นในสุด — ลงลึกกว่านี้ก่อน")
        elif run.get("boss_defeated"):
            io.write_line("บอสล้มแล้ว — เก็บของ/ออกได้")
        else:
            boss_id = run.get("boss_id")
            from game.domain.boss import spawn_boss

            area_for_boss = str(run.get("area_id") or "dark_forest")
            boss = spawn_boss(reg, area_for_boss, rng)
            if not boss:
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
            if boss:
                boss["dungeon_boss"] = True
                boss["boss"] = True
                io.write_line(f"\n☠ เผชิญบอสดันเจียน: {boss.get('name')}")
                _run_combat(player, reg, io, rng, mon=boss, ambush=False)
            else:
                io.write_line("ไม่พบบอส — ข้อมูลหาย")
            acted = True
    elif ch == "4":
        for line in try_escape(player, reg, rng):
            io.write_line(line)
        acted = True
    elif ch == "5":
        for line in format_dungeon_panel(player, reg):
            io.write_line(line)
        io.read_line("Enter...")
    elif ch == "6":
        result = _help_signal_menu(player, reg, io)
        if result == "quit_save":
            return "quit_save"
    elif ch in ("y", "Y"):
        _party_menu(player, reg, io)
    elif ch == "0":
        for line in exit_dungeon(player, reg, success=True):
            io.write_line(line)
    else:
        io.write_line("เลือกไม่ถูกต้อง")
    if acted and in_dungeon(player):
        for line in tick_dungeon_time(player, reg, rng, cost=1):
            io.write_line(line)
        sync_situation_from_dungeon(player, preserve_help=True)
    return True
