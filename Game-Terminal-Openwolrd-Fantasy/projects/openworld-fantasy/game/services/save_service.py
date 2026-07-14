"""Character save / load / export / import."""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from game.config import PROJECT_ROOT, SAVES_DIR

SAVE_VERSION = 3  # + inventory_items / equip_instances persistence
EXPORT_DIR = PROJECT_ROOT / "exports"


def _safe_name(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return s[:40] or "hero"


def list_saves(world_id: str = "default") -> List[Dict[str, Any]]:
    folder = SAVES_DIR / world_id
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
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
        except (OSError, json.JSONDecodeError):
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
    player["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    path = folder / f"{player['id']}.json"
    path.write_text(json.dumps(player, ensure_ascii=False, indent=2), encoding="utf-8")
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
    data.setdefault("equip_ids", {"weapon": None, "armor": None})
    # Repair orphan inventory names (e.g. iron_sword display without id)
    try:
        from game.data_load.registry import get_registry
        from game.domain.inventory_sys import sanitize_inventory

        sanitize_inventory(data, get_registry())
    except Exception:
        pass
    data.setdefault("sockets", {"weapon": [], "armor": []})
    data.setdefault("base_atk", int(data.get("bonus_atk", 5)))
    data.setdefault("base_max_hp", int(data.get("max_hp", 100)))
    data.setdefault("base_max_mana", int(data.get("max_mana", 50)))
    data.setdefault("base_skills", list(data.get("skills") or []))
    data.setdefault("base_pressure", int(data.get("pressure", 10)))
    data.setdefault("upgrade_levels", {"weapon": 0, "armor": 0})
    data.setdefault("quests", {})
    data.setdefault("quests_done", [])
    data.setdefault("bosses_defeated", [])
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
    data.setdefault("unit_mastery", 0)
    data.setdefault("unit_mastery_xp", 0)
    eq = dict(data.get("equip_ids") or {})
    eq.setdefault("weapon", None)
    eq.setdefault("armor", None)
    eq.setdefault("accessory", None)
    data["equip_ids"] = eq
    data.setdefault("inventory_rarities", [])
    data.setdefault("equip_rarities", {"weapon": None, "armor": None, "accessory": None})
    data.setdefault("inventory_items", [])
    data.setdefault("equip_instances", {"weapon": None, "armor": None, "accessory": None})
    data.setdefault("dungeon_run", None)
    data.setdefault("dungeon_knowledge", {})
    data.setdefault("dungeons_cleared", [])
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
