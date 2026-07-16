"""Field sights, approach tables, chest risk (P8)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.data_load.registry import DataRegistry
from game.domain.combat import pick_monster


def _pick_sight_monster(
    reg: DataRegistry,
    area_id: str,
    rng: random.Random,
    *,
    player_level: int,
    starter: bool,
) -> Dict[str, Any]:
    """Prefer fair fights in starter areas for low-level players (playtest P2)."""
    mon = pick_monster(reg, area_id, rng)
    if not starter or player_level > 4:
        return mon
    best = mon
    for _ in range(8):
        cand = pick_monster(reg, area_id, rng)
        if int(cand.get("level") or 1) <= player_level + 2:
            return cand
        if int(cand.get("level") or 99) < int(best.get("level") or 99):
            best = cand
    # last resort: soft-scale the weakest draw so city isn't a death gate
    if int(best.get("level") or 1) > player_level + 2:
        best = dict(best)
        best["level"] = max(1, player_level + 1)
        best["hp"] = max(12, int(int(best.get("hp") or 40) * 0.55))
        best["max_hp"] = int(best["hp"])
        best["atk"] = max(3, int(int(best.get("atk") or 8) * 0.55))
        best["_soft_town"] = True
    return best


def _weighted_pick(table: List[Dict[str, Any]], rng: random.Random) -> str:
    if not table:
        return "fair_combat"
    total = sum(int(e.get("weight", 1)) for e in table)
    roll = rng.randint(1, max(1, total))
    acc = 0
    for e in table:
        acc += int(e.get("weight", 1))
        if roll <= acc:
            return str(e.get("id", "fair_combat"))
    return str(table[-1].get("id", "fair_combat"))


def build_sights(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    count: int = 4,
) -> List[Dict[str, Any]]:
    """Generate visible targets in current area for this field tick."""
    area_id = str(player.get("location"))
    area = reg.areas.get(area_id) or {}
    know = (player.get("knowledge") or {}).get("monsters") or {}
    sights: List[Dict[str, Any]] = []

    # 2-3 monsters / silhouettes (starter city: fewer + softer)
    plv = int(player.get("level", 1))
    starter = area_id in ("ancient_city",)
    if starter and plv <= 3:
        n_mon = 1 if plv <= 2 else rng.randint(1, 2)
    else:
        n_mon = rng.randint(1, 3)
    for _ in range(n_mon):
        mon = _pick_sight_monster(reg, area_id, rng, player_level=plv, starter=starter)
        known = mon["id"] in know and know[mon["id"]].get("fought", 0) > 0
        if known:
            label = str(mon["name"])
            hint = "เคยสู้"
        else:
            label = "???"
            flavors = [
                "เงาร่างเคลื่อนไหว",
                "เสียงหายใจลึก",
                "ดวงตาวูบในความมืด",
                "รอยเท้าแปลกปลอม",
            ]
            hint = rng.choice(flavors)
        risk = "?"
        if mon["level"] >= plv + 3:
            risk = "สูง"
        elif starter and mon["level"] <= plv + 1:
            risk = "ต่ำ"
        sights.append(
            {
                "kind": "monster",
                "label": label,
                "hint": hint,
                "monster": mon,
                "known": known,
                "risk": risk,
            }
        )

    # npc
    if rng.random() < 0.55:
        sights.append(
            {
                "kind": "npc",
                "label": "คนแปลกหน้า",
                "hint": rng.choice(["คลุมผ้าคลุม", "ยืนนิ่ง", "ถือตะกร้า", "มีกลิ่นยา"]),
                "known": False,
                "risk": "?",
            }
        )

    # dungeon mouth (hidden difficulty)
    try:
        from game.domain.dungeon import in_dungeon, roll_dungeon_sight

        if not in_dungeon(player):
            ds = roll_dungeon_sight(player, reg, rng, area_id)
            if ds:
                sights.append(ds)
    except Exception:
        pass

    # chest
    if rng.random() < 0.45:
        sights.append(
            {
                "kind": "chest",
                "label": "หีบเก่า",
                "hint": rng.choice(["ผุกร่อน", "ล็อคร้าว", "สลักเลือน", "อุ่นผิดปกติ"]),
                "known": False,
                "risk": "?",
            }
        )

    # other players in this world (full save echoes)
    try:
        from game.domain.world_social import pick_echo_for_sight

        echo = pick_echo_for_sight(player, reg, rng)
        if echo:
            sights.append(echo)
    except Exception:
        pass

    # soft companion shadow (P1) — approach may offer join
    try:
        from game.domain.party import roll_companion_sight

        cs = roll_companion_sight(player, reg, rng)
        if cs:
            sights.append(cs)
    except Exception:
        pass

    # WO-039: Faction Mini-Moments (soft world gaze)
    try:
        from game.domain.faction_moments import roll_faction_moment_sight

        fm = roll_faction_moment_sight(player, rng, area_id=area_id)
        if fm:
            sights.append(fm)
    except Exception:
        pass

    rng.shuffle(sights)
    sights = sights[: max(1, count)]
    assign_sight_handles(sights)
    return sights


def assign_sight_handles(sights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Attach stable-per-tick handles: mn01, mn02, ch01, np01, dg01, pl01.
    Used by f_mn02 / o_ch01 command grammar.
    """
    counters: Dict[str, int] = {}
    prefix = {
        "monster": "mn",
        "chest": "ch",
        "npc": "np",
        "dungeon": "dg",
        "companion": "rc",
        "player": "pl",
        "echo": "pl",
        "faction_moment": "fm",
    }
    for s in sights:
        kind = str(s.get("kind") or "x")
        p = prefix.get(kind, "tx")
        counters[p] = counters.get(p, 0) + 1
        s["handle"] = f"{p}{counters[p]:02d}"
    return sights


def mark_monster_seen(player: MutableMapping[str, Any], mon: Mapping[str, Any]) -> None:
    know = dict(player.get("knowledge") or {})
    mons = dict(know.get("monsters") or {})
    entry = dict(mons.get(mon["id"]) or {"seen": True, "fought": 0, "won": 0})
    entry["seen"] = True
    entry["name"] = mon.get("name")
    mons[str(mon["id"])] = entry
    know["monsters"] = mons
    player["knowledge"] = know


def resolve_approach(
    kind: str,
    reg: DataRegistry,
    rng: random.Random,
) -> str:
    table = list((reg.approach or {}).get(kind) or [])
    return _weighted_pick(table, rng)
