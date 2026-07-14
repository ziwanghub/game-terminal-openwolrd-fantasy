"""Skill charge / lease uses — taught skills may expire after N uses."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from game.data_load.registry import DataRegistry


def ensure_skill_charges(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    ch = dict(player.get("skill_charges") or {})
    player["skill_charges"] = ch
    player.setdefault("skills", [])
    return ch


def charge_info(player: Mapping[str, Any], skill_id: str) -> Optional[Dict[str, Any]]:
    """Return charge record or None if unlimited."""
    ch = player.get("skill_charges") or {}
    rec = ch.get(skill_id)
    if not isinstance(rec, dict):
        return None
    if rec.get("max") is None and rec.get("remaining") is None:
        return None
    return rec


def is_skill_usable(player: Mapping[str, Any], skill_id: str, reg: Optional[DataRegistry] = None) -> bool:
    """Owned + charge remaining (or unlimited)."""
    owned = set(player.get("skills") or [])
    if skill_id not in owned:
        return False
    info = charge_info(player, skill_id)
    if info is None:
        return True
    return int(info.get("remaining", 0)) > 0


def set_lease(
    player: MutableMapping[str, Any],
    skill_id: str,
    uses: int,
    *,
    source: str = "master",
) -> None:
    ensure_skill_charges(player)
    uses = max(0, int(uses))
    player["skill_charges"][skill_id] = {
        "remaining": uses,
        "max": uses,
        "source": source,
    }
    skills = list(player.get("skills") or [])
    if skill_id not in skills:
        skills.append(skill_id)
        player["skills"] = skills
    base = list(player.get("base_skills") or [])
    if skill_id not in base:
        base.append(skill_id)
        player["base_skills"] = base


def renew_lease(
    player: MutableMapping[str, Any],
    skill_id: str,
    uses: Optional[int] = None,
) -> str:
    ensure_skill_charges(player)
    info = charge_info(player, skill_id)
    if info is None:
        if skill_id not in (player.get("skills") or []):
            return "ยังไม่มีสกิลนี้"
        uses_n = int(uses or 10)
        set_lease(player, skill_id, uses_n)
        return f"เติมครั้งใช้สกิล · ใช้ได้ {uses_n} ครั้ง"
    max_u = int(uses if uses is not None else info.get("max") or 10)
    player["skill_charges"][skill_id] = {
        "remaining": max_u,
        "max": max_u,
        "source": info.get("source") or "master",
    }
    return f"เติมครั้งใช้แล้ว · ใช้ได้ {max_u} ครั้ง"


def spend_charges(
    player: MutableMapping[str, Any],
    skill_ids: Sequence[str],
) -> List[str]:
    """Decrement remaining for each leased skill used. Returns flavor notes."""
    ensure_skill_charges(player)
    notes: List[str] = []
    ch = dict(player["skill_charges"])
    for sid in skill_ids:
        info = ch.get(sid)
        if not isinstance(info, dict):
            continue
        if info.get("max") is None and info.get("remaining") is None:
            continue
        rem = int(info.get("remaining", 0))
        if rem <= 0:
            continue
        rem -= 1
        info = {**info, "remaining": rem}
        ch[sid] = info
        if rem <= 0:
            notes.append("…ท่าหนึ่งหมดแรง (ต้องเติม/เรียนใหม่กับอาจารย์)")
        elif rem <= 2:
            notes.append(f"…ท่าหนึ่งใกล้หมดแรง (เหลือ {rem})")
    player["skill_charges"] = ch
    return notes


def filter_usable_skill_ids(
    player: Mapping[str, Any],
    skill_ids: Sequence[str],
) -> List[str]:
    return [s for s in skill_ids if is_skill_usable(player, s)]


def format_charge_hint(
    player: Mapping[str, Any],
    skill_id: str,
    reg: Optional[DataRegistry] = None,
) -> str:
    info = charge_info(player, skill_id)
    if not info:
        return ""
    rem = int(info.get("remaining", 0))
    mx = int(info.get("max", 0) or 0)
    return f" [{rem}/{mx}]"
