"""Application entry — independent worlds, latest save, rankings, social."""
from __future__ import annotations

from game.admin.cli import run_admin
from game.config import APP_NAME, APP_VERSION, PHASE, SAVES_DIR
from game.data_load.registry import DataRegistry, get_registry
from game.domain.world_social import format_ranking_lines
from game.ports.io import get_io
from game.services.field_loop import interactive_create, run_field
from game.services.save_service import (
    import_player,
    list_exports,
    list_saves,
    load_player,
)
from game.services.world_service import (
    enter_world_latest,
    list_world_menu_rows,
    world_summary_lines,
)
from game.ui_terminal.layout import render_box
from game.ui_terminal.menu import render_about, render_title


def render_main_menu() -> str:
    lines = [
        " เมนูหลัก",
        "---",
        " 1. เข้าโลก (เล่นต่อเซฟล่าสุด / สร้างใหม่)",
        " 2. โหลดตัวละครในโลกที่เลือก",
        " 3. อันดับชื่อเสียงของโลก (ไม่โชว์เลเวล/พลัง)",
        " 4. เกี่ยวกับ",
        " 5. นำเข้าเซฟจาก exports/",
        " 8. แอดมิน",
        " 0. ออก",
    ]
    return render_box(lines, double=False)


def pick_world(reg: DataRegistry, io) -> str:
    rows = list_world_menu_rows(reg)
    if not rows:
        return "default"
    io.write_line("\n── เลือกโลก (อิสระ · เซฟ/ประวัติแยก) ──")
    for i, r in enumerate(rows, 1):
        save_txt = (
            f"เซฟล่าสุด: {r['latest_name']}" if r["has_save"] else "ยังไม่มีเซฟ"
        )
        io.write_line(f"  {i}. {r['name']}")
        io.write_line(
            f"     ความยาก: {r['difficulty_label']} · ตัวละคร {r['char_count']} · {save_txt}"
        )
        io.write_line(f"     {r['description']}")
    try:
        idx = int(io.read_line("เลือกโลก: ").strip()) - 1
        return str(rows[max(0, min(len(rows) - 1, idx))]["id"])
    except Exception:
        return str(rows[0]["id"])


def run() -> None:
    io = get_io()
    io.write_line()
    io.write_line(render_title())

    try:
        reg = get_registry()
        io.write_line(
            f"โหลด data: {len(reg.areas)} พื้นที่ · {len(reg.worlds)} โลกอิสระ · "
            f"{len(reg.occupations)} อาชีพ"
        )
    except Exception as exc:
        io.write_line(f"⚠️ โหลด data ไม่สำเร็จ: {exc}")
        reg = None

    while True:
        io.write_line()
        io.write_line(render_main_menu())
        choice = io.read_line("\nเลือกหมายเลข: ").strip()

        if choice == "1":
            if reg is None:
                continue
            try:
                world_id = pick_world(reg, io)
                for line in world_summary_lines(reg, world_id):
                    io.write_line(line)
                latest = enter_world_latest(world_id)
                if latest:
                    io.write_line(
                        f"\nพบเซฟล่าสุด: {latest.get('name')} "
                        f"@ {latest.get('location')}"
                    )
                    io.write_line("1. เล่นต่อจากเซฟล่าสุด  2. สร้างตัวใหม่ในโลกนี้  0. กลับ")
                    sub = io.read_line("เลือก: ").strip()
                    if sub == "1":
                        # ensure world mods present
                        if not latest.get("world_modifiers"):
                            latest["world_modifiers"] = (
                                (reg.worlds.get(world_id) or {}).get("modifiers") or {}
                            )
                        latest["world_id"] = world_id
                        run_field(latest, reg, io)
                        continue
                    if sub != "2":
                        continue
                else:
                    io.write_line("\nยังไม่มีประวัติในโลกนี้ — สร้างตัวละครใหม่")
                player = interactive_create(reg, io)
                player["world_id"] = world_id
                player["world_modifiers"] = (
                    (reg.worlds.get(world_id) or {}).get("modifiers") or {}
                )
                start = (reg.worlds.get(world_id) or {}).get("starting_area")
                if start and start in reg.areas:
                    player["location"] = start
                player.setdefault("social_memory", {})
                run_field(player, reg, io)
            except KeyboardInterrupt:
                io.write_line("\n(Ctrl+C — กลับเมนู)")
            except Exception as exc:
                io.write_line(f"\nข้อผิดพลาด: {exc}")

        elif choice == "2":
            if reg is None:
                reg = get_registry()
            world_id = pick_world(reg, io)
            saves = list_saves(world_id)
            if not saves:
                io.write_line("โลกนี้ยังไม่มีเซฟ")
                continue
            io.write_line(f"\nตัวละครในโลก {world_id}:")
            for i, s in enumerate(saves, 1):
                io.write_line(
                    f"  {i}. {s['name']} · {s.get('occupation','?')} @ {s['location']}"
                )
                # deliberately no level in list for world lore feel — actually save list can show? user said ranking no level. load list can omit level
            try:
                idx = int(io.read_line("เลือก: ").strip()) - 1
                meta = saves[max(0, min(len(saves) - 1, idx))]
                player = load_player(meta["path"])
                player["world_id"] = world_id
                if not player.get("world_modifiers"):
                    player["world_modifiers"] = (
                        (reg.worlds.get(world_id) or {}).get("modifiers") or {}
                    )
                run_field(player, reg, io)
            except Exception as exc:
                io.write_line(f"โหลดไม่สำเร็จ: {exc}")

        elif choice == "3":
            if reg is None:
                continue
            world_id = pick_world(reg, io)
            io.write_line()
            for line in format_ranking_lines(world_id, reg):
                io.write_line(line)
            io.read_line("\nEnter...")

        elif choice == "4":
            io.write_line()
            io.write_line(render_about())
            io.write_line(
                "\nโลกอิสระ: ชื่อ · ความยาก · เซฟ/ประวัติ/อันดับแยก · "
                "เจอผู้เล่นอื่นจากเซฟในโลก · เพื่อนหรือศัตรูขึ้นกับท่าที (สูตรซ่อน)"
            )
            io.read_line("\nEnter...")

        elif choice == "5":
            exps = list_exports()
            if not exps:
                io.write_line("ยังไม่มี exports/")
                continue
            for i, p in enumerate(exps[:20], 1):
                io.write_line(f"  {i}. {p.name}")
            try:
                idx = int(io.read_line("นำเข้า: ").strip()) - 1
                path = exps[max(0, min(len(exps) - 1, idx))]
                player = import_player(str(path))
                io.write_line(f"นำเข้า {player.get('name')} แล้ว")
            except Exception as exc:
                io.write_line(f"ล้มเหลว: {exc}")

        elif choice == "8":
            try:
                run_admin(io)
            except KeyboardInterrupt:
                io.write_line("\n(ออกแอดมิน)")

        elif choice in ("0", "q", "Q"):
            io.write_line(f"\nลาก่อน — {APP_NAME} ({PHASE} / {APP_VERSION})")
            break
        else:
            io.write_line("เลือกไม่ถูกต้อง")
