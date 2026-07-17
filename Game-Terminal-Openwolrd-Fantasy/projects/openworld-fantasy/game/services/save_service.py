"""Character save / load / export / import."""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from game.config import PROJECT_ROOT, SAVES_DIR

SAVE_VERSION = 4  # EL0: multi-slot loadout main_hand/body/… (legacy weapon/armor migrate)
EXPORT_DIR = PROJECT_ROOT / "exports"

# World-folder JSON that are not player characters (must not appear in picker)
_SYSTEM_SAVE_STEMS = frozenset(
    {
        "market",
        "rank_board",
        "world_meta",
        "world_signals",
        "client_pointer",
        "tax_fund",
        "mission_board",
    }
)


def _safe_name(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return s[:40] or "hero"


def _is_player_save_payload(data: Dict[str, Any], stem: str) -> bool:
    """True if this JSON looks like a character save (not world infrastructure)."""
    if stem in _SYSTEM_SAVE_STEMS:
        return False
    # explicit world/meta markers
    if data.get("kind") in ("world_meta", "market", "rank_board", "world_signals"):
        return False
    if "host_status" in data and "players" in data and not data.get("occupation"):
        return False
    # character saves have occupation and/or name + level
    if data.get("occupation") or data.get("occupation_id"):
        return True
    if data.get("name") and data.get("level") is not None and data.get("location"):
        return True
    if data.get("stats") or data.get("stats_alloc") or data.get("equip_ids"):
        return True
    return False


def list_saves(world_id: str = "default") -> List[Dict[str, Any]]:
    folder = SAVES_DIR / world_id
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        try:
            if path.stem in _SYSTEM_SAVE_STEMS:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not _is_player_save_payload(data, path.stem):
                continue
            out.append(
                {
                    "path": str(path),
                    "id": data.get("id") or path.stem,
                    "name": data.get("name", path.stem),
                    "level": data.get("level", 1),
                    "location": data.get("location", "?"),
                    "occupation": data.get("occupation", "?"),
                    "updated_at": data.get("updated_at"),
                }
            )
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    return out


def save_player(player: Dict[str, Any], world_id: Optional[str] = None) -> Path:
    world_id = world_id or str(player.get("world_id") or "default")
    folder = SAVES_DIR / world_id
    folder.mkdir(parents=True, exist_ok=True)
    if not player.get("id"):
        player["id"] = f"{_safe_name(str(player.get('name', 'hero')))}_{int(time.time())}"
    # persist instance layer (keep inst_id stable)
    try:
        from game.data_load.registry import get_registry
        from game.domain.item_instances import ensure_item_instances

        ensure_item_instances(player, get_registry())
    except Exception:
        pass
    player["save_version"] = SAVE_VERSION
    player["world_id"] = world_id
    # T1: stamp saved_at for load-delta needs
    try:
        from game.domain.needs import stamp_saved_at

        stamp_saved_at(player)
    except Exception:
        player["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        player["saved_at"] = player["updated_at"]
        player["saved_at_unix"] = time.time()
    # allow next load to re-apply offline delta
    player.pop("_load_delta_done", None)
    path = folder / f"{player['id']}.json"
    # don't persist session-only flag
    payload = {k: v for k, v in player.items() if not str(k).startswith("_")}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # W1: write combat/social echo snapshot (safe for others to fight)
    try:
        from game.domain.world_social import write_echo_snapshot

        write_echo_snapshot(payload, world_id)
    except Exception:
        pass
    # W3: soft touch player index occasionally (not every save — cheap check)
    try:
        import random as _r

        if _r.random() < 0.25:
            from game.domain.world_meta import refresh_world_index

            refresh_world_index(world_id)
    except Exception:
        pass
    return path


def load_player(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid save")
    # migrate hooks
    ver = int(data.get("save_version") or 1)
    if ver < SAVE_VERSION:
        data["save_version"] = SAVE_VERSION
    data.setdefault("xp", data.get("exp", 0))  # legacy prototype field
    data.setdefault("xp_percent", 0.0)
    data.setdefault("knowledge", {"monsters": {}, "reactions": []})
    data.setdefault("statuses", [])
    data.setdefault("location", "dark_forest")
    data.setdefault("inventory_ids", [])
    data.setdefault("inventory", data.get("inventory") or [])
    data.setdefault("card_bag", [])
    data.setdefault("equip_ids", {})
    # Repair orphan inventory names (e.g. iron_sword display without id)
    try:
        from game.data_load.registry import get_registry
        from game.domain.inventory_sys import sanitize_inventory

        sanitize_inventory(data, get_registry())
    except Exception:
        pass
    data.setdefault("sockets", {})
    data.setdefault("base_atk", int(data.get("bonus_atk", 5)))
    data.setdefault("base_max_hp", int(data.get("max_hp", 100)))
    data.setdefault("base_max_mana", int(data.get("max_mana", 50)))
    data.setdefault("base_skills", list(data.get("skills") or []))
    data.setdefault("base_pressure", int(data.get("pressure", 10)))
    data.setdefault("upgrade_levels", {})
    data.setdefault("quests", {})
    data.setdefault("quests_done", [])
    data.setdefault("bosses_defeated", [])
    # WO-Worthiness-1: soft wall + trial flags
    try:
        from game.domain.worthiness import ensure_worthiness

        ensure_worthiness(data)
    except Exception:
        data.setdefault(
            "worthiness",
            {"trials_cleared": [], "rewards_granted": [], "god_eye_owned": False},
        )
    data.setdefault("stats", {})
    data.setdefault("world_modifiers", {})
    data.setdefault("tutorial_done", False)
    data.setdefault("stat_points", 0)
    data.setdefault("stats_alloc", {"atk": 0, "defense": 0, "magic": 0, "speed": 0, "crit": 0})
    data.setdefault("occ_rank_index", 0)
    data.setdefault("unit_class_id", None)
    data.setdefault("library_entries_read", [])
    data.setdefault("flags", {})
    data.setdefault("social_memory", {})
    data.setdefault("personality", {})
    data.setdefault("personality_labels", [])
    data.setdefault("personality_points", 0)
    data.setdefault("personality_points_spent", 0)
    data.setdefault("personality_progress", {})
    data.setdefault("personality_grants_done", [])
    data.setdefault("personality_invest", {})
    data.setdefault("personality_tips_read", [])
    data.setdefault("skill_charges", {})
    data.setdefault("skill_tree_unlocked", [])
    data.setdefault("party", [])
    data.setdefault("party_bonds", {})
    data.setdefault("party_bonus_atk", 0)
    data.setdefault("party_bonus_max_hp", 0)
    data.setdefault("party_bonus_max_mana", 0)
    data.setdefault("bag_cap", 40)
    # WO-Storage-1: personal warehouse
    try:
        from game.domain.warehouse import ensure_warehouse

        ensure_warehouse(data)
    except Exception:
        data.setdefault(
            "warehouse",
            {
                "schema": 1,
                "cap": 200,
                "user": "",
                "user_locked": False,
                "pass_salt": "",
                "pass_hash": "",
                "items": {
                    "inventory_ids": [],
                    "inventory_qty": [],
                    "inventory_rarities": [],
                    "inventory": [],
                    "inventory_items": [],
                },
                "money": {"world": 0, "heaven": 0, "hell": 0},
                "prefs": {"auto_stash": False},
            },
        )
    data.setdefault("unit_mastery", 0)
    data.setdefault("unit_mastery_xp", 0)
    data.setdefault("inventory_rarities", [])
    data.setdefault("equip_rarities", {})
    data.setdefault("inventory_items", [])
    data.setdefault("equip_instances", {})
    # EL0 migrate loadout slots
    try:
        from game.domain.equipment import ensure_gear_fields

        ensure_gear_fields(data)
    except Exception:
        pass
    data.setdefault("dungeon_run", None)
    data.setdefault("dungeon_knowledge", {})
    data.setdefault("dungeons_cleared", [])
    data.setdefault("situation", None)
    data.setdefault("world_inbox", [])
    data.setdefault("help_rep", 0)
    data.setdefault("help_assists", 0)
    data.setdefault("help_requests", 0)
    load_delta_notes: List[str] = []
    try:
        from game.domain.needs import apply_load_delta, ensure_needs

        ensure_needs(data)
        # T1: soft needs change from real-time away
        load_delta_notes = apply_load_delta(data)
    except Exception:
        data.setdefault("needs", {"hunger": 18, "fatigue": 12, "morale": 72})
    if load_delta_notes:
        data["_pending_load_notes"] = list(load_delta_notes)
    try:
        from game.domain.situation import ensure_situation_fields, sync_situation_from_dungeon

        ensure_situation_fields(data)
        # Re-sync situation if mid-dungeon save
        if isinstance(data.get("dungeon_run"), dict) and data["dungeon_run"].get("dungeon_id"):
            sync_situation_from_dungeon(data, preserve_help=True)
    except Exception:
        pass
    # migrate rarities length to match inventory_ids
    ids = list(data.get("inventory_ids") or [])
    rares = list(data.get("inventory_rarities") or [])
    while len(rares) < len(ids):
        rares.append("common")
    data["inventory_rarities"] = rares[: len(ids)]
    # inventory_items = preferred source of truth; mirror legacy lists
    try:
        from game.data_load.registry import get_registry
        from game.domain.item_instances import sync_canonical_inventory

        sync_canonical_inventory(data, get_registry())
    except Exception:
        pass
    # claim market payouts / reports if any pending
    try:
        from game.domain.market import claim_pending_payouts

        claim_pending_payouts(data, str(data.get("world_id") or "default"))
    except Exception:
        pass
    data.setdefault("market_inbox", [])
    return data


def export_player(player: Dict[str, Any], dest: Optional[Path] = None) -> Path:
    """Write a portable JSON copy under exports/ (or custom path)."""
    world_id = str(player.get("world_id") or "default")
    save_player(player, world_id)  # ensure on-disk save exists
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    cid = str(player.get("id") or "hero")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = dest or (EXPORT_DIR / f"{cid}_{stamp}.json")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(player)
    payload["exported_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload["save_version"] = SAVE_VERSION
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def import_player(path: str, world_id: Optional[str] = None) -> Dict[str, Any]:
    """Load external JSON and store into saves/."""
    data = load_player(path)
    if world_id:
        data["world_id"] = world_id
    # new id to avoid clobber unless same
    if not data.get("id"):
        data["id"] = f"import_{int(time.time())}"
    save_player(data)
    return data


def list_exports() -> List[Path]:
    if not EXPORT_DIR.is_dir():
        return []
    return sorted(EXPORT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
