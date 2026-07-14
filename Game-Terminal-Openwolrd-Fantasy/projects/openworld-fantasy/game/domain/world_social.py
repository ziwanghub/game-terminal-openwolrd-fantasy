"""
World-independent social layer:
- rankings without showing level/power numbers
- player-echo encounters using full save data
- hidden affinity → friend co-op or foe duel

Players never see affinity formula or component scores.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.config import SAVES_DIR
from game.services.save_service import list_saves, load_player


def _load_social_cfg(reg) -> Dict[str, Any]:
    return dict(getattr(reg, "world_social", None) or {})


def hidden_rank_score(player: Mapping[str, Any]) -> float:
    """Hidden score for ordering only — never displayed raw to player."""
    st = player.get("stats") or {}
    score = 0.0
    score += int(st.get("kills", 0)) * 0.8
    score += int(st.get("boss_kills", 0)) * 18
    score += int(st.get("quests_completed", 0)) * 12
    score += len(player.get("bosses_defeated") or []) * 22
    score += len(player.get("library_entries_read") or []) * 5
    score += int(player.get("occ_rank_index", 0)) * 15
    if player.get("unit_class_id"):
        score += 40
    # level contributes weakly but we never show level on board
    score += math.log1p(int(player.get("level", 1))) * 8
    # gear wealth proxy
    score += len(player.get("inventory_ids") or []) * 0.3
    score += sum(int(x) for x in (player.get("upgrade_levels") or {}).values()) * 4
    # W0+: social help contributes (never shown as number)
    score += int(player.get("help_assists") or 0) * 9
    score += int(player.get("help_rep") or 0) * 0.35
    score += len(player.get("dungeons_cleared") or []) * 14
    return score


def soft_rank_band(rank: int) -> str:
    """Soft place label — not a numeric score."""
    if rank <= 1:
        return "เงาแรกแห่งโลก"
    if rank <= 3:
        return "เงาชั้นบน"
    if rank <= 7:
        return "เงาที่รู้จัก"
    if rank <= 15:
        return "นักเดินทาง"
    return "ร่องรอย"


def reputation_title(score: float, reg) -> str:
    cfg = _load_social_cfg(reg)
    titles = list(cfg.get("rank_titles") or [])
    title = "นักเดินทางนิรนาม"
    for t in sorted(titles, key=lambda x: int(x.get("min_score", 0))):
        if score >= float(t.get("min_score", 0)):
            title = str(t.get("title") or title)
    return title


def build_world_ranking(world_id: str, reg, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Public ranking rows — NO level, NO atk/hp/power numbers.
    W0: soft band + optional helper title.
    """
    rows = []
    for meta in list_saves(world_id):
        try:
            p = load_player(meta["path"])
        except Exception:
            continue
        score = hidden_rank_score(p)
        path = p.get("occ_path") or p.get("occupation") or "???"
        help_title = ""
        try:
            from game.domain.situation import helper_soft_title

            help_title = helper_soft_title(p)
        except Exception:
            pass
        # hide dungeon location soft
        loc = str(p.get("location") or "?")
        if loc.startswith("dungeon:"):
            loc = "ในเงาถ้ำ…"
        rows.append(
            {
                "id": p.get("id"),
                "name": p.get("name", "?"),
                "path": path,
                "title": reputation_title(score, reg),
                "area": loc,
                "unit": bool(p.get("unit_class_id")),
                "help_title": help_title,
                "_score": score,  # strip before display
            }
        )
    rows.sort(key=lambda r: r["_score"], reverse=True)
    out = []
    for i, r in enumerate(rows[:limit], 1):
        out.append(
            {
                "rank": i,
                "id": r.get("id"),
                "name": r["name"],
                "path": r["path"],
                "title": r["title"],
                "area": r["area"],
                "unit_mark": "◆" if r["unit"] else "",
                "soft_band": soft_rank_band(i),
                "help_title": r.get("help_title") or "",
            }
        )
    return out


def format_ranking_lines(world_id: str, reg) -> List[str]:
    w = (reg.worlds.get(world_id) or {})
    lines = [
        f"อันดับชื่อเสียง — {w.get('name', world_id)}",
        f"ความยาก: {w.get('difficulty_label', '?')} (โลกอิสระ)",
        "— ไม่แสดงเลเวล / ค่าพลัง / คะแนนดิบ —",
        "— อันดับ ≠ ดาเมจสูงสุดเสมอ (ช่วยเหลือ·ภารกิจ·เอาตัวรอด ซ่อน) —",
    ]
    board = build_world_ranking(world_id, reg)
    if not board:
        lines.append("  (ยังไม่มีผู้เล่นในโลกนี้)")
        return lines
    for row in board:
        extra = f" · 〔{row['help_title']}〕" if row.get("help_title") else ""
        lines.append(
            f"  #{row['rank']} {row['unit_mark']}{row['name']} · {row['path']} · "
            f"{row['title']} · {row.get('soft_band', '')}{extra}"
        )
        if row.get("area"):
            lines.append(f"       ร่องรอย: {row['area']}")
    # W0: write soft public card file (no scores)
    try:
        write_rank_board_soft(world_id, board)
    except Exception:
        pass
    return lines


def write_rank_board_soft(world_id: str, board: List[Dict[str, Any]]) -> None:
    """Persist public rank cards only (W0) — never write hidden scores."""
    import json
    import time
    from pathlib import Path

    from game.config import SAVES_DIR

    folder = Path(SAVES_DIR) / world_id
    folder.mkdir(parents=True, exist_ok=True)
    public = []
    for row in board:
        public.append(
            {
                "rank": row.get("rank"),
                "name": row.get("name"),
                "path": row.get("path"),
                "title": row.get("title"),
                "soft_band": row.get("soft_band"),
                "help_title": row.get("help_title") or "",
                "area": row.get("area"),
            }
        )
    payload = {
        "world_id": world_id,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cards": public,
        "note": "public soft cards only — no scores",
    }
    (folder / "rank_board.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_other_players_in_world(
    world_id: str,
    exclude_id: Optional[str],
    area_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    others = []
    for meta in list_saves(world_id):
        try:
            p = load_player(meta["path"])
        except Exception:
            continue
        if exclude_id and p.get("id") == exclude_id:
            continue
        if area_id and str(p.get("location")) != str(area_id):
            # still allow global world echo with lower priority — include all, filter later
            pass
        others.append(p)
    return others


def _path_of(p: Mapping[str, Any], reg) -> str:
    oid = str(p.get("occupation_id") or "")
    occ = (reg.occupations.get(oid) or {})
    return str(occ.get("path") or p.get("occ_path") or "unknown")


def _stat_vector(p: Mapping[str, Any]) -> List[float]:
    a = p.get("stats_alloc") or {}
    keys = ("atk", "defense", "magic", "speed", "crit")
    vec = [float(a.get(k, 0)) for k in keys]
    s = sum(vec) or 1.0
    return [x / s for x in vec]


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return max(0.0, min(1.0, dot / (na * nb)))


def compute_affinity(
    self_p: Mapping[str, Any],
    other_p: Mapping[str, Any],
    reg,
    approach_id: str,
    rng: random.Random,
) -> float:
    """
    Hidden affinity score. Never expose components to UI.
    """
    cfg = _load_social_cfg(reg)
    w = cfg.get("weights") or {}
    aff = 0.0

    path_a = _path_of(self_p, reg)
    path_b = _path_of(other_p, reg)
    if path_a == path_b:
        aff += float(w.get("path_same", 18))
    else:
        adj = (cfg.get("path_adjacent") or {}).get(path_a) or []
        riv = (cfg.get("path_rival") or {}).get(path_a) or []
        if path_b in adj:
            aff += float(w.get("path_adjacent", 6))
        if path_b in riv:
            aff += float(w.get("path_rival", -14))

    # gear tags
    tags_a = set(self_p.get("gear_tags") or [])
    tags_b = set(other_p.get("gear_tags") or [])
    overlap = len(tags_a & tags_b)
    aff += min(float(w.get("gear_tag_overlap_cap", 16)), overlap * float(w.get("gear_tag_overlap_per", 4)))

    # stat alloc similarity (hidden)
    sim = _cosine(_stat_vector(self_p), _stat_vector(other_p))
    aff += sim * float(w.get("stat_vector_similarity", 20))

    # unit
    ua, ub = self_p.get("unit_class_id"), other_p.get("unit_class_id")
    if ua and ub and ua == ub:
        aff += float(w.get("unit_both", 10))
    elif ua and ub and ua != ub:
        aff += float(w.get("unit_mismatch", -4))

    # pressure gap
    pr_a = int(self_p.get("pressure", 10))
    pr_b = int(other_p.get("pressure", 10))
    if abs(pr_a - pr_b) <= 8:
        aff += float(w.get("pressure_close", 6))
    elif abs(pr_a - pr_b) >= 20:
        aff += float(w.get("pressure_far", -8))

    # prior history in this world (stored on self)
    hist = (self_p.get("social_memory") or {}).get(str(other_p.get("id") or ""), {})
    aff += int(hist.get("friend_pts", 0)) * 0.5
    aff += int(hist.get("rival_pts", 0)) * -0.6
    if hist.get("was_friend"):
        aff += float(w.get("prior_friend", 25))
    if hist.get("was_rival"):
        aff += float(w.get("prior_rival", -30))

    # rank gap (hidden scores)
    gap = abs(hidden_rank_score(self_p) - hidden_rank_score(other_p))
    aff += (gap / 20.0) * float(w.get("rank_gap_penalty", -0.4))

    # approach
    delta = (cfg.get("approach_affinity_delta") or {}).get(approach_id, 0)
    aff += float(delta)

    # personality compatibility (hidden)
    try:
        from game.domain.personality import (
            compatibility,
            compatibility_to_affinity_bonus,
            apply_event,
        )

        # ensure both have personality
        if isinstance(self_p, dict):
            from game.domain.personality import ensure_personality

            ensure_personality(self_p)  # type: ignore
        if isinstance(other_p, dict):
            from game.domain.personality import ensure_personality

            ensure_personality(other_p)  # type: ignore
        comp = compatibility(self_p, other_p, reg, approach_id=approach_id)
        aff += compatibility_to_affinity_bonus(comp)
        # track approach as personality event on self if mutable
        if isinstance(self_p, dict):
            apply_event(self_p, f"approach_{approach_id}", reg)  # type: ignore
    except Exception:
        pass

    noise = float(w.get("noise_range", 10))
    aff += rng.uniform(-noise, noise)
    return aff


def resolve_social_outcome(
    affinity: float,
    reg,
) -> str:
    cfg = _load_social_cfg(reg)
    friend_t = float(cfg.get("friend_threshold", 15))
    host_t = float(cfg.get("hostile_threshold", -10))
    if affinity >= friend_t:
        return "friend"
    if affinity <= host_t:
        return "foe"
    # grey zone
    if affinity >= 0:
        return "neutral_friendish"
    return "neutral_foeish"


def remember_social(
    self_p: MutableMapping[str, Any],
    other_id: str,
    outcome: str,
) -> None:
    mem = dict(self_p.get("social_memory") or {})
    entry = dict(mem.get(other_id) or {"friend_pts": 0, "rival_pts": 0})
    if outcome == "friend":
        entry["friend_pts"] = int(entry.get("friend_pts", 0)) + 3
        entry["was_friend"] = True
    elif outcome == "foe":
        entry["rival_pts"] = int(entry.get("rival_pts", 0)) + 3
        entry["was_rival"] = True
    elif outcome == "neutral_friendish":
        entry["friend_pts"] = int(entry.get("friend_pts", 0)) + 1
    else:
        entry["rival_pts"] = int(entry.get("rival_pts", 0)) + 1
    mem[other_id] = entry
    self_p["social_memory"] = mem


def other_as_combatant(other: Mapping[str, Any]) -> Dict[str, Any]:
    """Materialize full player data as a combat foe (uses their gear/stats)."""
    hp = int(other.get("hp") or other.get("max_hp") or 80)
    max_hp = int(other.get("max_hp") or hp)
    atk = int(other.get("bonus_atk") or 10)
    elements = list(other.get("gear_tags") or ["physical"])
    if not elements:
        elements = ["physical"]
    return {
        "id": f"player_{other.get('id')}",
        "name": str(other.get("name") or "ผู้เล่นลึกลับ"),
        "level": int(other.get("level") or 1),  # internal only
        "hp": max(20, hp),
        "max_hp": max(20, max_hp),
        "atk": max(5, atk),
        "elements": elements[:3],
        "xp_mult": 1.4,
        "attack_profiles": [
            {
                "id": "player_strike",
                "tags": elements[:1] or ["physical"],
                "telegraph": f"{other.get('name')} ยกอาวุธ!",
                "power": atk,
            },
            {
                "id": "player_skill",
                "tags": elements,
                "telegraph": f"{other.get('name')} ใช้สกิล!",
                "power": atk + 4,
            },
        ],
        "statuses": [],
        "is_player_echo": True,
        "echo_source_id": other.get("id"),
        "skills": list(other.get("skills") or []),
    }


def pick_echo_for_sight(
    player: Mapping[str, Any],
    reg,
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    cfg = _load_social_cfg(reg)
    world_id = str(player.get("world_id") or "default")
    others = list_other_players_in_world(world_id, exclude_id=str(player.get("id") or ""))
    if not others:
        return None
    if rng.random() > float(cfg.get("sight_chance", 0.42)):
        return None
    # prefer same area
    area = str(player.get("location") or "")
    same = [o for o in others if str(o.get("location")) == area]
    pool = same if same and rng.random() < 0.7 else others
    other = rng.choice(pool)
    return {
        "kind": "player",
        "label": str(other.get("name") or "ผู้เดินทาง"),
        "hint": rng.choice(
            [
                "ร่างคุ้นเคยในโลกนี้",
                "เงาที่มีประวัติ",
                "ผู้เล่นอีกคน (บันทึกโลก)",
                "นักผจญภัยจากเซฟอื่น",
            ]
        ),
        "known": True,
        "risk": "?",
        "player_echo": other,
    }
