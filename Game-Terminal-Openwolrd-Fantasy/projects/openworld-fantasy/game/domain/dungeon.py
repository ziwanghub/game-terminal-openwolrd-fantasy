"""
Dungeon runs — hidden difficulty, lock until clear or rare escape item.
Player discovers danger by play / incomplete hints.
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


def begin_dungeon(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    dungeon_id: str,
    rng: random.Random,
) -> List[str]:
    """Enter dungeon — lock exit until clear or escape item works."""
    ensure_dungeon_state(player)
    if in_dungeon(player):
        return ["คุณอยู่ในดันเจียนอยู่แล้ว"]
    d = dungeon_by_id(reg, dungeon_id)
    if not d:
        return ["ไม่พบทางเข้า"]
    notes = []
    escape_tokens = _scan_escape_items(player, reg)
    # snapshot for drain messaging (not full restore)
    snap = {
        "money_world": int(player.get("money_world") or 0),
        "money_heaven": int(player.get("money_heaven") or 0),
        "money_hell": int(player.get("money_hell") or 0),
        "inv_count": len(player.get("inventory_ids") or []),
    }
    diff = int(d.get("difficulty") or 2)
    floors = int(d.get("floors") or 2)
    turns_max = compute_time_limit(reg, d)
    layout = generate_floor_layout(reg, d, 1, rng)
    player["dungeon_run"] = {
        "dungeon_id": dungeon_id,
        "name": d.get("name"),
        "area_id": d.get("area_id"),
        "floor": 1,
        "floors": floors,
        "boss_id": d.get("boss_id"),
        "locked": True,
        "boss_defeated": False,
        "rewards_granted": False,
        "escape_ready": bool(escape_tokens),
        "escape_items": [t[0] for t in escape_tokens],
        "escape_chances": {t[0]: t[1] for t in escape_tokens},
        "snapshot": snap,
        "enemy_hp_mult": float(d.get("enemy_hp_mult") or 1.2),
        "enemy_atk_mult": float(d.get("enemy_atk_mult") or 1.15),
        "difficulty_hidden": diff,
        "fights_this_floor": 0,
        "turns_left": turns_max,
        "turns_max": turns_max,
        "floor_layout": layout,
        "floor_layouts": {1: layout},
    }
    # mark location feel
    player["location_before_dungeon"] = player.get("location")
    player["location"] = f"dungeon:{dungeon_id}"
    _bump_knowledge(player, dungeon_id, visits=1)
    notes.append(f"คุณก้าวเข้า「{d.get('name')}」— ทางกลับมืดลง")
    notes.append(" (ยังไม่รู้ว่าอันตรายแค่ไหน — ต้องสังเกตเอง)")
    notes.append(f" ภูมิชั้นนี้: {layout.get('label')} — {layout.get('desc')}")
    notes.append(" …เวลากดดันจากภายใน (ไม่บอกว่าเหลือกี่หน่วย)")
    if escape_tokens:
        notes.append(" …มีบางอย่างในกระเป๋าร้อนวูบ ราวกับดึงกลับได้")
    else:
        notes.append(" ไม่มีสิ่งใดรับประกันทางออก — ต้องเคลียร์หรือหาทางรอดเอง")
    notes.append(f" ชั้น 1/{floors} · ปาร์ตี้ {len(player.get('party') or [])}/3")
    try:
        from game.domain.situation import sync_situation_from_dungeon

        sync_situation_from_dungeon(player, preserve_help=False)
        notes.append(" …ถ้าตึงเครียด อาจเปิดสัญญาณขอแรงได้ (ยินยอมให้ช่วย — ระบบช่วยเต็มทีหลัง)")
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


def explore_floor_event(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    Resolve one explore action inside dungeon.
    Returns {kind, flavor, notes, trigger_combat, loot, rest_hp, trap_dmg}
    """
    run = get_run(player)
    if not run:
        return {"kind": "empty", "flavor": "…", "notes": ["ไม่ได้อยู่ในดันเจียน"]}
    events = list(_cfg(reg).get("floor_events") or [])
    if not events:
        events = [{"id": "ambush", "weight": 1, "kind": "combat", "flavor": "ศัตรู!"}]
    # layout biases event weights slightly
    layout_id = str((run.get("floor_layout") or {}).get("id") or "")
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
        weights.append(w)
    total = sum(weights)
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
    result: Dict[str, Any] = {
        "kind": kind,
        "flavor": flavor,
        "notes": notes,
        "trigger_combat": kind == "combat",
        "loot": [],
        "rest_hp": 0,
        "trap_dmg": 0,
    }
    if kind == "empty":
        am = dict(player.get("area_mastery") or {})
        aid = str(run.get("area_id") or "dark_forest")
        am[aid] = min(100, int(am.get(aid, 0)) + 1)
        player["area_mastery"] = am
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
    return result


def tick_dungeon_time(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    cost: int = 1,
) -> List[str]:
    """Spend dungeon turns; at 0 collapse and eject with drain."""
    run = get_run(player)
    if not run:
        return []
    notes: List[str] = []
    left = int(run.get("turns_left") or 0) - max(1, cost)
    run = dict(run)
    run["turns_left"] = left
    player["dungeon_run"] = run
    tl = _cfg(reg).get("time_limit") or {}
    warn = int(tl.get("warn_at") or 5)
    crit = int(tl.get("critical_at") or 2)
    # soft messages only — no numbers
    if left <= 0:
        notes.append("มิติดันเจียนยุบตัว! คุณถูกบีบออกมา...")
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="time_out"))
        _bump_knowledge(player, str(run.get("dungeon_id")), fails=1)
        notes.extend(exit_dungeon(player, reg, success=False, escaped=True))
        return notes
    if left <= crit:
        notes.append("⚠ แรงกดจากผนัง/เงารุนแรง — เวลาราวจะหมด (ไม่รู้ว่าเหลือเท่าไหร่)")
        # pressure spike
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
    run = get_run(player)
    if not run:
        return dict(mon)
    mon = dict(mon)
    hp_m = float(run.get("enemy_hp_mult") or 1.2)
    atk_m = float(run.get("enemy_atk_mult") or 1.15)
    # deeper floors slightly harder
    floor = int(run.get("floor") or 1)
    hp_m *= 1.0 + 0.08 * (floor - 1)
    atk_m *= 1.0 + 0.06 * (floor - 1)
    mon["hp"] = max(1, int(round(int(mon.get("hp") or 1) * hp_m)))
    mon["max_hp"] = max(1, int(round(int(mon.get("max_hp") or mon["hp"]) * hp_m)))
    mon["atk"] = max(1, int(round(int(mon.get("atk") or 1) * atk_m)))
    profiles = []
    for p in mon.get("attack_profiles") or []:
        p = dict(p)
        if "power" in p:
            p["power"] = max(1, int(round(int(p["power"]) * atk_m)))
        profiles.append(p)
    if profiles:
        mon["attack_profiles"] = profiles
    mon["dungeon_modded"] = True
    return mon


def note_dungeon_fight(player: MutableMapping[str, Any]) -> None:
    run = player.get("dungeon_run")
    if not isinstance(run, dict):
        return
    run = dict(run)
    run["fights_this_floor"] = int(run.get("fights_this_floor") or 0) + 1
    player["dungeon_run"] = run


def can_advance_floor(player: Mapping[str, Any]) -> Tuple[bool, str]:
    run = get_run(player)
    if not run:
        return False, "ไม่ได้อยู่ในดันเจียน"
    need = 2 + int(run.get("difficulty_hidden") or 2) // 2
    fights = int(run.get("fights_this_floor") or 0)
    if fights < need:
        return False, "ทางลึกยังไม่เปิด — ยังมีเงาขัดขวาง (สู้เพิ่ม?)"
    return True, "ok"


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
    floor = int(run["floor"]) + 1
    floors = int(run["floors"])
    run = dict(run)
    if floor > floors:
        return ["ถึงชั้นในสุดแล้ว — ต้องเผชิญบอส"]
    rng = rng or random.Random()
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    layout = generate_floor_layout(reg, d, floor, rng)
    run["floor"] = floor
    run["fights_this_floor"] = 0
    run["floor_layout"] = layout
    layouts = dict(run.get("floor_layouts") or {})
    layouts[floor] = layout
    run["floor_layouts"] = layouts
    player["dungeon_run"] = run
    return [
        f"คุณลงลึกสู่ชั้น {floor}/{floors}... อากาศเปลี่ยน",
        f" ภูมิชั้นใหม่: {layout.get('label')} — {layout.get('desc')}",
    ]


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
    run["locked"] = False
    player["dungeon_run"] = run
    did = str(run.get("dungeon_id"))
    _bump_knowledge(player, did, clears=1)
    cleared = list(player.get("dungeons_cleared") or [])
    if did not in cleared:
        cleared.append(did)
        player["dungeons_cleared"] = cleared
    notes = [
        f"✦ บอสดันเจียนล้ม — ทางออก「{run.get('name')}」เปิดแล้ว",
        " คุณอาจเดินออกได้โดยปลอดภัย (หรือสำรวจต่อ)",
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
    Attempt to leave while locked.
    - If boss defeated: free exit
    - If escape item was present at entry: roll chance, consume item on try
    - Else: fail, drain resources, stay locked
    """
    run = get_run(player)
    if not run:
        return ["ไม่ได้อยู่ในดันเจียน"]
    notes: List[str] = []
    if not run.get("locked") or run.get("boss_defeated"):
        notes.extend(exit_dungeon(player, reg, success=True))
        return notes

    # locked — need escape token from entry bag
    chances = dict(run.get("escape_chances") or {})
    items = list(run.get("escape_items") or [])
    # only items still in bag count
    bag = set(player.get("inventory_ids") or [])
    usable = [(i, chances.get(i, 0.4)) for i in items if i in bag]
    if not usable:
        notes.append("ทางออกปิดสนิท — ไม่มีอะไรดึงคุณกลับได้")
        notes.append(" ต้องเคลียร์บอส หรือ… มีของพิเศษตั้งแต่ตอนเข้า (คุณไม่รู้วิธีได้)")
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="fail_escape"))
        _bump_knowledge(player, str(run.get("dungeon_id")), fails=1)
        return notes

    # use best chance item
    usable.sort(key=lambda x: -x[1])
    iid, chance = usable[0]
    from game.domain.equipment import remove_inventory_id

    remove_inventory_id(player, iid, reg)
    name = (reg.items.get(iid) or {}).get("name") or iid
    notes.append(f"คุณบีบ「{name}」— บางอย่างตอบสนอง...")
    if rng.random() <= chance:
        notes.append("✦ เส้นทางฉีกเปิดครู่หนึ่ง — คุณถูกลากออกมา!")
        _bump_knowledge(player, str(run.get("dungeon_id")), escapes=1)
        notes.extend(exit_dungeon(player, reg, success=False, escaped=True))
        # light drain even on escape
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="escape_success", mild=True))
    else:
        notes.append("…แรงดึงไม่พอ ทางปิดอีกครั้ง ของชิ้นนั้นสลาย")
        notes.extend(drain_dungeon_resources(player, reg, rng, reason="fail_escape"))
        _bump_knowledge(player, str(run.get("dungeon_id")), fails=1)
        # remove from run tokens
        run = dict(player.get("dungeon_run") or {})
        left = [x for x in (run.get("escape_items") or []) if x != iid and x in set(player.get("inventory_ids") or [])]
        run["escape_items"] = left
        run["escape_ready"] = bool(left)
        player["dungeon_run"] = run
    return notes


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
    if run.get("locked") and not run.get("boss_defeated") and not escaped:
        return ["ทางออกยังล็อก — เคลียร์บอสหรือใช้ของพิเศษ"]
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
        return ["── ดันเจียน ──", " (ไม่อยู่ในดันเจียน)"]
    d = dungeon_by_id(reg, str(run.get("dungeon_id"))) or {}
    soft = soft_difficulty_text(player, reg, d) if d else "???"
    layout = run.get("floor_layout") or {}
    lines = [
        f"── ดันเจียน: {run.get('name')} ──",
        f" ชั้น {run.get('floor')}/{run.get('floors')}",
        f" ภูมิชั้น: {layout.get('label', '?')} — {layout.get('desc', '')}",
        f" สัญญาณอันตราย: {soft}",
        f" ทางออก: {'เปิด' if not run.get('locked') or run.get('boss_defeated') else 'ล็อก'}",
        f" บอส: {'ล้มแล้ว' if run.get('boss_defeated') else 'ยังอยู่ลึกภายใน'}",
        f" สู้ชั้นนี้: {run.get('fights_this_floor', 0)} ครั้ง",
    ]
    # time pressure soft only
    left = int(run.get("turns_left") or 0)
    tmax = max(1, int(run.get("turns_max") or 1))
    ratio = left / tmax
    if ratio > 0.5:
        lines.append(" แรงกดเวลา: ยังไหว")
    elif ratio > 0.25:
        lines.append(" แรงกดเวลา: เริ่มแน่น")
    elif left > 0:
        lines.append(" แรงกดเวลา: วิกฤต — รีบตัดสินใจ")
    else:
        lines.append(" แรงกดเวลา: ยุบ!")
    if run.get("escape_ready"):
        lines.append(" …มีของบางอย่างในกระเป๋าตอนเข้า — อาจดึงกลับได้")
    else:
        lines.append(" ไม่มีหลักประกันทางออก (นอกจากเคลียร์)")
    try:
        from game.domain.situation import (
            format_help_status_lines,
            sync_situation_from_dungeon,
        )

        # refresh severity soft while viewing
        if isinstance(player, dict):
            sync_situation_from_dungeon(player, preserve_help=True)  # type: ignore[arg-type]
        for hl in format_help_status_lines(player):
            if "สัญญาณ" in hl or "สถานการณ์" in hl:
                lines.append(" " + hl.lstrip())
    except Exception:
        pass
    lines.append(" (ความยาก · เวลา · สูตร — ซ่อนทั้งหมด)")
    return lines


def dungeon_menu_actions(player: Mapping[str, Any]) -> List[str]:
    run = get_run(player)
    if not run:
        return []
    try:
        from game.domain.situation import help_is_open

        help_line = (
            "6. สัญญาณขอแรง (เปิดอยู่ — ปิด/ดูสถานะ)"
            if help_is_open(player)
            else "6. สัญญาณขอแรง (ยินยอมให้ช่วย · ระบบสังคม)"
        )
    except Exception:
        help_line = "6. สัญญาณขอแรง"
    acts = [
        "1. สำรวจชั้นนี้ (เหตุการณ์สุ่ม / ศัตรู / ของ / กับดัก)",
        "2. ลงลึกกว่านี้ (ภูมิชั้นใหม่)",
        "3. ท้าทายบอสดันเจียน (ชั้นในสุด)",
        "4. พยายามออก / ใช้ของหนี",
        "5. ดูสถานะดันเจียน",
        help_line,
        "Y. ปาร์ตี้  0. ออก(ถ้าทางเปิด)",
    ]
    return acts
