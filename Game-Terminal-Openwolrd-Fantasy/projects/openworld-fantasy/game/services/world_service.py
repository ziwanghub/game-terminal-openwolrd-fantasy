"""World entry: independent worlds, latest save, rankings."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from game.config import SAVES_DIR
from game.data_load.registry import DataRegistry
from game.services.save_service import list_saves, load_player, save_player
from game.domain.world_social import format_ranking_lines


def world_summary_lines(reg: DataRegistry, world_id: str) -> List[str]:
    w = reg.worlds.get(world_id) or {}
    saves = list_saves(world_id)
    latest = latest_save_meta(world_id)
    lines = [
        f"โลก: {w.get('name', world_id)}",
        f"ความยาก: {w.get('difficulty_label', w.get('difficulty', '?'))}",
        f"จุดเริ่ม: {w.get('starting_area', '?')}",
        f"อิสระ: {'ใช่' if w.get('independent', True) else 'ไม่'}",
        f"ตัวละครในโลก: {len(saves)}",
    ]
    if latest:
        lines.append(
            f"เซฟล่าสุด: {latest.get('name')} @ {latest.get('location')} "
            f"({latest.get('updated_at') or '—'})"
        )
    else:
        lines.append("เซฟล่าสุด: (ยังไม่มี — ต้องสร้างตัวใหม่)")
    return lines


def latest_save_meta(world_id: str) -> Optional[Dict[str, Any]]:
    saves = list_saves(world_id)
    if not saves:
        return None
    # list_saves is sorted by name; pick max updated_at
    def key(s: Dict[str, Any]) -> str:
        return str(s.get("updated_at") or "")

    return max(saves, key=key)


def enter_world_latest(world_id: str) -> Optional[Dict[str, Any]]:
    meta = latest_save_meta(world_id)
    if not meta:
        return None
    return load_player(meta["path"])


def list_world_menu_rows(reg: DataRegistry) -> List[Dict[str, Any]]:
    rows = []
    for wid, w in reg.worlds.items():
        latest = latest_save_meta(wid)
        rows.append(
            {
                "id": wid,
                "name": w.get("name", wid),
                "difficulty_label": w.get("difficulty_label", "?"),
                "difficulty": int(w.get("difficulty", 1)),
                "description": w.get("description", ""),
                "has_save": latest is not None,
                "latest_name": (latest or {}).get("name"),
                "latest_location": (latest or {}).get("location"),
                "char_count": len(list_saves(wid)),
            }
        )
    rows.sort(key=lambda r: r["difficulty"])
    return rows


def _difficulty_mark(label: str, difficulty: int) -> str:
    """Soft badge for terminal scanability."""
    lab = str(label or "")
    d = int(difficulty or 1)
    if d <= 1 or "ปกติ" in lab:
        return "○ ปกติ"
    if d == 2 or "ท้าทาย" in lab:
        return "◇ ท้าทาย"
    if d >= 3 or "ฝันร้าย" in lab or "นรก" in lab:
        return "◆ ฝันร้าย"
    return f"· {lab}"


def format_world_picker_lines(reg: DataRegistry) -> List[str]:
    """
    Readable world picker lines for a box UI.
    Each world is a short block: number · name · difficulty · save status · blurb.
    """
    rows = list_world_menu_rows(reg)
    lines: List[str] = [
        " เลือกโลก",
        "---",
        " เซฟ · อันดับ · ประวัติ แยกกันแต่ละโลก (ไม่ปนกัน)",
        "---",
    ]
    if not rows:
        lines.append(" (ยังไม่มีโลกใน data)")
        return lines

    for i, r in enumerate(rows, 1):
        mark = _difficulty_mark(str(r.get("difficulty_label")), int(r.get("difficulty") or 1))
        name = str(r.get("name") or r.get("id") or "?")
        nchar = int(r.get("char_count") or 0)
        if r.get("has_save") and r.get("latest_name"):
            loc = r.get("latest_location") or "?"
            save_line = f" เซฟล่าสุด  {r['latest_name']} @ {loc}"
            if nchar > 1:
                save_line += f"  (+{nchar - 1} ตัวอื่น)"
        else:
            save_line = " เซฟ       ยังไม่มี — สร้างตัวใหม่ได้"

        lines.append(f" {i}. {name}")
        lines.append(f"    ความยาก  {mark}")
        lines.append(f"   {save_line}")
        desc = str(r.get("description") or "").strip()
        if desc:
            lines.append(f"    หมายเหตุ  {desc}")
        if i < len(rows):
            lines.append("")  # spacer between worlds

    lines.append("---")
    lines.append(f" พิมพ์ 1–{len(rows)} แล้ว Enter")
    return lines


def format_save_picker_lines(
    world_id: str,
    world_name: str = "",
) -> List[str]:
    """Character list in a world — scannable."""
    saves = list_saves(world_id)
    title = world_name or world_id
    lines: List[str] = [
        f" ตัวละครในโลก",
        "---",
        f" {title}",
        "---",
    ]
    if not saves:
        lines.append(" (ยังไม่มีเซฟในโลกนี้)")
        return lines
    for i, s in enumerate(saves, 1):
        occ = s.get("occupation") or "?"
        loc = s.get("location") or "?"
        when = s.get("updated_at") or ""
        when_bit = f" · {when}" if when else ""
        lines.append(f" {i}. {s.get('name') or '?'}")
        lines.append(f"    {occ}  @ {loc}{when_bit}")
        if i < len(saves):
            lines.append("")
    lines.append("---")
    lines.append(f" พิมพ์ 1–{len(saves)} แล้ว Enter")
    return lines
