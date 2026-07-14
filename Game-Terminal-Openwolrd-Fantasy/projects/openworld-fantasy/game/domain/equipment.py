"""Equipment, cards, sockets — recompute combat stats."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry


def ensure_gear_fields(player: MutableMapping[str, Any]) -> None:
    player.setdefault("base_atk", int(player.get("bonus_atk", 5)))
    player.setdefault("base_max_hp", int(player.get("max_hp", 100)))
    player.setdefault("base_max_mana", int(player.get("max_mana", 50)))
    player.setdefault("base_skills", list(player.get("skills") or []))
    player.setdefault("inventory_ids", [])
    player.setdefault("card_bag", [])
    player.setdefault("equip_ids", {"weapon": None, "armor": None, "accessory": None})
    eq = dict(player.get("equip_ids") or {})
    eq.setdefault("weapon", None)
    eq.setdefault("armor", None)
    eq.setdefault("accessory", None)
    player["equip_ids"] = eq
    player.setdefault(
        "sockets",
        {"weapon": [], "armor": [], "accessory": []},
    )
    socks = dict(player.get("sockets") or {})
    socks.setdefault("weapon", [])
    socks.setdefault("armor", [])
    socks.setdefault("accessory", [])
    player["sockets"] = socks
    player.setdefault("upgrade_levels", {"weapon": 0, "armor": 0, "accessory": 0})
    ups = dict(player.get("upgrade_levels") or {})
    ups.setdefault("weapon", 0)
    ups.setdefault("armor", 0)
    ups.setdefault("accessory", 0)
    player["upgrade_levels"] = ups
    # display names cache
    player.setdefault("equip", {"weapon": None, "armor": None, "accessory": None})


def item_by_id(reg: DataRegistry, item_id: str) -> Optional[Dict[str, Any]]:
    return reg.items.get(item_id) or reg.cards.get(item_id)


def add_item(
    player: MutableMapping[str, Any],
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
) -> str:
    from game.domain.rarity import (
        append_item_rarity,
        ensure_inventory_rarity,
        format_rarity_tag,
        item_default_rarity,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    it = item_by_id(reg, item_id)
    if not it:
        return f"ไม่พบไอเทม {item_id}"
    kind = it.get("kind") or ("card" if item_id.startswith("card_") or item_id in reg.cards else "item")
    from game.domain.rarity import display_item_name

    rid = str(rarity or item_default_rarity(it, reg))
    shown = display_item_name(str(it.get("name", item_id)), rid, reg)
    if kind == "card" or item_id in reg.cards:
        bag = list(player.get("card_bag") or [])
        bag.append(item_id)
        player["card_bag"] = bag
        # legacy display list
        cards = list(player.get("cards") or [])
        cards.append(shown)
        player["cards"] = cards
        # cards bag rarities optional parallel
        cr = list(player.get("card_rarities") or [])
        cr.append(rid)
        player["card_rarities"] = cr
    else:
        ids = list(player.get("inventory_ids") or [])
        ids.append(item_id)
        player["inventory_ids"] = ids
        append_item_rarity(player, rid)
        inv = list(player.get("inventory") or [])
        inv.append(shown)
        player["inventory"] = inv
        # instance layer (owned piece)
        try:
            from game.domain.item_instances import append_instance, ensure_item_instances

            # append_instance re-syncs lists — avoid double-append by only ensuring if already tracked
            items = list(player.get("inventory_items") or [])
            if len(items) == len(ids) - 1:
                from game.domain.item_instances import make_instance, sync_legacy_from_instances

                items.append(
                    make_instance(item_id, player, reg, rarity=rid, location="bag")
                )
                player["inventory_items"] = items
            else:
                player["inventory_items"] = []
                ensure_item_instances(player, reg)
        except Exception:
            pass
    return shown


def remove_inventory_id(player: MutableMapping[str, Any], item_id: str, reg: DataRegistry) -> bool:
    from game.domain.rarity import ensure_inventory_rarity, pop_item_rarity_at

    ids = list(player.get("inventory_ids") or [])
    if item_id not in ids:
        return False
    idx = ids.index(item_id)
    ids.pop(idx)
    player["inventory_ids"] = ids
    ensure_inventory_rarity(player)
    pop_item_rarity_at(player, idx)
    name = (reg.items.get(item_id) or {}).get("name", item_id)
    inv = list(player.get("inventory") or [])
    # remove first display line that starts with name
    for i, line in enumerate(inv):
        if str(line).startswith(str(name)):
            inv.pop(i)
            break
    else:
        if name in inv:
            inv.remove(name)
    player["inventory"] = inv
    return True


def recompute_stats(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Rebuild bonus_atk / max_hp / max_mana / skills from base + gear + cards."""
    ensure_gear_fields(player)
    atk = int(player.get("base_atk", 5)) + int(player.get("alloc_atk_bonus", 0))
    max_hp = int(player.get("base_max_hp", 100)) + int(player.get("alloc_def_bonus", 0))
    max_mana = int(player.get("base_max_mana", 50)) + int(player.get("alloc_mag_bonus", 0)) // 2
    # party passive (recruited companions)
    atk += int(player.get("party_bonus_atk") or 0)
    max_hp += int(player.get("party_bonus_max_hp") or 0)
    max_mana += int(player.get("party_bonus_max_mana") or 0)
    pressure = int(player.get("pressure", 10))
    # reset pressure bonus from cards carefully: store base_pressure
    if "base_pressure" not in player:
        player["base_pressure"] = pressure
    pressure = int(player["base_pressure"]) + int(player.get("alloc_spd_bonus", 0)) // 3

    skills = list(player.get("base_skills") or [])
    # always keep progression skills that were unlocked beyond base
    unlocked = [s for s in (player.get("skills") or []) if s not in skills]
    # filter gear-granted from previous recompute using tag
    progression = [s for s in unlocked if not str(s).startswith("_gear_")]

    tags: List[str] = []
    on_hit: List[Dict[str, Any]] = []

    from game.domain.rarity import (
        equip_rarity_for_slot,
        format_rarity_tag,
        item_default_rarity,
        scaled_item_stats,
    )

    for slot in ("weapon", "armor", "accessory"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            player.setdefault("equip", {})[slot] = None
            continue
        it = reg.items.get(eid) or {}
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        rid = equip_rarity_for_slot(player, slot)
        if rid in (None, "None", ""):
            rid = item_default_rarity(it, reg)
        st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=slot)
        atk += st["atk"]
        max_hp += st["max_hp"]
        max_mana += st["max_mana"]
        for t in it.get("tags") or []:
            if t not in tags:
                tags.append(str(t))
        up_txt = f" +{up}" if up else ""
        rtag = format_rarity_tag(reg, rid)
        player.setdefault("equip", {})[slot] = f"{it.get('name', eid)}{up_txt} {rtag}"

        socks = list((player.get("sockets") or {}).get(slot) or [])
        socket_n = int(it.get("sockets", 0))
        # pad/trim
        while len(socks) < socket_n:
            socks.append(None)
        socks = socks[:socket_n]
        player.setdefault("sockets", {})[slot] = socks

        for cid in socks:
            if not cid:
                continue
            card = reg.cards.get(cid) or {}
            bon = card.get("bonuses") or {}
            atk += int(bon.get("atk", 0))
            max_hp += int(bon.get("max_hp", 0))
            max_mana += int(bon.get("max_mana", 0))
            pressure += int(bon.get("pressure", 0))
            for t in card.get("grant_tags") or []:
                if t not in tags:
                    tags.append(str(t))
            for sk in card.get("grant_skills") or []:
                if sk not in skills and sk not in progression:
                    progression.append(str(sk))
            if card.get("on_hit"):
                on_hit.append(dict(card["on_hit"]))

    # --- set bonuses ---
    set_counts: Dict[str, int] = {}
    for slot in ("weapon", "armor", "accessory"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            continue
        sid = (reg.items.get(eid) or {}).get("set_id")
        if sid:
            set_counts[str(sid)] = set_counts.get(str(sid), 0) + 1

    active_sets: List[str] = []
    set_flavors: List[str] = []
    for set_id, cnt in set_counts.items():
        sdef = (getattr(reg, "gear_sets", None) or {}).get(set_id) or {}
        if not sdef:
            continue
        need = int(sdef.get("pieces_required", 2))
        if cnt >= need:
            active_sets.append(str(sdef.get("name") or set_id))
            bon = sdef.get("bonuses") or {}
            atk += int(bon.get("atk", 0))
            max_hp += int(bon.get("max_hp", 0))
            max_mana += int(bon.get("max_mana", 0))
            pressure += int(bon.get("pressure", 0))
            for t in sdef.get("grant_tags") or []:
                if t not in tags:
                    tags.append(str(t))
            for sk in sdef.get("grant_skills") or []:
                if sk not in skills and sk not in progression:
                    progression.append(str(sk))
            if sdef.get("flavor"):
                set_flavors.append(str(sdef["flavor"]))

    # preserve HP/mana ratios roughly when max changes
    old_max_hp = max(1, int(player.get("max_hp", max_hp)))
    old_max_mp = max(1, int(player.get("max_mana", max_mana)))
    hp_ratio = float(player.get("hp", max_hp)) / old_max_hp
    mp_ratio = float(player.get("mana", max_mana)) / old_max_mp

    player["bonus_atk"] = atk
    player["max_hp"] = max_hp
    player["max_mana"] = max_mana
    player["pressure"] = pressure
    player["hp"] = max(1, min(max_hp, int(round(max_hp * hp_ratio))))
    player["mana"] = max(0, min(max_mana, int(round(max_mana * mp_ratio))))
    player["skills"] = list(dict.fromkeys(skills + progression + ["guard_basic"]))
    if "guard_basic" not in player["skills"]:
        player["skills"].append("guard_basic")
    player["gear_tags"] = tags
    player["on_hit_effects"] = on_hit
    player["active_sets"] = active_sets
    player["set_flavors"] = set_flavors


def equip_item(player: MutableMapping[str, Any], item_id: str, reg: DataRegistry) -> str:
    from game.domain.rarity import (
        append_item_rarity,
        ensure_inventory_rarity,
        equip_rarity_for_slot,
        format_rarity_tag,
        item_default_rarity,
        rarity_of_inventory_index,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    it = reg.items.get(item_id)
    if not it or it.get("kind") != "equipment":
        return "ไม่ใช่อุปกรณ์"
    if item_id not in (player.get("inventory_ids") or []):
        return "ไม่มีไอเทมนี้ในคลัง"
    slot = str(it.get("slot") or "weapon")
    if slot not in ("weapon", "armor", "accessory"):
        return "สวมช่องนี้ไม่ได้"

    # capture rarity + instance of the piece being equipped
    idx = list(player.get("inventory_ids") or []).index(item_id)
    new_rarity = rarity_of_inventory_index(player, idx)
    moved_inst = None
    try:
        from game.domain.item_instances import ensure_item_instances, pop_instance_at

        ensure_item_instances(player, reg)
        items = list(player.get("inventory_items") or [])
        if 0 <= idx < len(items) and str(items[idx].get("template_id")) == str(item_id):
            moved_inst = pop_instance_at(player, idx, reg)
        else:
            remove_inventory_id(player, item_id, reg)
            ensure_item_instances(player, reg)
    except Exception:
        remove_inventory_id(player, item_id, reg)
        moved_inst = None

    # unequip old back to inventory (keep its rarity + instance)
    old = (player.get("equip_ids") or {}).get(slot)
    old_r = equip_rarity_for_slot(player, slot)
    old_eq_inst = ((player.get("equip_instances") or {}).get(slot) if old else None)
    if old:
        ids = list(player.get("inventory_ids") or [])
        ids.append(old)
        player["inventory_ids"] = ids
        append_item_rarity(player, old_r or item_default_rarity(reg.items.get(old) or {}, reg))
        old_name = (reg.items.get(old) or {}).get("name", old)
        inv = list(player.get("inventory") or [])
        from game.domain.rarity import display_item_name as _din

        inv.append(_din(str(old_name), old_r or "common", reg))
        player["inventory"] = inv
        for cid in (player.get("sockets") or {}).get(slot) or []:
            if cid:
                bag = list(player.get("card_bag") or [])
                bag.append(cid)
                player["card_bag"] = bag
        player["cards"] = [
            str((reg.cards.get(c) or {}).get("name", c)) for c in (player.get("card_bag") or [])
        ]
        # return old instance to bag
        try:
            from game.domain.item_instances import ensure_item_instances, make_instance

            bag_items = list(player.get("inventory_items") or [])
            if old_eq_inst and isinstance(old_eq_inst, dict):
                back = dict(old_eq_inst)
                back["location"] = "bag"
                bag_items.append(back)
            else:
                bag_items.append(
                    make_instance(
                        str(old),
                        player,
                        reg,
                        rarity=str(old_r or "common"),
                        location="bag",
                    )
                )
            player["inventory_items"] = bag_items
            ensure_item_instances(player, reg)
        except Exception:
            pass

    if moved_inst is None:
        # already removed via remove_inventory_id path above if pop failed
        pass
    player.setdefault("equip_ids", {})[slot] = item_id
    er = dict(player.get("equip_rarities") or {})
    er[slot] = new_rarity
    player["equip_rarities"] = er
    n = int(it.get("sockets", 0))
    # keep sockets from instance if present
    if moved_inst and moved_inst.get("sockets"):
        player.setdefault("sockets", {})[slot] = list(moved_inst.get("sockets") or [None] * n)
    else:
        player.setdefault("sockets", {})[slot] = [None] * n
    # upgrade from instance if any
    ups = dict(player.get("upgrade_levels") or {})
    if moved_inst and int(moved_inst.get("upgrade") or 0) > 0:
        ups[slot] = int(moved_inst.get("upgrade") or 0)
    else:
        ups[slot] = 0
    player["upgrade_levels"] = ups
    # place equipped instance (preserve inst_id)
    try:
        from game.domain.item_instances import ensure_item_instances, make_instance

        eqi = dict(player.get("equip_instances") or {})
        if moved_inst:
            moved_inst = dict(moved_inst)
            moved_inst["location"] = f"equip:{slot}"
            moved_inst["rarity"] = new_rarity
            eqi[slot] = moved_inst
        else:
            eqi[slot] = make_instance(
                item_id,
                player,
                reg,
                rarity=new_rarity,
                upgrade=int(ups.get(slot) or 0),
                sockets=list((player.get("sockets") or {}).get(slot) or []),
                location=f"equip:{slot}",
            )
        player["equip_instances"] = eqi
        ensure_item_instances(player, reg)
    except Exception:
        pass
    recompute_stats(player, reg)
    from game.domain.rarity import display_item_name as _din2

    return (
        f"สวม {_din2(str(it.get('name')), new_rarity, reg)} ({slot}) แล้ว · ช่องการ์ด {n}"
    )


def unequip_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Move equipped piece back to inventory; cards in sockets return to card_bag."""
    from game.domain.rarity import (
        append_item_rarity,
        display_item_name,
        equip_rarity_for_slot,
        ensure_inventory_rarity,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    if slot not in ("weapon", "armor", "accessory"):
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    rid = equip_rarity_for_slot(player, slot)
    it = reg.items.get(eid) or {}
    # return socketed cards
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    # inventory
    ids = list(player.get("inventory_ids") or [])
    ids.append(eid)
    player["inventory_ids"] = ids
    append_item_rarity(player, rid or "common")
    inv = list(player.get("inventory") or [])
    inv.append(display_item_name(str(it.get("name") or eid), rid or "common", reg))
    player["inventory"] = inv
    # clear equip
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in (player.get("card_bag") or [])
    ]
    recompute_stats(player, reg)
    try:
        from game.domain.item_instances import ensure_item_instances

        player["inventory_items"] = []
        player["equip_instances"] = dict(player.get("equip_instances") or {})
        player["equip_instances"][slot] = None
        ensure_item_instances(player, reg)
    except Exception:
        pass
    from game.domain.item_codes import item_code

    code = item_code(str(eid), reg)
    shown = display_item_name(str(it.get("name") or eid), rid or "common", reg)
    return f"ถอด {code} {shown} กลับเข้ากระเป๋าแล้ว"


def sell_equipped_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Sell currently equipped piece for world money (no shop tax UI)."""
    from game.domain.balance import sell_price
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name, equip_rarity_for_slot

    ensure_gear_fields(player)
    if slot not in ("weapon", "armor", "accessory"):
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    it = reg.items.get(eid) or {}
    rid = equip_rarity_for_slot(player, slot)
    base = int(it.get("price_world") or 40)
    pay = sell_price(base, reg, player, rarity=rid)
    # return socket cards first
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    player["money_world"] = int(player.get("money_world") or 0) + pay
    recompute_stats(player, reg)
    shown = display_item_name(str(it.get("name") or eid), rid, reg)
    return f"ขาย {item_code(str(eid), reg)} {shown} ได้เงินโลก +{pay}"


def discard_equipped_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Destroy equipped piece permanently; socket cards return to bag."""
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name, equip_rarity_for_slot

    ensure_gear_fields(player)
    if slot not in ("weapon", "armor", "accessory"):
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    it = reg.items.get(eid) or {}
    rid = equip_rarity_for_slot(player, slot)
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    recompute_stats(player, reg)
    shown = display_item_name(str(it.get("name") or eid), rid, reg)
    return f"ทิ้ง {item_code(str(eid), reg)} {shown} แล้ว (หายถาวร)"


def _slot_label(slot: str) -> str:
    return {"weapon": "อาวุธ", "armor": "เกราะ", "accessory": "เครื่องประดับ"}.get(slot, slot)


def socket_card(
    player: MutableMapping[str, Any],
    slot: str,
    socket_index: int,
    card_id: str,
    reg: DataRegistry,
) -> str:
    ensure_gear_fields(player)
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ยังไม่มี{slot}"
    it = reg.items.get(eid) or {}
    socks = list((player.get("sockets") or {}).get(slot) or [])
    n = int(it.get("sockets", 0))
    if socket_index < 0 or socket_index >= n:
        return "ช่องไม่ถูกต้อง"
    if card_id not in (player.get("card_bag") or []):
        return "ไม่มีการ์ดนี้"
    card = reg.cards.get(card_id) or {}
    compat = list(card.get("compatible") or ["weapon", "armor"])
    if slot not in compat and "any" not in compat:
        return f"การ์ดนี้ใส่{slot}ไม่ได้"

    # return previous card
    prev = socks[socket_index] if socket_index < len(socks) else None
    bag = list(player.get("card_bag") or [])
    bag.remove(card_id)
    if prev:
        bag.append(prev)
    player["card_bag"] = bag

    while len(socks) < n:
        socks.append(None)
    socks[socket_index] = card_id
    player.setdefault("sockets", {})[slot] = socks

    # sync display cards list roughly
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in bag
    ]
    recompute_stats(player, reg)
    return f"ใส่ {(card.get('name') or card_id)} ใน {slot} ช่อง {socket_index + 1}"


def unsocket_card(player: MutableMapping[str, Any], slot: str, socket_index: int, reg: DataRegistry) -> str:
    ensure_gear_fields(player)
    socks = list((player.get("sockets") or {}).get(slot) or [])
    if socket_index < 0 or socket_index >= len(socks) or not socks[socket_index]:
        return "ช่องว่าง"
    cid = socks[socket_index]
    socks[socket_index] = None
    player.setdefault("sockets", {})[slot] = socks
    bag = list(player.get("card_bag") or [])
    bag.append(cid)
    player["card_bag"] = bag
    player["cards"] = [str((reg.cards.get(c) or {}).get("name", c)) for c in bag]
    recompute_stats(player, reg)
    return f"ถอดการ์ดจาก {slot} ช่อง {socket_index + 1}"


def gear_attack_bonus_elements(player: Mapping[str, Any]) -> List[str]:
    return list(player.get("gear_tags") or [])


def count_materials(player: Mapping[str, Any], mat_id: str) -> int:
    return sum(1 for x in (player.get("inventory_ids") or []) if x == mat_id)


def consume_materials(player: MutableMapping[str, Any], mat_id: str, n: int, reg: DataRegistry) -> bool:
    if count_materials(player, mat_id) < n:
        return False
    for _ in range(n):
        if not remove_inventory_id(player, mat_id, reg):
            return False
    return True


def upgrade_cost(slot: str, level: int) -> Dict[str, int]:
    """
    Material costs for next upgrade.
    Early game ( +0→+1, +1→+2 ) softer so starters can upgrade once;
    mid/late still steeper.
    """
    nxt = level + 1
    acc = 0.85 if slot == "accessory" else 1.0
    # Early curve (playtest: first upgrade should be reachable ~100–150 world gold)
    if nxt == 1:
        return {
            "upgrade_mat": 1,
            "rare_mat": 0,
            "money": int(40 * acc),
        }
    if nxt == 2:
        return {
            "upgrade_mat": 1,
            "rare_mat": 0,
            "money": int(60 * acc),
        }
    if nxt == 3:
        return {
            "upgrade_mat": max(1, int(2 * acc)),
            "rare_mat": 0,
            "money": int(90 * acc),
        }
    return {
        "upgrade_mat": max(1, int((1 + nxt // 2 + (1 if nxt >= 5 else 0)) * acc)),
        "rare_mat": (1 if nxt >= 4 else 0) + (1 if nxt >= 7 else 0),
        "money": int((45 + nxt * 40 + (nxt ** 2) * 3) * acc),
    }


def upgrade_equipped(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    ensure_gear_fields(player)
    if slot not in ("weapon", "armor", "accessory"):
        return "ช่องไม่ถูกต้อง"
    if not (player.get("equip_ids") or {}).get(slot):
        return f"ยังไม่มี{slot}สวมอยู่"
    ups = dict(player.get("upgrade_levels") or {})
    cur = int(ups.get(slot, 0))
    if cur >= 10:
        return "อัปเกรดถึงขีด (10) แล้ว — ขยายได้ใน data ภายหลัง"
    cost = upgrade_cost(slot, cur)
    money = int(player.get("money_world", 0))
    if money < cost["money"]:
        return f"เงินไม่พอ (ต้องการ {cost['money']})"
    if count_materials(player, "upgrade_mat") < cost["upgrade_mat"]:
        return f"วัสดุอัพเกรดไม่พอ (ต้องการ {cost['upgrade_mat']})"
    if cost["rare_mat"] and count_materials(player, "rare_mat") < cost["rare_mat"]:
        return f"วัสดุหายากไม่พอ (ต้องการ {cost['rare_mat']})"
    player["money_world"] = money - cost["money"]
    consume_materials(player, "upgrade_mat", cost["upgrade_mat"], reg)
    if cost["rare_mat"]:
        consume_materials(player, "rare_mat", cost["rare_mat"], reg)
    ups[slot] = cur + 1
    player["upgrade_levels"] = ups
    recompute_stats(player, reg)
    return f"อัปเกรด {slot} → +{ups[slot]} สำเร็จ! (ATK/HP ตามชิ้นเกียร์เพิ่ม)"


def describe_loadout(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_gear_fields(player)  # type: ignore
    lines = []
    labels = {"weapon": "weapon", "armor": "armor", "accessory": "accessory"}
    for slot in ("weapon", "armor", "accessory"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            lines.append(f"{labels[slot]}: -")
            continue
        name = (reg.items.get(eid) or {}).get("name", eid)
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        socks = (player.get("sockets") or {}).get(slot) or []
        sock_txt = []
        for cid in socks:
            if cid:
                sock_txt.append((reg.cards.get(cid) or {}).get("name", cid))
            else:
                sock_txt.append("ว่าง")
        lines.append(
            f"{slot}: {name} +{up}  การ์ด[{', '.join(sock_txt) if sock_txt else '-'}]"
        )
        cost = upgrade_cost(slot, up)
        lines.append(
            f"   อัปถัดไป: เงิน {cost['money']} · วัสดุ {cost['upgrade_mat']}"
            + (f" · หายาก {cost['rare_mat']}" if cost["rare_mat"] else "")
        )
    if player.get("card_bag"):
        names = [(reg.cards.get(c) or {}).get("name", c) for c in player["card_bag"]]
        lines.append("การ์ดในถุง: " + ", ".join(str(n) for n in names))
    else:
        lines.append("การ์ดในถุง: -")
    um = count_materials(player, "upgrade_mat")
    rm = count_materials(player, "rare_mat")
    lines.append(f"วัสดุ: อัพเกรด x{um} · หายาก x{rm}")
    lines.append(
        f"ATK {player.get('bonus_atk')} · HP {player.get('hp')}/{player.get('max_hp')} · "
        f"MP {player.get('mana')}/{player.get('max_mana')}"
    )
    if player.get("gear_tags"):
        lines.append("แท็กเกียร์: " + ", ".join(player["gear_tags"]))
    if player.get("active_sets"):
        lines.append("เซ็ต: " + ", ".join(player["active_sets"]))
        for fl in player.get("set_flavors") or []:
            lines.append(f"  “{fl}”")
    return lines

