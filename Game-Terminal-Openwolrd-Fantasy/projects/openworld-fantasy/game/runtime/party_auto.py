"""
WO-PARTY-5 — Auto Party Care (soft).

- Soft gift when companion bond is cool and bag has safe surplus
- Never auto-dismiss · never auto-recruit · never force call
- Respects food/potion reserves (does not steal emergency stock)
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry

DEFAULT_PARTY_AUTO: Dict[str, Any] = {
    "party_care": True,  # master switch
    "party_gift": True,  # soft gift when bond cool
    "party_gift_bond_below": 42,  # gift if bond < this
    "party_gift_cooldown": 6,  # care ticks between gifts
    "party_min_food_keep": 2,  # never gift food below this stock
    "party_min_hp_pots_keep": 1,
}


def ensure_party_auto_prefs(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    from game.runtime.dungeon_auto import ensure_auto_prefs

    prefs = ensure_auto_prefs(player)
    for k, v in DEFAULT_PARTY_AUTO.items():
        if k not in prefs:
            prefs[k] = v
    prefs["party_care"] = bool(prefs.get("party_care", True))
    prefs["party_gift"] = bool(prefs.get("party_gift", True))
    prefs["party_gift_bond_below"] = int(
        max(10, min(80, int(prefs.get("party_gift_bond_below") or 42)))
    )
    prefs["party_gift_cooldown"] = int(
        max(2, min(30, int(prefs.get("party_gift_cooldown") or 6)))
    )
    prefs["party_min_food_keep"] = int(
        max(0, min(12, int(prefs.get("party_min_food_keep") or 2)))
    )
    prefs["party_min_hp_pots_keep"] = int(
        max(0, min(8, int(prefs.get("party_min_hp_pots_keep") or 1)))
    )
    player["auto_prefs"] = prefs
    return prefs


def _tick(player: Mapping[str, Any]) -> int:
    return int(
        player.get("auto_ticks")
        or player.get("_combat_round")
        or player.get("time_units")
        or 0
    )


def _is_safe_gift_item(
    player: Mapping[str, Any],
    reg: DataRegistry,
    item_id: str,
    rarity: str,
    prefs: Mapping[str, Any],
) -> bool:
    """Never gift emergency / rare / relic / key items."""
    iid = str(item_id or "")
    it = dict((reg.items or {}).get(iid) or {})
    if not it:
        return False
    try:
        from game.domain.bag_sell import is_relic_item, is_bulk_sell_protected

        if is_relic_item(iid, it):
            return False
        if is_bulk_sell_protected(iid, it, rarity, reg):
            # rare+ gear protected — also skip for gifts
            if str(it.get("kind") or "") in ("equipment",) or it.get("slot"):
                return False
    except Exception:
        if iid.startswith("relic_") or it.get("unique") or it.get("quest"):
            return False
    rar = str(rarity or "common").lower()
    if rar not in ("common", "uncommon", ""):
        return False
    # no combat potions as gifts (emergency stock)
    if it.get("heal_hp") or it.get("heal_mana") or "potion" in iid.lower():
        return False
    try:
        from game.domain.chest_loot import is_chest_item

        if is_chest_item(it):
            return False
    except Exception:
        pass
    # food only if surplus above keep
    try:
        from game.domain.needs import is_food_item
        from game.runtime.dungeon_auto import count_food

        if is_food_item(it):
            keep = int(prefs.get("party_min_food_keep") or 2)
            if count_food(player, reg) <= keep:
                return False
            return True
    except Exception:
        pass
    kind = str(it.get("kind") or "").lower()
    # prefer materials / scrap / common junk
    if kind in ("material", "mat", "junk", "scrap") or "mat" in iid.lower():
        return True
    # soft: cheap common non-equip other
    if kind not in ("equipment", "weapon", "armor", "accessory") and not it.get("slot"):
        price = int(it.get("price_world") or 0)
        if price <= 40 and rar in ("common", ""):
            return True
    return False


def _pick_cool_member(
    player: Mapping[str, Any],
    bond_below: int,
) -> Optional[Tuple[int, str, int]]:
    """Return (index, member_id, bond) for coolest member below threshold."""
    from game.domain.party import ensure_party, get_relationship

    ensure_party(player)  # type: ignore
    party = list(player.get("party") or [])
    best: Optional[Tuple[int, str, int]] = None
    for i, m in enumerate(party):
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id") or "")
        if not mid:
            continue
        rel = get_relationship(player, mid, m)
        if rel >= bond_below:
            continue
        if best is None or rel < best[2]:
            best = (i, mid, rel)
    return best


def _pick_gift_index(
    player: Mapping[str, Any],
    reg: DataRegistry,
    prefs: Mapping[str, Any],
) -> int:
    """First safe bag index for auto gift, or -1."""
    from game.domain.rarity import rarity_of_inventory_index

    ids = list(player.get("inventory_ids") or [])
    # prefer materials first: scan for material, then food, then other safe
    scored: List[Tuple[int, int]] = []  # (priority, index) lower better
    for i, iid in enumerate(ids):
        rid = rarity_of_inventory_index(player, i)
        if not _is_safe_gift_item(player, reg, str(iid), rid, prefs):
            continue
        it = (reg.items or {}).get(str(iid)) or {}
        kind = str(it.get("kind") or "").lower()
        pri = 2
        if kind in ("material", "mat") or "mat" in str(iid).lower():
            pri = 0
        else:
            try:
                from game.domain.needs import is_food_item

                if is_food_item(it):
                    pri = 1
            except Exception:
                pass
        scored.append((pri, i))
    if not scored:
        return -1
    scored.sort(key=lambda x: (x[0], x[1]))
    return scored[0][1]


def auto_party_care(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    context: str = "auto",
) -> List[str]:
    """
    One soft care pass for active party.
    Safe to call every dungeon/field auto tick.
    """
    notes: List[str] = []
    prefs = ensure_party_auto_prefs(player)
    if not prefs.get("party_care", True):
        return notes

    from game.domain.party import ensure_party, tick_relationship_decay

    ensure_party(player)
    # decay for known-out companions (idempotent slow)
    try:
        tick_relationship_decay(player, ticks=1)
    except Exception:
        pass

    party = list(player.get("party") or [])
    if not party:
        return notes

    if not prefs.get("party_gift", True):
        return notes

    # cooldown
    now = _tick(player)
    last = int(player.get("_party_gift_tick") or -999)
    cd = int(prefs.get("party_gift_cooldown") or 6)
    if now - last < cd and last >= 0:
        return notes

    cool = _pick_cool_member(player, int(prefs.get("party_gift_bond_below") or 42))
    if cool is None:
        return notes
    mi, mid, rel = cool
    gidx = _pick_gift_index(player, reg, prefs)
    if gidx < 0:
        return notes

    from game.domain.party import give_item_gift

    gift_notes = give_item_gift(player, reg, mi, gidx)
    if not gift_notes or gift_notes[0].startswith("ไม่มี"):
        return notes
    player["_party_gift_tick"] = now
    name = str((party[mi] if mi < len(party) else {}).get("name") or mid)
    msg = f"  ออโต้ทีม: ยื่นของเล็กๆ ให้「{name}」(สัมพันธ์ยังแผ่ว)"
    notes.append(msg)
    # keep one soft line from gift reaction
    for gn in gift_notes[1:3]:
        if gn.strip():
            notes.append(f"  {gn.strip()}")
            break
    try:
        from game.domain.needs import append_auto_care_note  # type: ignore

        append_auto_care_note(player, msg)
    except Exception:
        pass
    return notes
