"""
Personality system — shaped by choices and playstyle.
Traits are mostly hidden; only soft labels when extreme.
Compatibility with NPCs / player-echoes affects social outcomes.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry

AXES = (
    "kindness",
    "courage",
    "honor",
    "greed",
    "curiosity",
    "aggression",
    "loyalty",
    "caution",
)


def _cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "personality", None) or {})


def _grants_cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "personality_grants", None) or {})


def ensure_personality(player: MutableMapping[str, Any], reg: Optional[DataRegistry] = None) -> Dict[str, float]:
    traits = dict(player.get("personality") or {})
    for a in AXES:
        traits.setdefault(a, 0.0)
    for a in AXES:
        traits[a] = max(-100.0, min(100.0, float(traits[a])))
    player["personality"] = traits
    player.setdefault("personality_events", 0)
    player.setdefault("personality_points", 0)
    player.setdefault("personality_points_spent", 0)
    player.setdefault("personality_progress", {})
    player.setdefault("personality_grants_done", [])
    player.setdefault("personality_invest", {a: 0 for a in AXES})
    player.setdefault("personality_tips_read", [])
    player.setdefault("win_streak_no_flee", 0)
    if reg is not None and int(player.get("personality_points", 0)) == 0 and not player.get("_pers_start"):
        g = _grants_cfg(reg)
        start = int(g.get("points_on_start", 1))
        if start and not player.get("personality_grants_done"):
            # only apply start points once via flag
            if "start_points" not in (player.get("personality_grants_done") or []):
                player["personality_points"] = start
                player["personality_grants_done"] = list(player.get("personality_grants_done") or []) + [
                    "start_points"
                ]
        player["_pers_start"] = True
    return traits


def apply_event(
    player: MutableMapping[str, Any],
    event_id: str,
    reg: DataRegistry,
    scale: float = 1.0,
) -> List[str]:
    """Nudge personality from a gameplay event (hidden). May grant invest points."""
    ensure_personality(player, reg)
    cfg = _cfg(reg)
    deltas = (cfg.get("event_deltas") or {}).get(event_id) or {}
    notes: List[str] = []
    if deltas:
        traits = dict(player["personality"])
        for k, v in deltas.items():
            if k not in traits:
                continue
            traits[k] = max(-100.0, min(100.0, traits[k] + float(v) * scale))
        decay = float(cfg.get("decay_per_day", 0.02))
        for a in AXES:
            traits[a] *= 1.0 - decay * 0.15
        player["personality"] = traits
        player["personality_events"] = int(player.get("personality_events", 0)) + 1
        _refresh_labels(player, reg)

    # map events → hidden progress counters
    _bump_progress_from_event(player, event_id, reg)
    notes.extend(check_personality_point_grants(player, reg))
    return notes


def _bump_progress_from_event(
    player: MutableMapping[str, Any],
    event_id: str,
    reg: DataRegistry,
) -> None:
    prog = dict(player.get("personality_progress") or {})
    st = player.get("stats") or {}

    def add(key: str, n: int = 1) -> None:
        prog[key] = int(prog.get(key, 0)) + n

    if event_id in ("approach_polite", "approach_gift", "approach_aid"):
        add("approach_kind")
    if event_id == "approach_gift":
        add("gifts_given")
    if event_id == "combat_win":
        add("combat_wins")
        # streak if not broken by flee recently
        prog["win_streak_no_flee"] = int(prog.get("win_streak_no_flee", 0)) + 1
    if event_id == "combat_flee":
        prog["win_streak_no_flee"] = 0
    if event_id == "combat_combo":
        add("combos_used")
    if event_id == "explore":
        add("explore_count")
    if event_id == "library_visit":
        add("library_visits")
    if event_id == "combat_death":
        # sync deaths from stats if available
        prog["deaths"] = int(st.get("deaths", prog.get("deaths", 0)))
    # sync level / boss / quests from live stats
    prog["level_reached"] = max(int(prog.get("level_reached", 0)), int(player.get("level", 1)))
    prog["boss_kills"] = int(st.get("boss_kills", prog.get("boss_kills", 0)))
    prog["quests_done"] = max(
        int(prog.get("quests_done", 0)), len(player.get("quests_done") or [])
    )
    prog["deaths"] = int(st.get("deaths", prog.get("deaths", 0)))
    player["personality_progress"] = prog


def note_player_meet(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_personality(player, reg)
    prog = dict(player.get("personality_progress") or {})
    prog["player_meets"] = int(prog.get("player_meets", 0)) + 1
    player["personality_progress"] = prog
    return check_personality_point_grants(player, reg)


def check_personality_point_grants(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Hidden: award invest points when counters hit thresholds."""
    ensure_personality(player, reg)
    gcfg = _grants_cfg(reg)
    grants = list(gcfg.get("grants") or [])
    prog = dict(player.get("personality_progress") or {})
    # refresh synced counters
    st = player.get("stats") or {}
    prog["level_reached"] = max(int(prog.get("level_reached", 0)), int(player.get("level", 1)))
    prog["boss_kills"] = int(st.get("boss_kills", prog.get("boss_kills", 0)))
    prog["quests_done"] = max(int(prog.get("quests_done", 0)), len(player.get("quests_done") or []))
    prog["deaths"] = int(st.get("deaths", prog.get("deaths", 0)))
    player["personality_progress"] = prog

    done = list(player.get("personality_grants_done") or [])
    notes: List[str] = []
    max_unspent = int(gcfg.get("max_unspent", 12))
    pts = int(player.get("personality_points", 0))

    for g in grants:
        gid = str(g.get("id") or "")
        counter = str(g.get("counter") or "")
        need = int(g.get("need", 1))
        award = int(g.get("points", 1))
        once = bool(g.get("once", True))
        every = g.get("every")
        val = int(prog.get(counter, 0))

        if once:
            if gid in done:
                continue
            if val >= need:
                if pts + award > max_unspent:
                    award = max(0, max_unspent - pts)
                if award <= 0:
                    continue
                player["personality_points"] = pts + award
                pts += award
                done.append(gid)
                notes.append(
                    "✦ รู้สึกถึงช่องว่างในใจเปิดขึ้น... (ได้แต้มนิสัย — ไม่รู้ว่าเพราะอะไร)"
                )
        else:
            # repeatable every N
            if not every:
                continue
            every = int(every)
            # use grant marker count
            marker = f"{gid}#{val // every}"
            if val >= every and marker not in done and val % every == 0:
                if pts + award > max_unspent:
                    award = max(0, max_unspent - pts)
                if award <= 0:
                    continue
                player["personality_points"] = pts + award
                pts += award
                done.append(marker)
                notes.append("✦ เส้นทางนิสัยขยายอีกนิด... (ได้แต้มนิสัย)")

    player["personality_grants_done"] = done
    return notes


def invest_personality_point(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    axis: str,
    points: int = 1,
) -> str:
    """Player-visible: spend points to push a trait toward its high pole."""
    ensure_personality(player, reg)
    if axis not in AXES:
        return "แกนนิสัยไม่ถูกต้อง"
    points = max(1, int(points))
    have = int(player.get("personality_points", 0))
    if have < points:
        return "แต้มนิสัยไม่พอ (หาเอง — ระบบไม่บอกวิธี)"
    gcfg = _grants_cfg(reg)
    delta = float(gcfg.get("invest_delta", 4.0)) * points
    traits = dict(player["personality"])
    traits[axis] = max(-100.0, min(100.0, float(traits.get(axis, 0)) + delta))
    player["personality"] = traits
    player["personality_points"] = have - points
    inv = dict(player.get("personality_invest") or {})
    inv[axis] = int(inv.get(axis, 0)) + points
    player["personality_invest"] = inv
    player["personality_points_spent"] = int(player.get("personality_points_spent", 0)) + points
    _refresh_labels(player, reg)
    # show only investment, not raw value
    labels = {a["id"]: a for a in (_cfg(reg).get("axes") or []) if a.get("id")}
    nice = (labels.get(axis) or {}).get("high_label") or axis
    return (
        f"ลงทุนนิสัยไปทาง「{nice}」×{points} "
        f"(ลงทุนสะสม {inv[axis]}) · เหลือแต้ม {player['personality_points']}"
    )


def roll_personality_library_tip(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Library fragment system for personality:
    - often partial (fragment)
    - sometimes wrong (rumor)
    - rarely complete accurate guide
    """
    tips = list((getattr(reg, "personality_tips", None) or {}).values())
    if not tips:
        return []
    cfg_tip = None
    # tip meta may live as non-id file fields — stored on first load as separate
    meta = getattr(reg, "personality_tips_meta", None) or {}
    chance = float(meta.get("personality_tip_chance", 0.55))
    rng = rng or random.Random(int(player.get("latent_seed", 1)) + int(player.get("time_units", 0)))
    if rng.random() > chance:
        return []

    # weight pick, prefer unread
    read = set(player.get("personality_tips_read") or [])
    pool = [t for t in tips if t.get("id") not in read] or tips
    weights = [max(1, int(t.get("weight", 10))) for t in pool]
    total = sum(weights)
    roll = rng.randint(1, total)
    acc = 0
    chosen = pool[0]
    for t, w in zip(pool, weights):
        acc += w
        if roll <= acc:
            chosen = t
            break

    tid = str(chosen.get("id") or "")
    if tid:
        read.add(tid)
        player["personality_tips_read"] = list(read)

    kind = str(chosen.get("kind") or "fragment")
    notes = [f"📖 {chosen.get('title', 'บันทึกนิสัย')}"]
    if kind == "fragment":
        notes.append("  (ข้อมูลไม่ครบ — ต้องเดาต่อเอง)")
    elif kind == "rumor":
        notes.append("  (อาจเป็นข่าวลือ — ไม่การันตีความจริง)")
    elif kind == "complete":
        notes.append("  ✦ โชคดี: ข้อมูลชุดนี้ดูครบถ้วนผิดปกติ")
    body = str(chosen.get("body") or "").strip()
    for line in body.splitlines():
        if line.strip():
            notes.append(f"   {line.strip()}")
    return notes


def _refresh_labels(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    cfg = _cfg(reg)
    thr = float(cfg.get("label_threshold", 35))
    axes_meta = {a["id"]: a for a in (cfg.get("axes") or []) if a.get("id")}
    labels = []
    traits = player.get("personality") or {}
    for a in AXES:
        val = float(traits.get(a, 0))
        meta = axes_meta.get(a) or {}
        if val >= thr:
            labels.append(str(meta.get("high_label") or a))
        elif val <= -thr:
            labels.append(str(meta.get("low_label") or a))
    player["personality_labels"] = labels[:4]  # soft public impression


def soft_impression(player: Mapping[str, Any]) -> str:
    labels = player.get("personality_labels") or []
    if not labels:
        return "ยังอ่านไม่ออก"
    return " · ".join(str(x) for x in labels)


def trait_vector(player: Mapping[str, Any]) -> List[float]:
    t = player.get("personality") or {}
    return [float(t.get(a, 0)) / 100.0 for a in AXES]


def compatibility(
    self_p: Mapping[str, Any],
    other: Mapping[str, Any],
    reg: DataRegistry,
    *,
    other_is_npc: bool = False,
    npc_archetype: Optional[str] = None,
    approach_id: Optional[str] = None,
) -> float:
    """
    Hidden compatibility score roughly -1..+1 then scaled.
    Higher = easier friend / better deals / teach success.
    """
    ensure_personality(self_p if isinstance(self_p, dict) else dict(self_p), reg)  # type: ignore
    va = trait_vector(self_p)
    score = 0.0

    if other_is_npc and npc_archetype:
        arch = (getattr(reg, "npc_archetypes", None) or {}).get(npc_archetype) or {}
        prefers = arch.get("prefers") or {}
        dislikes = arch.get("dislikes") or {}
        # preference: player high on preferred axes is good
        for ax, pref in prefers.items():
            if ax not in AXES:
                continue
            pval = float((self_p.get("personality") or {}).get(ax, 0))
            # want player trait aligned with preferred sign of pref
            score += (pval / 100.0) * (float(pref) / 40.0)
        for ax, bad in dislikes.items():
            if ax == "threaten":
                if approach_id == "threaten":
                    score -= 0.8
                continue
            if ax not in AXES:
                continue
            pval = float((self_p.get("personality") or {}).get(ax, 0))
            # high dislike axis on player is bad
            score -= max(0.0, pval / 100.0) * (float(bad) / 50.0)
        if approach_id == "threaten" and dislikes.get("threaten"):
            score -= 0.5
    else:
        # player-echo: cosine similarity of personality
        vb = trait_vector(other)
        # map -1..1 traits: similarity of direction
        dot = sum(x * y for x, y in zip(va, vb))
        na = math.sqrt(sum(x * x for x in va)) or 1.0
        nb = math.sqrt(sum(x * x for x in vb)) or 1.0
        cos = dot / (na * nb)
        score = cos  # -1..1
        # opposite aggression vs kindness clash
        sa = float((self_p.get("personality") or {}).get("aggression", 0))
        oa = float((other.get("personality") or {}).get("aggression", 0))
        sk = float((self_p.get("personality") or {}).get("kindness", 0))
        ok = float((other.get("personality") or {}).get("kindness", 0))
        if sa > 40 and ok > 40:
            score -= 0.25
        if sk > 40 and oa > 40:
            score -= 0.15
        if sk > 30 and ok > 30:
            score += 0.2

    return max(-1.5, min(1.5, score))


def compatibility_to_affinity_bonus(comp: float) -> float:
    """Map -1.5..1.5 → affinity points for social system."""
    return comp * 22.0


def npc_roll_modifier(
    player: Mapping[str, Any],
    reg: DataRegistry,
    archetype: str,
    approach_id: str,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    Returns hidden modifiers for NPC resolution.
    friend_bias: added to friend chance / outcome weights
    """
    comp = compatibility(
        player, {}, reg, other_is_npc=True, npc_archetype=archetype, approach_id=approach_id
    )
    arch = (getattr(reg, "npc_archetypes", None) or {}).get(archetype) or {}
    return {
        "compatibility": comp,
        "friend_bias": comp * 0.35,
        "shop_discount": float(arch.get("shop_discount_if_friend", 0.1)) if comp > 0.35 else 0.0,
        "shop_surcharge": float(arch.get("shop_surcharge_if_foe", 0.15)) if comp < -0.35 else 0.0,
        "teach_bonus": bool(arch.get("teach_bonus_if_friend")) and comp > 0.3,
        "ambush_bias": float(arch.get("ambush_bias_if_foe", 0.0)) if comp < -0.2 else 0.0,
        "library_hint": bool(arch.get("library_hint_if_friend")) and comp > 0.4,
    }


def format_personality_panel(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> List[str]:
    """Sectioned personality overview (soft — no raw axis numbers)."""
    labels = player.get("personality_labels") or []
    pts = int(player.get("personality_points") or 0)
    inv = player.get("personality_invest") or {}
    lines: List[str] = [
        " นิสัย",
        "---",
        f" แต้มลงทุนได้  {pts}",
    ]
    if labels:
        lines.append(f" ภาพที่สังเกต  {' · '.join(str(x) for x in labels)}")
    else:
        lines.append(" ภาพที่สังเกต  ยังอ่านไม่ออก")

    # show investment counts only (not raw -100..100)
    invested: List[str] = []
    meta = {}
    if reg:
        meta = {x["id"]: x for x in (_cfg(reg).get("axes") or []) if x.get("id")}
    for a in AXES:
        n = int(inv.get(a, 0))
        if n > 0:
            lab = (meta.get(a) or {}).get("high_label") or a
            invested.append((lab, n))
    if invested:
        lines.append("---")
        lines.append(" ลงทุนแล้ว")
        for lab, n in invested:
            filled = min(8, n)
            bar = "█" * filled + "░" * (8 - filled)
            lines.append(f"  {lab:<8}  [{bar}]  ×{n}")

    lines.append("---")
    lines.append(" หมายเหตุ soft")
    lines.append("  · วิธีได้แต้ม: ค้นเอง / ห้องสมุดใบ้ไม่ครบ")
    lines.append("  · ตัวเลขแกน · เงื่อนไข · สูตร — ซ่อนทั้งหมด")
    return lines


def format_personality_menu_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Numbered invest choices for personality axes."""
    axes = personality_allocate_menu_axes(reg)
    inv = player.get("personality_invest") or {}
    lines: List[str] = [
        " ลงทุนทางใด",
        "---",
        " ดันไปขั้ว「สูง」ของแกน (soft)",
        "---",
    ]
    for i, (aid, lab) in enumerate(axes, 1):
        inv_n = int(inv.get(aid, 0))
        tag = f"  ×{inv_n}" if inv_n else ""
        lines.append(f"  {i}  {lab}{tag}")
    lines.extend(
        [
            "---",
            "  0  กลับ",
            "---",
            f" พิมพ์ 1–{len(axes)} แล้วใส่จำนวนแต้ม",
        ]
    )
    return lines


def personality_allocate_menu_axes(reg: DataRegistry) -> List[Tuple[str, str]]:
    """Return (axis_id, high_label) for invest UI."""
    meta = {x["id"]: x for x in (_cfg(reg).get("axes") or []) if x.get("id")}
    out = []
    for a in AXES:
        lab = (meta.get(a) or {}).get("high_label") or a
        out.append((a, str(lab)))
    return out

