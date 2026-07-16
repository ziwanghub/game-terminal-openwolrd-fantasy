"""
WO-004 P1.4 — Auto Inventory Management.
WO-021 — sell junk (passive gold) + optional auto-buy supplies.

Central place for auto-run bag care:
  · soft stock warnings (food / HP potions)
  · free bag space by selling (prefer) or dropping low-value junk
  · optional light auto-buy of early food/pots when gold enough
  · threshold consumable use (delegates to dungeon_auto helpers)

Does NOT: equip gear, craft, or touch unique/quest items.
Soft anti-spoiler logs only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.needs import append_auto_care_note, ensure_needs, get_needs, is_food_item

# Nested under player["auto_prefs"] for one prefs surface
DEFAULT_INV_AUTO: Dict[str, Any] = {
    "inv_manage": True,  # master switch
    "inv_min_food": 2,  # warn when food below this
    "inv_min_hp_pots": 1,  # warn when HP pots below this
    "inv_drop_junk": True,  # free space when bag nearly full (if sell off/fails)
    "inv_sell_junk": True,  # WO-021: sell junk for world gold instead of pure drop
    "inv_bag_free_slots": 2,  # try to keep this many free slots
    "inv_max_junk_drops": 3,  # per manage pass
    "auto_buy_supplies": True,  # WO-022 soft default ON
    "auto_buy_reserve": 50,
    "auto_buy_max": 2,
}

# Cheap early stock Auto may buy (traveling merchant style) — world currency only
_AUTO_BUY_CANDIDATES: Tuple[Tuple[str, str], ...] = (
    ("city_bread", "food"),
    ("hunter_ration", "food"),
    ("traveler_ration", "food"),
    ("potion_hp_small", "hp"),
    ("potion_hp", "hp"),
    ("potion_mana", "mp"),
)


def ensure_inv_auto_prefs(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    """Merge inventory-auto keys into auto_prefs (same dict as dungeon auto)."""
    from game.runtime.dungeon_auto import ensure_auto_prefs

    prefs = ensure_auto_prefs(player)
    for k, v in DEFAULT_INV_AUTO.items():
        if k not in prefs:
            prefs[k] = v
    # clamp
    prefs["inv_min_food"] = int(max(0, min(12, int(prefs.get("inv_min_food") or 2))))
    prefs["inv_min_hp_pots"] = int(max(0, min(8, int(prefs.get("inv_min_hp_pots") or 1))))
    prefs["inv_bag_free_slots"] = int(max(0, min(8, int(prefs.get("inv_bag_free_slots") or 2))))
    prefs["inv_max_junk_drops"] = int(max(0, min(6, int(prefs.get("inv_max_junk_drops") or 3))))
    prefs["inv_manage"] = bool(prefs.get("inv_manage", True))
    prefs["inv_drop_junk"] = bool(prefs.get("inv_drop_junk", True))
    prefs["inv_sell_junk"] = bool(prefs.get("inv_sell_junk", True))
    prefs["auto_buy_supplies"] = bool(prefs.get("auto_buy_supplies", True))
    prefs["auto_buy_reserve"] = int(max(0, min(500, int(prefs.get("auto_buy_reserve") or 50))))
    prefs["auto_buy_max"] = int(max(0, min(6, int(prefs.get("auto_buy_max") or 2))))
    player["auto_prefs"] = prefs
    return prefs


def _bag_cap(player: Mapping[str, Any]) -> int:
    try:
        from game.domain.inventory_sys import BAG_SOFT_CAP

        return int(player.get("bag_cap") or BAG_SOFT_CAP or 40)
    except Exception:
        return int(player.get("bag_cap") or 40)


def bag_used(player: Mapping[str, Any]) -> int:
    return len(list(player.get("inventory_ids") or []))


def bag_free_slots(player: Mapping[str, Any]) -> int:
    return max(0, _bag_cap(player) - bag_used(player))


def inventory_stock_snapshot(
    player: Mapping[str, Any], reg: DataRegistry
) -> Dict[str, int]:
    """Counts used by auto agent (soft)."""
    from game.runtime.dungeon_auto import count_food, count_potions

    return {
        "slots_used": bag_used(player),
        "slots_free": bag_free_slots(player),
        "bag_cap": _bag_cap(player),
        "food": count_food(player, reg),
        "hp_pots": count_potions(player, reg, kind="hp"),
        "mp_pots": count_potions(player, reg, kind="mp"),
    }


def _item_def(reg: DataRegistry, iid: str) -> Dict[str, Any]:
    return dict((reg.items or {}).get(str(iid)) or {"id": iid, "name": iid})


def _is_protected_item(it: Mapping[str, Any], iid: str) -> bool:
    """Never auto-drop these."""
    kind = str(it.get("kind") or "").lower()
    if kind in ("weapon", "armor", "accessory", "relic", "key", "quest"):
        return True
    if it.get("unique") or it.get("quest") or it.get("soulbound"):
        return True
    if is_food_item(it):
        return True
    if it.get("heal_hp") or it.get("heal_mana"):
        return True
    sid = str(iid).lower()
    if "potion" in sid or "key" in sid or "shard" in sid and "escape" in sid:
        return True
    if it.get("clear_status") or it.get("clear_all_debuffs"):
        return True
    return False


def _junk_score(it: Mapping[str, Any], iid: str, rarity: str) -> int:
    """
    Higher = more droppable.
    Prefer common materials / low price trash.
    """
    if _is_protected_item(it, iid):
        return -1
    rar = str(rarity or it.get("rarity") or "common").lower()
    rar_rank = {
        "common": 40,
        "uncommon": 20,
        "rare": 5,
        "sacred": 0,
        "legendary": -10,
        "divine": -20,
        "archdivine": -30,
        "mythic": -40,
    }.get(rar, 10)
    kind = str(it.get("kind") or "").lower()
    kind_b = 15 if kind in ("material", "mat", "junk", "scrap") else 5
    price = int(it.get("price_world") or 0)
    price_b = 10 if price < 30 else (5 if price < 80 else 0)
    name = str(it.get("name") or iid).lower()
    if "เศษ" in name or "scrap" in name or "chip" in str(iid).lower():
        kind_b += 10
    return rar_rank + kind_b + price_b


def find_junk_drop_candidates(
    player: Mapping[str, Any], reg: DataRegistry
) -> List[Tuple[int, int, str, str]]:
    """
    Returns list of (score, index, item_id, display_name) sorted score desc.
    """
    ids = list(player.get("inventory_ids") or [])
    rars = list(player.get("inventory_rarities") or [])
    while len(rars) < len(ids):
        rars.append("common")
    out: List[Tuple[int, int, str, str]] = []
    for i, iid in enumerate(ids):
        it = _item_def(reg, str(iid))
        rar = str(rars[i] if i < len(rars) else "common")
        sc = _junk_score(it, str(iid), rar)
        if sc < 0:
            continue
        nm = str(it.get("name") or iid)
        out.append((sc, i, str(iid), nm))
    out.sort(key=lambda x: (-x[0], -x[1]))  # high score first; stable high index drop
    return out


def _remove_inventory_at(player: MutableMapping[str, Any], idx: int, reg: DataRegistry) -> None:
    try:
        from game.domain.rarity import remove_inventory_at_index

        remove_inventory_at_index(player, idx, reg)
    except Exception:
        ids = list(player.get("inventory_ids") or [])
        rar = list(player.get("inventory_rarities") or [])
        inv = list(player.get("inventory") or [])
        if 0 <= idx < len(ids):
            ids.pop(idx)
        if 0 <= idx < len(rar):
            rar.pop(idx)
        if 0 <= idx < len(inv):
            inv.pop(idx)
        player["inventory_ids"] = ids
        player["inventory_rarities"] = rar
        player["inventory"] = inv


def _junk_sell_gold(
    player: Mapping[str, Any],
    reg: DataRegistry,
    iid: str,
    rarity: str,
) -> int:
    """Small world gold for junk sell (floor 1)."""
    it = _item_def(reg, iid)
    base = int(it.get("price_world") or 0)
    if base <= 0:
        base = 5  # scrap floor
    try:
        from game.domain.balance import sell_price

        return max(1, int(sell_price(base, reg, player, rarity=rarity or "common")))
    except Exception:
        return max(1, int(base * 0.25) or 1)


def auto_free_bag_space(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    need_free: int = 2,
    max_drops: int = 3,
    sell: Optional[bool] = None,
) -> List[str]:
    """
    Free bag slots by selling junk (WO-021 passive income) and/or dropping.
    Prefer sell when inv_sell_junk; drop only if sell off or as fallback.
    """
    notes: List[str] = []
    if need_free <= 0 or max_drops <= 0:
        return notes
    prefs = ensure_inv_auto_prefs(player)
    do_sell = bool(prefs.get("inv_sell_junk", True)) if sell is None else bool(sell)
    do_drop = bool(prefs.get("inv_drop_junk", True))
    if not do_sell and not do_drop:
        return notes

    actions = 0
    while bag_free_slots(player) < need_free and actions < max_drops:
        cands = find_junk_drop_candidates(player, reg)
        if not cands:
            notes.append("  ออโต้กระเป๋า: เต็ม แต่ไม่มีของทิ้ง/ขายได้ปลอดภัย")
            break
        _sc, idx, iid, nm = cands[0]
        ids = list(player.get("inventory_ids") or [])
        rars = list(player.get("inventory_rarities") or [])
        try:
            idx = ids.index(iid)
        except ValueError:
            idx = cands[0][1]
            if idx < 0 or idx >= len(ids):
                break
            iid = str(ids[idx])
            nm = str(_item_def(reg, iid).get("name") or iid)
        rar = str(rars[idx] if idx < len(rars) else "common")

        if do_sell:
            gold = _junk_sell_gold(player, reg, str(iid), rar)
            _remove_inventory_at(player, idx, reg)
            player["money_world"] = int(player.get("money_world") or 0) + gold
            try:
                from game.domain.stats import bump_stat

                bump_stat(player, "money_gained_total", gold)
            except Exception:
                pass
            actions += 1
            msg = f"  ออโต้กระเป๋า: ขาย「{nm}」+{gold} โลก (หาที่ว่าง)"
            notes.append(msg)
            append_auto_care_note(player, msg)
            continue

        # drop path
        _remove_inventory_at(player, idx, reg)
        actions += 1
        msg = f"  ออโต้กระเป๋า: ทิ้ง「{nm}」เพื่อหาที่ว่าง"
        notes.append(msg)
        append_auto_care_note(player, msg)
    return notes


def _auto_buy_budget(prefs: Mapping[str, Any]) -> Tuple[int, int, bool]:
    """
    WO-022: item_mode shapes spend.
    Returns (reserve, max_buy, allow_mp_topup).
    """
    mode = str(prefs.get("item_mode") or "normal").lower()
    reserve = int(prefs.get("auto_buy_reserve") or 50)
    max_buy = int(prefs.get("auto_buy_max") or 2)
    if mode == "thrift":
        # spend less: higher reserve, at most 1, no mp top-up
        reserve = max(reserve, 80)
        max_buy = min(max_buy, 1)
        return reserve, max_buy, False
    if mode == "safe":
        reserve = min(reserve, 30)
        max_buy = max(max_buy, 3)
        return reserve, max_buy, True
    return reserve, max_buy, False


def try_auto_buy_supplies(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """
    WO-021/022: light restock of food/HP pots via virtual traveling merchant.
    When auto_buy_supplies is on, gold > reserve, and stock below mins.
    Emergency: food=0 + hunger bad may buy 1 bread even if flag off (survive).
    """
    prefs = ensure_inv_auto_prefs(player)
    notes: List[str] = []
    if not prefs.get("inv_manage", True):
        return notes

    from game.domain.balance import scaled_price
    from game.domain.equipment import add_item
    from game.domain.needs import band, get_needs
    from game.runtime.dungeon_auto import count_food, count_potions

    food_n = count_food(player, reg)
    hun = int(get_needs(player).get("hunger") or 0)
    emergency = food_n <= 0 and band("hunger", hun) in ("bad", "crit")
    if not prefs.get("auto_buy_supplies") and not emergency:
        return notes

    reserve, max_buy, allow_mp = _auto_buy_budget(prefs)
    if emergency and not prefs.get("auto_buy_supplies"):
        # one cheap food only, keep a small reserve
        reserve = min(reserve, 15)
        max_buy = 1
        allow_mp = False

    min_food = int(prefs.get("inv_min_food") or 2)
    min_hp = int(prefs.get("inv_min_hp_pots") or 1)
    bought = 0

    def _need_kind(kind: str) -> bool:
        if kind == "food":
            return count_food(player, reg) < min_food or emergency
        if kind == "hp":
            if emergency and not prefs.get("auto_buy_supplies"):
                return False
            return count_potions(player, reg, kind="hp") < min_hp
        if kind == "mp":
            if not allow_mp:
                return False
            return count_potions(player, reg, kind="mp") < 1
        return False

    candidates = _AUTO_BUY_CANDIDATES
    if emergency and not prefs.get("auto_buy_supplies"):
        candidates = (("city_bread", "food"), ("hunter_ration", "food"))

    for iid, kind in candidates:
        if bought >= max_buy:
            break
        if not _need_kind(kind):
            continue
        if iid not in (reg.items or {}):
            continue
        it = dict((reg.items or {}).get(iid) or {})
        if it.get("price_heaven") or it.get("price_hell"):
            continue  # world-only auto buy
        base = int(it.get("price_world") or 0)
        if base <= 0:
            continue
        price = scaled_price(base, reg, player, rarity=str(it.get("rarity") or "common"))
        money = int(player.get("money_world") or 0)
        if money < price + reserve:
            continue
        if bag_free_slots(player) <= 0:
            notes.append("  ออโต้ซื้อ: กระเป๋าเต็ม — ข้ามเติมเสบียง")
            break
        player["money_world"] = money - price
        nm = add_item(player, iid, reg, rarity=str(it.get("rarity") or "common"))
        bought += 1
        tag = "ฉุกเฉิน" if emergency and not prefs.get("auto_buy_supplies") else "ออโต้ซื้อ"
        msg = f"  {tag}: {nm} (−{price} โลก) · เหลือ {player['money_world']}"
        notes.append(msg)
        append_auto_care_note(player, msg)

    return notes


def soft_stock_warnings(
    player: Mapping[str, Any],
    reg: DataRegistry,
    prefs: Mapping[str, Any],
) -> List[str]:
    snap = inventory_stock_snapshot(player, reg)
    notes: List[str] = []
    if snap["food"] < int(prefs.get("inv_min_food") or 0):
        notes.append(
            f"  ออโต้กระเป๋า: เสบียงเหลือน้อย ({snap['food']}) — ควรเติม"
        )
    if snap["hp_pots"] < int(prefs.get("inv_min_hp_pots") or 0):
        notes.append(
            f"  ออโต้กระเป๋า: ยาเลือดเหลือน้อย ({snap['hp_pots']})"
        )
    if snap["slots_free"] <= 0:
        notes.append("  ออโต้กระเป๋า: เต็ม — อาจทิ้งของไร้ค่า")
    return notes


def auto_use_consumables(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    force: bool = False,
) -> List[str]:
    """Threshold food/potion use — single entry for inventory auto."""
    from game.runtime.dungeon_auto import use_items_by_thresholds

    return list(use_items_by_thresholds(player, reg, force=force))


def auto_manage_inventory(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    context: str = "auto",
    force_consumables: bool = False,
) -> List[str]:
    """
    Full inventory-auto pass for one tick/care cycle.

    Order:
      1) free space if bag tight (sell junk prefer / drop)
      2) optional auto-buy supplies (WO-021)
      3) soft stock warnings
      4) use consumables by needs thresholds
    """
    prefs = ensure_inv_auto_prefs(player)
    if not prefs.get("inv_manage", True):
        return []

    notes: List[str] = []
    need_free = int(prefs.get("inv_bag_free_slots") or 2)

    if (
        (prefs.get("inv_sell_junk", True) or prefs.get("inv_drop_junk", True))
        and bag_free_slots(player) < need_free
    ):
        notes.extend(
            auto_free_bag_space(
                player,
                reg,
                need_free=need_free,
                max_drops=int(prefs.get("inv_max_junk_drops") or 3),
            )
        )

    # WO-021: optional restock when gold allows
    notes.extend(try_auto_buy_supplies(player, reg))

    for w in soft_stock_warnings(player, reg, prefs):
        notes.append(w)
        append_auto_care_note(player, w)

    # consumables (needs-driven)
    ensure_needs(player)
    used = auto_use_consumables(player, reg, force=force_consumables)
    notes.extend(used)

    if context and notes and context not in ("", "auto"):
        # optional prefix once
        pass
    return notes


def format_inv_auto_hud(player: Mapping[str, Any], reg: DataRegistry) -> str:
    snap = inventory_stock_snapshot(player, reg)
    return (
        f"กระเป๋า {snap['slots_used']}/{snap['bag_cap']} "
        f"· อาหาร {snap['food']} · ยาHP {snap['hp_pots']} · ยาMP {snap['mp_pots']}"
    )
