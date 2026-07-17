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
    from game.ui_terminal.status import format_personal_hub_lines

    # T3: stamp panel session + optional enter animation
    try:
        from game.domain.needs import (
            apply_tama_panel_live_tick,
            close_tama_panel_session,
            stamp_tama_panel_open,
            tama_enter_animation_frames,
        )
        from game.domain.ui_prefs import ensure_ui_prefs

        stamp_tama_panel_open(player)
        prefs = ensure_ui_prefs(player)
        if prefs.get("tama_enter_anim", True) and not player.get("_tama_enter_anim_done"):
            for frame in tama_enter_animation_frames(player):
                io.write_line()
                io.write_line(render_box([" Tama", "---", *frame], double=False))
            player["_tama_enter_anim_done"] = True
    except Exception:
        pass

    while True:
        # T3: soft live drip while hub open (wall clock between inputs)
        try:
            from game.domain.needs import apply_tama_panel_live_tick

            live_notes = apply_tama_panel_live_tick(player)
        except Exception:
            live_notes = []

        io.write_line()
        io.write_line(render_mode_chrome("ตัวละคร", area_name))
        # One unified frame: vitals + tama + points (no repeat)
        mission = active_mission_line(player)
        io.write_line(
            render_box(
                format_personal_hub_lines(
                    player,
                    area_name,
                    mission_line=mission or "",
                ),
                double=False,
            )
        )
        # T1: flush pending load notes once (below frame)
        pending = player.pop("_pending_load_notes", None)
        if pending:
            io.write_line()
            for line in pending:
                io.write_line(line)
        if live_notes:
            for line in live_notes:
                io.write_line(line)
        # Menu only — points/mission already in hub frame above
        io.write_line()
        pts = int(player.get("stat_points") or 0)
        ppts = int(player.get("personality_points") or 0)
        io.write_line(
            render_mode_actions(
                MODE_PERSONAL,
                stat_points=pts,
                personality_points=ppts,
                mission_line="",
                money_world=None,
                player=player,
                reg=reg,
            )
        )
        if not player.get("_hub_relic_banner_done"):
            player["_hub_relic_banner_done"] = True
            io.write_line(
                "  ใบ้: V=เรื่องของฉัน · W=วิหาร · G=ห้องเรลิก · A=Policy · X=playtest"
            )
        try:
            from game.domain.stat_grades import can_temple_unlock, grade_revealed

            if can_temple_unlock(player) and not grade_revealed(player):
                io.write_line("  …พลังตัน · กด W เข้าวิหารปลดเกรด")
        except Exception:
            pass
        ch = io.read_line(
            "\n  เลือก (V=เรื่องของฉัน · W=วิหาร · R/E/H/M/A · X · G · 1–6 · 0 กลับ): "
        ).strip()
        if ch in ("0", "", "q", "Q"):
            try:
                from game.domain.needs import close_tama_panel_session

                close_tama_panel_session(player)
            except Exception:
                pass
            # WO-Storage-1: lock warehouse session when leaving PERSONAL
            try:
                from game.services.warehouse_hub import lock_warehouse_on_personal_exit

                lock_warehouse_on_personal_exit(player)
            except Exception:
                pass
            break
        # WO-053: Personal Narrative 「เรื่องของฉัน」 (+ optional deep appraisal)
        if ch in (
            "v",
            "V",
            "assess",
            "ประเมิน",
            "self",
            "story",
            "me",
            "เรื่อง",
            "ตัวตน",
        ):
            from game.domain.personal_system import (
                format_personal_narrative_panel,
                maybe_seed_opening_journal,
            )

            maybe_seed_opening_journal(player)
            player["_personal_seen_v"] = True
            io.write_line()
            io.write_line(
                render_box(
                    format_personal_narrative_panel(player, reg),
                    double=False,
                )
            )
            sub = io.read_line(
                "  d=อ่านชั้นลึก · a=ประเมิน soft เดิม · Enter=กลับ: "
            ).strip().lower()
            if sub in ("d", "deep", "appraise", "อ่าน"):
                try:
                    from game.domain.appraisal import run_appraisal

                    deep, growth = run_appraisal(
                        player, target="self", reg=reg, paid=True
                    )
                    io.write_line()
                    box = list(deep)
                    if growth:
                        box.append(growth)
                    io.write_line(render_box(box, double=False))
                except Exception:
                    io.write_line(" …อ่านชั้นลึกไม่ได้ตอนนี้")
                io.read_line("Enter...")
            elif sub in ("a", "assess", "v2", "soft"):
                from game.domain.stat_arch import self_assess_lines

                io.write_line()
                io.write_line(
                    render_box(
                        self_assess_lines(player, force=True, reg=reg),
                        double=False,
                    )
                )
                io.read_line("Enter...")
            continue
        # WO-048: Temple unlock (letter grade + soft desc)
        if ch in ("w", "W", "temple", "วิหาร", "ปลด"):
            from game.domain.stat_grades import temple_unlock

            io.write_line()
            io.write_line(
                render_box(
                    [" วิหาร · ปลดเผยเกรด", "---", *temple_unlock(player, reg)],
                    double=False,
                )
            )
            io.read_line("Enter...")
            continue
        # WO-023: Godforge Chamber
        if ch in ("g", "G", "godforge", "chamber"):
            from game.services.godforge_chamber import run_godforge_chamber

            run_godforge_chamber(player, reg, io)
            continue
        # WO-011: Playtest / Test Run
        if ch in ("x", "X", "testrun", "test", "playtest"):
            from game.runtime.auto_run_log import run_playtest_hub

            run_playtest_hub(
                player, reg, io, area_name=area_name or ""
            )
            continue
        # WO-007 index
        if ch == "1" or ch in ("s", "S"):
            _show_overview_status(player, reg, io, area_name)
        elif ch == "2" or ch in ("bag",):
            _open_bag(player, reg, io)
            # gear quick path
            sub = io.read_line("  เกียร์? (g=เปิด / Enter=ข้าม): ").strip().lower()
            if sub in ("g", "gear", "3"):
                _manage_gear(player, reg, io)
        elif ch == "3" or ch in ("k", "K"):
            _skill_tree_menu(player, reg, io)
        elif ch == "4" or ch in ("n", "N", "p", "P", "c", "C"):
            if ch in ("p", "P"):
                _stat_allocate_menu(player, reg, io)
            elif ch in ("c", "C"):
                _class_change_menu(player, reg, io)
            else:
                _points_submenu(player, reg, io)
        elif ch == "5" or ch in ("y", "Y"):
            _party_menu(player, reg, io)
        elif ch == "6":
            _show_auto_history_log(player, io)
        # WO-Storage-1: 7 / U = คลังส่วนตัว (K still skill tree on 3)
        elif ch == "7" or ch in (
            "u",
            "U",
            "vault",
            "warehouse",
            "คลัง",
            "storage",
        ):
            from game.services.warehouse_hub import run_warehouse_hub

            run_warehouse_hub(player, reg, io)
        elif ch == "j" or ch == "J":
            _show_missions(player, reg, io)
            sub = io.read_line("  J=กระดานเต็ม · Enter=กลับ: ").strip()
            if sub in ("j", "J"):
                from game.services.mission_service import run_mission_board

                run_mission_board(player, reg, io)
        elif ch == "8":
            _settings_save_submenu(player, io)
        elif ch == "9":
            for line in money_summary_lines(player):
                io.write_line(line)
            io.write_line(" L=ห้องสมุด · shop=ตลาด · Enter=กลับ")
            sub = io.read_line("เลือก: ").strip().lower()
            if sub in ("l", "library"):
                _library(player, reg, io)
            elif sub in ("shop", "market", "ตลาด"):
                from game.services.shop_hub import run_shop_hub

                run_shop_hub(player, reg, io, area_name=area_name)
        # care + WO-008 Auto Policy (A only here — field A remains rank)
        elif ch in ("r", "R"):
            from game.domain.needs import personal_rest_care

            for line in personal_rest_care(player):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("e", "E"):
            from game.domain.needs import personal_eat_first_food

            for line in personal_eat_first_food(player, reg):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("h", "H"):
            from game.services.consumables import quick_use_care_potion

            for line in quick_use_care_potion(player, reg, kind="hp"):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("m", "M"):
            from game.services.consumables import quick_use_care_potion

            for line in quick_use_care_potion(player, reg, kind="mp"):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("y", "Y"):
            from game.services.consumables import quick_use_care_potion

            for line in quick_use_care_potion(player, reg, kind="py"):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("a", "A"):
            from game.services.auto_policy_hub import run_auto_policy_hub

            run_auto_policy_hub(player, reg, io)
        elif ch in ("l", "L"):
            _library(player, reg, io)
        else:
            io.write_line(
                "1–6 · 7/U คลังส่วนตัว · 8 ตั้งค่า · J ภารกิจ · 9 เงิน · "
                "R/E/H/M/Y ดูแล · A=Auto Policy · X=Test Run · 0 กลับ"
            )


def _show_overview_status(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    area_name: str,
) -> None:
    """WO-007 item 1: overview with Needs prominent + optional full dump."""
    ensure_stats(player)
    io.write_line()
    io.write_line(render_mode_chrome("สถานะโดยรวม", area_name))
    io.write_line(render_status_l1c(player, area_name))
    try:
        from game.services.auto_policy_hub import soft_agent_summary

        io.write_line()
        for line in soft_agent_summary(player, reg)[:8]:
            io.write_line(line if line.startswith(" ") or line.startswith("─") else f" {line}")
    except Exception:
        pass
    io.write_line()
    more = io.read_line("  f=สถานะเต็ม+สถิติ · Enter=กลับ: ").strip().lower()
    if more in ("f", "full", "1"):
        _show_full_status(player, reg, io, area_name)


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
    try:
        from game.domain.needs import format_tama_panel

        io.write_line()
        io.write_line(render_box(format_tama_panel(player), double=False))
    except Exception:
        pass
    io.read_line("Enter...")


def _show_auto_history_log(player: Dict[str, Any], io: IO) -> None:
    """WO-007/011: auto care notes + Auto Run events + last summary."""
    from game.runtime.auto_run_log import (
        format_auto_run_summary,
        format_recent_auto_events,
    )

    # God-readable event log first
    lines = list(format_recent_auto_events(player, limit=14))
    notes = list(player.get("auto_care_notes") or [])
    if notes:
        lines.append("---")
        lines.append(" care ring (ล่าสุด):")
        for n in notes[-8:]:
            lines.append(f"  · {n}" if not str(n).startswith(" ") else str(n))
    if player.get("_auto_run_last"):
        lines.append("---")
        lines.extend(format_auto_run_summary(player)[:10])
    # WO-016: multi-run snapshot
    try:
        from game.runtime.auto_run_log import format_playtest_history

        if player.get("_playtest_run_history"):
            lines.append("---")
            lines.extend(format_playtest_history(player, limit=4))
    except Exception:
        pass
    lines.append("---")
    try:
        from game.domain.stats import format_stats_lines as _fsl

        for line in list(_fsl(player))[:6]:
            lines.append(f" {line}" if not str(line).startswith(" ") else line)
    except Exception:
        stats = player.get("stats") or {}
        if stats:
            lines.append(
                f" kills {stats.get('kills', 0)} · auto_ticks {stats.get('auto_ticks', 0)}"
            )
    io.write_line()
    io.write_line(render_box(lines, double=False))
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
