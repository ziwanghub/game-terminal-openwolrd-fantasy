"""
WO-INV-3 — Auto organize bag storage (sort slots, keep stacks).

Order: category (fixed) → rarity rank desc → name → id
Does not touch card_bag order beyond optional stable sort.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry

# display / sort category rank (lower = earlier)
_CAT_ORDER = {
    "equipment": 0,
    "relic": 1,
    "weapon": 0,
    "food": 2,
    "healing": 3,
    "chest": 4,
    "material": 5,
    "card": 6,
    "other": 7,
}


def organize_bag(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """
    Sort inventory slots in place. Preserves qty/rarity/instance alignment.
    Returns soft notes.
    """
    from game.domain.bag_stack import collapse_stackable_slots, ensure_inventory_qty, qty_at
    from game.domain.inventory_sys import item_category
    from game.domain.rarity import display_item_name, tier_rank

    # merge stacks first
    freed = collapse_stackable_slots(player, reg)
    ensure_inventory_qty(player)

    ids = list(player.get("inventory_ids") or [])
    if not ids:
        return ["กระเป๋าว่าง — ไม่ต้องจัด"]

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

    rows: List[Tuple[Any, ...]] = []
    for i, iid in enumerate(ids):
        cat = item_category(str(iid), reg)
        rid = str(rares[i] if i < len(rares) else "common")
        rk = tier_rank(reg, rid)
        it = (reg.items or {}).get(str(iid)) or {}
        nm = str(it.get("name") or iid)
        q = max(1, int(qtys[i] if i < len(qtys) else 1))
        inst = items[i] if i < len(items) and isinstance(items[i], dict) else None
        rows.append(
            (
                _CAT_ORDER.get(cat, 9),
                -int(rk),  # higher rarity first within cat
                nm,
                str(iid),
                rid,
                q,
                inv[i] if i < len(inv) else nm,
                inst,
            )
        )
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))

    new_ids: List[str] = []
    new_rares: List[str] = []
    new_qtys: List[int] = []
    new_inv: List[str] = []
    new_items: List[Dict[str, Any]] = []
    for _co, _rk, nm, iid, rid, q, inv_line, inst in rows:
        new_ids.append(iid)
        new_rares.append(rid)
        new_qtys.append(q)
        shown = display_item_name(nm, rid, reg)
        new_inv.append(str(inv_line or shown))
        if inst is not None:
            inst = dict(inst)
            inst["qty"] = q
            inst["rarity"] = rid
            inst["location"] = "bag"
            new_items.append(inst)

    player["inventory_ids"] = new_ids
    player["inventory_rarities"] = new_rares
    player["inventory_qty"] = new_qtys
    player["inventory"] = new_inv
    if new_items and len(new_items) == len(new_ids):
        player["inventory_items"] = new_items
    else:
        try:
            from game.domain.item_instances import ensure_item_instances

            player["inventory_items"] = []
            ensure_item_instances(player, reg, force_rebuild=True)
            insts = list(player.get("inventory_items") or [])
            for j, inst in enumerate(insts):
                if isinstance(inst, dict) and j < len(new_qtys):
                    inst["qty"] = new_qtys[j]
            player["inventory_items"] = insts
        except Exception:
            pass
    ensure_inventory_qty(player)

    notes = [f"จัดเรียงกระเป๋าแล้ว · {len(new_ids)} ช่อง"]
    if freed:
        notes.append(f"รวมกองซ้ำ · ว่างขึ้น {freed} ช่อง")
    return notes
