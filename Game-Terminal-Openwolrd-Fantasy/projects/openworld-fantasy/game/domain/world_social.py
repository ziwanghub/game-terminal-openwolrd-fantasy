"""
World-independent social layer:
- rankings without showing level/power numbers
- player-echo encounters via W1 combat/social snapshots
- hidden affinity → friend co-op or foe duel
- W2 lite: rank challenge + bounty

Players never see affinity formula or component scores.
Echo fights NEVER write back to owner save files.
"""
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.config import SAVES_DIR
from game.services.save_service import list_saves, load_player

ECHO_SCHEMA_VERSION = 2


def _load_social_cfg(reg) -> Dict[str, Any]:
    return dict(getattr(reg, "world_social", None) or {})


def echo_age_seconds(snap: Mapping[str, Any]) -> Optional[float]:
    """Age of echo snapshot in seconds (from updated_at). None if unknown."""
    ua = snap.get("updated_at") or snap.get("echo_at")
    if not ua:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            t = time.mktime(time.strptime(str(ua)[:19], fmt))
            return max(0.0, time.time() - t)
        except Exception:
            continue
    return None


def echo_freshness_label(snap: Mapping[str, Any]) -> str:
    """
    Soft presence band (H5-lite style) — no exact timestamps shown.
    ร่องรอยสด / เพิ่งผ่าน / เงาคุ้นเคย / เงาเก่า
    """
    age = echo_age_seconds(snap)
    if age is None:
        return "เงาเลือน"
    if age < 3600:
        return "ร่องรอยสด"
    if age < 86400:
        return "เพิ่งผ่าน"
    if age < 604800:
        return "เงาคุ้นเคย"
    return "เงาเก่า"


def soft_relation_hint(
    player: Mapping[str, Any],
    other_id: str,
) -> str:
    """Soft social memory line — no affinity numbers."""
    mem = (player.get("social_memory") or {}).get(str(other_id) or "") or {}
    rel = str(mem.get("relation") or mem.get("last") or "")
    if rel == "friend":
        return " · เคยเป็นมิตร"
    if rel == "foe":
        return " · เคยปะทะ"
    if rel:
        return " · เคยพบ"
    return ""


def soft_self_standing(
    player: Mapping[str, Any],
    world_id: str,
    reg,
    *,
    limit: int = 15,
) -> str:
    """
    Soft line about where *you* sit on the world board — no raw score.
    """
    pid = str(player.get("id") or "")
    board = build_world_ranking(world_id, reg, limit=limit)
    for row in board:
        if pid and str(row.get("id") or "") == pid:
            band = row.get("soft_band") or soft_rank_band(int(row.get("rank") or 99))
            return (
                f"ร่องรอยของคุณ: 「{band}」 · ชื่อขึ้นบอร์ด "
                f"(#{int(row.get('rank') or 0)} · ไม่โชว์คะแนน)"
            )
    # not listed — soft estimate vs board size
    my_score = hidden_rank_score(player)
    if not board:
        return "โลกยังว่าง — ร่องรอยของคุณอาจเป็นเส้นแรก"
    # rebuild temporary scores of listed via re-load is heavy; soft heuristic:
    if my_score < 15:
        return "ร่องรอยของคุณยังจาง — ยังไม่ขึ้นบอร์ดบน"
    if my_score < 60:
        return "ร่องรอยของคุณกำลังก่อตัว — ยังไม่ติดชั้นบน"
    return "ร่องรอยของคุณหนาขึ้น — ใกล้/เกินขอบบอร์ด (soft · ไม่การันตีที่นั่ง)"


def hidden_rank_score(player: Mapping[str, Any]) -> float:
    """Hidden score for ordering only — never displayed raw to player."""
    # echo snapshot may carry precomputed score
    if player.get("is_echo_snapshot") and player.get("_rank_score") is not None:
        try:
            return float(player.get("_rank_score") or 0)
        except Exception:
            pass
    st = player.get("stats") or {}
    score = 0.0
    score += int(st.get("kills", 0)) * 0.8
    score += int(st.get("boss_kills", 0)) * 18
    score += int(st.get("quests_completed", 0)) * 12
    score += int(st.get("rank_challenge_wins", 0)) * 28
    score += len(player.get("bosses_defeated") or []) * 22
    score += len(player.get("library_entries_read") or []) * 5
    score += int(player.get("occ_rank_index", 0)) * 15
    if player.get("unit_class_id"):
        score += 40
    # level contributes weakly but we never show level on board
    score += math.log1p(int(player.get("level", 1))) * 8
    # gear wealth proxy
    score += len(player.get("inventory_ids") or []) * 0.3
    ups = player.get("upgrade_levels") or {}
    if isinstance(ups, dict):
        score += sum(int(x or 0) for x in ups.values()) * 4
    # W0+: social help contributes (never shown as number)
    score += int(player.get("help_assists") or 0) * 9
    score += int(player.get("help_rep") or 0) * 0.35
    score += len(player.get("dungeons_cleared") or []) * 14
    flags = player.get("flags") or {}
    score += int(flags.get("rank_challenge_wins") or 0) * 15
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


def format_ranking_lines(
    world_id: str,
    reg,
    *,
    viewer: Optional[Mapping[str, Any]] = None,
) -> List[str]:
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
    else:
        for row in board:
            extra = f" · 〔{row['help_title']}〕" if row.get("help_title") else ""
            lines.append(
                f"  #{row['rank']} {row['unit_mark']}{row['name']} · {row['path']} · "
                f"{row['title']} · {row.get('soft_band', '')}{extra}"
            )
            if row.get("area"):
                lines.append(f"       ร่องรอย: {row['area']}")
    if viewer is not None:
        try:
            lines.append("---")
            lines.append(f"  {soft_self_standing(viewer, world_id, reg)}")
        except Exception:
            pass
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
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path = folder / "rank_board.json"
    try:
        from game.domain.file_lock import world_file_lock

        with world_file_lock(world_id, "rank", timeout=6.0):
            path.write_text(text, encoding="utf-8")
    except Exception:
        path.write_text(text, encoding="utf-8")


def echoes_dir(world_id: str) -> Path:
    d = Path(SAVES_DIR) / str(world_id) / "echoes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cap_int(v: Any, lo: int, hi: int, default: int = 0) -> int:
    try:
        n = int(v)
    except Exception:
        n = default
    return max(lo, min(hi, n))


def build_echo_snapshot(player: Mapping[str, Any]) -> Dict[str, Any]:
    """
    W1 combat/social snapshot — enough for fight/talk/party.
    No inventory dump, no admin flags, values capped (sanitize).
    """
    equip = dict(player.get("equip_ids") or {})
    # strip legacy only keep main pieces summary
    equip_summary = {
        "main_hand": equip.get("main_hand") or equip.get("weapon"),
        "off_hand": equip.get("off_hand"),
        "body": equip.get("body") or equip.get("armor"),
        "acc_1": equip.get("acc_1") or equip.get("accessory"),
        "head": equip.get("head"),
    }
    skills = [str(s) for s in (player.get("skills") or []) if s][:24]
    soft_titles = list(player.get("soft_titles") or [])[:5]
    snap: Dict[str, Any] = {
        "schema": ECHO_SCHEMA_VERSION,
        "id": str(player.get("id") or ""),
        "name": str(player.get("name") or "เงานิรนาม"),
        "world_id": str(player.get("world_id") or "default"),
        "location": str(player.get("location") or ""),
        "occupation_id": str(player.get("occupation_id") or ""),
        "occupation": str(player.get("occupation") or ""),
        "occ_path": str(player.get("occ_path") or ""),
        "level": _cap_int(player.get("level"), 1, 200, 1),
        "bonus_atk": _cap_int(player.get("bonus_atk"), 1, 500, 5),
        "max_hp": _cap_int(player.get("max_hp"), 20, 5000, 80),
        "hp": _cap_int(player.get("hp"), 1, 5000, 80),
        "max_mana": _cap_int(player.get("max_mana"), 0, 2000, 40),
        "pressure": _cap_int(player.get("pressure"), 0, 100, 10),
        "stats_alloc": {
            k: _cap_int((player.get("stats_alloc") or {}).get(k), 0, 200, 0)
            for k in ("atk", "defense", "magic", "speed", "intelligence", "crit")
        },
        "skills": skills,
        "gear_tags": [str(t) for t in (player.get("gear_tags") or [])][:12],
        "equip_summary": equip_summary,
        "unit_class_id": player.get("unit_class_id"),
        "soft_titles": soft_titles,
        "help_rep": _cap_int(player.get("help_rep"), 0, 9999, 0),
        "personality_labels": list(player.get("personality_labels") or [])[:6],
        # rank proxy soft (not full score dump for client trust — internal only)
        "_rank_score": float(hidden_rank_score(player)),
        "is_echo_snapshot": True,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "echo_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        # MI soft: echoes fight like cunning travelers (not bosses)
        "intel_tier": 2,
        "can_flee": True,
    }
    # strip any accidental admin / session keys
    for bad in ("admin", "is_admin", "god_mode", "debug", "inventory_ids", "money_world"):
        snap.pop(bad, None)
    return snap


def write_echo_snapshot(player: Mapping[str, Any], world_id: Optional[str] = None) -> Optional[Path]:
    """Persist snapshot under saves/{world}/echoes/{id}.json"""
    wid = str(world_id or player.get("world_id") or "default")
    pid = str(player.get("id") or "").strip()
    if not pid:
        return None
    snap = build_echo_snapshot(player)
    path = echoes_dir(wid) / f"{pid}.json"
    text = json.dumps(snap, ensure_ascii=False, indent=2)
    try:
        from game.domain.file_lock import world_file_lock

        with world_file_lock(wid, f"echo_{pid}", timeout=5.0):
            path.write_text(text, encoding="utf-8")
    except Exception:
        path.write_text(text, encoding="utf-8")
    return path


def load_echo_snapshot(world_id: str, player_id: str) -> Optional[Dict[str, Any]]:
    path = echoes_dir(world_id) / f"{player_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            data["is_echo_snapshot"] = True
            return data
    except Exception:
        return None
    return None


def list_echo_snapshots(
    world_id: str,
    exclude_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load all W1 echo files; prefer snapshots over full saves for encounters."""
    out: List[Dict[str, Any]] = []
    folder = echoes_dir(world_id)
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or not data.get("id"):
            continue
        if exclude_id and str(data.get("id")) == str(exclude_id):
            continue
        data["is_echo_snapshot"] = True
        out.append(data)
    return out


def list_other_players_in_world(
    world_id: str,
    exclude_id: Optional[str],
    area_id: Optional[str] = None,
    *,
    prefer_echo: bool = True,
) -> List[Dict[str, Any]]:
    """
    Others in world. W1: prefer echo snapshots (safe copies).
    Fallback: load full save then convert to snapshot (still not mutates disk).
    """
    others: List[Dict[str, Any]] = []
    if prefer_echo:
        snaps = list_echo_snapshots(world_id, exclude_id=exclude_id)
        if snaps:
            others = snaps
    if not others:
        for meta in list_saves(world_id):
            try:
                p = load_player(meta["path"])
            except Exception:
                continue
            if exclude_id and p.get("id") == exclude_id:
                continue
            # never hand out live mutable save — always snapshot view
            others.append(build_echo_snapshot(p))
    if area_id:
        # sort: same area first (caller may filter)
        others = sorted(
            others,
            key=lambda o: 0 if str(o.get("location")) == str(area_id) else 1,
        )
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
    """
    Materialize echo snapshot as combat foe.
    Uses copy only — never mutates owner save / echo file mid-fight source.
    """
    # accept full player or snapshot
    src = dict(other) if not other.get("is_echo_snapshot") else dict(other)
    if not src.get("is_echo_snapshot") and src.get("id"):
        # if raw save dict slipped in, still snapshot-sanitize
        try:
            src = build_echo_snapshot(src)
        except Exception:
            pass
    hp = _cap_int(src.get("hp") or src.get("max_hp"), 20, 5000, 80)
    max_hp = _cap_int(src.get("max_hp") or hp, 20, 5000, 80)
    atk = _cap_int(src.get("bonus_atk"), 5, 500, 10)
    elements = list(src.get("gear_tags") or ["physical"])
    if not elements:
        elements = ["physical"]
    name = str(src.get("name") or "เงาลึกลับ")
    tier = _cap_int(src.get("intel_tier"), 0, 5, 2)
    return {
        "id": f"echo_{src.get('id')}",
        "name": f"เงา·{name}",
        "level": _cap_int(src.get("level"), 1, 200, 1),
        "hp": max(20, hp),
        "max_hp": max(20, max_hp),
        "atk": max(5, atk),
        "elements": elements[:3],
        "xp_mult": 1.35,
        "attack_profiles": [
            {
                "id": "echo_strike",
                "tags": elements[:1] or ["physical"],
                "telegraph": f"เงาของ{name} ยกอาวุธ!",
                "power": atk,
            },
            {
                "id": "echo_skill",
                "tags": elements,
                "telegraph": f"เงาของ{name} ใช้ท่าที่เคยมี…",
                "power": atk + 4,
            },
            {
                "id": "echo_feint",
                "tags": elements[:1] or ["physical"],
                "telegraph": f"เงาของ{name} เปลี่ยนจังหวะ — หลอกแนว!",
                "power": max(5, atk - 2),
            },
        ],
        "statuses": [],
        "is_player_echo": True,
        "echo_source_id": src.get("id"),
        "skills": list(src.get("skills") or [])[:16],
        # MI: smart traveler echo — may pick profiles / soft flee
        "intel_tier": max(2, tier),
        "can_flee": bool(src.get("can_flee", True)),
        "elite": False,
        "boss": False,
        # combat mutations stay on this dict only
        "_echo_combat_copy": True,
    }


def pick_echo_for_sight(
    player: Mapping[str, Any],
    reg,
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    cfg = _load_social_cfg(reg)
    world_id = str(player.get("world_id") or "default")
    others = list_other_players_in_world(
        world_id, exclude_id=str(player.get("id") or ""), prefer_echo=True
    )
    if not others:
        return None
    if rng.random() > float(cfg.get("sight_chance", 0.42)):
        return None
    # prefer same area
    area = str(player.get("location") or "")
    same = [o for o in others if str(o.get("location")) == area]
    pool = same if same and rng.random() < 0.7 else others
    other = dict(rng.choice(pool))  # defensive copy
    soft_title = ""
    titles = other.get("soft_titles") or []
    if titles:
        soft_title = f" · 〔{titles[0]}〕"
    fresh = echo_freshness_label(other)
    rel = soft_relation_hint(player, str(other.get("id") or ""))
    base_hint = rng.choice(
        [
            "ร่องรอยจากเซฟในโลกนี้ — ไม่ใช่ตัวจริง",
            "เงาความสามารถที่เคยบันทึก",
            "ร่างคุ้นเคย (echo · ไม่ทำร้ายเซฟเจ้าของ)",
            "นักผจญภัยจากบันทึกโลก",
        ]
    )
    return {
        "kind": "player",
        "label": f"เงา·{other.get('name') or 'ผู้เดินทาง'}",
        "hint": f"{base_hint} · 〔{fresh}〕{soft_title}{rel}",
        "known": True,
        "risk": "?",
        "echo_freshness": fresh,
        "player_echo": other,
    }


# ── W2 lite: rank challenge ─────────────────────────────────────────


def challenge_bounty(rank: int, reg=None) -> int:
    """World money cost to challenge rank position (hidden curve)."""
    r = max(1, int(rank))
    base = 40 + r * 25
    if r <= 3:
        base += 80
    if r == 1:
        base += 120
    return int(base)


def load_rank_board(world_id: str) -> Dict[str, Any]:
    path = Path(SAVES_DIR) / world_id / "rank_board.json"
    if not path.is_file():
        return {"cards": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"cards": []}
    except Exception:
        return {"cards": []}


def try_rank_challenge(
    challenger: MutableMapping[str, Any],
    reg,
    rng: random.Random,
    *,
    target_rank: int = 1,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    W2 lite: pay bounty → return (ok, message, foe_combatant or None).
    Does not auto-resolve fight; caller runs combat then apply_rank_challenge_result.
    """
    world_id = str(challenger.get("world_id") or "default")
    board = build_world_ranking(world_id, reg, limit=15)
    if not board:
        return False, "ยังไม่มีใครบนบอร์ดอันดับ", None
    target = None
    for row in board:
        if int(row.get("rank") or 0) == int(target_rank):
            target = row
            break
    if not target:
        return False, f"ไม่พบอันดับ #{target_rank}", None
    tid = str(target.get("id") or "")
    if tid and tid == str(challenger.get("id") or ""):
        return False, "คุณถือที่นั่งนี้อยู่แล้ว (หรือชื่อซ้ำ)", None
    bounty = challenge_bounty(int(target_rank), reg)
    money = int(challenger.get("money_world") or 0)
    if money < bounty:
        return False, f"ค่าหัวไม่พอ (ต้องการเงินโลก ~{bounty} · soft)", None
    # load echo of target
    echo = load_echo_snapshot(world_id, tid) if tid else None
    if not echo and tid:
        for meta in list_saves(world_id):
            try:
                p = load_player(meta["path"])
            except Exception:
                continue
            if str(p.get("id")) == tid:
                echo = build_echo_snapshot(p)
                break
    if not echo:
        # synthetic from board card
        echo = {
            "id": tid or f"rank_{target_rank}",
            "name": target.get("name") or "เงาอันดับ",
            "bonus_atk": 12 + int(target_rank) * 2,
            "max_hp": 90 + int(target_rank) * 15,
            "hp": 90 + int(target_rank) * 15,
            "level": 5 + int(target_rank),
            "gear_tags": ["physical"],
            "skills": ["basic_strike", "guard_basic"],
            "is_echo_snapshot": True,
            "occ_path": target.get("path"),
        }
    challenger["money_world"] = money - bounty
    challenger["_rank_challenge"] = {
        "target_rank": int(target_rank),
        "target_id": tid,
        "target_name": target.get("name"),
        "bounty": bounty,
        "soft_band": target.get("soft_band"),
    }
    foe = other_as_combatant(echo)
    foe["name"] = f"เงาอันดับ·{target.get('name')}"
    foe["xp_mult"] = 1.5
    return (
        True,
        f"จ่ายค่าหัว {bounty} — ท้าเงาของ {target.get('name')} (#{target_rank})",
        foe,
    )


def apply_rank_challenge_result(
    challenger: MutableMapping[str, Any],
    reg,
    *,
    won: bool,
) -> List[str]:
    """
    After combat: win → soft seat on board via rewriting cards order soft.
    Loss → bounty already paid (kept by world / no transfer to owner save).
    Never deletes owner save.
    """
    ctx = dict(challenger.pop("_rank_challenge", None) or {})
    if not ctx:
        return []
    lines: List[str] = []
    bounty = int(ctx.get("bounty") or 0)
    world_id = str(challenger.get("world_id") or "default")
    if not won:
        lines.append(f"แพ้การท้า — เสียค่าหัว {bounty} (เงาเจ้าของไม่เสียของในเซฟ)")
        # soft: part of bounty to world tax fund (not owner save)
        try:
            from game.domain.market import load_market, save_market

            m = load_market(world_id)
            m["tax_fund"] = int(m.get("tax_fund") or 0) + max(1, bounty // 3)
            save_market(world_id, m)
        except Exception:
            pass
        return lines
    lines.append(f"ชนะเงาอันดับ — ที่นั่งโชว์ขยับ (soft)")
    # rebuild board with challenger boosted soft score write is via build which reads saves
    # ensure echo + save reflect presence; write rank board after bumping a soft flag
    flags = dict(challenger.get("flags") or {})
    flags["rank_challenge_wins"] = int(flags.get("rank_challenge_wins") or 0) + 1
    flags["last_challenged_rank"] = int(ctx.get("target_rank") or 1)
    challenger["flags"] = flags
    # temporary score boost via stats so they appear higher
    st = dict(challenger.get("stats") or {})
    st["rank_challenge_wins"] = int(st.get("rank_challenge_wins") or 0) + 1
    challenger["stats"] = st
    try:
        board = build_world_ranking(world_id, reg, limit=15)
        write_rank_board_soft(world_id, board)
        my_rank = None
        for row in board:
            if str(row.get("id")) == str(challenger.get("id")):
                my_rank = row.get("rank")
                break
        if my_rank:
            lines.append(f"ร่องรอยบนบอร์ด: #{my_rank} · {soft_rank_band(int(my_rank))}")
        else:
            lines.append("ยังไม่ติดบอร์ดโชว์ — เงื่อนไขซ่อน (ช่วย/ภารกิจ/เอาตัวรอด…)")
    except Exception:
        lines.append("บอร์ดอัปเดตไม่สมบูรณ์ — แต่ชัยชนะถูกจำ")
    return lines
