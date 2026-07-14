"""
W3: world_meta.json + player index + host heartbeat.

Shared world state index — concurrent writes go through file locks.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.config import APP_VERSION, SAVES_DIR
from game.domain.file_lock import world_file_lock

WORLD_META_SCHEMA = 1
HOST_STALE_SEC = 45.0


def world_dir(world_id: str) -> Path:
    d = Path(SAVES_DIR) / str(world_id or "default")
    d.mkdir(parents=True, exist_ok=True)
    return d


def meta_path(world_id: str) -> Path:
    return world_dir(world_id) / "world_meta.json"


def empty_meta(world_id: str) -> Dict[str, Any]:
    return {
        "schema": WORLD_META_SCHEMA,
        "world_id": str(world_id or "default"),
        "app_version": APP_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "host": None,
        "player_index": [],
        "flags": {},
    }


def load_world_meta(world_id: str) -> Dict[str, Any]:
    path = meta_path(world_id)
    if not path.is_file():
        return empty_meta(world_id)
    try:
        with world_file_lock(world_id, "meta", timeout=4.0):
            data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return empty_meta(world_id)
        data.setdefault("schema", WORLD_META_SCHEMA)
        data.setdefault("player_index", [])
        data.setdefault("host", None)
        return data
    except Exception:
        return empty_meta(world_id)


def save_world_meta(world_id: str, data: Mapping[str, Any]) -> Path:
    path = meta_path(world_id)
    payload = dict(data)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload["world_id"] = str(world_id or "default")
    payload["schema"] = WORLD_META_SCHEMA
    with world_file_lock(world_id, "meta", timeout=6.0) as ok:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _ = ok
    return path


def rebuild_player_index(world_id: str) -> List[Dict[str, Any]]:
    """Scan saves + echoes → soft public index (no HP/ATK)."""
    from game.services.save_service import list_saves, load_player

    index: List[Dict[str, Any]] = []
    for meta in list_saves(world_id):
        try:
            p = load_player(meta["path"])
        except Exception:
            continue
        index.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "location": p.get("location"),
                "occupation": p.get("occupation") or p.get("occ_path"),
                "level_soft": "…" ,  # never show number on host board
                "has_echo": (
                    world_dir(world_id) / "echoes" / f"{p.get('id')}.json"
                ).is_file(),
                "updated_at": p.get("updated_at") or p.get("saved_at"),
            }
        )
    # also orphans in echoes only
    echo_dir = world_dir(world_id) / "echoes"
    if echo_dir.is_dir():
        known = {str(x.get("id")) for x in index}
        for path in sorted(echo_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            eid = str(data.get("id") or "")
            if not eid or eid in known:
                continue
            index.append(
                {
                    "id": eid,
                    "name": data.get("name"),
                    "location": data.get("location"),
                    "occupation": data.get("occ_path") or data.get("occupation"),
                    "level_soft": "…",
                    "has_echo": True,
                    "updated_at": data.get("updated_at"),
                    "echo_only": True,
                }
            )
    return index


def refresh_world_index(world_id: str) -> Dict[str, Any]:
    """Rebuild index + stamp meta (host or client maintenance)."""
    meta = load_world_meta(world_id)
    meta["player_index"] = rebuild_player_index(world_id)
    meta["app_version"] = APP_VERSION
    save_world_meta(world_id, meta)
    return meta


def host_heartbeat(
    world_id: str,
    *,
    host_id: Optional[str] = None,
    pid: Optional[int] = None,
) -> Dict[str, Any]:
    """Write host presence into world_meta (W3)."""
    meta = load_world_meta(world_id)
    hid = host_id or f"local-{os.getpid()}"
    meta["host"] = {
        "id": hid,
        "pid": int(pid if pid is not None else os.getpid()),
        "last_beat_unix": time.time(),
        "last_beat": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "app_version": APP_VERSION,
        "mode": "file",  # W3 lite file host; http later
    }
    # also refresh index on beat occasionally
    if int(time.time()) % 3 == 0:
        meta["player_index"] = rebuild_player_index(world_id)
    save_world_meta(world_id, meta)
    return meta


def host_status(world_id: str) -> Dict[str, Any]:
    """Soft status for clients — is host alive?"""
    meta = load_world_meta(world_id)
    host = meta.get("host")
    if not isinstance(host, dict) or not host:
        return {
            "alive": False,
            "label": "ไม่มี host (โหมดไฟล์ตรง)",
            "soft": "เซฟ/ตลาดเขียนตรงดิสก์ · lock ยังกันชนกัน",
            "meta": meta,
        }
    last = float(host.get("last_beat_unix") or 0)
    age = time.time() - last if last else 9999
    alive = age <= HOST_STALE_SEC
    return {
        "alive": alive,
        "age_sec": round(age, 1),
        "label": "host ทำงาน" if alive else "host เงียบ (stale)",
        "soft": (
            f"host {host.get('id')} · beat {host.get('last_beat')}"
            if alive
            else "host ไม่ตอบ — ลูกค้าใช้โหมดไฟล์ตรงได้"
        ),
        "host": host,
        "meta": meta,
        "players": len(meta.get("player_index") or []),
    }


def format_host_status_lines(world_id: str) -> List[str]:
    st = host_status(world_id)
    lines = [
        f" โลก-host · {world_id}",
        "---",
        f" สถานะ: {st.get('label')}",
        f" {st.get('soft')}",
    ]
    if st.get("players") is not None:
        lines.append(f" ดัชนีผู้เล่น: {st.get('players')} รายการ (soft)")
    meta = st.get("meta") or {}
    idx = list(meta.get("player_index") or [])[:8]
    if idx:
        lines.append("---")
        lines.append(" ร่องรอยในโลก (ไม่โชว์พลัง):")
        for row in idx:
            mark = "◆" if row.get("has_echo") else "·"
            loc = row.get("location") or "?"
            if str(loc).startswith("dungeon:"):
                loc = "ในเงาถ้ำ…"
            lines.append(f"  {mark} {row.get('name')} · {row.get('occupation') or '?'} · {loc}")
    lines.append("---")
    lines.append(" W3 lite: file lock + heartbeat · ยังไม่ใช่ MMO online")
    return lines


def client_pointer_path() -> Path:
    return Path(SAVES_DIR) / "client_pointer.json"


def set_client_pointer(world_id: str, *, prefer_host: bool = True) -> Path:
    """Client remembers which world + whether to check host first."""
    path = client_pointer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "world_id": str(world_id or "default"),
        "prefer_host": bool(prefer_host),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "file",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_client_pointer() -> Dict[str, Any]:
    path = client_pointer_path()
    if not path.is_file():
        return {"world_id": "default", "prefer_host": True, "mode": "file"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"world_id": "default"}
    except Exception:
        return {"world_id": "default", "prefer_host": True, "mode": "file"}
