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
    format_save_picker_lines,
    format_world_picker_lines,
    list_world_menu_rows,
    pick_world_interactive,
    world_summary_lines,
)
from game.ui_terminal.layout import render_box
from game.ui_terminal.menu import render_about, render_title


def render_main_menu() -> str:
    lines = [
        " เมนูหลัก",
        "---",
        " 1  เข้าโลก          เล่นต่อ / สร้างตัวใหม่",
        " 2  โหลดตัวละคร      เลือกจากรายชื่อในโลก",
        " 3  อันดับชื่อเสียง   ของโลกที่เลือก",
        " 4  เกี่ยวกับ",
        " 5  นำเข้าเซฟ         จาก exports/",
        " 6  โลก-host (W3)    สถานะ / ชี้โลก",
        " 8  แอดมิน",
        "---",
        " 0  ออก",
    ]
    return render_box(lines, double=False)


def pick_world(reg: DataRegistry, io) -> str:
    """
    World picker — simple catalog list (default).
    WO-002 theme/custom path only if WORLD_THEME_UX_ENABLED.
    """
    from game.config import WORLD_THEME_UX_ENABLED

    if WORLD_THEME_UX_ENABLED:
        wid = pick_world_interactive(reg, io)
        if wid:
            return wid
        rows = list_world_menu_rows(reg)
        return str(rows[0]["id"]) if rows else "default"

    # Simple original path
    rows = list_world_menu_rows(reg)
    if not rows:
        return "default"
    io.write_line()
    io.write_line(render_box(format_world_picker_lines(reg), double=False))
    n = len(rows)
    raw = io.read_line(f"\n  เลือกโลก (1–{n}): ").strip()
    if raw in ("", "0", "q", "Q"):
        return str(rows[0]["id"])
    try:
        idx = int(raw) - 1
        return str(rows[max(0, min(n - 1, idx))]["id"])
    except Exception:
        io.write_line(" (ใช้เลขไม่ถูกต้อง — เลือกโลกแรก)")
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
                wname = (reg.worlds.get(world_id) or {}).get("name") or world_id
                try:
                    from game.domain.world_meta import set_client_pointer, host_status

                    set_client_pointer(world_id, prefer_host=True)
                    st = host_status(world_id)
                    host_line = str(st.get("label") or "")
                except Exception:
                    host_line = ""
                io.write_line()
                summary = list(world_summary_lines(reg, world_id))
                if host_line:
                    summary.append(f" host: {host_line}")
                io.write_line(
                    render_box(
                        [
                            " สรุปโลกที่เลือก",
                            "---",
                            *summary,
                        ],
                        double=False,
                    )
                )
                latest = enter_world_latest(world_id)
                if latest:
                    io.write_line()
                    io.write_line(
                        render_box(
                            [
                                " พบเซฟล่าสุด",
                                "---",
                                f" {latest.get('name')}  @  {latest.get('location')}",
                                "---",
                                " 1  เล่นต่อจากเซฟนี้",
                                " 2  สร้างตัวใหม่ในโลกนี้",
                                " 0  กลับเมนู",
                            ],
                            double=False,
                        )
                    )
                    sub = io.read_line("\n  เลือก (1/2/0): ").strip()
                    if sub == "1":
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
                    io.write_line()
                    io.write_line(
                        render_box(
                            [
                                f" {wname}",
                                "---",
                                " ยังไม่มีเซฟ — จะสร้างตัวละครใหม่",
                            ],
                            double=False,
                        )
                    )
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
                io.write_line()
                io.write_line(
                    render_box(
                        [" โลกนี้ยังไม่มีเซฟ", "---", " ใช้เมนู 1 เพื่อสร้างตัวใหม่"],
                        double=False,
                    )
                )
                continue
            wname = (reg.worlds.get(world_id) or {}).get("name") or world_id
            io.write_line()
            io.write_line(
                render_box(format_save_picker_lines(world_id, wname), double=False)
            )
            try:
                raw = io.read_line(f"\n  เลือกตัวละคร (1–{len(saves)}): ").strip()
                idx = int(raw) - 1
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

        elif choice == "6":
            # W3: host status + client pointer
            if reg is None:
                reg = get_registry()
            world_id = pick_world(reg, io)
            from game.domain.world_meta import (
                format_host_status_lines,
                refresh_world_index,
                set_client_pointer,
            )

            try:
                refresh_world_index(world_id)
            except Exception:
                pass
            io.write_line()
            io.write_line(render_box(format_host_status_lines(world_id), double=False))
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ชี้ client ไปโลกนี้?",
                        "---",
                        "  1  ตั้ง pointer (prefer host)",
                        "  0  กลับ",
                        "---",
                        " รัน host: python -m game.host " + world_id,
                    ],
                    double=False,
                )
            )
            sub = io.read_line("\n  เลือก (1/0): ").strip()
            if sub == "1":
                set_client_pointer(world_id, prefer_host=True)
                io.write_line(f" ตั้ง client_pointer → โลก {world_id}")
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
