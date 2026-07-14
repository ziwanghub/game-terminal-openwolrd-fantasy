"""
Soft class-change eligibility + permanent accept/decline offers.

Player never sees unlock conditions.
If they decline an offered occupation, that occupation path is gone for the
character — other occupations may still appear later when eligible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def _paths(reg: DataRegistry) -> List[Dict[str, Any]]:
    cfg = getattr(reg, "class_paths", None) or {}
    return list(cfg.get("paths") or [])


def ensure_class_offer_state(player: MutableMapping[str, Any]) -> None:
    player.setdefault("declined_occupations", [])
    player.setdefault("declined_class_path_ids", [])
    player.setdefault("class_change_log", [])
    player.setdefault("pending_class_offers", [])  # soft ids offered this session


def declined_occupations(player: Mapping[str, Any]) -> List[str]:
    return [str(x) for x in (player.get("declined_occupations") or [])]


def is_occupation_declined(player: Mapping[str, Any], occupation_id: str) -> bool:
    return str(occupation_id) in declined_occupations(player)


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


def can_receive_class_offers(player: Mapping[str, Any], reg: DataRegistry) -> bool:
    """True while player may still be offered a main occupation path."""
    occ = reg.occupations.get(str(player.get("occupation_id") or "")) or {}
    if (
        occ.get("is_starter")
        or occ.get("can_class_change")
        or str(player.get("occupation_id")) == "vagabond"
    ):
        return True
    if (player.get("flags") or {}).get("allow_reclass"):
        return True
    return False


def list_available_class_paths(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """
    Paths the system may offer now.
    Hides declined occupations and current occupation.
    Conditions never shown.
    """
    ensure_class_offer_state(player)  # type: ignore
    if not can_receive_class_offers(player, reg):
        return []
    declined = set(declined_occupations(player))
    declined_paths = {str(x) for x in (player.get("declined_class_path_ids") or [])}
    out: List[Dict[str, Any]] = []
    cur = str(player.get("occupation_id") or "")
    for path in _paths(reg):
        pid = str(path.get("id") or "")
        to_id = str(path.get("to_occupation") or "")
        if not to_id or to_id == cur:
            continue
        if to_id in declined or pid in declined_paths:
            continue
        if to_id not in (reg.occupations or {}):
            continue
        ok, score = evaluate_path(player, reg, path)
        if ok:
            d = dict(path)
            d["_score"] = score
            out.append(d)
    # stable soft order by score then id
    out.sort(key=lambda p: (-int(p.get("_score") or 0), str(p.get("id") or "")))
    return out


def decline_class_offer(
    player: MutableMapping[str, Any],
    path: Mapping[str, Any],
) -> List[str]:
    """
    Permanently refuse this occupation offer.
    That occupation will not be offered again; other paths may still appear.
    """
    ensure_class_offer_state(player)
    to_id = str(path.get("to_occupation") or "")
    pid = str(path.get("id") or "")
    declined = list(player.get("declined_occupations") or [])
    if to_id and to_id not in declined:
        declined.append(to_id)
    player["declined_occupations"] = declined
    dpaths = list(player.get("declined_class_path_ids") or [])
    if pid and pid not in dpaths:
        dpaths.append(pid)
    player["declined_class_path_ids"] = dpaths
    label = path.get("label") or to_id
    # clear pending if no more offers
    try:
        from game.data_load.registry import get_registry

        reg = get_registry()
        if not list_available_class_paths(player, reg):
            player.setdefault("flags", {})["class_offer_pending"] = False
    except Exception:
        pass
    return [
        f"…คุณผลักทาง「{label}」ออกไป — ทางนั้นปิดสำหรับคุณแล้ว",
        " (อาชีพอื่นยังอาจมาเสนอเองหากเงื่อนไขที่มองไม่เห็นถึง)",
    ]


def apply_class_change(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    path: Mapping[str, Any],
) -> List[str]:
    """Accept offer — switch occupation. Stats already invested are kept (free alloc)."""
    ensure_class_offer_state(player)
    to_id = str(path.get("to_occupation") or "")
    occ = reg.occupations.get(to_id)
    if not occ:
        return ["ทางนั้นใช้ไม่ได้"]
    if is_occupation_declined(player, to_id):
        return ["ทางนี้ถูกปิดไปแล้ว — เลือกไม่ได้"]
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
    player.setdefault("flags", {})["no_class_yet"] = False
    player.setdefault("class_change_log", []).append(to_id)
    # recompute latent powers (growth mult changes with class)
    try:
        from game.domain.progression import recompute_powers
        from game.domain.equipment import recompute_stats

        recompute_powers(player, reg)
        recompute_stats(player, reg)
    except Exception:
        pass
    prim = list(occ.get("primary_stats") or [])
    soft_hint = ""
    if prim:
        soft_map = {
            "atk": "โจมตี",
            "defense": "อึด",
            "magic": "เวท",
            "speed": "เร็ว",
            "intelligence": "สติ",
            "crit": "คม",
        }
        soft_hint = " · ".join(soft_map.get(p, p) for p in prim[:3])
    notes = [
        f"✦ รับทางอาชีพ: {old} → {occ.get('name')}",
        f"  {path.get('flavor') or 'โลกดึงคุณไปทางหนึ่ง…'}",
        "  คุณเดินหน้าในสายนี้แล้ว (ขั้นอาชีพ · ต้นไม้สกิล)",
        "  แต้มสถานะลงได้อิสระ — ไม่บังคับตามสาย",
    ]
    if soft_hint:
        notes.append(f"  (สายนี้มักเข้ากับ: {soft_hint} — แต่ประยุกต์เองได้)")
    if sk and sk in (reg.skills or {}):
        notes.append(f"  ได้สกิลพื้นฐาน: {(reg.skills.get(sk) or {}).get('name', sk)}")
    notes.append("  (คุณไม่รู้แน่ชัดว่าทำไมทางนี้ถึงเปิด)")
    player.setdefault("flags", {})["class_offer_pending"] = False
    return notes


def soft_offer_hint(player: Mapping[str, Any], reg: DataRegistry) -> Optional[str]:
    """One-line soft notify when offers exist (no spoilers)."""
    paths = list_available_class_paths(player, reg)
    if not paths:
        return None
    if len(paths) == 1:
        return "…มีทางอาชีพหนึ่งกำลังยื่นมือมา (กด C · รับหรือปฏิเสธ)"
    return f"…มีทางอาชีพ {len(paths)} ทางกำลังยื่นมือมา (กด C · รับหรือปฏิเสธ)"
