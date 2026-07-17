"""
Dungeon runs v2 — depth scaling, floor bosses, free exit, boss-only shard escape.
Hidden difficulty / max depth; soft anti-spoiler labels only.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def _cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "dungeons_cfg", None) or {})


def all_dungeons(reg: DataRegistry) -> List[Dict[str, Any]]:
    raw = _cfg(reg).get("dungeons") or []
    return [dict(d) for d in raw if isinstance(d, dict) and d.get("id")]


def dungeon_by_id(reg: DataRegistry, dungeon_id: str) -> Optional[Dict[str, Any]]:
    for d in all_dungeons(reg):
        if str(d.get("id")) == str(dungeon_id):
            return d
    return None


def dungeons_for_area(reg: DataRegistry, area_id: str) -> List[Dict[str, Any]]:
    return [d for d in all_dungeons(reg) if str(d.get("area_id")) == str(area_id)]


def ensure_dungeon_state(player: MutableMapping[str, Any]) -> None:
    player.setdefault("dungeon_run", None)
    player.setdefault("dungeon_knowledge", {})
    player.setdefault("dungeons_cleared", [])
    try:
        from game.domain.situation import ensure_situation_fields

        ensure_situation_fields(player)
    except Exception:
        pass


def in_dungeon(player: Mapping[str, Any]) -> bool:
    run = player.get("dungeon_run")
    return isinstance(run, dict) and bool(run.get("dungeon_id"))


def get_run(player: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    run = player.get("dungeon_run")
    return dict(run) if isinstance(run, dict) else None


def knowledge_entry(player: Mapping[str, Any], dungeon_id: str) -> Dict[str, Any]:
    know = dict(player.get("dungeon_knowledge") or {})
    return dict(know.get(dungeon_id) or {"visits": 0, "clears": 0, "fails": 0, "escapes": 0})


def _bump_knowledge(
    player: MutableMapping[str, Any],
    dungeon_id: str,
    *,
    visits: int = 0,
    clears: int = 0,
    fails: int = 0,
    escapes: int = 0,
) -> None:
    know = dict(player.get("dungeon_knowledge") or {})
    e = dict(know.get(dungeon_id) or {"visits": 0, "clears": 0, "fails": 0, "escapes": 0})
    e["visits"] = int(e.get("visits", 0)) + visits
    e["clears"] = int(e.get("clears", 0)) + clears
    e["fails"] = int(e.get("fails", 0)) + fails
    e["escapes"] = int(e.get("escapes", 0)) + escapes
    know[dungeon_id] = e
    player["dungeon_knowledge"] = know


def soft_difficulty_text(
    player: Mapping[str, Any],
    reg: DataRegistry,
    dungeon: Mapping[str, Any],
) -> str:
    """Never show numeric difficulty — only soft labels from knowledge."""
    cfg = _cfg(reg)
    kcfg = cfg.get("knowledge") or {}
    need_v = int(kcfg.get("soft_label_visits") or 2)
    need_c = int(kcfg.get("accurate_after_clears") or 1)
    kid = str(dungeon.get("id"))
    e = knowledge_entry(player, kid)
    labels = dungeon.get("soft_labels") or {}
    if int(e.get("clears", 0)) >= need_c:
        return str(labels.get("accurate") or labels.get("known") or "เคยเผชิญมา")
    if int(e.get("visits", 0)) >= need_v:
        return str(labels.get("known") or labels.get("vague") or "อันตราย…?")
    return str(labels.get("vague") or "ไม่รู้ว่าอันตรายแค่ไหน")


def roll_dungeon_sight(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    area_id: str,
) -> Optional[Dict[str, Any]]:
    """Maybe return a sight dict for a dungeon entrance."""
    if in_dungeon(player):
        return None
    pool = dungeons_for_area(reg, area_id)
    if not pool:
        return None
    chance = float(_cfg(reg).get("appear_chance") or 0.18)
    if rng.random() > chance:
        return None
    weights = [max(1, int(d.get("appear_weight") or 10)) for d in pool]
    total = sum(weights)
    r = rng.randint(1, total)
    acc = 0
    chosen = pool[0]
    for d, w in zip(pool, weights):
        acc += w
        if r <= acc:
            chosen = d
            break
    soft = soft_difficulty_text(player, reg, chosen)
    return {
        "kind": "dungeon",
        "label": str(chosen.get("name") or "ปากถ้ำ"),
        "hint": soft,
        "dungeon_id": chosen.get("id"),
        "risk": "?",
        "known": False,
    }


def _scan_escape_items(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Tuple[str, float]]:
    """Items currently in bag that can act as escape tokens (id, chance)."""
    cfg = (_cfg(reg).get("escape") or {})
    table = list(cfg.get("items") or [])
    bag = set(player.get("inventory_ids") or [])
    out = []
    for row in table:
        iid = str(row.get("id") or "")
        if iid and iid in bag:
            out.append((iid, float(row.get("success_chance") or 0.4)))
    return out


def roll_max_depth(reg: DataRegistry, dungeon: Mapping[str, Any], rng: random.Random) -> int:
    """
    Hidden ceiling for this run — never shown as /N in UI.
    v2.1: longer runs — heart is late so players can gear/loot first.
    """
    depth_cfg = dict(dungeon.get("depth") or {})
    floors_legacy = int(dungeon.get("floors") or 2)
    diff = int(dungeon.get("difficulty") or 2)
    # default: soft dungeons 4–7 floors, hard 6–10 (was ~2–4)
    default_min = max(4, floors_legacy + 1 + diff // 2)
    default_max = max(default_min + 2, floors_legacy + 3 + diff)
    default_cap = max(default_max + 2, 8 + diff)
    base_min = int(depth_cfg.get("base_min") or default_min)
    base_max = int(depth_cfg.get("base_max") or default_max)
    hard_cap = int(depth_cfg.get("hard_cap") or default_cap)
    if base_max < base_min:
        base_max = base_min
    rolled = rng.randint(base_min, base_max)
    return max(4, min(hard_cap, rolled))


def current_depth(run: Mapping[str, Any]) -> int:
    return int(run.get("depth") or run.get("floor") or 1)


def max_depth_hidden(run: Mapping[str, Any]) -> int:
    return int(run.get("max_depth_hidden") or run.get("floors") or 2)


def is_boss_encounter_active(player: Mapping[str, Any]) -> bool:
    run = get_run(player)
    return bool(run and run.get("boss_encounter_active"))


def set_boss_encounter(player: MutableMapping[str, Any], active: bool) -> None:
    run = player.get("dungeon_run")
    if not isinstance(run, dict):
        return
    run = dict(run)
    run["boss_encounter_active"] = bool(active)
    player["dungeon_run"] = run


def count_escape_shards(player: Mapping[str, Any], reg: DataRegistry) -> List[Tuple[str, float, str]]:
    """(id, chance, display_name) for escape items currently in bag."""
    rows = _scan_escape_items(player, reg)
    out: List[Tuple[str, float, str]] = []
    for iid, chance in rows:
        nm = str((reg.items.get(iid) or {}).get("name") or iid)
        out.append((iid, chance, nm))
    return out


def begin_dungeon(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    dungeon_id: str,
    rng: random.Random,
) -> List[str]:
    """Enter dungeon — free walk-out; floor bosses gate depth; max depth hidden."""
    ensure_dungeon_state(player)
    if in_dungeon(player):
        return ["คุณอยู่ในดันเจียนอยู่แล้ว"]
    d = dungeon_by_id(reg, dungeon_id)
    if not d:
        return ["ไม่พบทางเข้า"]
    notes: List[str] = []
    escape_tokens = _scan_escape_items(player, reg)
    snap = {
        "money_world": int(player.get("money_world") or 0),
        "money_heaven": int(player.get("money_heaven") or 0),
        "money_hell": int(player.get("money_hell") or 0),
        "inv_count": len(player.get("inventory_ids") or []),
    }
    diff = int(d.get("difficulty") or 2)
    max_d = roll_max_depth(reg, d, rng)
    # v2: time collapse off by default (free exit design)
    tl = _cfg(reg).get("time_limit") or {}
    time_on = bool(tl.get("enabled", False))
    turns_max = compute_time_limit(reg, d) if time_on else 999
    layout = generate_floor_layout(reg, d, 1, rng)
    player["dungeon_run"] = {
        "dungeon_id": dungeon_id,
        "name": d.get("name"),
        "area_id": d.get("area_id"),
        "floor": 1,
        "floors": max_d,  # legacy alias = hidden max
        "depth": 1,
        "max_depth_hidden": max_d,
        "boss_id": d.get("boss_id"),
        "locked": False,  # v2 free exit
        "boss_defeated": False,
        "floor_boss_cleared": False,
        "boss_encounter_active": False,
        "auto_boss_depths": [],  # depths where boss was beaten → auto rematch ok
        "rewards_granted": False,
        "escape_ready": bool(escape_tokens),
        "escape_items": [t[0] for t in escape_tokens],
        "escape_chances": {t[0]: t[1] for t in escape_tokens},
        "snapshot": snap,
        "enemy_hp_mult": float(d.get("enemy_hp_mult") or 1.2),
        "enemy_atk_mult": float(d.get("enemy_atk_mult") or 1.15),
        "difficulty_hidden": diff,
        "fights_this_floor": 0,
        "path_progress": 0,
        "empty_streak": 0,
        "time_collapse_enabled": time_on,
        "turns_left": turns_max,
        "turns_max": turns_max,
        "floor_layout": layout,
        "floor_layouts": {1: layout},
        "ruleset": "v2",
    }
    player["location_before_dungeon"] = player.get("location")
    player["location"] = f"dungeon:{dungeon_id}"
    _bump_knowledge(player, dungeon_id, visits=1)
    notes.append(f"คุณก้าวเข้า「{d.get('name')}」— โพรงมืดไม่รู้จบ")
    notes.append(" (ยังไม่รู้ว่าอันตรายแค่ไหน — ต้องสังเกตเอง)")
    notes.append(f" ภูมิชั้นนี้: {layout.get('label')} — {layout.get('desc')}")
    notes.append(" เดินออกได้ทุกเมื่อ · ยกเว้นตอนท้าทายผู้เฝ้าชั้น")
    notes.append(" ต้องกำจัดผู้เฝ้าชั้น ถึงจะลงลึกกว่านี้ได้")
    notes.append(" โพรงลึก — หัวใจดันอยู่ไกล เก็บของ/พัก/ร้านเงาก่อนท้าได้")
    notes.append(" (7 กระเป๋า · 8 ร้านเงา · 9 พัก — นอนอาจถูกซุ่มถ้าไม่มีของกลืนเงา)")
    if escape_tokens:
        notes.append(" …มีเศษ/ของในกระเป๋า — อาจใช้หนีตอนไฟต์บอสได้")
    else:
        notes.append(" …ไม่มีเศษหนี — ท้าบอสเมื่อมั่นใจว่าชนะได้")
    notes.append(f" ลงมาชั้นที่ 1 · ปาร์ตี้ {len(player.get('party') or [])}/3")
    try:
        from game.domain.situation import sync_situation_from_dungeon

        sync_situation_from_dungeon(player, preserve_help=False)
        notes.append(" …ถ้าตึงเครียด อาจเปิดสัญญาณขอแรงได้")
    except Exception:
        pass
    return notes


def compute_time_limit(reg: DataRegistry, dungeon: Mapping[str, Any]) -> int:
    """Hidden turn budget — never shown as raw number in UI."""
    tl = _cfg(reg).get("time_limit") or {}
    base = int(tl.get("base_turns") or 14)
    per_f = int(tl.get("per_floor") or 4)
    per_d = int(tl.get("per_difficulty") or 2)
    floors = int(dungeon.get("floors") or 2)
    diff = int(dungeon.get("difficulty") or 2)
    # harder dungeons get a bit more time but still tight
    return max(8, base + per_f * floors + per_d * diff)


def generate_floor_layout(
    reg: DataRegistry,
    dungeon: Mapping[str, Any],
    floor: int,
    rng: random.Random,
) -> Dict[str, Any]:
    """Soft random 'map' for this floor — flavor + tag, not a grid."""
    layouts = list(_cfg(reg).get("floor_layouts") or [])
    if not layouts:
        return {"id": "winding", "label": "ทางคดเคี้ยว", "desc": "ทางคดไม่รู้จบ"}
    bias = list(dungeon.get("layout_bias") or [])
    pool = []
    for L in layouts:
        lid = str(L.get("id"))
        w = 3 + (5 if lid in bias else 0)
        # deeper floors prefer harsher layouts
        if floor >= 3 and lid in ("void", "collapse", "choke"):
            w += 3
        pool.append((L, w))
    total = sum(w for _, w in pool)
    r = rng.randint(1, max(1, total))
    acc = 0
    chosen = pool[0][0]
    for L, w in pool:
        acc += w
        if r <= acc:
            chosen = L
            break
    descs = {
        "winding": "ทางแยกซ้ำ — ง่ายต่อการหลง",
        "chamber": "พื้นที่เปิด ศัตรูเห็นคุณก่อน",
        "choke": "ทางแคบ หนีลำบาก",
        "collapse": "ซากพัง — กับดักได้",
        "shrine": "แท่นเก่า อาจได้หรือเสีย",
        "pool": "ชื้นและเย็น พิษลอย",
        "crystal": "แสงสะท้อน มึนและคม",
        "void": "ทิศทางหาย เวลาถูกล้อม",
    }
    lid = str(chosen.get("id"))
    return {
        "id": lid,
        "label": str(chosen.get("label") or lid),
        "desc": descs.get(lid, "ภูมิประเทศเปลี่ยน"),
        "floor": floor,
    }


def _bump_path_progress(player: MutableMapping[str, Any], amount: int = 1) -> int:
    """Track floor path knowledge; returns new total."""
    run = player.get("dungeon_run")
    if not isinstance(run, dict):
        return 0
    run = dict(run)
    total = int(run.get("path_progress") or 0) + max(0, int(amount))
    run["path_progress"] = total
    player["dungeon_run"] = run
    return total


def _bump_area_mastery_for_run(player: MutableMapping[str, Any], run: Mapping[str, Any], amount: int = 1) -> int:
    """Raise mastery on host area (+ dungeon key) so status UI can show progress."""
    am = dict(player.get("area_mastery") or {})
    aid = str(run.get("area_id") or "dark_forest")
    am[aid] = min(100, int(am.get(aid, 0) or 0) + amount)
    did = str(run.get("dungeon_id") or "")
    if did:
        dkey = f"dungeon:{did}"
        am[dkey] = min(100, int(am.get(dkey, 0) or 0) + amount)
    player["area_mastery"] = am
    return int(am.get(aid, 0))


def explore_floor_event(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    Resolve one explore action inside dungeon.
    Returns {kind, flavor, notes, trigger_combat, loot, rest_hp, trap_dmg}
    Always advances path_progress so floor is not soft-locked on empty rolls.
    """
    run = get_run(player)
    if not run:
        return {"kind": "empty", "flavor": "…", "notes": ["ไม่ได้อยู่ในดันเจียน"]}
    events = list(_cfg(reg).get("floor_events") or [])
    if not events:
        events = [{"id": "ambush", "weight": 1, "kind": "combat", "flavor": "ศัตรู!"}]
    # layout biases event weights slightly
    layout_id = str((run.get("floor_layout") or {}).get("id") or "")
    fights = int(run.get("fights_this_floor") or 0)
    empty_streak = int(run.get("empty_streak") or 0)
    # pity: after 2 non-combat explores with 0 fights, force a combat so floors advance
    force_combat = empty_streak >= 2 and fights <= 0
    weights = []
    for e in events:
        w = int(e.get("weight") or 1)
        kind = str(e.get("kind") or "empty")
        if layout_id == "choke" and kind == "combat":
            w += 8
        if layout_id == "collapse" and kind == "trap":
            w += 10
        if layout_id == "shrine" and kind in ("loot", "rest", "omen"):
            w += 8
        if layout_id == "pool" and kind == "trap":
            w += 6
        if layout_id == "void" and kind == "combat":
            w += 5
        # bias toward combat when floor has no fights yet
        if fights == 0 and kind == "combat":
            w += 12
        if force_combat:
            w = 100 if kind == "combat" else 0
        weights.append(w)
    total = sum(weights)
    if total <= 0:
        # fallback combat event
        chosen = next(
            (e for e in events if str(e.get("kind")) == "combat"),
            events[0],
        )
    else:
        r = rng.randint(1, max(1, total))
        acc = 0
        chosen = events[0]
        for e, w in zip(events, weights):
            acc += w
            if r <= acc:
                chosen = e
                break
    kind = str(chosen.get("kind") or "empty")
    flavor = str(chosen.get("flavor") or "")
    notes: List[str] = [flavor]
    if force_combat and kind == "combat":
        notes.insert(0, "เงาที่ขวางทางพุ่งเข้าใส่ — หลีกไม่พ้น!")
    result: Dict[str, Any] = {
        "kind": kind,
        "flavor": flavor,
        "notes": notes,
        "trigger_combat": kind == "combat",
        "loot": [],
        "rest_hp": 0,
        "trap_dmg": 0,
    }
    # every explore teaches the floor a bit
    path_total = _bump_path_progress(player, 1)
    run = get_run(player) or run

    if kind == "empty":
        _bump_area_mastery_for_run(player, run, 1)
        notes.append(" ชำนาญเส้นทาง +1")
    elif kind == "loot":
        # small cache — not full clear reward
        cache = [
            ("upgrade_mat", 0.5, "common"),
            ("potion_hp_small", 0.4, "common"),
            ("rare_mat", 0.15, "uncommon"),
        ]
        from game.domain.equipment import add_item

        for iid, chance, rar in cache:
            if rng.random() < chance and iid in (reg.items or {}):
                nm = add_item(player, iid, reg, rarity=rar)
                notes.append(f"  ได้ {nm}")
                result["loot"].append(iid)
        if not result["loot"]:
            notes.append("  หีบว่าง — เหลือแต่ฝุ่น")
        _bump_area_mastery_for_run(player, run, 1)
    elif kind == "rest":
        heal = 12 + rng.randint(0, 10)
        player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + heal)
        player["mana"] = min(int(player["max_mana"]), int(player.get("mana", 0)) + 8)
        result["rest_hp"] = heal
        notes.append(f"  ฟื้น HP+{heal} MP+8")
    elif kind == "trap":
        dmg = 8 + int(run.get("difficulty_hidden") or 2) * 3 + rng.randint(0, 8)
        # layout choke/collapse hurts more
        if layout_id in ("collapse", "choke", "void"):
            dmg = int(dmg * 1.25)
        player["hp"] = max(1, int(player["hp"]) - dmg)
        result["trap_dmg"] = dmg
        notes.append(f"  โดนกับดัก −{dmg} HP")
        if rng.random() < 0.25:
            from game.domain.status_fx import apply_status, status_display_name

            applied = apply_status(
                player, "poison", reg, rng, duration=2, source="dungeon_trap"
            )
            if applied:
                notes.append(f"  ติด{status_display_name(reg, applied)}!")
    elif kind == "omen":
        # knowledge tick without combat
        notes.append("  คุณจำความรู้สึกอันตรายนี้ได้ชัดขึ้น")
        _bump_knowledge(player, str(run.get("dungeon_id")), visits=0)
        _bump_area_mastery_for_run(player, run, 1)
    elif kind == "combat":
        _bump_area_mastery_for_run(player, run, 1)

    # track non-combat streak for pity combat
    run = dict(get_run(player) or {})
    if kind == "combat":
        run["empty_streak"] = 0
    else:
        run["empty_streak"] = int(run.get("empty_streak") or 0) + 1
    player["dungeon_run"] = run

    # soft hint if still blocked after this explore
    ok, why = can_advance_floor(player)
    if not ok and kind != "combat":
        notes.append(f"  …{why}")
    elif ok and path_total > 0:
        notes.append("  ทางลึกดูเหมือนจะเปิดแล้ว — ลอง (3) ลงลึก")
    return result


def tick_dungeon_time(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    cost: int = 1,
) -> List[str]:
    """Optional time pressure. v2 default: disabled (free-exit design)."""
    run = get_run(player)
    if not run:
        return []
    if not run.get("time_collapse_enabled"):
        return []
    notes: List[str] = []
    left = int(run.get("turns_left") or 0) - max(1, cost)
    run = dict(run)
    run["turns_left"] = left
    player["dungeon_run"] = run
    tl = _cfg(reg).get("time_limit") or {}
    warn = int(tl.get("warn_at") or 5)
    crit = int(tl.get("critical_at") or 2)
    if left <= 0:
        notes.append("มิติดันเจียนยุบตัว! คุณถูกบีบออกมา...")
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="time_out"))
        _bump_knowledge(player, str(run.get("dungeon_id")), fails=1)
        notes.extend(exit_dungeon(player, reg, success=False, escaped=True))
        return notes
    if left <= crit:
        notes.append("⚠ แรงกดจากผนัง/เงารุนแรง — เวลาราวจะหมด (ไม่รู้ว่าเหลือเท่าไหร่)")
        mon_mult = float(run.get("enemy_atk_mult") or 1.15) * 1.05
        run["enemy_atk_mult"] = mon_mult
        player["dungeon_run"] = run
    elif left <= warn:
        notes.append("…อากาศเปลี่ยน — รู้สึกว่าอยู่ได้อีกไม่นาน")
    return notes


def grant_dungeon_clear_rewards(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> List[str]:
    """Unique rewards when boss defeated (once per run)."""
    run = get_run(player)
    if not run or run.get("rewards_granted"):
        return []
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    rewards = dict(d.get("rewards") or _cfg(reg).get("default_rewards") or {})
    notes = ["── รางวัลดันเจียน ──"]
    from game.domain.equipment import add_item
    from game.domain.leveling import grant_xp

    # money ranges
    for key, label in (
        ("money_world", "เงินโลก"),
        ("money_heaven", "เงินสวรรค์"),
        ("money_hell", "เงินนรก"),
    ):
        rng_pair = rewards.get(key)
        if not rng_pair:
            continue
        if isinstance(rng_pair, (list, tuple)) and len(rng_pair) >= 2:
            lo, hi = int(rng_pair[0]), int(rng_pair[1])
            amt = rng.randint(lo, max(lo, hi))
        else:
            amt = int(rng_pair)
        if amt > 0:
            player[key] = int(player.get(key) or 0) + amt
            notes.append(f"  +{amt} {label}")
    # xp
    xp_pair = rewards.get("xp")
    if xp_pair:
        if isinstance(xp_pair, (list, tuple)) and len(xp_pair) >= 2:
            xp = rng.randint(int(xp_pair[0]), max(int(xp_pair[0]), int(xp_pair[1])))
        else:
            xp = int(xp_pair)
        if xp > 0:
            summary = grant_xp(player, xp, reg.levels)
            notes.append(f"  XP +{summary.get('gained', xp)}")
            for n in summary.get("notes") or []:
                notes.append(f"  {n}")
    # items
    for row in rewards.get("items") or []:
        if not isinstance(row, dict):
            continue
        iid = str(row.get("id") or "")
        if not iid or iid not in (reg.items or {}) and iid not in (reg.cards or {}):
            continue
        if rng.random() > float(row.get("chance") or 0.5):
            continue
        rar = str(row.get("rarity") or "common")
        nm = add_item(player, iid, reg, rarity=rar)
        notes.append(f"  ของดันเจียน: {nm}")
    run = dict(player.get("dungeon_run") or {})
    run["rewards_granted"] = True
    player["dungeon_run"] = run
    if len(notes) == 1:
        notes.append("  (รางวัลเบาบาง — โชคยังไม่เข้าข้าง)")
    return notes


def apply_dungeon_enemy_mods(mon: MutableMapping[str, Any], player: Mapping[str, Any]) -> Dict[str, Any]:
    """Scale monster by dungeon bias + depth (hidden formulas)."""
    run = get_run(player)
    if not run:
        return dict(mon)
    mon = dict(mon)
    depth = current_depth(run)
    hp_m = float(run.get("enemy_hp_mult") or 1.2)
    atk_m = float(run.get("enemy_atk_mult") or 1.15)
    # depth curves (v2)
    hp_m *= 1.0 + 0.10 * (depth - 1)
    atk_m *= 1.0 + 0.08 * (depth - 1)
    if mon.get("dungeon_floor_boss") or mon.get("dungeon_boss"):
        hp_m *= 1.55 + 0.12 * (depth - 1)
        atk_m *= 1.28 + 0.08 * (depth - 1)
    mon["hp"] = max(1, int(round(int(mon.get("hp") or 1) * hp_m)))
    mon["max_hp"] = max(1, int(round(int(mon.get("max_hp") or mon["hp"]) * hp_m)))
    mon["atk"] = max(1, int(round(int(mon.get("atk") or 1) * atk_m)))
    # level soft scale
    base_lv = int(mon.get("level") or 1)
    mon["level"] = max(1, base_lv + (depth - 1))
    xp_m = float(mon.get("xp_mult") or 1.0) * (1.0 + 0.12 * (depth - 1))
    if mon.get("dungeon_floor_boss") or mon.get("dungeon_boss"):
        xp_m *= 1.35
    mon["xp_mult"] = xp_m
    profiles = []
    for p in mon.get("attack_profiles") or []:
        p = dict(p)
        if "power" in p:
            p["power"] = max(1, int(round(int(p["power"]) * atk_m)))
        profiles.append(p)
    if profiles:
        mon["attack_profiles"] = profiles
    mon["dungeon_modded"] = True
    mon["dungeon_depth"] = depth
    return mon


def note_dungeon_fight(player: MutableMapping[str, Any]) -> None:
    run = player.get("dungeon_run")
    if not isinstance(run, dict):
        return
    run = dict(run)
    run["fights_this_floor"] = int(run.get("fights_this_floor") or 0) + 1
    player["dungeon_run"] = run


def floor_clear_need(run: Mapping[str, Any]) -> int:
    """Legacy explore score threshold (kept for tests / soft progress)."""
    diff = int(run.get("difficulty_hidden") or 2)
    return max(2, 1 + (diff + 1) // 2)


def floor_clear_score(run: Mapping[str, Any]) -> int:
    fights = int(run.get("fights_this_floor") or 0)
    path = int(run.get("path_progress") or 0)
    return fights * 2 + path


def can_advance_floor(player: Mapping[str, Any]) -> Tuple[bool, str]:
    """v2: must clear floor boss (ผู้เฝ้าชั้น) to go deeper."""
    run = get_run(player)
    if not run:
        return False, "ไม่ได้อยู่ในดันเจียน"
    if run.get("boss_encounter_active"):
        return False, "ยังติดวงบอส — จบไฟต์ก่อน"
    if run.get("floor_boss_cleared") or run.get("boss_defeated"):
        depth = current_depth(run)
        mx = max_depth_hidden(run)
        if depth >= mx:
            return False, "มิติดันจบที่นี่ — ทางลงปิด (เดินออกได้)"
        return True, "ok"
    if int(run.get("path_progress") or 0) == 0 and int(run.get("fights_this_floor") or 0) == 0:
        return False, "ทางลึกยังมืด — สำรวจชั้น แล้วท้าทายผู้เฝ้าชั้น"
    return False, "ผู้เฝ้าชั้นยังขวางทาง — ต้องกำจัดก่อนลงลึก"


def advance_floor(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
) -> List[str]:
    run = get_run(player)
    if not run:
        return ["ไม่ได้อยู่ในดันเจียน"]
    ok, why = can_advance_floor(player)
    if not ok:
        return [why]
    depth = current_depth(run) + 1
    mx = max_depth_hidden(run)
    run = dict(run)
    if depth > mx:
        return ["มิติดันจบที่นี่ — ไม่มีทางลงอีก (เดินออกได้)"]
    rng = rng or random.Random()
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    layout = generate_floor_layout(reg, d, depth, rng)
    run["floor"] = depth
    run["depth"] = depth
    run["fights_this_floor"] = 0
    run["path_progress"] = 0
    run["empty_streak"] = 0
    run["floor_boss_cleared"] = False
    run["boss_encounter_active"] = False
    run["floor_layout"] = layout
    layouts = dict(run.get("floor_layouts") or {})
    layouts[depth] = layout
    run["floor_layouts"] = layouts
    player["dungeon_run"] = run
    notes = [
        f"คุณลงลึกกว่าเดิม... อากาศเปลี่ยน (ลงมาชั้นที่ {depth})",
        f" ภูมิชั้นใหม่: {layout.get('label')} — {layout.get('desc')}",
        " ผู้เฝ้าชั้นใหม่ขวางทาง — ต้องกำจัดก่อนลงต่อ",
    ]
    if depth >= mx:
        notes.append(" …รู้สึกว่าใกล้จุดจบของโพรงนี้")
    return notes


def spawn_floor_boss(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    """
    Floor warden or heart boss at hidden max depth.
    Sets flags for combat (caller should set boss_encounter_active).
    """
    run = get_run(player)
    if not run:
        return None
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    depth = current_depth(run)
    mx = max_depth_hidden(run)
    area_id = str(run.get("area_id") or "dark_forest")
    is_heart = depth >= mx
    boss: Optional[Dict[str, Any]] = None

    if is_heart:
        from game.domain.boss import spawn_boss

        boss_id = str(run.get("boss_id") or d.get("boss_id") or "")
        boss = spawn_boss(reg, area_id, rng)
        if not boss and boss_id and boss_id in (reg.monsters or {}):
            base = reg.monsters[boss_id]
            boss = {
                "id": boss_id,
                "name": base.get("name") or boss_id,
                "level": int(base.get("level_min") or 10),
                "hp": int(base.get("hp_base") or 200),
                "max_hp": int(base.get("hp_base") or 200),
                "atk": int(base.get("atk_base") or 20),
                "elements": list(base.get("elements") or ["physical"]),
                "xp_mult": float(base.get("xp_mult") or 3),
                "attack_profiles": [],
                "statuses": [],
                "boss": True,
            }
        if boss:
            boss["dungeon_boss"] = True
            boss["dungeon_heart_boss"] = True
            boss["dungeon_floor_boss"] = True
            boss["boss"] = True
            boss["never_flee"] = True
    else:
        from game.domain.combat import pick_monster

        mon = pick_monster(reg, area_id, rng)
        mon = dict(mon)
        mon["boss"] = True
        mon["dungeon_floor_boss"] = True
        mon["never_flee"] = True
        mon["intel_tier"] = max(2, int(mon.get("intel_tier") or 1) + 1)
        # soft name — not full spoiler
        base_name = str(mon.get("name") or "เงา")
        mon["base_name"] = base_name
        mon["name"] = f"ผู้เฝ้าชั้น · {base_name}"
        mon["xp_mult"] = float(mon.get("xp_mult") or 1.0) * 1.8
        mon["hp"] = int(int(mon.get("hp") or 50) * 1.45)
        mon["max_hp"] = mon["hp"]
        mon["atk"] = int(int(mon.get("atk") or 8) * 1.25)
        boss = mon

    if not boss:
        return None
    # mods applied once in combat_session.apply_dungeon_enemy_mods
    boss["boss"] = True
    boss["never_flee"] = True
    boss["dungeon_floor_boss"] = True
    return boss


def on_floor_boss_defeated(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
    mon: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    """Clear floor gate; if heart boss, full dungeon clear rewards."""
    run = get_run(player)
    if not run:
        return []
    rng = rng or random.Random(int(player.get("latent_seed", 1)))
    mon = mon or {}
    set_boss_encounter(player, False)
    run = dict(get_run(player) or {})
    depth = current_depth(run)
    mx = max_depth_hidden(run)
    is_heart = bool(
        mon.get("dungeon_heart_boss")
        or mon.get("dungeon_boss")
        or depth >= mx
    )
    run["floor_boss_cleared"] = True
    run["boss_encounter_active"] = False
    player["dungeon_run"] = run

    notes: List[str] = []
    # enable auto-farm boss rematch on this depth
    won = list(run.get("auto_boss_depths") or [])
    if depth not in won:
        won.append(depth)
    run["auto_boss_depths"] = won
    player["dungeon_run"] = run

    if is_heart:
        notes.extend(on_dungeon_boss_defeated(player, reg, rng))
        notes.append(" ออโต้ชั้นนี้: เคยพิชิตหัวใจแล้ว — วนซ้ำชั้นนี้ได้อัตโนมัติ")
        return notes

    notes.append(" ผู้เฝ้าชั้นล้ม")
    notes.append("---")
    notes.append(" สถานะชั้น")
    notes.append("  ทางลงเปิดแล้ว")
    notes.append("  3  ลงลึกได้")
    notes.append("  4  เดินออกได้ทุกเมื่อ")
    notes.append("  A  ออโต้ — สู้บอสชั้นนี้ซ้ำได้อัตโนมัติแล้ว")
    notes.append("---")
    notes.append(" รางวัลชั้น")
    # small floor reward
    from game.domain.equipment import add_item
    from game.domain.leveling import grant_xp

    gold = 8 + depth * 6 + rng.randint(0, 10)
    player["money_world"] = int(player.get("money_world") or 0) + gold
    notes.append(f"  เงินโลก     +{gold}")
    # WO-021: light guaranteed special currency on floor clear (not combat RNG only)
    if depth <= 2 and rng.random() < 0.55:
        if rng.random() < 0.5:
            player["money_heaven"] = int(player.get("money_heaven") or 0) + 1
            notes.append("  เงินสวรรค์   +1")
        else:
            player["money_hell"] = int(player.get("money_hell") or 0) + 1
            notes.append("  เงินนรก     +1")
    elif depth >= 3 and rng.random() < 0.7:
        amt = 1 + (1 if depth >= 4 else 0)
        if rng.random() < 0.5:
            player["money_heaven"] = int(player.get("money_heaven") or 0) + amt
            notes.append(f"  เงินสวรรค์   +{amt}")
        else:
            player["money_hell"] = int(player.get("money_hell") or 0) + amt
            notes.append(f"  เงินนรก     +{amt}")
    xp = 10 + depth * 8
    summary = grant_xp(player, xp, reg.levels)
    notes.append(f"  XP         +{summary.get('gained', xp)}")
    if rng.random() < 0.18 + min(0.25, depth * 0.03):
        if "dungeon_thread" in (reg.items or {}):
            nm = add_item(player, "dungeon_thread", reg, rarity="rare")
            notes.append(f"  ของ        {nm}")
        elif "escape_shard" in (reg.items or {}):
            nm = add_item(player, "escape_shard", reg, rarity="uncommon")
            notes.append(f"  ของ        {nm}")
    return notes


def on_dungeon_boss_defeated(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
) -> List[str]:
    run = get_run(player)
    if not run:
        return []
    run = dict(run)
    run["boss_defeated"] = True
    run["floor_boss_cleared"] = True
    run["locked"] = False
    run["boss_encounter_active"] = False
    depth = current_depth(run)
    won = list(run.get("auto_boss_depths") or [])
    if depth not in won:
        won.append(depth)
    run["auto_boss_depths"] = won
    player["dungeon_run"] = run
    did = str(run.get("dungeon_id"))
    _bump_knowledge(player, did, clears=1)
    cleared = list(player.get("dungeons_cleared") or [])
    if did not in cleared:
        cleared.append(did)
        player["dungeons_cleared"] = cleared
    notes = [
        f"✦ หัวใจดัน「{run.get('name')}」สงบ — โพรงนี้จบลงแล้ว",
        " เดินออกได้ทุกเมื่อ · ไม่มีทางลงอีก",
    ]
    rng = rng or random.Random(int(player.get("latent_seed", 1)))
    notes.extend(grant_dungeon_clear_rewards(player, reg, rng))
    try:
        from game.domain.quests import bump_quest

        notes.extend(bump_quest(player, reg, "dungeon_clear", area_id=did))
    except Exception:
        pass
    return notes


def try_escape(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> List[str]:
    """
    v2: free walk-out when not in boss fight.
    Escape items are for boss combat (see try_boss_combat_escape).
    """
    run = get_run(player)
    if not run:
        return ["ไม่ได้อยู่ในดันเจียน"]
    if run.get("boss_encounter_active"):
        return [
            "ติดวงบอส — ออกดันตรงๆ ไม่ได้",
            " ในไฟต์: ใช้เศษหนี (เมนูหนี) หรือสู้ให้จบ",
        ]
    # free exit
    notes = list(exit_dungeon(player, reg, success=bool(run.get("boss_defeated")), escaped=False))
    return notes


def try_boss_combat_escape(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Tuple[bool, List[str]]:
    """
    Use shard/item during floor/heart boss fight.
    Success: leave combat, stay in dungeon, boss not cleared.
    Returns (left_combat, notes).
    """
    run = get_run(player)
    if not run:
        return False, ["ไม่ได้อยู่ในดันเจียน"]
    if not run.get("boss_encounter_active"):
        return False, ["ไม่ได้อยู่ในวงบอส"]
    usable = count_escape_shards(player, reg)
    if not usable:
        return False, [
            "วงบอสขังคุณ — หนีธรรมดาไม่ได้",
            " ไม่มีเศษหนีในมือ — ต้องสู้ให้จบ",
        ]
    usable.sort(key=lambda x: -x[1])
    iid, chance, name = usable[0]
    from game.domain.equipment import remove_inventory_id

    remove_inventory_id(player, iid, reg)
    notes = [f"คุณบีบ「{name}」กลางวงบอส — บางอย่างตอบสนอง..."]
    if rng.random() <= chance:
        notes.append("✦ เงาฉีกเปิด — คุณถอยจากวงบอสกลับชั้นนี้!")
        notes.append(" ผู้เฝ้ายังอยู่ — ทางลงยังไม่เปิด")
        set_boss_encounter(player, False)
        _bump_knowledge(player, str(run.get("dungeon_id")), escapes=1)
        # mild cost
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="boss_shard_ok", mild=True))
        return True, notes
    notes.append("…แรงดึงไม่พอ ของสลาย — วงบอสยังขัง")
    notes.extend(drain_dungeon_resources(player, reg, rng, reason="boss_shard_fail", mild=True))
    return False, notes


def drain_dungeon_resources(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    reason: str = "fail",
    mild: bool = False,
) -> List[str]:
    """Reduce money / random items — punishment for failing dungeon leave."""
    esc = _cfg(reg).get("escape") or {}
    pct = float(esc.get("drain_money_pct") or 0.12)
    if mild:
        pct *= 0.4
    notes = []
    for key, label in (
        ("money_world", "เงินโลก"),
        ("money_heaven", "เงินสวรรค์"),
        ("money_hell", "เงินนรก"),
    ):
        val = int(player.get(key) or 0)
        loss = int(val * pct)
        if loss > 0:
            player[key] = val - loss
            notes.append(f"  เสีย{label} {loss}")
    # random item loss
    chance = float(esc.get("drain_item_chance") or 0.4)
    if mild:
        chance *= 0.5
    max_n = int(esc.get("drain_max_items") or 2)
    if mild:
        max_n = 1
    ids = list(player.get("inventory_ids") or [])
    lost = 0
    if ids and rng.random() < chance:
        from game.domain.rarity import remove_inventory_at_index

        n = rng.randint(1, min(max_n, len(ids)))
        for _ in range(n):
            ids = list(player.get("inventory_ids") or [])
            if not ids:
                break
            idx = rng.randint(0, len(ids) - 1)
            rem = remove_inventory_at_index(player, idx, reg)
            if rem:
                nm = (reg.items.get(rem[0]) or {}).get("name") or rem[0]
                notes.append(f"  ของหายไป: {nm}")
                lost += 1
    if not notes:
        notes.append("  ทรัพยากรสั่นคลอน แต่ยังไม่เสียมาก")
    else:
        notes.insert(0, "ทรัพยากรที่นำเข้าถูกกลืน/สึกกร่อน...")
    return notes


def exit_dungeon(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    success: bool = True,
    escaped: bool = False,
) -> List[str]:
    run = get_run(player)
    if not run:
        return ["ไม่ได้อยู่ในดันเจียน"]
    # v2: block only during active boss encounter (unless forced eject)
    if run.get("boss_encounter_active") and not escaped:
        return ["ติดวงบอส — ออกดันไม่ได้จนกว่าจะจบไฟต์ (สู้หรือใช้เศษหนี)"]
    # legacy locked runs (old saves): still allow free exit in v2 ruleset or if not locked
    if run.get("locked") and not run.get("boss_defeated") and not escaped and run.get("ruleset") != "v2":
        # migrate soft: treat as free exit for playability
        pass
    back = player.get("location_before_dungeon") or run.get("area_id") or "dark_forest"
    player["location"] = back
    player["dungeon_run"] = None
    player.pop("location_before_dungeon", None)
    try:
        from game.domain.situation import help_is_open, owner_exit_cleanup

        was_help = help_is_open(player) or bool(
            (player.get("situation") or {}).get("help", {}).get("escrow")
        )
        exit_extra = list(owner_exit_cleanup(player, reg))
        if was_help and not any("สัญญาณ" in x for x in exit_extra):
            exit_extra.append(" สัญญาณขอแรงดับลงพร้อมการออกจากสถานการณ์")
    except Exception:
        exit_extra = []
    name = run.get("name") or "ดันเจียน"
    if success and run.get("boss_defeated"):
        return [
            f"คุณเดินออกจาก「{name}」อย่างผู้พิชิต",
            f" กลับสู่ {reg.area_name(str(back))}",
            *exit_extra,
        ]
    if escaped:
        return [
            f"คุณรอดจาก「{name}」แบบหวุดหวิด",
            f" กลับสู่ {reg.area_name(str(back))}",
            *exit_extra,
        ]
    return [f"ออกจาก「{name}」", f" กลับสู่ {reg.area_name(str(back))}", *exit_extra]


def format_dungeon_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    run = get_run(player)
    if not run:
        return [" ดันเจียน", "---", " (ไม่อยู่ในดันเจียน)"]
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    soft = soft_difficulty_text(player, reg, d) if d else "???"
    layout = run.get("floor_layout") or {}
    depth = current_depth(run)
    shards = count_escape_shards(player, reg)
    lines = [
        f" ดันเจียน · {run.get('name')}",
        "---",
        f" ความลึก   ลงมาชั้นที่ {depth}",
        f" ภูมิชั้น   {layout.get('label', '?')} — {layout.get('desc', '')}",
        f" สัญญาณ   {soft}",
        "---",
        " ทางออก   เปิด (สำรวจ) · ปิดเฉพาะตอนไฟต์บอส",
    ]
    if run.get("boss_defeated"):
        lines.append(" ผู้เฝ้า    หัวใจดันสงบแล้ว")
        lines.append(" ทางลึก   ปิด — โพรงนี้จบแล้ว")
    elif run.get("floor_boss_cleared"):
        lines.append(" ผู้เฝ้า    ล้มแล้ว — ทางลงเปิด")
        ok_adv, why_adv = can_advance_floor(player)
        if ok_adv:
            lines.append(" ทางลึก   เปิดแล้ว — เลือก (3) ลงลึกได้")
        else:
            lines.append(f" ทางลึก   {why_adv}")
    else:
        lines.append(" ผู้เฝ้า    ยังขวางทาง")
        lines.append(" ทางลึก   ยังปิด — ท้าทายผู้เฝ้าชั้น (2)")
    lines.append(
        f" สู้ชั้นนี้  {run.get('fights_this_floor', 0)} ครั้ง"
        f"  ·  เส้นทาง {run.get('path_progress', 0)}"
    )
    try:
        from game.runtime.dungeon_auto import count_food, format_dungeon_auto_hud

        # compact resource line for dungeon panel
        ensure_needs_line = format_dungeon_auto_hud(player, reg)
        # strip trailing money bit for panel space — show food focus
        food_n = count_food(player, reg)
        from game.domain.needs import ensure_needs, get_needs

        ensure_needs(player)  # type: ignore
        hun = int(get_needs(player).get("hunger") or 0)  # type: ignore
        lines.append(
            f" ทรัพยากร  อาหาร {food_n}  ·  หิว {hun}"
            f"  ·  HP {int(player.get('hp') or 0)}/{int(player.get('max_hp') or 1)}"
            f"  ·  MP {int(player.get('mana') or 0)}/{int(player.get('max_mana') or 1)}"
        )
        if food_n <= 2:
            lines.append(" ⚠ อาหารใกล้หมด — ร้านเงา (8) หรือออกซื้อ")
        auto_depths = list(run.get("auto_boss_depths") or [])
        if current_depth(run) in auto_depths:
            lines.append(" ออโต้บอส  ชั้นนี้เคยชนะแล้ว — A ฟาร์มซ้ำผู้เฝ้าได้")
        else:
            lines.append(" ออโต้บอส  ยังต้องสู้เอง 1 ครั้ง (เมนู 2) ก่อนฟาร์มบอส")
    except Exception:
        pass
    lines.append("---")
    if shards:
        lines.append(f" เศษหนี    มี {len(shards)} ชิ้นในมือ (ใช้ตอนไฟต์บอส)")
    else:
        lines.append(" เศษหนี    ไม่มี — ท้าบอสเมื่อมั่นใจ")
    if run.get("time_collapse_enabled"):
        left = int(run.get("turns_left") or 0)
        tmax = max(1, int(run.get("turns_max") or 1))
        ratio = left / tmax
        if ratio > 0.5:
            lines.append(" แรงกดเวลา  ยังไหว")
        elif ratio > 0.25:
            lines.append(" แรงกดเวลา  เริ่มแน่น")
        elif left > 0:
            lines.append(" แรงกดเวลา  วิกฤต")
        else:
            lines.append(" แรงกดเวลา  ยุบ!")
    try:
        from game.domain.situation import (
            format_help_status_lines,
            sync_situation_from_dungeon,
        )

        if isinstance(player, dict):
            sync_situation_from_dungeon(player, preserve_help=True)  # type: ignore[arg-type]
        for hl in format_help_status_lines(player):
            if "สัญญาณ" in hl or "สถานการณ์" in hl:
                lines.append(" " + hl.lstrip())
    except Exception:
        pass
    lines.append("---")
    lines.append(" (ความยาก · เพดานชั้น · สูตร — ซ่อน)")
    return lines




def has_dungeon_stealth(player: Mapping[str, Any]) -> bool:
    """Item that soft-hides from common monsters while resting."""
    bag = set(player.get("inventory_ids") or [])
    stealth_ids = {
        "shadow_cloak",
        "dust_veil",
        "dungeon_thread",
        "escape_shard",
        "blessed_charm",
        "void_key_shard",
    }
    return bool(bag & stealth_ids)


def dungeon_rest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    Rest inside dungeon: heal HP/MP, risk ambush unless stealth item.
    Returns {notes, trigger_combat, ambush}.
    """
    notes: List[str] = []
    if not in_dungeon(player):
        return {"notes": ["ไม่ได้อยู่ในดันเจียน"], "trigger_combat": False, "ambush": False}
    if is_boss_encounter_active(player):
        return {
            "notes": ["ติดวงบอส — พักไม่ได้"],
            "trigger_combat": False,
            "ambush": False,
        }
    # heal
    mhp = max(1, int(player.get("max_hp") or 1))
    mmp = max(1, int(player.get("max_mana") or 1))
    heal = max(12, int(mhp * 0.28) + rng.randint(0, 10))
    mana = max(8, int(mmp * 0.22) + rng.randint(0, 6))
    player["hp"] = min(mhp, int(player.get("hp") or 0) + heal)
    player["mana"] = min(mmp, int(player.get("mana") or 0) + mana)
    notes.append(f"คุณหลับตาพักในมุมมืด… ฟื้น HP+{heal} MP+{mana}")
    try:
        from game.domain.needs import apply_needs_event

        for line in apply_needs_event(player, "rest"):
            notes.append(line)
    except Exception:
        pass
    # ambush risk
    stealthed = has_dungeon_stealth(player)
    if stealthed:
        notes.append(" …มีของที่กลืนกลิ่น/เงา — มอนทั่วไปมองไม่ค่อยเห็น")
        ambush_chance = 0.08
    else:
        ambush_chance = 0.38
        depth = current_depth(get_run(player) or {})
        ambush_chance = min(0.62, ambush_chance + 0.03 * max(0, depth - 1))
    if rng.random() < ambush_chance:
        notes.append(" ⚠ ตื่นขึ้นมากลางวง — มีเงาพุ่งเข้าใส่!")
        return {"notes": notes, "trigger_combat": True, "ambush": True}
    notes.append(" ตื่นขึ้นมาโดยไม่มีใครรบกวน… ครั้งนี้")
    return {"notes": notes, "trigger_combat": False, "ambush": False}


def dungeon_shop_price_mult(player: Mapping[str, Any]) -> float:
    """Soft markup for shadow shop inside dungeon."""
    run = get_run(player) or {}
    depth = current_depth(run)
    return 1.35 + 0.06 * max(0, depth - 1)



def dungeon_menu_actions(player: Mapping[str, Any]) -> List[str]:
    run = get_run(player)
    if not run:
        return []
    try:
        from game.domain.situation import help_is_open

        help_line = (
            "  6  สัญญาณขอแรง  (เปิดอยู่)"
            if help_is_open(player)
            else "  6  สัญญาณขอแรง  (ยินยอมช่วย)"
        )
    except Exception:
        help_line = "  6  สัญญาณขอแรง"
    ok_adv, _why = can_advance_floor(player)
    if run.get("boss_defeated"):
        deep_line = "  3  ลงลึกกว่านี้  (โพรงจบแล้ว)"
        boss_line = "  2  ท้าทายผู้เฝ้าชั้น  (เคลียร์แล้ว)"
    elif run.get("floor_boss_cleared"):
        boss_line = "  2  ท้าทายผู้เฝ้าชั้น  (ล้มแล้ว)"
        deep_line = (
            "  3  ลงลึกกว่านี้  ← ทางเปิด"
            if ok_adv
            else "  3  ลงลึกกว่านี้  (ปิด)"
        )
    else:
        boss_line = "  2  ท้าทายผู้เฝ้าชั้น  (หนีปกติไม่ได้)"
        deep_line = "  3  ลงลึกกว่านี้  (ต้องกำจัดผู้เฝ้าก่อน)"
    return [
        " ทำอะไรในดัน",
        "---",
        "  1  สำรวจชั้นนี้  (มอนทั่วไป — หนีได้)",
        boss_line,
        deep_line,
        "  4  เดินออกจากดัน  (ฟรี · ยกเว้นตอนไฟต์บอส)",
        "  5  ดูสถานะดัน",
        help_line,
        "  7  กระเป๋า / ใช้ยา",
        "  8  ร้านเงาในดัน  (ของจำกัด · ราคาสูง soft)",
        "  9  พัก/นอนในดัน  (ฟื้น — อาจถูกซุ่ม)",
        "  A  ออโต้ฟาร์มชั้นนี้  (กิน/สู้/เก็บของ · บอสต้องชนะเองก่อน 1 ครั้ง)",
        "---",
        "  Y  ปาร์ตี้     0  ออก (ฟรี)",
    ]
