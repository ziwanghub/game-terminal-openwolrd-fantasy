"""L2 Spotlight — ASCII banners for rare events (P11 lite)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from game.config import ART_DIR
from game.ui_terminal.layout import render_box


def load_art(art_id: str, category: str = "ui") -> Optional[str]:
    path = ART_DIR / category / f"{art_id}.txt"
    if not path.is_file():
        # try other folders
        for cat in ("ui", "items", "monsters", "cards"):
            p = ART_DIR / cat / f"{art_id}.txt"
            if p.is_file():
                path = p
                break
        else:
            return None
    return path.read_text(encoding="utf-8").rstrip()


def spotlight(title: str, body_lines: list[str], art_id: Optional[str] = None, category: str = "ui") -> str:
    chunks: list[str] = []
    art = load_art(art_id, category) if art_id else None
    if art:
        chunks.append(art)
        chunks.append("")
    lines = [f" ✦ {title} ✦", "---", *[f" {x}" for x in body_lines]]
    chunks.append(render_box(lines, double=True))
    return "\n".join(chunks)


def level_up_banner(level: int) -> str:
    return spotlight(
        "LEVEL UP",
        [f"ขึ้นเป็นเลเวล {level}", "เลเวลไม่จำกัด — เลเวลถัดไปต้องใช้ XP มากขึ้น"],
        art_id="level_up",
        category="ui",
    )


def rare_loot_banner(item_name: str, detail: str = "") -> str:
    return spotlight(
        "ของหายาก",
        [item_name, detail or "โชคเข้าข้างในโลกเปิดนี้"],
        art_id="rare_relic",
        category="items",
    )
