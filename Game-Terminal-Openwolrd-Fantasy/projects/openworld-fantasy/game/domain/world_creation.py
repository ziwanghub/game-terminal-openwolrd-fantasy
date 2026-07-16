"""
WO-002: World selection flavor + custom world creation (theme).
Keeps world_id folder structure under saves/{world_id}/.
Soft open-skill emergence bias — no formula dump to player.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.config import DATA_DIR, SAVES_DIR, WORLD_THEME_UX_ENABLED
from game.data_load.registry import DataRegistry

_THEME_CACHE: Optional[Dict[str, Any]] = None
PROFILE_NAME = "world_profile.json"


def world_theme_ux_enabled() -> bool:
    """WO-002 feature gate — False = simple world list (default after defer)."""
    return bool(WORLD_THEME_UX_ENABLED)


def _load_themes_raw() -> Dict[str, Any]:
    global _THEME_CACHE
    if _THEME_CACHE is not None:
        return _THEME_CACHE
    path = Path(DATA_DIR) / "worlds" / "themes.yaml"
    try:
        from game.data_load.loader import load_file

        data = load_file(path)
        _THEME_CACHE = data if isinstance(data, dict) else {}
    except Exception:
        _THEME_CACHE = {}
    return _THEME_CACHE


def clear_theme_cache() -> None:
    global _THEME_CACHE
    _THEME_CACHE = None


def list_themes() -> List[Dict[str, Any]]:
    raw = _load_themes_raw()
    themes = list(raw.get("themes") or [])
    out: List[Dict[str, Any]] = []
    for t in themes:
        if isinstance(t, dict) and t.get("id"):
            out.append(dict(t))
    return out


def theme_by_id(theme_id: str) -> Optional[Dict[str, Any]]:
    tid = str(theme_id or "")
    for t in list_themes():
        if str(t.get("id")) == tid:
            return dict(t)
    return None


def theme_for_area(area_id: str) -> Optional[Dict[str, Any]]:
    aid = str(area_id or "")
    for t in list_themes():
        if str(t.get("starting_area") or "") == aid:
            return dict(t)
    return None


def theme_for_catalog_world(world_id: str, reg: Optional[DataRegistry] = None) -> Optional[Dict[str, Any]]:
    raw = _load_themes_raw()
    cmap = dict(raw.get("catalog_theme") or {})
    tid = cmap.get(str(world_id))
    if tid:
        t = theme_by_id(str(tid))
        if t:
            return t
    if reg is not None:
        w = reg.worlds.get(str(world_id)) or {}
        start = str(w.get("starting_area") or "")
        return theme_for_area(start)
    return None


def soft_flavor_lines(theme: Optional[Mapping[str, Any]], *, max_lines: int = 2) -> List[str]:
    if not theme:
        return []
    lines = [str(x).strip() for x in (theme.get("soft_flavor") or []) if str(x).strip()]
    return lines[: max(0, int(max_lines))]


def area_display_name(reg: DataRegistry, area_id: str) -> str:
    a = reg.areas.get(str(area_id)) or {}
    return str(a.get("name") or area_id or "?")


def slug_world_id(name: str, *, suffix: str = "") -> str:
    """Filesystem-safe world_id — ASCII-ish + underscore; keep structure saves/{id}/."""
    s = str(name or "").strip()
    # keep Thai letters by allowing word chars via unicode; replace spaces
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\-]+", "", s, flags=re.UNICODE)
    s = s.strip("_-")[:28] or "world"
    if suffix:
        s = f"{s}_{suffix}"[:40]
    # avoid reserved / catalog collision handled by caller
    if s in ("social", "themes", "world_social"):
        s = f"w_{s}"
    return s


def profile_path(world_id: str) -> Path:
    return Path(SAVES_DIR) / str(world_id) / PROFILE_NAME


def load_world_profile(world_id: str) -> Optional[Dict[str, Any]]:
    path = profile_path(world_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_world_profile(profile: Mapping[str, Any]) -> Path:
    wid = str(profile.get("id") or "default")
    folder = Path(SAVES_DIR) / wid
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / PROFILE_NAME
    payload = dict(profile)
    payload["id"] = wid
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def ensure_catalog_profile(
    reg: DataRegistry,
    world_id: str,
) -> Dict[str, Any]:
    """Soft profile for built-in worlds (not required on disk)."""
    existing = load_world_profile(world_id)
    if existing:
        return existing
    w = reg.worlds.get(world_id) or {}
    theme = theme_for_catalog_world(world_id, reg)
    return {
        "id": world_id,
        "name": w.get("name") or world_id,
        "source": "catalog",
        "theme_id": (theme or {}).get("id"),
        "starting_area": w.get("starting_area") or (theme or {}).get("starting_area"),
        "difficulty": int(w.get("difficulty") or 1),
        "difficulty_label": w.get("difficulty_label") or "?",
        "description": w.get("description") or "",
        "modifiers": dict(w.get("modifiers") or {}),
        "independent": bool(w.get("independent", True)),
    }


def build_custom_profile(
    *,
    display_name: str,
    theme: Mapping[str, Any],
    world_id: str,
    base_difficulty: int = 1,
    modifiers: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    mods = dict(modifiers or {})
    if not mods:
        mods = {
            "enemy_hp_mult": 1.0,
            "enemy_atk_mult": 1.0,
            "xp_mult": 1.0,
            "money_mult": 1.0,
            "start_money_mult": 1.0,
        }
    # slight soft pressure if theme hints harder fringe
    if int(theme.get("difficulty_hint") or 0) >= 2:
        mods.setdefault("enemy_hp_mult", 1.0)
        mods["enemy_hp_mult"] = float(mods.get("enemy_hp_mult") or 1.0) * 1.08
        mods["enemy_atk_mult"] = float(mods.get("enemy_atk_mult") or 1.0) * 1.06
        base_difficulty = max(base_difficulty, 2)
    dlabel = {1: "ปกติ", 2: "ท้าทาย", 3: "ฝันร้าย"}.get(base_difficulty, "ปกติ")
    return {
        "id": world_id,
        "name": display_name.strip() or world_id,
        "source": "custom",
        "theme_id": str(theme.get("id") or ""),
        "theme_name": str(theme.get("name") or ""),
        "starting_area": str(theme.get("starting_area") or "dark_forest"),
        "difficulty": int(base_difficulty),
        "difficulty_label": dlabel,
        "description": f"โลกที่คุณตั้งต้น — ธีม「{theme.get('name') or '?'}」",
        "modifiers": mods,
        "independent": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "open_skill_tags": list(theme.get("open_skill_tags") or []),
    }


def allocate_custom_world_id(display_name: str) -> str:
    base = slug_world_id(display_name)
    candidate = base
    n = 0
    while True:
        folder = Path(SAVES_DIR) / candidate
        # free if no profile and no json saves (or empty dir ok to claim)
        if not folder.exists():
            return candidate
        has_profile = (folder / PROFILE_NAME).is_file()
        has_saves = any(folder.glob("*.json")) and not (
            len(list(folder.glob("*.json"))) == 1 and (folder / PROFILE_NAME).is_file()
        )
        # if only profile without player saves, still occupied
        if has_profile or any(p.name != PROFILE_NAME for p in folder.glob("*.json")):
            n += 1
            candidate = slug_world_id(display_name, suffix=str(n) if n < 10 else str(int(time.time()) % 10000))
            if n > 20:
                candidate = slug_world_id(display_name, suffix=str(int(time.time()) % 100000))
                return candidate
            continue
        return candidate


def resolve_world_def(reg: DataRegistry, world_id: str) -> Dict[str, Any]:
    """
    Unified world definition for UI + create.
    Catalog from registry; custom from world_profile.json.
    """
    wid = str(world_id)
    if wid in (reg.worlds or {}):
        return ensure_catalog_profile(reg, wid)
    prof = load_world_profile(wid)
    if prof:
        return prof
    # orphan save folder without profile
    return {
        "id": wid,
        "name": wid,
        "source": "orphan",
        "theme_id": None,
        "starting_area": "dark_forest",
        "difficulty": 1,
        "difficulty_label": "ปกติ",
        "description": "โลกจากโฟลเดอร์เซฟ",
        "modifiers": {},
        "independent": True,
    }


def list_custom_world_ids() -> List[str]:
    root = Path(SAVES_DIR)
    if not root.is_dir():
        return []
    out: List[str] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if name.startswith("."):
            continue
        if (p / PROFILE_NAME).is_file():
            prof = load_world_profile(name) or {}
            if str(prof.get("source") or "") == "catalog":
                continue
            out.append(name)
            continue
        # has player saves but not in catalog — treat as custom/orphan
        if any(f.suffix == ".json" and f.name != PROFILE_NAME for f in p.iterdir()):
            out.append(name)
    return out


def apply_world_theme_to_player(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    world_id: str,
    profile: Optional[Mapping[str, Any]] = None,
    force_seed: bool = False,
) -> List[str]:
    """
    Apply world profile + theme to player.
    Mastery / skill_chance seeds apply **once** per theme (flag world_theme_applied).
    force_seed=True for brand-new characters.
    When WORLD_THEME_UX_ENABLED is False: only stamp world_id + catalog modifiers
    (simple path — no theme mastery / open-skill seed).
    """
    notes: List[str] = []
    if not world_theme_ux_enabled():
        player["world_id"] = str(world_id)
        mods = dict(player.get("world_modifiers") or {})
        if not mods and world_id in (reg.worlds or {}):
            mods = dict((reg.worlds.get(world_id) or {}).get("modifiers") or {})
        player["world_modifiers"] = mods
        if force_seed:
            start = str((reg.worlds.get(world_id) or {}).get("starting_area") or "")
            if start and start in (reg.areas or {}):
                player["location"] = start
        return notes

    prof = dict(profile or resolve_world_def(reg, world_id))
    theme_id = str(prof.get("theme_id") or "")
    theme = theme_by_id(theme_id) if theme_id else theme_for_catalog_world(world_id, reg)
    if theme is None and prof.get("starting_area"):
        theme = theme_for_area(str(prof.get("starting_area")))

    player["world_id"] = str(world_id)
    player["world_display_name"] = str(prof.get("name") or world_id)
    player["world_source"] = str(prof.get("source") or "catalog")

    mods = dict(prof.get("modifiers") or player.get("world_modifiers") or {})
    if not mods and world_id in (reg.worlds or {}):
        mods = dict((reg.worlds.get(world_id) or {}).get("modifiers") or {})
    player["world_modifiers"] = mods

    start = str(prof.get("starting_area") or player.get("location") or "dark_forest")
    # only move location for new chars / force; never yank existing adventurers on load
    if force_seed and start in (reg.areas or {}):
        player["location"] = start

    if not theme:
        if force_seed:
            notes.append(" …โลกนี้ยังไม่กำหนดธีมชัด — เดินทางจะค่อยรู้เอง")
        return notes

    tid = str(theme.get("id"))
    player["world_theme_id"] = tid
    player["world_theme_name"] = str(theme.get("name") or "")
    tags = [str(x) for x in (theme.get("open_skill_tags") or [])]
    player["open_skill_tags"] = tags
    player["open_skill_hint"] = str(theme.get("soft_skill_hint") or "")

    already = str(player.get("world_theme_applied") or "") == tid
    if already and not force_seed:
        return notes

    # seed once
    sc = int(theme.get("skill_chance_bonus") or 0)
    player["skill_chance_bonus"] = int(player.get("skill_chance_bonus") or 0) + sc
    lp = int(theme.get("learn_points_seed") or 0)
    if lp:
        player["learn_points"] = int(player.get("learn_points") or 0) + lp
    mg = int(theme.get("mastery_gain_bonus") or 0)
    if mg:
        player["mastery_gain_bonus"] = int(player.get("mastery_gain_bonus") or 0) + mg

    am = dict(player.get("area_mastery") or {})
    start_bonus = int(theme.get("mastery_start_bonus") or 0)
    aff_bonus = int(theme.get("affinity_mastery_bonus") or 0)
    climates = set(str(c) for c in (theme.get("climate_affinity") or []))
    if start in am or start in (reg.areas or {}):
        base = int(am.get(start) or (reg.areas.get(start) or {}).get("mastery_start") or 10)
        am[start] = min(100, base + start_bonus)
    for aid, area in (reg.areas or {}).items():
        if aid == start:
            continue
        acl = set(str(c) for c in (area.get("climate") or []))
        if climates and (climates & acl):
            base = int(am.get(aid) or area.get("mastery_start") or 10)
            am[aid] = min(100, base + aff_bonus)
    player["area_mastery"] = am
    player["world_theme_applied"] = tid

    tname = theme.get("name") or tid
    aname = area_display_name(reg, start)
    notes.append(f" ธีมโลก「{tname}」· จุดเริ่ม {aname}")
    notes.append(f" ชำนาญ{aname} อุ่นขึ้น — โลกจำรอยเท้าคุณ")
    hint = str(theme.get("soft_skill_hint") or "").strip()
    if hint:
        notes.append(f" {hint}")
    for fl in soft_flavor_lines(theme, max_lines=1):
        notes.append(f" …{fl}")
    return notes


def try_open_skill_emergence(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Any,
    *,
    context_tags: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Soft open-skill emergence after explore/combat.
    Uses skill_chance_bonus + theme tag overlap — never shows %.
    Disabled while WORLD_THEME_UX_ENABLED is False.
    """
    notes: List[str] = []
    if not world_theme_ux_enabled():
        return notes
    bonus = int(player.get("skill_chance_bonus") or 0)
    # base ~3% + bonus*0.4%  capped ~18%
    p = min(0.18, 0.03 + max(0, bonus) * 0.004)
    try:
        roll = float(rng.random())
    except Exception:
        return notes
    if roll > p:
        return notes

    tags = set(str(t).lower() for t in (player.get("open_skill_tags") or []))
    ctx = set(str(t).lower() for t in (context_tags or []))
    affinity = 1.0
    if tags and ctx and (tags & ctx):
        affinity = 1.35
    elif tags and ctx:
        affinity = 0.85
    if roll > p * affinity:
        return notes

    # soft learn_points drip
    player["learn_points"] = int(player.get("learn_points") or 0) + 1
    # chance to reveal a soft tree whisper (unlock visibility only if prereq-ish)
    try:
        from game.domain.skill_tree import ensure_skill_tree_state, list_visible_tree_nodes

        ensure_skill_tree_state(player)
        nodes = list_visible_tree_nodes(player, reg)
        owned = set(player.get("skills") or [])
        candidates = [n for n in nodes if str(n.get("id") or n.get("skill_id") or "") not in owned]
        # prefer tag match on skill def
        scored: List[Tuple[int, str, str]] = []
        for n in candidates:
            sid = str(n.get("id") or n.get("skill_id") or "")
            if not sid:
                continue
            sk = reg.skills.get(sid) or {}
            stags = set(str(x).lower() for x in (sk.get("tags") or []))
            name = str(sk.get("name") or n.get("name") or sid)
            score = 1
            if tags & stags:
                score += 3
            if ctx & stags:
                score += 1
            scored.append((score, sid, name))
        if scored:
            scored.sort(key=lambda x: -x[0])
            # only soft whisper — do not auto-learn full skill
            _sid, sname = scored[0][1], scored[0][2]
            unlocked = list(player.get("skill_tree_unlocked") or [])
            if _sid not in unlocked and _sid not in owned:
                # mark as "sensed" via unlocked list soft edge if adjacent already visible
                pass
            notes.append(f" …กระซิบสกิล「{sname}」— โลกธีมนี้ดึงเส้นทางเปิด (open skill)")
        else:
            notes.append(" …ความรู้สึกสกิลใหม่ซ่าน — ยังจับไม่ชัด")
    except Exception:
        notes.append(" …ความรู้สึกสกิลใหม่ซ่านเบาๆ")
    return notes
