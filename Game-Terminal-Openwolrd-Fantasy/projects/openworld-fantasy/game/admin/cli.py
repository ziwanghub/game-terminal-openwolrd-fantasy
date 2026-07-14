"""P10 Admin tools — reset saves, list worlds, reload data, grant XP (dev)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from game.config import APP_NAME, APP_VERSION, DATA_DIR, SAVES_DIR
from game.data_load.registry import get_registry
from game.ports.io import IO, get_io
from game.services.save_service import list_saves


def run_admin(io: Optional[IO] = None) -> None:
    io = io or get_io()
    io.write_line(f"\n══ ADMIN · {APP_NAME} {APP_VERSION} ══")
    io.write_line("เครื่องมือพัฒนา — ใช้ด้วยความระมัดระวัง")

    while True:
        io.write_line("\n1. รายชื่อโลก (+ modifiers)")
        io.write_line("2. รายการเซฟทุกโลก")
        io.write_line("3. ลบเซฟทั้งโลก")
        io.write_line("4. ลบเซฟตัวละครเดียว")
        io.write_line("5. Reload data registry")
        io.write_line("6. ตรวจสุขภาพ data")
        io.write_line("7. รายการ exports/")
        io.write_line("8. แดชบอร์ดระบบเกม (ประเมิน text + แผนเฟส)")
        io.write_line("0. กลับ")
        ch = io.read_line("admin> ").strip()

        if ch == "1":
            reg = get_registry()
            for wid, w in reg.worlds.items():
                io.write_line(f" · {wid}: {w.get('name')} — {w.get('description', '')}")
                io.write_line(f"     start={w.get('starting_area')}")
                mods = w.get("modifiers") or {}
                if mods:
                    io.write_line(f"     mods={mods}")
        elif ch == "2":
            if not SAVES_DIR.is_dir():
                io.write_line("(ยังไม่มี saves/)")
                continue
            for world_dir in sorted(SAVES_DIR.iterdir()):
                if not world_dir.is_dir():
                    continue
                saves = list_saves(world_dir.name)
                io.write_line(f"[{world_dir.name}] {len(saves)} ตัว")
                for s in saves:
                    io.write_line(
                        f"  - {s['name']} Lv.{s['level']} {s['occupation']} @ {s['location']}"
                    )
        elif ch == "3":
            wid = io.read_line("world_id ที่จะลบเซฟทั้งก้อน: ").strip()
            folder = SAVES_DIR / wid
            if not folder.is_dir():
                io.write_line("ไม่พบโฟลเดอร์")
                continue
            conf = io.read_line(f"พิมพ์ DELETE เพื่อลบ {folder}: ").strip()
            if conf == "DELETE":
                shutil.rmtree(folder)
                io.write_line("ลบแล้ว")
            else:
                io.write_line("ยกเลิก")
        elif ch == "4":
            wid = io.read_line("world_id: ").strip() or "default"
            saves = list_saves(wid)
            if not saves:
                io.write_line("ไม่มีเซฟ")
                continue
            for i, s in enumerate(saves, 1):
                io.write_line(f"  {i}. {s['name']} ({s['id']})")
            try:
                idx = int(io.read_line("ลบหมายเลข: ").strip()) - 1
                path = Path(saves[idx]["path"])
                conf = io.read_line(f"พิมพ์ yes เพื่อลบ {path.name}: ").strip()
                if conf == "yes":
                    path.unlink(missing_ok=True)
                    io.write_line("ลบแล้ว")
                else:
                    io.write_line("ยกเลิก")
            except Exception as exc:
                io.write_line(f"ล้มเหลว: {exc}")
        elif ch == "5":
            try:
                reg = get_registry(reload=True)
                io.write_line(
                    f"reload OK — areas={len(reg.areas)} monsters={len(reg.monsters)} "
                    f"skills={len(reg.skills)} worlds={len(reg.worlds)}"
                )
            except Exception as exc:
                io.write_line(f"reload failed: {exc}")
        elif ch == "6":
            try:
                reg = get_registry(reload=True)
                io.write_line(f"DATA_DIR={DATA_DIR}")
                io.write_line(f"areas={list(reg.areas.keys())}")
                io.write_line(f"worlds={list(reg.worlds.keys())}")
                io.write_line(f"fusions={len((reg.fusions_cfg or {}).get('fusions') or [])}")
                io.write_line(f"sets={list(reg.gear_sets.keys())}")
                io.write_line(f"recipes={len(reg.recipes)}")
                io.write_line("health: OK")
            except Exception as exc:
                io.write_line(f"health FAIL: {exc}")
        elif ch == "7":
            from game.services.save_service import list_exports

            exps = list_exports()
            if not exps:
                io.write_line("(ว่าง)")
            for p in exps[:30]:
                io.write_line(f" · {p}")
        elif ch == "8":
            from game.admin.dashboard import run_dashboard

            try:
                run_dashboard(io, do_export=True)
            except Exception as exc:
                io.write_line(f"dashboard failed: {exc}")
            io.read_line("\nEnter...")
        elif ch == "0":
            break
        else:
            io.write_line("?")
