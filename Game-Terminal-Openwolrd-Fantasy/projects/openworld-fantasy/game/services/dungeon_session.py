"""Dungeon field session v2 — free exit, floor bosses, depth, help signal."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional, Union

from game.data_load.registry import DataRegistry
from game.domain.dungeon import (
    advance_floor,
    begin_dungeon,
    can_advance_floor,
    count_escape_shards,
    dungeon_by_id,
    dungeon_menu_actions,
    dungeon_rest,
    dungeon_shop_price_mult,
    exit_dungeon,
    explore_floor_event,
    format_dungeon_panel,
    get_run,
    in_dungeon,
    set_boss_encounter,
    soft_difficulty_text,
    spawn_floor_boss,
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
    """Confirm party prep then enter — difficulty / depth unknown."""
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
        " ความยาก  ซ่อน · ลึกแค่ไหน — ไม่รู้จนกว่าจะลง",
        f" ปาร์ตี้   {len(player.get('party') or [])}/3",
        "---",
        " · เดินออกได้ทุกเมื่อ (ยกเว้นตอนท้าผู้เฝ้าชั้น)",
        " · ต้องกำจัดผู้เฝ้าชั้น ถึงจะลงลึก",
        " · ไฟต์ผู้เฝ้า: หนีปกติไม่ได้ — ใช้เศษหนีหรือสู้",
        "---",
    ]
    # WO-015: soft foresight before entry
    try:
        from game.domain.soft_foresight import soft_dungeon_entry_warnings

        for w in soft_dungeon_entry_warnings(player, reg, dungeon=d):
            lines.append(w if str(w).startswith(" ") else f" {w}")
        lines.append("---")
    except Exception:
        pass
    for line in format_party_panel(player, reg):
        if "ปาร์ตี้" in line or "·" in line:
            lines.append(f" {line.strip()}")
    lines.extend(
        [
            "---",
            "  1  เข้าไป (สำรวจ / ลงลึก)",
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
    # extreme underprep: one more soft confirm
    try:
        from game.domain.soft_foresight import should_soft_block_dungeon

        if should_soft_block_dungeon(player, reg):
            io.write_line(
                " ⚠ สภาพวิกฤต (หิว/ขวัญ + ไม่มีอาหาร) — ลงต่ออาจสลบเร็ว"
            )
            conf2 = io.read_line("  ยังจะลง? (1=ยืนยัน · 0=ถอย): ").strip()
            if conf2 != "1":
                io.write_line("คุณถอยจากปากถ้ำ")
                return
    except Exception:
        pass
    for line in begin_dungeon(player, reg, dungeon_id, rng):
        io.write_line(line)


def _confirm_floor_boss(player: Dict[str, Any], reg: DataRegistry, io: IO) -> bool:
    """UX: player must confirm boss challenge (no normal flee)."""
    from game.ui_terminal.layout import render_box

    shards = count_escape_shards(player, reg)
    run = get_run(player) or {}
    depth = int(run.get("depth") or run.get("floor") or 1)
    lines = [
        " ท้าทายผู้เฝ้าชั้น",
        "---",
        f" ความลึก   ลงมาชั้นที่ {depth}",
        " · หนีปกติใช้ไม่ได้",
        " · ชนะ = ทางลงเปิด · แพ้ = ถูกเหวี่ยงออก (เสียของบางส่วน)",
    ]
    if shards:
        names = " · ".join(n for _, _, n in shards[:3])
        lines.append(f" · เศษหนีในมือ: {len(shards)} ชิ้น ({names})")
    else:
        lines.append(" · เศษหนีในมือ: ไม่มี — ต้องมั่นใจว่าชนะได้")
    lines.extend(
        [
            "---",
            "  1  มั่นใจ — ท้าทาย",
            "  0  ยังไม่พร้อม",
        ]
    )
    io.write_line()
    io.write_line(render_box(lines, double=False))
    ch = io.read_line("\n  ยืนยัน (1/0): ").strip()
    return ch == "1"


def _dungeon_field_turn(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
) -> Union[bool, str]:
    """
    Dungeon explore loop (v2).
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
    ch = io.read_line("\n  ในดัน เลือก (1–9 · A ออโต้ · Y · 0): ").strip()
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
        run = get_run(player) or {}
        if run.get("boss_defeated"):
            io.write_line("หัวใจดันสงบแล้ว — ไม่มีผู้เฝ้าอีก")
        elif run.get("floor_boss_cleared"):
            io.write_line("ผู้เฝ้าชั้นนี้ล้มแล้ว — ลงลึก (3) หรือออก (4)")
        else:
            if not _confirm_floor_boss(player, reg, io):
                io.write_line("คุณยังไม่ท้าทาย — เตรียมตัวต่อ")
            else:
                boss = spawn_floor_boss(player, reg, rng)
                if not boss:
                    io.write_line("เงาผู้เฝ้าจางหาย... (ลองสำรวจก่อน)")
                else:
                    set_boss_encounter(player, True)
                    soft_name = "ผู้เฝ้าชั้น" if not boss.get("dungeon_heart_boss") else "เงาที่ปลายโพรง"
                    io.write_line(f"\n☠ {soft_name} ปรากฏ — วงบอสขังคุณ!")
                    io.write_line(" หนีปกติใช้ไม่ได้ · เศษหนีเท่านั้น (เมนูหนี)")
                    _run_combat(player, reg, io, rng, mon=boss, ambush=False)
                    # ensure flag cleared if combat ended oddly
                    if in_dungeon(player):
                        set_boss_encounter(player, False)
                    acted = True

    elif ch == "3":
        for line in advance_floor(player, reg, rng):
            io.write_line(line)
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

    elif ch == "7":
        # bag / potions while in dungeon
        try:
            from game.services.bag_hub import run_bag_hub
            from game.services.shop import run_shop

            run_bag_hub(
                player,
                reg,
                io,
                open_shop=lambda p, r, i: run_shop(p, r, i),
            )
        except Exception as e:
            io.write_line(f" กระเป๋าใช้ไม่ได้ชั่วคราว ({e})")

    elif ch == "8":
        # shadow shop inside dungeon (prices auto markup via scaled_price)
        try:
            from game.services.shop import run_shop

            io.write_line(
                f" ร้านเงาในโพรง — ราคาประมาณ ×{dungeon_shop_price_mult(player):.2f} (soft)"
            )
            run_shop(player, reg, io)
        except Exception as e:
            io.write_line(f" ร้านเงาเลือนหาย... ({e})")

    elif ch == "9":
        io.write_line("พักในมุมมืด...")
        result = dungeon_rest(player, reg, rng)
        for line in result.get("notes") or []:
            io.write_line(line)
        if result.get("trigger_combat"):
            _run_combat(
                player, reg, io, rng, ambush=bool(result.get("ambush"))
            )
        acted = True

    elif ch in ("a", "A"):
        from game.runtime.dungeon_auto import (
            can_auto_fight_floor_boss,
            count_food,
            ensure_auto_prefs,
            format_dungeon_auto_hud,
            run_dungeon_auto,
        )

        ensure_auto_prefs(player)
        io.write_line(format_dungeon_auto_hud(player, reg))
        if count_food(player, reg) <= 0:
            io.write_line(" ⚠ ไม่มีอาหาร — ออโต้จะหิวเร็ว · แนะนำ 8 ร้านเงาก่อน")
        if not can_auto_fight_floor_boss(player):
            io.write_line(
                " บอสชั้นนี้ยังไม่เคยชนะด้วยมือ — ออโต้จะไม่ท้าหัวใจ/ผู้เฝ้าแทนคุณ"
            )
            io.write_line(" (สำรวจ/มอนทั่วไปยังออโต้ได้ · ท้าบอสใช้เมนู 2 ก่อน 1 ครั้ง)")
        conf = io.read_line(" ตั้งค่าออโต้ก่อน? (Enter=ใช่ · s=ข้ามใช้ค่าเดิม): ").strip().lower()
        skip_cfg = conf in ("s", "skip", "n", "0")
        raw = io.read_line(" ติก (Enter=15 · หรือเลข 5–40): ").strip()
        ticks = 15
        if raw.isdigit():
            ticks = max(5, min(40, int(raw)))
        run_dungeon_auto(
            player,
            reg,
            io,
            rng,
            max_ticks=ticks,
            continuous=True,
            skip_config=skip_cfg,
        )
        acted = True

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
