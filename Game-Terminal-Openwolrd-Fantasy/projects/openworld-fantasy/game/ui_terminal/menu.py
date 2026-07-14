"""Menus and banners."""
from __future__ import annotations

from game.config import APP_NAME, APP_VERSION, PHASE
from game.ui_terminal.layout import render_box


def render_title() -> str:
    lines = [
        f" {APP_NAME}",
        f" Terminal Text RPG  ·  {APP_VERSION}  ·  {PHASE}",
        "---",
        " โลกเปิด | ความยากหลายระดับ | บอสหลายเฟส | เซ็ตเกียร์",
        " เลเวลไม่จำกัด · สถิติ · export เซฟ · ข้อความล้วน",
    ]
    return render_box(lines, double=True)


def render_about() -> str:
    lines = [
        " เกี่ยวกับ",
        "---",
        f" {APP_NAME} v{APP_VERSION} ({PHASE})",
        " เกมข้อความ open world / open skill ใน Terminal",
        " โลก: default · hardcore · nightmare",
        " เมนู 4 = นำเข้า export · ในเกม S = สถิติ · B = บอส",
        " โค้ด: projects/openworld-fantasy · data/ ขยายได้",
        " กฎพัฒนา: core/Z-MOS · สเปค: design/RD/",
    ]
    return render_box(lines, double=False)
