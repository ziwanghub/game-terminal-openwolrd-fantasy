"""Shop service — rarity markets, price insurance, sell tax."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.balance import scaled_price, sell_breakdown, sell_price
from game.domain.equipment import add_item
from game.ports.io import IO


def _normalize_stock(shop: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not shop:
        return [
            {"id": "potion_hp", "rarity": None},
            {"id": "potion_mana", "rarity": None},
            {"id": "iron_sword", "rarity": "common"},
            {"id": "leather_armor", "rarity": "common"},
        ]
    out: List[Dict[str, Any]] = []
    for entry in shop.get("stock") or []:
        if isinstance(entry, str):
            out.append({"id": entry, "rarity": None})
        elif isinstance(entry, dict) and entry.get("id"):
            out.append(
                {
                    "id": str(entry["id"]),
                    "rarity": entry.get("rarity"),
                    "price_override": entry.get("price"),
                }
            )
    return out


def shop_rank_window(shop: Optional[Mapping[str, Any]]) -> Tuple[int, int]:
    """min_rank, max_rank inclusive for this market (1–8)."""
    if not shop:
        return 1, 8
    return (
        int(shop.get("min_rarity_rank") or shop.get("min_rank") or 1),
        int(shop.get("max_rarity_rank") or shop.get("max_rank") or 8),
    )


def _price_tuple(
    it: Dict[str, Any],
    reg: DataRegistry,
    player: Dict[str, Any],
    rarity: Optional[str],
) -> Tuple[str, int]:
    if it.get("price_heaven"):
        base = int(it["price_heaven"])
        from game.domain.rarity import rarity_price_mult

        mult = rarity_price_mult(reg, rarity or "common") if rarity else 1.0
        return "money_heaven", max(1, int(round(base * mult)))
    if it.get("price_hell"):
        base = int(it["price_hell"])
        from game.domain.rarity import rarity_price_mult

        mult = rarity_price_mult(reg, rarity or "common") if rarity else 1.0
        return "money_hell", max(1, int(round(base * mult)))
    base = int(it.get("price_world", 50))
    return "money_world", scaled_price(base, reg, player, rarity=rarity)


def _resolve_buy_rarity(reg: DataRegistry, iid: str, forced: Optional[str]) -> str:
    from game.domain.rarity import item_default_rarity

    if forced:
        return str(forced)
    it = reg.items.get(iid) or reg.cards.get(iid) or {}
    return item_default_rarity(it, reg)


def run_shop(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    shop_id: str = "traveling_merchant",
) -> None:
    from game.domain.rarity import (
        display_item_name,
        ensure_inventory_rarity,
        rarity_label,
        tier_rank,
    )

    shop = reg.shops.get(shop_id) or {}
    title = str(shop.get("name") or shop_id)
    stock = _normalize_stock(shop if shop else None)
    min_rk, max_rk = shop_rank_window(shop)
    filter_mode = "all"
    # specialty markets force filter
    if min_rk >= 3 and max_rk <= 8 and min_rk == 3:
        pass  # rare market
    specialty = min_rk > 1 or max_rk < 8

    while True:
        io.write_line(f"\n══ {title} ══")
        if specialty:
            lo = rarity_label(reg, _rank_to_id(reg, min_rk))
            hi = rarity_label(reg, _rank_to_id(reg, max_rk))
            io.write_line(f" ตลาดเฉพาะระดับ: {lo} – {hi}")
        io.write_line(
            f"โลก {player.get('money_world', 0)} | "
            f"สวรรค์ {player.get('money_heaven', 0)} | "
            f"นรก {player.get('money_hell', 0)}"
        )
        io.write_line(
            " ประกันราคา: ขายไม่ต่ำกว่าพื้น · ภาษีตามระดับของ (สูงยิ่งหักมาก)"
        )
        if not specialty:
            io.write_line(
                f" กรอง: [A]ทั้งหมด [C]ธรรมดา-สูง [R]หายาก+  ตอนนี้={filter_mode}"
            )
        io.write_line(" B. ซื้อ  S. ขาย  0. ออก")
        top = io.read_line("เลือก: ").strip().lower()
        if top in ("0", ""):
            break
        if not specialty:
            if top in ("a",):
                filter_mode = "all"
                continue
            if top in ("c",):
                filter_mode = "common"
                continue
            if top in ("r",):
                filter_mode = "rare"
                continue
        if top == "s":
            _run_sell(player, reg, io, shop=shop)
            continue
        if top not in ("b", "buy", "1"):
            io.write_line("พิมพ์ B=ซื้อ S=ขาย 0=ออก")
            continue

        rows: List[Tuple[str, str, int, Dict[str, Any], str]] = []
        io.write_line("\n── สินค้า ──")
        n = 0
        for entry in stock:
            iid = str(entry["id"])
            it = reg.items.get(iid) or reg.cards.get(iid) or {
                "name": iid,
                "price_world": 99,
            }
            rid = _resolve_buy_rarity(reg, iid, entry.get("rarity"))
            rk = tier_rank(reg, rid)
            if rk < min_rk or rk > max_rk:
                continue
            if not specialty:
                if filter_mode == "common" and rk > 2:
                    continue
                if filter_mode == "rare" and rk < 3:
                    continue
            cur, price = _price_tuple(dict(it), reg, player, rid)
            if entry.get("price_override") is not None:
                price = int(entry["price_override"])
            cur_name = {
                "money_world": "โลก",
                "money_heaven": "สวรรค์",
                "money_hell": "นรก",
            }[cur]
            kind = it.get("kind") or ("card" if iid in reg.cards else "?")
            shown = display_item_name(str(it.get("name") or iid), rid, reg)
            n += 1
            io.write_line(f"  {n}. {shown} [{kind}] — {price} {cur_name}")
            rows.append((iid, cur, price, dict(it), rid))
        if not rows:
            io.write_line("  (ไม่มีสินค้าในช่วงระดับของร้านนี้)")
            continue
        io.write_line("  0. กลับ")
        ch = io.read_line("ซื้อหมายเลข: ").strip()
        if ch in ("0", ""):
            continue
        try:
            idx = int(ch) - 1
            iid, cur, price, it, rid = rows[max(0, min(len(rows) - 1, idx))]
        except Exception:
            io.write_line("ไม่ถูกต้อง")
            continue
        flags = player.get("flags") or {}
        if flags.get("shop_discount"):
            price = max(1, int(price * (1.0 - float(flags["shop_discount"]))))
        if flags.get("shop_surcharge"):
            price = max(1, int(price * (1.0 + float(flags["shop_surcharge"]))))
        if int(player.get(cur, 0)) < price:
            io.write_line("เงินชนิดนี้ไม่พอ")
            continue
        player[cur] = int(player[cur]) - price
        name = add_item(player, iid, reg, rarity=rid)
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "shop_purchases", 1)
        except Exception:
            pass
        cur_name = {
            "money_world": "โลก",
            "money_heaven": "สวรรค์",
            "money_hell": "นรก",
        }[cur]
        io.write_line(f"ซื้อ {name} (-{price} {cur_name})")


def _rank_to_id(reg: DataRegistry, rank: int) -> str:
    for t in (getattr(reg, "rarity", None) or {}).get("tiers") or []:
        if int(t.get("rank") or 0) == rank:
            return str(t.get("id"))
    return "common"


def _run_sell(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    shop: Optional[Dict[str, Any]] = None,
) -> None:
    from game.domain.rarity import (
        display_item_name,
        ensure_inventory_rarity,
        rarity_label,
        rarity_of_inventory_index,
        remove_inventory_at_index,
        tier_rank,
    )

    shop = shop or {}
    min_rk, max_rk = shop_rank_window(shop)
    ensure_inventory_rarity(player)
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        io.write_line("กระเป๋าว่าง — ไม่มีอะไรขาย")
        return
    io.write_line("\n── ขายของ ──")
    io.write_line(" (ราคา = อ้างอิงซื้อ×อัตรา − ภาษีระดับ · ไม่ต่ำกว่าประกันราคา)")
    if min_rk > 1 or max_rk < 8:
        io.write_line(
            f" ร้านรับเฉพาะระดับ {rarity_label(reg, _rank_to_id(reg, min_rk))}"
            f"–{rarity_label(reg, _rank_to_id(reg, max_rk))}"
        )
    rows = []
    for i, iid in enumerate(ids):
        it = reg.items.get(iid) or {}
        rid = rarity_of_inventory_index(player, i)
        rk = tier_rank(reg, rid)
        accepted = min_rk <= rk <= max_rk
        base = int(
            it.get("price_world")
            or it.get("price_heaven")
            or it.get("price_hell")
            or 10
        )
        if it.get("price_heaven") and not it.get("price_world"):
            cur = "money_heaven"
            bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop)
            # recompute for heaven base
            from game.domain.rarity import rarity_price_mult

            buy = max(1, int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid))))
            # approximate using sell_price path with synthetic
            price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
            bd = {
                **bd,
                "net": price,
                "tax": max(0, int(buy * 0.4) - price),
                "insurance_applied": False,
            }
        elif it.get("price_hell") and not it.get("price_world"):
            cur = "money_hell"
            from game.domain.rarity import rarity_price_mult

            buy = max(1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid))))
            bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop)
            price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
            bd = {**bd, "net": price}
        else:
            cur = "money_world"
            bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop)
            price = int(bd["net"])
        shown = display_item_name(str(it.get("name") or iid), rid, reg)
        cur_name = {
            "money_world": "โลก",
            "money_heaven": "สวรรค์",
            "money_hell": "นรก",
        }[cur]
        if not accepted:
            io.write_line(f"  {i + 1}. {shown} — ร้านไม่รับระดับนี้")
            rows.append(None)
            continue
        tax_pct = int(float(bd.get("tax_rate") or 0) * 100)
        ins = " · ประกันราคา" if bd.get("insurance_applied") else ""
        io.write_line(
            f"  {i + 1}. {shown} → ได้ {price} {cur_name} "
            f"(ภาษี ~{tax_pct}%{ins})"
        )
        rows.append((i, iid, rid, cur, price, bd))
    io.write_line("  0. กลับ")
    ch = io.read_line("ขายหมายเลข (comma ได้): ").strip()
    if ch in ("0", ""):
        return
    sold = 0
    picks = []
    for part in ch.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            picks.append(int(part) - 1)
        except Exception:
            continue
    for idx in sorted(set(picks), reverse=True):
        if idx < 0 or idx >= len(rows) or rows[idx] is None:
            if 0 <= idx < len(rows) and rows[idx] is None:
                io.write_line("  ร้านไม่รับชิ้นนั้น")
            continue
        # recompute live
        ids_now = list(player.get("inventory_ids") or [])
        if idx >= len(ids_now):
            continue
        iid_live = ids_now[idx]
        rid_live = rarity_of_inventory_index(player, idx)
        rk = tier_rank(reg, rid_live)
        if not (min_rk <= rk <= max_rk):
            io.write_line("  ร้านไม่รับระดับนี้")
            continue
        it = reg.items.get(iid_live) or {}
        base = int(
            it.get("price_world")
            or it.get("price_heaven")
            or it.get("price_hell")
            or 10
        )
        if it.get("price_heaven") and not it.get("price_world"):
            cur = "money_heaven"
            from game.domain.rarity import rarity_price_mult

            bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop)
            buy = max(
                1, int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid_live)))
            )
            price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
        elif it.get("price_hell") and not it.get("price_world"):
            cur = "money_hell"
            from game.domain.rarity import rarity_price_mult

            bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop)
            buy = max(
                1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid_live)))
            )
            price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
        else:
            cur = "money_world"
            bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop)
            price = int(bd["net"])
        removed = remove_inventory_at_index(player, idx, reg)
        if not removed:
            continue
        player[cur] = int(player.get(cur, 0)) + price
        shown = display_item_name(str(it.get("name") or iid_live), rid_live, reg)
        cur_name = {
            "money_world": "โลก",
            "money_heaven": "สวรรค์",
            "money_hell": "นรก",
        }[cur]
        tax_note = ""
        if bd.get("tax_rate"):
            tax_note = f" · ภาษี {int(float(bd['tax_rate']) * 100)}%"
        if bd.get("insurance_applied"):
            tax_note += " · ใช้ประกันราคา"
        io.write_line(f"  ขาย {shown} +{price} {cur_name}{tax_note}")
        sold += 1
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "shop_sales", 1)
        except Exception:
            pass
    if sold == 0:
        io.write_line("ไม่ได้ขายชิ้นใด")
