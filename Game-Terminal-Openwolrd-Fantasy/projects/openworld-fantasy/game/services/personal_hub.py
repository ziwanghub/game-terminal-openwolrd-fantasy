"""PERSONAL mode hub — player management (Mode Shell Phase A)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.mode_shell import (
    MODE_PERSONAL,
    active_mission_line,
    money_summary_lines,
    render_mode_actions,
)
from game.domain.quests import ensure_quests, list_quest_lines
from game.domain.stats import ensure_stats, format_stats_lines
from game.ports.io import IO
from game.services.field_menus import (
    _class_change_menu,
    _manage_gear,
    _party_menu,
    _personality_allocate_menu,
    _run_craft_menu,
    _skill_tree_menu,
    _stat_allocate_menu,
    _ui_prefs_menu,
)
from game.services.save_service import save_player
from game.services.shop import run_shop
from game.ui_terminal.layout import render_box
from game.ui_terminal.status import render_mode_chrome, render_status_l1, render_status_l1c


def run_personal_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    area_name: str = "",
) -> None:
    """
    PERSONAL mode loop until 0.
    Player management. Shop/market: EXPLORE → 6 (SHOP hub). Bag = inventory only.
    """
    area_name = area_name or str(player.get("location") or "")
    while True:
        io.write_line()
        io.write_line(render_mode_chrome("ตัวละคร", area_name))
        io.write_line(render_status_l1c(player, area_name))
        io.write_line(
            render_mode_actions(
                MODE_PERSONAL,
                stat_points=int(player.get("stat_points") or 0),
                personality_points=int(player.get("personality_points") or 0),
                mission_line=active_mission_line(player),
                money_world=int(player.get("money_world") or 0),
            )
        )
        ch = io.read_line("\n〔ตัวละคร〕 เลือก: ").strip()
        if ch in ("0", "", "q", "Q"):
            break
        if ch == "1" or ch in ("s", "S"):
            _show_full_status(player, reg, io, area_name)
        elif ch == "2" or ch in ("bag",):
            _open_bag(player, reg, io)
        elif ch == "3":
            _manage_gear(player, reg, io)
        elif ch == "4" or ch == "9":
            _show_missions(player, reg, io)
        elif ch == "5":
            for line in money_summary_lines(player):
                io.write_line(line)
            io.write_line(" ร้าน/ตลาด → 0 กลับ แล้วกด 6 จากสำรวจ (หรือ M ทางลัด)")
            sub = io.read_line("M=ตลาดผู้เล่น · Enter=กลับ: ").strip()
            if sub in ("m", "M"):
                from game.services.shop_hub import run_shop_hub

                run_shop_hub(player, reg, io, area_name=area_name)
        elif ch == "6":
            _points_submenu(player, reg, io)
        elif ch == "7":
            _skills_party_lib_submenu(player, reg, io)
        elif ch == "8":
            _settings_save_submenu(player, io)
        # hotkey aliases inside PERSONAL
        elif ch in ("p", "P"):
            _stat_allocate_menu(player, reg, io)
        elif ch in ("n", "N"):
            _personality_allocate_menu(player, reg, io)
        elif ch in ("c", "C"):
            _class_change_menu(player, reg, io)
        elif ch in ("k", "K"):
            _skill_tree_menu(player, reg, io)
        elif ch in ("y", "Y"):
            _party_menu(player, reg, io)
        elif ch in ("u", "U"):
            _ui_prefs_menu(player, io)
        elif ch in ("l", "L"):
            _library(player, reg, io)
        elif ch in ("m", "M"):
            from game.services.shop_hub import run_shop_hub

            run_shop_hub(player, reg, io, area_name=area_name)
        elif ch in ("j", "J"):
            from game.services.mission_service import run_mission_board

            run_mission_board(player, reg, io)
        else:
            io.write_line("เลือก 0–8 หรือ hotkey (P/N/S/…)")


def _show_full_status(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    area_name: str,
) -> None:
    ensure_stats(player)
    io.write_line()
    io.write_line(render_mode_chrome("สถานะเต็ม", area_name))
    io.write_line(render_status_l1(player, area_name))
    io.write_line("\n── สถิติการเล่น ──")
    mods = player.get("world_modifiers") or {}
    if mods:
        io.write_line(
            f" โมดิฟายเออร์โลก: HPศัตรู×{mods.get('enemy_hp_mult', 1)} "
            f"ATK×{mods.get('enemy_atk_mult', 1)} XP×{mods.get('xp_mult', 1)}"
        )
    for line in format_stats_lines(player):
        io.write_line(line)
    io.read_line("Enter...")


def _open_bag(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    from game.services.bag_hub import run_bag_hub

    # Phase B: bag = inventory; shop callbacks still optional shortcuts
    run_bag_hub(
        player,
        reg,
        io,
        open_shop=lambda p, r, i: run_shop(p, r, i),
        open_craft=lambda p, r, i: _run_craft_menu(p, r, i),
        open_gear=lambda p, r, i: _manage_gear(p, r, i),
    )


def _show_missions(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_quests(player, reg)
    lines = [" ภารกิจ", "---", *list_quest_lines(player, reg)]
    bm = player.get("board_mission")
    if isinstance(bm, dict) and bm.get("name"):
        lines.append("---")
        lines.append(f" กระดานที่รับ: {bm.get('name')} · แรงก์ {bm.get('rank')}")
        lines.append(f"  {bm.get('desc') or ''}")
    else:
        lines.append(" (ไม่มีงานกระดานค้าง — เปิด J ในกระเป๋าหรือเมนูนี้)")
    io.write_line()
    io.write_line(render_box(lines, double=False))
    io.write_line(" J = กระดานเต็ม · Enter กลับ")
    sub = io.read_line("เลือก: ").strip()
    if sub in ("j", "J"):
        from game.services.mission_service import run_mission_board

        run_mission_board(player, reg, io)


def _points_submenu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    io.write_line(" 1/P แต้มสถานะ  2/N นิสัย  3/C อาชีพ  0 กลับ")
    ch = io.read_line("เลือก: ").strip()
    if ch in ("1", "p", "P"):
        _stat_allocate_menu(player, reg, io)
    elif ch in ("2", "n", "N"):
        _personality_allocate_menu(player, reg, io)
    elif ch in ("3", "c", "C"):
        _class_change_menu(player, reg, io)


def _skills_party_lib_submenu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    io.write_line(" 1/K สกิล  2/Y ปาร์ตี้  3/L ห้องสมุด  0 กลับ")
    ch = io.read_line("เลือก: ").strip()
    if ch in ("1", "k", "K"):
        _skill_tree_menu(player, reg, io)
    elif ch in ("2", "y", "Y"):
        _party_menu(player, reg, io)
    elif ch in ("3", "l", "L"):
        _library(player, reg, io)


def _settings_save_submenu(player: Dict[str, Any], io: IO) -> None:
    io.write_line(" 1/U ตั้งค่าจอ  2 เซฟทันที  0 กลับ")
    ch = io.read_line("เลือก: ").strip()
    if ch in ("1", "u", "U"):
        _ui_prefs_menu(player, io)
    elif ch == "2":
        path = save_player(player)
        io.write_line(f"เซฟแล้ว → {path}")
        io.read_line("Enter...")


def _library(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    from game.domain.narrative import emit_narrative, narrate_field
    from game.domain.progression import (
        library_visit,
        try_occupation_rank_up,
        try_unit_unlock,
    )
    import random

    rng = random.Random(player.get("latent_seed") or 0)
    notes = library_visit(player, reg)
    if notes and "ปิด" in str(notes[0]):
        emit_narrative(io, narrate_field(reg, "library_denied", rng))
    else:
        emit_narrative(io, narrate_field(reg, "library", rng))
    for line in notes:
        io.write_line(line)
    for line in try_occupation_rank_up(player, reg):
        io.write_line(line)
    for line in try_unit_unlock(player, reg):
        io.write_line(line)
    io.read_line("Enter...")
