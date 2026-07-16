"""
WO-INV-1 — True stack + soft-cap helpers.

Stack rule: same item_id + rarity share one bag *slot* with qty >= 1.
Stackable kinds: consumable / material / food / healing / sealed chests / other non-gear.
Non-stackable: equipment, relics, unique/quest/soulbound, items with equip slots.

Soft cap counts *slots* (stacks + unique pieces + cards), not total unit count.
Adding into an existing stack does not need a free slot.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def ensure_inventory_qty(player: MutableMapping[str, Any]) -> None:
    """Keep inventory_qty parallel to inventory_ids (default 1 per slot)."""
    ids = list(player.get("inventory_ids") or [])
    qtys = list(player.get("inventory_qty") or [])
    while len(qtys) < len(ids):
        qtys.append(1)
    if len(qtys) > len(ids):
        qtys = qtys[: len(ids)]
    # clamp invalid
    qtys = [max(1, int(q or 1)) for q in qtys]
    player["inventory_qty"] = qtys
    # mirror qty onto inventory_items when lengths match
    items = list(player.get("inventory_items") or [])
    if items and len(items) == len(ids):
        for i, inst in enumerate(items):
            if isinstance(inst, dict):
                inst["qty"] = int(qtys[i])
        player["inventory_items"] = items


def qty_at(player: Mapping[str, Any], index: int) -> int:
    ids = list(player.get("inventory_ids") or [])
    if index < 0 or index >= len(ids):
        return 0
    qtys = list(player.get("inventory_qty") or [])
    if index < len(qtys):
        return max(1, int(qtys[index] or 1))
    # fall back to inventory_items
    items = list(player.get("inventory_items") or [])
    if index < len(items) and isinstance(items[index], dict):
        return max(1, int(items[index].get("qty") or 1))
    return 1


def set_qty_at(player: MutableMapping[str, Any], index: int, qty: int) -> None:
    ensure_inventory_qty(player)
    qtys = list(player.get("inventory_qty") or [])
    if index < 0 or index >= len(qtys):
        return
    qtys[index] = max(1, int(qty))
    player["inventory_qty"] = qtys
    items = list(player.get("inventory_items") or [])
    if index < len(items) and isinstance(items[index], dict):
        items[index]["qty"] = qtys[index]
        player["inventory_items"] = items


def is_stackable_item(
    item_id: str,
    reg: Optional[DataRegistry],
    it: Optional[Mapping[str, Any]] = None,
) -> bool:
    """True when this template may share a slot by (id, rarity)."""
    iid = str(item_id or "")
    if not iid:
        return False
    meta: Mapping[str, Any] = it or {}
    if reg is not None and not meta:
        meta = (reg.items or {}).get(iid) or (reg.cards or {}).get(iid) or {}
    if not meta and reg is not None and (iid in (reg.cards or {}) or iid.startswith("card_")):
        return False  # cards live in card_bag
    if meta.get("unique") or meta.get("quest") or meta.get("soulbound"):
        return False
    kind = str(meta.get("kind") or "").lower()
    if kind in ("equipment", "weapon", "armor", "accessory", "relic", "card"):
        return False
    slot = str(meta.get("slot") or "")
    if slot:
        try:
            from game.domain.equipment import EQUIP_SLOTS, normalize_slot

            if normalize_slot(slot) in EQUIP_SLOTS or slot in (
                "weapon",
                "armor",
                "accessory",
            ):
                return False
        except Exception:
            if slot in ("weapon", "armor", "accessory"):
                return False
    if int(meta.get("sockets") or 0) > 0:
        return False
    # consumable / material / food / healing / chest / scrap
    if kind in ("material", "consumable", "item", "chest", "junk", "scrap", ""):
        return True
    if "mat" in iid.lower() or kind == "material":
        return True
    if meta.get("heal_hp") or meta.get("heal_mana") or meta.get("clear_status"):
        return True
    if meta.get("food_tier") or meta.get("hunger_relief"):
        return True
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if any(t in ("food", "consumable", "material", "chest") for t in tags):
        return True
    if meta.get("chest_rank") or "chest" in iid.lower():
        return True
    # default: non-equipment without slot stacks (soft potions etc.)
    if kind not in ("equipment", "weapon", "armor", "accessory", "relic"):
        return True
    return False


def find_stack_index(
    player: Mapping[str, Any],
    item_id: str,
    rarity: str = "common",
) -> int:
    """First bag index matching (item_id, rarity). -1 if none."""
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    rid = str(rarity or "common")
    for i, iid in enumerate(ids):
        if str(iid) != str(item_id):
            continue
        r = str(rares[i] if i < len(rares) else "common") or "common"
        if r == rid:
            return i
    return -1


def count_item_units(
    player: Mapping[str, Any],
    item_id: str,
    *,
    rarity: Optional[str] = None,
) -> int:
    """Total units of item_id (optionally filter rarity)."""
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    total = 0
    for i, iid in enumerate(ids):
        if str(iid) != str(item_id):
            continue
        if rarity is not None:
            r = str(rares[i] if i < len(rares) else "common") or "common"
            if r != str(rarity):
                continue
        total += qty_at(player, i)
    return total


def collapse_stackable_slots(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> int:
    """
    Merge stackable (id, rarity) rows into single slots with summed qty.
    Returns number of slots freed by merge.
    """
    ensure_inventory_qty(player)
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        player.setdefault("inventory_qty", [])
        return 0
    rares = list(player.get("inventory_rarities") or [])
    qtys = list(player.get("inventory_qty") or [])
    inv = list(player.get("inventory") or [])
    items = list(player.get("inventory_items") or [])
    while len(rares) < len(ids):
        rares.append("common")
    while len(qtys) < len(ids):
        qtys.append(1)
    while len(inv) < len(ids):
        inv.append("")

    new_ids: List[str] = []
    new_rares: List[str] = []
    new_qtys: List[int] = []
    new_inv: List[str] = []
    new_items: List[Dict[str, Any]] = []
    # key -> index in new_*
    key_to_i: Dict[Tuple[str, str], int] = {}

    before = len(ids)
    for i, iid in enumerate(ids):
        rid = str(rares[i] if i < len(rares) else "common") or "common"
        q = max(1, int(qtys[i] if i < len(qtys) else 1) or 1)
        stackable = True
        if reg is not None:
            stackable = is_stackable_item(str(iid), reg)
        key = (str(iid), rid)
        if stackable and key in key_to_i:
            j = key_to_i[key]
            new_qtys[j] = new_qtys[j] + q
            if j < len(new_items) and isinstance(new_items[j], dict):
                new_items[j]["qty"] = new_qtys[j]
            continue
        key_to_i[key] = len(new_ids)
        new_ids.append(str(iid))
        new_rares.append(rid)
        new_qtys.append(q)
        new_inv.append(str(inv[i] if i < len(inv) else iid))
        if i < len(items) and isinstance(items[i], dict):
            inst = dict(items[i])
            inst["qty"] = q
            new_items.append(inst)
        elif items:
            # length mismatch — rebuild later
            pass

    player["inventory_ids"] = new_ids
    player["inventory_rarities"] = new_rares
    player["inventory_qty"] = new_qtys
    player["inventory"] = new_inv[: len(new_ids)]
    if new_items and len(new_items) == len(new_ids):
        player["inventory_items"] = new_items
    elif player.get("inventory_items"):
        # force rebuild from legacy with qty
        try:
            from game.domain.item_instances import ensure_item_instances

            player["inventory_items"] = []
            ensure_item_instances(player, reg, force_rebuild=True)
            # re-apply qty onto instances
            insts = list(player.get("inventory_items") or [])
            for j, inst in enumerate(insts):
                if isinstance(inst, dict) and j < len(new_qtys):
                    inst["qty"] = new_qtys[j]
            player["inventory_items"] = insts
        except Exception:
            pass
    return max(0, before - len(new_ids))


def bag_slots_used(player: Mapping[str, Any]) -> int:
    """Slot count for cap: inventory stacks + card_bag entries."""
    return len(player.get("inventory_ids") or []) + len(player.get("card_bag") or [])


def _soft_cap(player: Mapping[str, Any]) -> int:
    try:
        from game.domain.inventory_sys import BAG_SOFT_CAP

        return int(player.get("bag_cap") or BAG_SOFT_CAP or 40)
    except Exception:
        return int(player.get("bag_cap") or 40)


def slots_full(player: Mapping[str, Any]) -> bool:
    return bag_slots_used(player) >= _soft_cap(player)


def can_accept_item(
    player: Mapping[str, Any],
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: str = "common",
    amount: int = 1,
) -> bool:
    """
    True if we can add `amount` units:
    - stack into existing stackable slot, or
    - open a new slot when not full.
    """
    rid = str(rarity or "common")
    # cards: 1 card = 1 slot (no stack merge in card_bag)
    if item_id in (reg.cards or {}) or str(item_id).startswith("card_"):
        return not slots_full(player)

    if is_stackable_item(item_id, reg) and find_stack_index(player, item_id, rid) >= 0:
        return True
    return not slots_full(player)


def remove_units_at(
    player: MutableMapping[str, Any],
    index: int,
    reg: DataRegistry,
    *,
    amount: int = 1,
) -> Optional[Tuple[str, str, int]]:
    """
    Remove up to `amount` units from slot index.
    If qty hits 0, remove the whole slot.
    Returns (item_id, rarity, removed_count) or None.
    """
    from game.domain.rarity import ensure_inventory_rarity, remove_inventory_at_index

    ensure_inventory_qty(player)
    ensure_inventory_rarity(player)
    ids = list(player.get("inventory_ids") or [])
    if index < 0 or index >= len(ids):
        return None
    q = qty_at(player, index)
    take = max(1, int(amount or 1))
    take = min(take, q)
    iid = str(ids[index])
    rares = list(player.get("inventory_rarities") or [])
    rid = str(rares[index] if index < len(rares) else "common")
    if take < q:
        set_qty_at(player, index, q - take)
        return iid, rid, take
    # remove whole slot
    remove_inventory_at_index(player, index, reg)
    # also drop qty entry (remove_inventory_at_index may not know qty)
    ensure_inventory_qty(player)
    return iid, rid, take


def remove_one_unit(
    player: MutableMapping[str, Any],
    item_id: str,
    reg: DataRegistry,
) -> bool:
    """Remove one unit of item_id (first matching slot)."""
    ids = list(player.get("inventory_ids") or [])
    try:
        idx = ids.index(item_id)
    except ValueError:
        return False
    res = remove_units_at(player, idx, reg, amount=1)
    return res is not None
