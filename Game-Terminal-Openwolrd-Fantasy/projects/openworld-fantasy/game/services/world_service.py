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
                "char_count": len(list_saves(wid)),
            }
        )
    rows.sort(key=lambda r: r["difficulty"])
    return rows
