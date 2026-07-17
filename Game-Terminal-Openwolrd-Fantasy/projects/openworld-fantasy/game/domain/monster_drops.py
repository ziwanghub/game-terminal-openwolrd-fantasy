"""
Per-monster drop tables (RO-like structure, soft rates — never show %).

YAML on monster:
  drops:
    - item: wolf_fang
      rate: common          # common|uncommon|rare|very_rare|boss | float 0–1
      qty: [1, 2]           # optional
      note: เขี้ยว           # optional soft note
  card_id: card_vitality    # optional bound card (drop-only)
  card_rate: very_rare      # default very_rare
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# Hidden chance bands — UI never shows these numbers
_RATE_CHANCE: Dict[str, float] = {
    "common": 0.48,
    "uncommon": 0.20,
    "rare": 0.07,
    "very_rare": 0.018,
    "boss": 0.52,
    "always": 1.0,
    "guaranteed": 1.0,
}


def rate_to_chance(rate: Any) -> float:
    if rate is None:
        return float(_RATE_CHANCE["uncommon"])
    if isinstance(rate, (int, float)):
        return max(0.0, min(1.0, float(rate)))
    key = str(rate).strip().lower()
    return float(_RATE_CHANCE.get(key, _RATE_CHANCE["uncommon"]))


def _qty_range(entry: Mapping[str, Any]) -> Tuple[int, int]:
    q = entry.get("qty")
    if q is None:
        return 1, 1
    if isinstance(q, int):
        n = max(1, int(q))
        return n, n
    if isinstance(q, (list, tuple)) and len(q) >= 1:
        a = max(1, int(q[0]))
        b = max(a, int(q[1]) if len(q) > 1 else a)
        return a, b
    return 1, 1


def _anti_farm_mult(player: Mapping[str, Any], mon_id: str) -> float:
    recent = list(player.get("recent_kill_ids") or [])
    mid = str(mon_id or "")
    if not mid:
        return 1.0
    same = sum(1 for x in recent[-12:] if str(x) == mid)
    if same <= 2:
        return 1.0
    # soft decay — never zero
    return max(0.35, 0.85 ** (same - 2))


def mon_drop_entries(mon: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Normalize drops list + optional card_id row."""
    out: List[Dict[str, Any]] = []
    for raw in mon.get("drops") or []:
        if not isinstance(raw, Mapping):
            continue
        iid = str(raw.get("item") or raw.get("id") or raw.get("card") or "").strip()
        if not iid:
            continue
        row = dict(raw)
        row["item"] = iid
        out.append(row)
    # bound card (RO-like trophy card)
    cid = str(mon.get("card_id") or "").strip()
    if cid:
        # avoid duplicate if already in drops
        if not any(str(r.get("item")) == cid for r in out):
            out.append(
                {
                    "item": cid,
                    "rate": mon.get("card_rate") or "very_rare",
                    "note": "การ์ด · พันธะมอน",
                }
            )
    return out


def roll_monster_table_drops(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Roll per-monster table → list of drop dicts {id, qty_extra hint via multiple entries}.
    Returns raw packs before rarity formatting (id + optional note + count).
    """
    entries = mon_drop_entries(mon)
    if not entries:
        return []

    farm = _anti_farm_mult(player, str(mon.get("id") or ""))
    boss = bool(mon.get("boss"))
    rolled: List[Dict[str, Any]] = []

    for entry in entries:
        iid = str(entry.get("item") or "")
        if not iid:
            continue
        # validate id exists
        if iid not in (reg.items or {}) and iid not in (reg.cards or {}):
            continue
        # WO-Worthiness-1: Reward Lock — no trial-exclusive / god-tier from farm table
        try:
            from game.domain.worthiness import item_blocked_on_farm

            if item_blocked_on_farm(iid, reg, allow_god=False):
                continue
        except Exception:
            pass
        chance = rate_to_chance(entry.get("rate"))
        if boss and str(entry.get("rate") or "").lower() in ("rare", "very_rare"):
            chance = min(0.95, chance * 1.35)
        chance *= farm
        if rng.random() > chance:
            continue
        lo, hi = _qty_range(entry)
        n = rng.randint(lo, hi) if hi > lo else lo
        note = str(entry.get("note") or "")
        for _ in range(n):
            rolled.append({"id": iid, "note": note})
    return rolled


def monster_has_drop_table(mon: Mapping[str, Any]) -> bool:
    return bool(mon_drop_entries(mon))
