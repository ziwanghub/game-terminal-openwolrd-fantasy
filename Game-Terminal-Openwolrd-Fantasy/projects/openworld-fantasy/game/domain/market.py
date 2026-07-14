"""
Central player market (per-world shared file).

Economics (soft, not fully revealed in UI):
- Suggested list price from base item price, rarity, recent volume
- Market fee on sale (taken from buyer price before seller receives)
- Supply soft-depresses suggestion when many same item listed
"""
from __future__ import annotations

import json
import time
import secrets
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.config import SAVES_DIR
from game.data_load.registry import DataRegistry


def market_path(world_id: str) -> Path:
    folder = SAVES_DIR / str(world_id or "default")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "market.json"


def load_market(world_id: str) -> Dict[str, Any]:
    path = market_path(world_id)
    if not path.is_file():
        return _empty_market()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("bad market")
        data.setdefault("listings", [])
        data.setdefault("sales_log", [])
        data.setdefault("pending_payouts", [])
        data.setdefault("price_index", {})
        data.setdefault("tax_fund", 0)  # ภาษีตลาด → กองทุนค่าจ้างภารกิจ
        data.setdefault("tax_log", [])
        data.setdefault("version", 1)
        return data
    except Exception:
        return _empty_market()


def _empty_market() -> Dict[str, Any]:
    return {
        "version": 1,
        "listings": [],
        "sales_log": [],
        "pending_payouts": [],
        "price_index": {},
        "tax_fund": 0,
        "tax_log": [],
    }


def save_market(world_id: str, data: Mapping[str, Any]) -> Path:
    path = market_path(world_id)
    path.write_text(
        json.dumps(dict(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _base_price(reg: DataRegistry, item_id: str, rarity: str) -> int:
    from game.domain.balance import scaled_price
    from game.domain.rarity import item_default_rarity

    it = reg.items.get(item_id) or reg.cards.get(item_id) or {}
    rid = rarity or item_default_rarity(it, reg)
    if it.get("price_heaven"):
        return max(1, int(it["price_heaven"]))
    if it.get("price_hell"):
        return max(1, int(it["price_hell"]))
    base = int(it.get("price_world") or 40)
    # neutral player context for market valuation
    dummy = {"location": "dark_forest", "level": 5}
    return scaled_price(base, reg, dummy, rarity=rid)


def market_fee_rate(reg: DataRegistry, rarity: str) -> float:
    """Fee taken from sale — higher rarity slightly higher fee (soft economy)."""
    rcfg = getattr(reg, "rarity", None) or {}
    tax = (rcfg.get("sell_tax_rate") or {}).get(rarity or "common", 0.05)
    # market fee between 5–18%
    return max(0.05, min(0.18, 0.05 + float(tax) * 0.4))


def suggest_list_price(
    reg: DataRegistry,
    world_id: str,
    item_id: str,
    rarity: str,
    market: Optional[Mapping[str, Any]] = None,
) -> int:
    """Suggested price for listing — supply soft-depresses."""
    market = market or load_market(world_id)
    base = _base_price(reg, item_id, rarity)
    idx = (market.get("price_index") or {}).get(item_id) or {}
    avg = idx.get("avg")
    if avg:
        base = int(round((base + float(avg)) / 2))
    # supply on board
    same = sum(
        1
        for L in market.get("listings") or []
        if str(L.get("item_id")) == str(item_id)
        and str(L.get("rarity") or "common") == str(rarity or "common")
    )
    if same >= 3:
        base = int(round(base * 0.92))
    if same >= 6:
        base = int(round(base * 0.88))
    # player market usually between 55–95% of shop buy-equivalent
    suggested = max(1, int(round(base * 0.72)))
    return suggested


def list_item_on_market(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    inv_index: int,
    price: int,
    *,
    world_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Remove item from bag and create market listing."""
    from game.domain.item_instances import ensure_item_instances, pop_instance_at
    from game.domain.rarity import rarity_of_inventory_index

    world_id = world_id or str(player.get("world_id") or "default")
    ids = list(player.get("inventory_ids") or [])
    if inv_index < 0 or inv_index >= len(ids):
        return False, "ไม่มีชิ้นนั้นในคลัง"
    item_id = str(ids[inv_index])
    it = reg.items.get(item_id) or {}
    if not it and item_id not in (reg.cards or {}):
        return False, "ขายชิ้นนี้ในตลาดกลางไม่ได้"
    # cards: skip for v1 simplicity or allow
    if item_id in (reg.cards or {}) or str(it.get("kind")) == "card":
        return False, "การ์ดยังฝากขายตลาดกลางไม่ได้ (เฟสถัดไป)"

    rid = rarity_of_inventory_index(player, inv_index)
    price = max(1, int(price))
    suggest = suggest_list_price(reg, world_id, item_id, rid)
    # soft clamp extreme prices (anti dump/exploit soft)
    if price > suggest * 5:
        return False, f"ราคาสูงเกินตลาดรับได้ (แนะนำราว {suggest})"
    if price < max(1, suggest // 5):
        return False, f"ราคาต่ำเกิน — ตลาดสงสัย (แนะนำราว {suggest})"

    # remove from inventory (prefer instance pop)
    ensure_item_instances(player, reg)
    inst = None
    try:
        inst = pop_instance_at(player, inv_index, reg)
    except Exception:
        inst = None
    if inst is None:
        # fallback remove by id once
        from game.domain.equipment import remove_inventory_id

        if not remove_inventory_id(player, item_id, reg):
            return False, "นำออกจากคลังไม่สำเร็จ"

    if not player.get("id"):
        player["id"] = f"temp_{int(time.time())}"

    market = load_market(world_id)
    listing = {
        "listing_id": f"L_{secrets.token_hex(4)}",
        "seller_id": str(player.get("id")),
        "seller_name": str(player.get("name") or "???"),
        "item_id": item_id,
        "rarity": rid,
        "price": price,
        "currency": "money_world",
        "listed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "instance": inst,
        "name": str(it.get("name") or item_id),
    }
    listings = list(market.get("listings") or [])
    listings.append(listing)
    market["listings"] = listings
    save_market(world_id, market)
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name

    shown = display_item_name(str(it.get("name") or item_id), rid, reg)
    code = item_code(item_id, reg)
    return True, f"ฝากขาย {code} {shown} ราคา {price} เงินโลก · รหัสรายการ {listing['listing_id']}"


def cancel_listing(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    listing_id: str,
    *,
    world_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Seller cancels — item returns to bag."""
    from game.domain.equipment import add_item

    world_id = world_id or str(player.get("world_id") or "default")
    market = load_market(world_id)
    listings = list(market.get("listings") or [])
    found = None
    rest = []
    for L in listings:
        if str(L.get("listing_id")) == str(listing_id):
            found = L
        else:
            rest.append(L)
    if not found:
        return False, "ไม่พบรายการ"
    if str(found.get("seller_id")) != str(player.get("id")):
        return False, "นี่ไม่ใช่ของที่คุณฝากขาย"
    market["listings"] = rest
    save_market(world_id, market)
    iid = str(found.get("item_id"))
    rid = str(found.get("rarity") or "common")
    add_item(player, iid, reg, rarity=rid)
    # restore instance if present
    inst = found.get("instance")
    if inst and isinstance(inst, dict):
        try:
            from game.domain.item_instances import ensure_item_instances

            items = list(player.get("inventory_items") or [])
            # replace last matching template with saved instance
            if items and str(items[-1].get("template_id")) == iid:
                inst = dict(inst)
                inst["location"] = "bag"
                items[-1] = inst
                player["inventory_items"] = items
            ensure_item_instances(player, reg)
        except Exception:
            pass
    return True, f"ถอนขาย {found.get('name') or iid} กลับคลังแล้ว"


def buy_listing(
    buyer: MutableMapping[str, Any],
    reg: DataRegistry,
    listing_id: str,
    *,
    world_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Buyer purchases listing:
    - pays full list price
    - seller receives price * (1 - fee)
    - seller gets report who bought
    """
    from game.domain.equipment import add_item

    world_id = world_id or str(buyer.get("world_id") or "default")
    market = load_market(world_id)
    listings = list(market.get("listings") or [])
    found = None
    rest = []
    for L in listings:
        if str(L.get("listing_id")) == str(listing_id):
            found = L
        else:
            rest.append(L)
    if not found:
        return False, "รายการนี้ไม่มีแล้ว (อาจมีคนซื้อไป)"
    if str(found.get("seller_id")) == str(buyer.get("id")):
        return False, "ซื้อของตัวเองไม่ได้ — ใช้ถอนขายแทน"

    price = int(found.get("price") or 0)
    if price <= 0:
        return False, "ราคาไม่ถูกต้อง"
    money = int(buyer.get("money_world") or 0)
    if money < price:
        return False, f"เงินไม่พอ (ต้องการ {price} · มี {money})"

    rid = str(found.get("rarity") or "common")
    fee_r = market_fee_rate(reg, rid)
    fee = max(0, int(round(price * fee_r)))
    seller_gain = max(1, price - fee)

    # ภาษีตลาด → กองทุนค่าจ้างประกาศภารกิจ (ไม่คืนผู้เล่นโดยตรง)
    market["tax_fund"] = int(market.get("tax_fund") or 0) + fee
    tlog = list(market.get("tax_log") or [])
    tlog.append(
        {
            "amount": fee,
            "from_sale": price,
            "item_id": found.get("item_id"),
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    )
    market["tax_log"] = tlog[-100:]

    # commit: remove listing, charge buyer, give item
    buyer["money_world"] = money - price
    iid = str(found.get("item_id"))
    add_item(buyer, iid, reg, rarity=rid)
    inst = found.get("instance")
    if inst and isinstance(inst, dict):
        try:
            from game.domain.item_instances import ensure_item_instances

            items = list(buyer.get("inventory_items") or [])
            if items and str(items[-1].get("template_id")) == iid:
                inst = dict(inst)
                inst["location"] = "bag"
                inst["owner_id"] = str(buyer.get("id") or "")
                from game.domain.item_instances import owner_short

                inst["owner_short"] = owner_short(buyer)
                items[-1] = inst
                buyer["inventory_items"] = items
            ensure_item_instances(buyer, reg)
        except Exception:
            pass

    market["listings"] = rest
    # price index update
    idx = dict(market.get("price_index") or {})
    entry = dict(idx.get(iid) or {"avg": price, "volume": 0})
    vol = int(entry.get("volume") or 0)
    old_avg = float(entry.get("avg") or price)
    entry["avg"] = round((old_avg * vol + price) / (vol + 1), 1)
    entry["volume"] = vol + 1
    idx[iid] = entry
    market["price_index"] = idx

    sale = {
        "listing_id": found.get("listing_id"),
        "item_id": iid,
        "rarity": rid,
        "price": price,
        "fee": fee,
        "seller_gain": seller_gain,
        "seller_id": found.get("seller_id"),
        "seller_name": found.get("seller_name"),
        "buyer_id": str(buyer.get("id") or ""),
        "buyer_name": str(buyer.get("name") or "???"),
        "sold_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "item_name": found.get("name") or iid,
    }
    log = list(market.get("sales_log") or [])
    log.append(sale)
    market["sales_log"] = log[-200:]  # cap

    # pay seller
    paid = _pay_seller(
        world_id,
        str(found.get("seller_id") or ""),
        seller_gain,
        report={
            "type": "market_sold",
            "item_name": sale["item_name"],
            "item_id": iid,
            "price": price,
            "received": seller_gain,
            "fee": fee,
            "buyer_name": sale["buyer_name"],
            "buyer_id": sale["buyer_id"],
            "sold_at": sale["sold_at"],
            "listing_id": sale["listing_id"],
        },
    )
    if not paid:
        pend = list(market.get("pending_payouts") or [])
        pend.append(
            {
                "seller_id": found.get("seller_id"),
                "amount": seller_gain,
                "report": {
                    "type": "market_sold",
                    "item_name": sale["item_name"],
                    "item_id": iid,
                    "price": price,
                    "received": seller_gain,
                    "fee": fee,
                    "buyer_name": sale["buyer_name"],
                    "buyer_id": sale["buyer_id"],
                    "sold_at": sale["sold_at"],
                    "listing_id": sale["listing_id"],
                },
            }
        )
        market["pending_payouts"] = pend

    save_market(world_id, market)
    from game.domain.rarity import display_item_name

    shown = display_item_name(str(found.get("name") or iid), rid, reg)
    return (
        True,
        f"ซื้อ {shown} จาก {found.get('seller_name')} ราคา {price} "
        f"(ค่าธรรมเนียมตลาดหักจากผู้ขาย · คุณจ่าย {price})",
    )


def _pay_seller(
    world_id: str,
    seller_id: str,
    amount: int,
    report: Dict[str, Any],
) -> bool:
    """Load seller save, add money + inbox report, save. Returns False if offline path needed."""
    if not seller_id:
        return False
    folder = SAVES_DIR / str(world_id or "default")
    path = folder / f"{seller_id}.json"
    if not path.is_file():
        # try scan by id field
        if folder.is_dir():
            for p in folder.glob("*.json"):
                if p.name == "market.json":
                    continue
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if str(data.get("id")) == str(seller_id):
                        path = p
                        break
                except Exception:
                    continue
            else:
                return False
        else:
            return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["money_world"] = int(data.get("money_world") or 0) + int(amount)
        inbox = list(data.get("market_inbox") or [])
        inbox.append(report)
        data["market_inbox"] = inbox[-50:]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def get_tax_fund(world_id: str) -> int:
    return int(load_market(world_id).get("tax_fund") or 0)


def withdraw_tax_fund(world_id: str, amount: int) -> int:
    """Pull wages from tax fund. Returns actual withdrawn."""
    amount = max(0, int(amount))
    market = load_market(world_id)
    fund = int(market.get("tax_fund") or 0)
    take = min(fund, amount)
    market["tax_fund"] = fund - take
    save_market(world_id, market)
    return take


def claim_pending_payouts(player: MutableMapping[str, Any], world_id: Optional[str] = None) -> List[str]:
    """On load / enter market: deliver pending payouts + show inbox."""
    world_id = world_id or str(player.get("world_id") or "default")
    notes: List[str] = []
    market = load_market(world_id)
    sid = str(player.get("id") or "")
    if not sid:
        return notes
    pend = list(market.get("pending_payouts") or [])
    keep = []
    for p in pend:
        if str(p.get("seller_id")) != sid:
            keep.append(p)
            continue
        amt = int(p.get("amount") or 0)
        player["money_world"] = int(player.get("money_world") or 0) + amt
        rep = p.get("report") or {}
        inbox = list(player.get("market_inbox") or [])
        inbox.append(rep)
        player["market_inbox"] = inbox[-50:]
        notes.append(
            f"ตลาด: ได้รับ {amt} เงินโลก จากยอดขาย "
            f"{rep.get('item_name') or ''} (ผู้ซื้อ {rep.get('buyer_name') or '?'})"
        )
    if len(keep) != len(pend):
        market["pending_payouts"] = keep
        save_market(world_id, market)

    # surface inbox messages once
    inbox = list(player.get("market_inbox") or [])
    unread = [m for m in inbox if not m.get("_read")]
    for m in unread:
        if m.get("type") == "market_sold":
            notes.append(
                f"รายงานตลาด: {m.get('buyer_name')} ซื้อ {m.get('item_name')} "
                f"ราคา {m.get('price')} · คุณได้ {m.get('received')} "
                f"(หักค่าธรรมเนียม {m.get('fee')})"
            )
        m["_read"] = True
    player["market_inbox"] = inbox
    return notes


def format_market_listings(
    reg: DataRegistry,
    world_id: str,
    *,
    exclude_seller_id: Optional[str] = None,
) -> List[str]:
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name, format_rarity_tag

    market = load_market(world_id)
    lines = ["── ตลาดกลาง ──"]
    listings = list(market.get("listings") or [])
    if exclude_seller_id:
        # still show all; mark own
        pass
    if not listings:
        lines.append("  (ยังไม่มีใครฝากขาย)")
        return lines
    for i, L in enumerate(listings, 1):
        iid = str(L.get("item_id"))
        rid = str(L.get("rarity") or "common")
        name = display_item_name(str(L.get("name") or iid), rid, reg)
        code = item_code(iid, reg)
        own = " [ของคุณ]" if exclude_seller_id and str(L.get("seller_id")) == str(exclude_seller_id) else ""
        lines.append(
            f"  {i}. {L.get('listing_id')}  {code} {name} {format_rarity_tag(reg, rid)}  "
            f"ราคา {L.get('price')}  · โดย {L.get('seller_name')}{own}"
        )
    return lines
