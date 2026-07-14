"""Mission board UI — funded by market tax wages."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.mission_board import (
    abandon_mission,
    accept_mission,
    check_mission_progress,
    complete_mission_if_done,
    format_board_status,
    list_visible_missions,
    player_rank,
)
from game.ports.io import IO
from game.services.save_service import save_player


def run_mission_board(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    world_id: Optional[str] = None,
) -> None:
    world_id = world_id or str(player.get("world_id") or "default")
    # auto-complete if already done
    for line in complete_mission_if_done(player, reg):
        io.write_line(line)

    while True:
        io.write_line()
        for line in format_board_status(player, world_id):
            io.write_line(line)
        io.write_line("---")
        io.write_line(" 1. ดู/รับงานตามแรงก์")
        io.write_line(" 2. ตรวจความคืบหน้างานค้าง")
        io.write_line(" 3. ละทิ้งงานค้าง")
        io.write_line(" 0. กลับ")
        ch = io.read_line("กระดาน: ").strip()
        if ch in ("0", ""):
            try:
                save_player(player, world_id=world_id)
            except Exception:
                pass
            break
        if ch == "1":
            _accept_flow(player, reg, io, world_id)
        elif ch == "2":
            _progress_flow(player, reg, io)
        elif ch == "3":
            io.write_line(abandon_mission(player))
        else:
            io.write_line("เลือก 0–3")


def _accept_flow(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    world_id: str,
) -> None:
    if player.get("board_mission"):
        io.write_line("มีงานค้าง — เคลียร์หรือละทิ้งก่อน")
        return
    missions = list_visible_missions(player, reg)
    if not missions:
        io.write_line(
            f"ยังไม่มีงานที่แรงก์ {player_rank(player)} รับได้ "
            "(หรืองานพิเศษยังไม่เปิดให้คุณ — ไม่บอกเงื่อนไข)"
        )
        return
    io.write_line(f"── งานที่รับได้ (แรงก์คุณ {player_rank(player)}) ──")
    io.write_line("  แรงก์: F < E < D < C < B < A < S < SS < SSS")
    for i, m in enumerate(missions, 1):
        star = "★ " if m.get("special") else ""
        io.write_line(
            f"  {i}. [{m.get('rank')}] {star}{m.get('name')}  "
            f"รางวัล ~{m.get('reward_money')} เงิน / XP ~{m.get('reward_xp')}"
        )
        if m.get("desc"):
            io.write_line(f"      {m.get('desc')}")
    raw = io.read_line("รับหมายเลข (0=กลับ): ").strip()
    if raw in ("0", ""):
        return
    try:
        idx = int(raw) - 1
        m = missions[idx]
    except Exception:
        io.write_line("ไม่ถูกต้อง")
        return
    conf = io.read_line(
        f"รับ 「{m.get('name')}」 แรงก์ {m.get('rank')}? ประเมินความสามารถเอง (y/n): "
    ).strip().lower()
    if conf not in ("y", "yes", "ใช่", "1"):
        io.write_line("ยังไม่รับ")
        return
    ok, msg = accept_mission(player, reg, str(m.get("id")), world_id=world_id)
    io.write_line(msg)


def _progress_flow(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    bm = player.get("board_mission")
    if not bm:
        io.write_line("ไม่มีงานค้าง")
        return
    d, t, done = check_mission_progress(player)
    io.write_line(f" {bm.get('name')} [{bm.get('rank')}]  ความคืบ {d}/{t}")
    if bm.get("desc"):
        io.write_line(f"  {bm.get('desc')}")
    if done:
        for line in complete_mission_if_done(player, reg):
            io.write_line(line)
    else:
        io.write_line("  ยังไม่ครบ — ไปเล่นตามประเภทงาน (ฆ่า/สำรวจ/พัก/เดินทาง/บอส/ดัน)")
    io.read_line("Enter...")


def try_complete_board_mission(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """Hook after field actions that may progress board missions."""
    notes = complete_mission_if_done(player, reg)
    for line in notes:
        io.write_line(line)
