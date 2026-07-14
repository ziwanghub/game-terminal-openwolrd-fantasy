"""
Soft class-change eligibility — free-form conditions, never shown to player.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def _paths(reg: DataRegistry) -> List[Dict[str, Any]]:
    cfg = getattr(reg, "class_paths", None) or {}
    return list(cfg.get("paths") or [])


def _cond_ok(player: Mapping[str, Any], reg: DataRegistry, c: Mapping[str, Any]) -> bool:
    t = str(c.get("type") or "")
    st = player.get("stats") or {}
    alloc = player.get("stats_alloc") or {}
    if t == "min_level":
        return int(player.get("level") or 1) >= int(c.get("value") or 0)
    if t == "min_alloc":
        return int(alloc.get(str(c.get("stat") or ""), 0)) >= int(c.get("value") or 0)
    if t == "min_kills":
        return int(st.get("kills") or 0) >= int(c.get("value") or 0)
    if t == "min_combos":
        combos = int(st.get("combos") or 0) or int(
            (player.get("action_counts") or {}).get("attack", 0)
        ) // 3
        return combos >= int(c.get("value") or 0)
    if t == "min_explores":
        return int(st.get("explores") or 0) >= int(c.get("value") or 0)
    if t == "min_flees":
        return int(st.get("flees") or 0) >= int(c.get("value") or 0)
    if t == "min_heals":
        return int(st.get("heals") or 0) >= int(c.get("value") or 0)
    if t == "library_entries":
        return len(player.get("library_entries_read") or []) >= int(c.get("value") or 0)
    if t == "min_stat_points_spent":
        spent = sum(int(v or 0) for v in (alloc or {}).values())
        return spent >= int(c.get("value") or 0)
    if t == "personality_axis":
        inv = player.get("personality_invest") or {}
        axis = str(c.get("axis") or "")
        return int(inv.get(axis) or 0) >= int(c.get("min") or 0)
    return False


def evaluate_path(
    player: Mapping[str, Any],
    reg: DataRegistry,
    path: Mapping[str, Any],
) -> Tuple[bool, int]:
    """Return (eligible, score)."""
    conds = list(path.get("conditions") or [])
    if not conds:
        return False, 0
    score = sum(1 for c in conds if _cond_ok(player, reg, c))
    need = int(path.get("min_score") or max(1, len(conds) // 2))
    return score >= need, score


def list_available_class_paths(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """Paths player can take now (from vagabond or any can_class_change)."""
    occ = reg.occupations.get(str(player.get("occupation_id") or "")) or {}
    # Only offer if starter / flagged, or still free path
    if not (
        occ.get("is_starter")
        or occ.get("can_class_change")
        or str(player.get("occupation_id")) == "vagabond"
    ):
        # allow rare second path if flag
        if not (player.get("flags") or {}).get("allow_reclass"):
            return []
    out: List[Dict[str, Any]] = []
    cur = str(player.get("occupation_id") or "")
    for path in _paths(reg):
        to_id = str(path.get("to_occupation") or "")
        if to_id == cur:
            continue
        if to_id not in (reg.occupations or {}):
            continue
        ok, score = evaluate_path(player, reg, path)
        if ok:
            d = dict(path)
            d["_score"] = score
            out.append(d)
    return out


def apply_class_change(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    path: Mapping[str, Any],
) -> List[str]:
    """Switch occupation — soft, no refund of stats."""
    to_id = str(path.get("to_occupation") or "")
    occ = reg.occupations.get(to_id)
    if not occ:
        return ["ทางนั้นใช้ไม่ได้"]
    old = player.get("occupation") or player.get("occupation_id")
    player["occupation_id"] = to_id
    player["occupation"] = occ.get("name") or to_id
    player["occ_path"] = occ.get("path_name") or occ.get("path") or ""
    player["occ_rank_index"] = 0
    ranks = list(occ.get("ranks") or [])
    player["occ_rank_title"] = (ranks[0].get("title") if ranks else occ.get("name")) or ""
    # grant starter skill if missing
    sk = occ.get("skill")
    if sk:
        skills = list(player.get("skills") or [])
        base = list(player.get("base_skills") or [])
        if sk not in skills:
            skills.append(sk)
            player["skills"] = skills
        if sk not in base:
            base.append(sk)
            player["base_skills"] = base
    player.setdefault("flags", {})["had_class_change"] = True
    player.setdefault("class_change_log", []).append(to_id)
    # recompute latent powers
    try:
        from game.domain.progression import recompute_powers
        from game.domain.equipment import recompute_stats

        recompute_powers(player, reg)
        recompute_stats(player, reg)
    except Exception:
        pass
    notes = [
        f"✦ ทางแยกอาชีพ: จาก {old} → {occ.get('name')}",
        f"  {path.get('flavor') or 'โลกดึงคุณไปทางหนึ่ง…'}",
        "  (คุณไม่รู้แน่ชัดว่าทำไมทางนี้ถึงเปิด)",
    ]
    if sk and sk in (reg.skills or {}):
        notes.append(f"  ได้สกิล: {(reg.skills.get(sk) or {}).get('name', sk)}")
    return notes
