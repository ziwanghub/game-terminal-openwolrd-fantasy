"""
WO-INV-2 — Bulk sell helpers + sell-price for inventory rows.

Manual shop: sell one unit, whole stack, whole category, or all common.
Never bulk-sell protected pieces (relic / unique / quest / divine_burden).
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry


def is_relic_item(item_id: str, it: Optional[Mapping[str, Any]] = None) -> bool:
    """True for divine-burden / relic_* / kind=relic / tag relic."""
    iid = str(item_id or "")
    meta = dict(it or {})
    if meta.get("divine_burden") or meta.get("force_burden"):
        return True
    if iid.startswith("relic_"):
        return True
    kind = str(meta.get("kind") or "").lower()
    if kind == "relic":
        return True
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if "relic" in tags or "divine" in tags and meta.get("latent_atk_pct"):
        return True
    # short codes rl_*
    code = str(meta.get("code") or "")
    if code.startswith("rl_"):
        return True
    return False


def is_bulk_sell_protected(
    item_id: str,
    it: Mapping[str, Any],
    rarity: str,
    reg: Optional[DataRegistry] = None,
) -> bool:
    """Pieces bulk sell must never touch without explicit single-item sell."""
    if is_relic_item(item_id, it):
        return True
    if it.get("unique") or it.get("quest") or it.get("soulbound"):
        return True
    kind = str(it.get("kind") or "").lower()
    if kind in ("key", "quest"):
        return True
    sid = str(item_id).lower()
    if "key" in sid or sid.endswith("_key"):
        return True
    # high rarity equipment protected from bulk
    try:
        from game.domain.rarity import tier_rank

        rk = tier_rank(reg, str(rarity or "common"))
        if rk >= 3 and (
            kind in ("equipment", "weapon", "armor", "accessory")
            or it.get("slot")
        ):
            return True  # rare+
    except Exception:
        pass
    return False


def compute_sell_offer(
    player: Mapping[str, Any],
    reg: DataRegistry,
    item_id: str,
    rarity: str,
    *,
    shop: Optional[Mapping[str, Any]] = None,
    qty: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Price for selling `qty` units of one stack row.
    Returns {cur, unit_price, total, accepted, tax_rate} or None if missing.
    """
    from game.domain.balance import sell_breakdown
    from game.domain.rarity import rarity_price_mult, tier_rank

    shop = shop or {}
    it = (reg.items or {}).get(str(item_id)) or (reg.cards or {}).get(str(item_id)) or {}
    if not it and not str(item_id).startswith("card_"):
        return None
    rid = str(rarity or "common")
    min_rk = int(shop.get("min_rarity_rank") or shop.get("min_rank") or 1)
    max_rk = int(shop.get("max_rarity_rank") or shop.get("max_rank") or 8)
    # cards cheap fixed
    if str(item_id) in (reg.cards or {}) or str(item_id).startswith("card_"):
        unit = 8
        return {
            "cur": "money_world",
            "unit_price": unit,
            "total": unit * max(1, int(qty)),
            "accepted": True,
            "tax_rate": 0.0,
            "qty": max(1, int(qty)),
        }
    rk = tier_rank(reg, rid)
    accepted = min_rk <= rk <= max_rk
    base = int(
        it.get("price_world") or it.get("price_heaven") or it.get("price_hell") or 10
    )
    q = max(1, int(qty or 1))
    kind = str(it.get("kind") or "")
    iid = str(item_id)
    if it.get("price_heaven") and not it.get("price_world"):
        cur = "money_heaven"
        bd = sell_breakdown(
            base, reg, player, rarity=rid, shop=shop, item_kind=kind, item_id=iid
        )
        buy = max(1, int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid))))
        unit = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
        return {
            "cur": cur,
            "unit_price": unit,
            "total": unit * q,
            "accepted": accepted,
            "tax_rate": float(bd.get("tax_rate") or 0),
            "qty": q,
        }
    if it.get("price_hell") and not it.get("price_world"):
        cur = "money_hell"
        bd = sell_breakdown(
            base, reg, player, rarity=rid, shop=shop, item_kind=kind, item_id=iid
        )
        buy = max(1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid))))
        unit = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
        return {
            "cur": cur,
            "unit_price": unit,
            "total": unit * q,
            "accepted": accepted,
            "tax_rate": float(bd.get("tax_rate") or 0),
            "qty": q,
        }
    cur = "money_world"
    bd = sell_breakdown(
        base, reg, player, rarity=rid, shop=shop, item_kind=kind, item_id=iid
    )
    unit = int(bd["net"])
    return {
        "cur": cur,
        "unit_price": unit,
        "total": unit * q,
        "accepted": accepted,
        "tax_rate": float(bd.get("tax_rate") or 0),
        "qty": q,
    }


def list_bulk_sell_candidates(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    category: Optional[str] = None,
    common_only: bool = False,
    shop: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Candidate bag rows for bulk sell.
    Each: {index, id, rarity, qty, category, offer, name}
    """
    from game.domain.bag_stack import qty_at
    from game.domain.inventory_sys import item_category
    from game.domain.rarity import display_item_name, rarity_of_inventory_index

    out: List[Dict[str, Any]] = []
    ids = list(player.get("inventory_ids") or [])
    for i, iid in enumerate(ids):
        cat = item_category(str(iid), reg)
        if category and cat != category:
            continue
        it = (reg.items or {}).get(str(iid)) or {}
        rid = rarity_of_inventory_index(player, i)
        if common_only and str(rid).lower() not in ("common", ""):
            continue
        if is_bulk_sell_protected(str(iid), it, rid, reg):
            continue
        # chests not bulk by default (open instead)
        if cat == "chest":
            continue
        q = qty_at(player, i)
        offer = compute_sell_offer(player, reg, str(iid), rid, shop=shop, qty=q)
        if not offer or not offer.get("accepted"):
            continue
        shown = display_item_name(str(it.get("name") or iid), rid, reg)
        out.append(
            {
                "index": i,
                "id": str(iid),
                "rarity": rid,
                "qty": q,
                "category": cat,
                "offer": offer,
                "name": shown,
            }
        )
    return out


def preview_bulk_sell(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    category: Optional[str] = None,
    common_only: bool = False,
    shop: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    cands = list_bulk_sell_candidates(
        player, reg, category=category, common_only=common_only, shop=shop
    )
    total_units = sum(int(c.get("qty") or 1) for c in cands)
    # group gold by currency
    by_cur: Dict[str, int] = {}
    for c in cands:
        off = c.get("offer") or {}
        cur = str(off.get("cur") or "money_world")
        by_cur[cur] = by_cur.get(cur, 0) + int(off.get("total") or 0)
    return {
        "candidates": cands,
        "slots": len(cands),
        "units": total_units,
        "by_cur": by_cur,
    }


def execute_bulk_sell(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    category: Optional[str] = None,
    common_only: bool = False,
    shop: Optional[Mapping[str, Any]] = None,
) -> Tuple[int, Dict[str, int], List[str]]:
    """
    Sell all matching candidates (whole stacks).
    Returns (units_sold, currency_gains, notes).
    """
    from game.domain.rarity import remove_inventory_at_index

    prev = preview_bulk_sell(
        player, reg, category=category, common_only=common_only, shop=shop
    )
    cands = list(prev.get("candidates") or [])
    if not cands:
        return 0, {}, ["ไม่มีของที่ขายแบบกลุ่มได้"]
    # remove high index first
    cands_sorted = sorted(cands, key=lambda c: int(c["index"]), reverse=True)
    gains: Dict[str, int] = {}
    units = 0
    notes: List[str] = []
    for c in cands_sorted:
        idx = int(c["index"])
        ids_now = list(player.get("inventory_ids") or [])
        if idx < 0 or idx >= len(ids_now):
            # re-find by id+rarity
            from game.domain.bag_stack import find_stack_index

            idx = find_stack_index(player, str(c["id"]), str(c.get("rarity") or "common"))
            if idx < 0:
                continue
        off = c.get("offer") or {}
        # recompute with live qty
        from game.domain.bag_stack import qty_at
        from game.domain.rarity import rarity_of_inventory_index

        q = qty_at(player, idx)
        rid = rarity_of_inventory_index(player, idx)
        live = compute_sell_offer(
            player, reg, str(ids_now[idx] if idx < len(ids_now) else c["id"]), rid, shop=shop, qty=q
        )
        if not live or not live.get("accepted"):
            continue
        removed = remove_inventory_at_index(player, idx, reg)
        if not removed:
            continue
        cur = str(live.get("cur") or "money_world")
        gold = int(live.get("total") or 0)
        player[cur] = int(player.get(cur) or 0) + gold
        gains[cur] = gains.get(cur, 0) + gold
        units += q
        notes.append(f"ขาย {c.get('name')} x{q} +{gold}")
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "shop_sales", max(1, units))
    except Exception:
        pass
    # WO-Shop-4: bulk sell soft-builds shop rep (mat lean)
    try:
        from game.domain.shop_experience import bump_shop_rep

        sid = str((shop or {}).get("id") or player.get("_shop_active_id") or "")
        if sid and units > 0:
            amt = 1 + min(4, units // 3)
            if category == "material" or common_only:
                bump_shop_rep(player, sid, amount=amt, reason="sell_mat")
            else:
                bump_shop_rep(player, sid, amount=max(1, amt // 2), reason="sell")
    except Exception:
        pass
    return units, gains, notes
