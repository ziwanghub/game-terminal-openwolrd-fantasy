"""Shop service — category browse, rarity markets, price insurance, sell tax."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.balance import scaled_price, sell_breakdown
from game.domain.equipment import add_item
from game.ports.io import IO

# Shop browse categories (same spirit as bag hub)
SHOP_CAT_ORDER = (
    "food",
    "healing",
    "equipment",
    "material",
    "card",
    "other",
)
SHOP_CAT_LABELS = {
    "food": "อาหาร / เสบียง",
    "healing": "ยา / รักษา / บัฟ",
    "equipment": "อุปกรณ์ (อาวุธ·เกราะ·เครื่องประดับ)",
    "material": "วัตถุดิบ",
    "card": "การ์ด",
    "other": "อื่นๆ",
}


def _is_shop_banned_card(reg: Optional[DataRegistry], iid: str) -> bool:
    """Cards are drop-only — never sold by system shops (1.24)."""
    s = str(iid or "")
    if not s:
        return False
    if s.startswith("card_"):
        return True
    if reg is not None and s in (reg.cards or {}):
        return True
    return False


def _normalize_stock(
    shop: Optional[Dict[str, Any]],
    reg: Optional[DataRegistry] = None,
) -> List[Dict[str, Any]]:
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
            row = {"id": entry, "rarity": None}
        elif isinstance(entry, dict) and entry.get("id"):
            row = {
                "id": str(entry["id"]),
                "rarity": entry.get("rarity"),
                "price_override": entry.get("price"),
            }
        else:
            continue
        if _is_shop_banned_card(reg, str(row.get("id") or "")):
            continue
        out.append(row)
    return out


def shop_rank_window(shop: Optional[Any]) -> Tuple[int, int]:
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


def _stock_item_category(reg: DataRegistry, iid: str) -> str:
    """Classify shop stock id into browse category."""
    if iid in (reg.cards or {}) or str(iid).startswith("card_"):
        return "card"
    try:
        from game.domain.inventory_sys import item_category

        return item_category(str(iid), reg)
    except Exception:
        it = reg.items.get(iid) or {}
        kind = str(it.get("kind") or "")
        if kind == "equipment":
            return "equipment"
        if kind == "material":
            return "material"
        if kind == "consumable":
            return "healing"
        return "other"


def _eligible_buy_rows(
    player: Dict[str, Any],
    reg: DataRegistry,
    stock: Sequence[Dict[str, Any]],
    *,
    min_rk: int,
    max_rk: int,
    category: Optional[str] = None,
) -> List[Tuple[str, str, int, Dict[str, Any], str, str]]:
    """
    Build buy rows: (iid, currency, price, it, rarity, bag_cat)
    """
    from game.domain.rarity import display_item_name, tier_rank

    rows: List[Tuple[str, str, int, Dict[str, Any], str, str]] = []
    for entry in stock:
        iid = str(entry["id"])
        it = reg.items.get(iid) or reg.cards.get(iid) or {
            "name": iid,
            "price_world": 99,
        }
        it = dict(it)
        rid = _resolve_buy_rarity(reg, iid, entry.get("rarity"))
        rk = tier_rank(reg, rid)
        if rk < min_rk or rk > max_rk:
            continue
        cat = _stock_item_category(reg, iid)
        if category and cat != category:
            continue
        cur, price = _price_tuple(it, reg, player, rid)
        if entry.get("price_override") is not None:
            price = int(entry["price_override"])
        rows.append((iid, cur, price, it, rid, cat))
    # sort within category: food tier then name
    def _sk(r: Tuple[str, str, int, Dict[str, Any], str, str]) -> Tuple:
        it = r[3]
        return (int(it.get("food_tier") or 99), str(it.get("name") or r[0]))

    rows.sort(key=_sk)
    return rows


def _count_stock_by_category(
    player: Dict[str, Any],
    reg: DataRegistry,
    stock: Sequence[Dict[str, Any]],
    min_rk: int,
    max_rk: int,
) -> Dict[str, int]:
    counts = {c: 0 for c in SHOP_CAT_ORDER}
    for row in _eligible_buy_rows(
        player, reg, stock, min_rk=min_rk, max_rk=max_rk, category=None
    ):
        cat = row[5]
        if cat not in counts:
            counts[cat] = 0
        counts[cat] += 1
    return counts


def _currency_name(cur: str) -> str:
    return {
        "money_world": "โลก",
        "money_heaven": "สวรรค์",
        "money_hell": "นรก",
    }.get(cur, cur)


def _slot_th(slot: str) -> str:
    return {
        "weapon": "อาวุธ",
        "main_hand": "มือหลัก",
        "off_hand": "มือรอง",
        "body": "ลำตัว",
        "head": "ศีรษะ",
        "legs": "ส่วนล่าง",
        "feet": "เท้า",
        "acc_1": "เครื่องประดับ",
        "armor": "เกราะ",
        "accessory": "เครื่องประดับ",
    }.get(str(slot or ""), str(slot or ""))


def _buy_row_detail(
    it: Dict[str, Any],
    cat: str,
) -> str:
    """One soft detail line under item name."""
    bits: List[str] = []
    if cat == "food":
        tier = it.get("food_tier")
        if tier:
            bits.append(f"ชั้น{tier}")
        if it.get("hunger_relief"):
            bits.append("อิ่มท้อง")
        if it.get("heal_hp"):
            bits.append(f"อุ่น+{it['heal_hp']}")
    elif cat == "equipment":
        if it.get("slot"):
            bits.append(_slot_th(str(it["slot"])))
        if it.get("atk"):
            bits.append(f"ATK+{it['atk']}")
        if it.get("defense") or it.get("max_hp"):
            if it.get("defense"):
                bits.append(f"DEF+{it['defense']}")
            if it.get("max_hp"):
                bits.append(f"HP+{it['max_hp']}")
        if it.get("sockets"):
            bits.append(f"ช่องการ์ด {it['sockets']}")
    elif cat == "healing":
        if it.get("heal_hp"):
            bits.append(f"HP+{it['heal_hp']}")
        if it.get("heal_mana"):
            bits.append(f"MP+{it['heal_mana']}")
    elif cat == "material":
        bits.append("วัตถุดิบ")
    return " · ".join(str(b) for b in bits if b)


def _buy_from_rows(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rows: List[Tuple[str, str, int, Dict[str, Any], str, str]],
    *,
    cat_label: str,
) -> None:
    from game.domain.rarity import display_item_name
    from game.ui_terminal.layout import render_box

    if not rows:
        io.write_line()
        io.write_line(
            render_box(
                [" ซื้อ · " + cat_label, "---", " (หมวดนี้ว่างในร้านนี้)", "---", "  0  กลับ"],
                double=False,
            )
        )
        io.read_line("\n  Enter...")
        return

    short_label = str(cat_label).split("(")[0].strip()
    lines: List[str] = [
        f" ซื้อ · {short_label}",
        "---",
        f" เงินคุณ  โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}",
        "---",
        " รายการ",
    ]
    for i, (iid, cur, price, it, rid, cat) in enumerate(rows, 1):
        shown = display_item_name(str(it.get("name") or iid), rid, reg)
        detail = _buy_row_detail(it, cat)
        lines.append(f"  {i}. {shown}")
        price_line = f"      {price} {_currency_name(cur)}"
        if detail:
            price_line += f"  ·  {detail}"
        lines.append(price_line)
        if i < len(rows):
            lines.append("")
    lines.extend(
        [
            "---",
            f"  0  กลับหมวด",
            "---",
            f" พิมพ์ 1–{len(rows)} เพื่อซื้อ",
        ]
    )
    io.write_line()
    io.write_line(render_box(lines, double=False))
    ch = io.read_line(f"\n  ซื้อหมายเลข (1–{len(rows)} · 0 กลับ): ").strip()
    if ch in ("0", ""):
        return
    try:
        idx = int(ch) - 1
        if idx < 0 or idx >= len(rows):
            io.write_line("  หมายเลขนอกช่วง")
            return
        iid, cur, price, it, rid, _cat = rows[idx]
    except Exception:
        io.write_line("  พิมพ์เลขเท่านั้น")
        return
    flags = player.get("flags") or {}
    if flags.get("shop_discount"):
        price = max(1, int(price * (1.0 - float(flags["shop_discount"]))))
    if flags.get("shop_surcharge"):
        price = max(1, int(price * (1.0 + float(flags["shop_surcharge"]))))
    shown = display_item_name(str(it.get("name") or iid), rid, reg)
    have = int(player.get(cur, 0) or 0)
    if have < price:
        io.write_line()
        io.write_line(
            render_box(
                [
                    " เงินไม่พอ",
                    "---",
                    f" ต้องการ  {price} {_currency_name(cur)}",
                    f" มีอยู่    {have} {_currency_name(cur)}",
                ],
                double=False,
            )
        )
        return
    # soft confirm for equipment / expensive
    conf_need = _cat == "equipment" or price >= 80
    if conf_need:
        conf = io.read_line(
            f"  ซื้อ「{shown}」 {price} {_currency_name(cur)}? (y/n): "
        ).strip().lower()
        if conf not in ("y", "yes", "ใช่", "1"):
            io.write_line("  ยกเลิก")
            return
    player[cur] = have - price
    name = add_item(player, iid, reg, rarity=rid)
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "shop_purchases", 1)
    except Exception:
        pass
    result = [
        " ซื้อสำเร็จ",
        "---",
        f" ได้  {name}",
        f" จ่าย {price} {_currency_name(cur)}  ·  เหลือ {player.get(cur, 0)}",
    ]
    if _cat == "food":
        result.append(" → กระเป๋าหมวด「อาหาร」(5/I → 2)")
    elif _cat == "equipment":
        result.append(" → กระเป๋าหมวด「อุปกรณ์」· สวมที่ เกียร์")
    elif _cat == "healing":
        result.append(" → กระเป๋าหมวด「รักษา」")
    io.write_line()
    io.write_line(render_box(result, double=False))


def _buy_browse(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    stock: List[Dict[str, Any]],
    *,
    min_rk: int,
    max_rk: int,
) -> None:
    """Category-first buy menu — เลือกหมวดก่อน แล้วค่อยเลือกชิ้น."""
    from game.ui_terminal.layout import render_box

    while True:
        counts = _count_stock_by_category(player, reg, stock, min_rk, max_rk)
        total = sum(counts.values())
        lines: List[str] = [
            " ซื้อ · เลือกหมวด",
            "---",
            f" สินค้าในร้านนี้ ~{total} ชิ้น",
            "---",
        ]
        menu: List[Tuple[str, str]] = []  # key, cat_id
        n = 0
        for cat in SHOP_CAT_ORDER:
            c = counts.get(cat, 0)
            if c <= 0:
                continue
            n += 1
            label = SHOP_CAT_LABELS.get(cat, cat)
            lines.append(f"  {n}  {label}  ({c})")
            menu.append((str(n), cat))
        if not menu:
            lines.append("  (ร้านนี้ไม่มีสินค้าในช่วงระดับ)")
            io.write_line()
            io.write_line(render_box(lines, double=False))
            io.read_line("\n  Enter...")
            return
        lines.extend(
            [
                "---",
                "  A  ดูทั้งหมด (รายการยาว)",
                "  0  กลับหน้าร้าน",
            ]
        )
        io.write_line()
        io.write_line(render_box(lines, double=False))
        ch = io.read_line("\n  หมวด (เลข · A · 0): ").strip().lower()
        if ch in ("0", ""):
            return
        if ch in ("a", "all", "ทั้งหมด"):
            rows = _eligible_buy_rows(
                player, reg, stock, min_rk=min_rk, max_rk=max_rk, category=None
            )
            _buy_from_rows(player, reg, io, rows, cat_label="ทั้งหมด")
            continue
        cat_id = None
        for key, cid in menu:
            if ch == key:
                cat_id = cid
                break
        shortcuts = {
            "f": "food",
            "h": "healing",
            "e": "equipment",
            "m": "material",
            "k": "card",
            "o": "other",
        }
        if ch in shortcuts and counts.get(shortcuts[ch], 0) > 0:
            cat_id = shortcuts[ch]
        if not cat_id:
            io.write_line("  เลือกหมายเลขหมวด")
            continue
        rows = _eligible_buy_rows(
            player, reg, stock, min_rk=min_rk, max_rk=max_rk, category=cat_id
        )
        _buy_from_rows(
            player, reg, io, rows, cat_label=SHOP_CAT_LABELS.get(cat_id, cat_id)
        )


def format_shop_hub_lines(
    player: Dict[str, Any],
    reg: DataRegistry,
    *,
    title: str,
    stock: List[Dict[str, Any]],
    min_rk: int,
    max_rk: int,
    specialty: bool,
) -> List[str]:
    """Sectioned shop front desk for box UI."""
    from game.domain.rarity import rarity_label

    lines: List[str] = [
        f" ร้าน · {title}",
        "---",
        f" เงิน  โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}",
    ]
    if specialty:
        lo = rarity_label(reg, _rank_to_id(reg, min_rk))
        hi = rarity_label(reg, _rank_to_id(reg, max_rk))
        lines.append(f" ระดับที่รับ  {lo} – {hi}")
    lines.append("---")
    lines.append(" สต็อกตามหมวด")
    counts = _count_stock_by_category(player, reg, stock, min_rk, max_rk)
    short = {
        "food": "อาหาร",
        "healing": "ยา",
        "equipment": "อุปกรณ์",
        "material": "วัตถุดิบ",
        "card": "การ์ด",
        "other": "อื่นๆ",
    }
    any_stock = False
    for c in SHOP_CAT_ORDER:
        n = int(counts.get(c, 0) or 0)
        if n <= 0:
            continue
        any_stock = True
        lines.append(f"  · {short.get(c, c):<8}  {n} ชิ้น")
    if not any_stock:
        lines.append("  (ว่าง)")
    lines.append("---")
    lines.append(" หมายเหตุ soft")
    lines.append("  · ขายไม่ต่ำกว่าพื้น · ภาษีสูงขึ้นตามระดับของ")
    lines.append("---")
    lines.append("  1 / B   ซื้อ (เลือกหมวดก่อน)")
    lines.append("  2 / S   ขาย (เลือกหมวดจากกระเป๋า)")
    lines.append("  0       ออก")
    return lines


def run_shop(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    shop_id: str = "traveling_merchant",
) -> None:
    from game.ui_terminal.layout import render_box

    shop = reg.shops.get(shop_id) or {}
    title = str(shop.get("name") or shop_id)
    stock = _normalize_stock(shop if shop else None, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    specialty = min_rk > 1 or max_rk < 8

    while True:
        io.write_line()
        io.write_line(
            render_box(
                format_shop_hub_lines(
                    player,
                    reg,
                    title=title,
                    stock=stock,
                    min_rk=min_rk,
                    max_rk=max_rk,
                    specialty=specialty,
                ),
                double=False,
            )
        )
        top = io.read_line("\n  เลือก (1 ซื้อ · 2 ขาย · 0 ออก): ").strip().lower()
        if top in ("0", "", "q"):
            break
        if top in ("2", "s", "sell", "ขาย"):
            _run_sell(player, reg, io, shop=shop)
            continue
        if top not in ("1", "b", "buy", "ซื้อ"):
            io.write_line("  พิมพ์ 1=ซื้อ · 2=ขาย · 0=ออก")
            continue
        _buy_browse(player, reg, io, stock, min_rk=min_rk, max_rk=max_rk)


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
    from game.domain.inventory_sys import BAG_CATEGORY_LABELS, item_category, list_bag_entries
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
    if not ids and not (player.get("card_bag") or []):
        io.write_line("กระเป๋าว่าง — ไม่มีอะไรขาย")
        return

    # category pick for sell
    while True:
        io.write_line("\n── ขาย · เลือกหมวดจากกระเป๋า ──")
        # count sellable per cat
        from game.domain.inventory_sys import count_bag_categories

        counts = count_bag_categories(player, reg)
        menu: List[Tuple[str, str]] = []
        n = 0
        for cat in ("food", "healing", "equipment", "material", "other", "card"):
            c = int(counts.get(cat) or 0)
            if c <= 0:
                continue
            n += 1
            lab = BAG_CATEGORY_LABELS.get(cat, cat)
            io.write_line(f"  {n}. {lab}  ({c})")
            menu.append((str(n), cat))
        if not menu:
            io.write_line("  (ไม่มีของขาย)")
            return
        io.write_line("  A. ทั้งหมด")
        io.write_line("  0. กลับ")
        ch = io.read_line("หมวดขาย: ").strip().lower()
        if ch in ("0", ""):
            return
        sell_cat: Optional[str] = None
        if ch in ("a", "all"):
            sell_cat = None
        else:
            for key, cid in menu:
                if ch == key:
                    sell_cat = cid
                    break
            if sell_cat is None:
                io.write_line("เลือกหมายเลขหมวด")
                continue

        io.write_line("\n── รายการขาย ──")
        if min_rk > 1 or max_rk < 8:
            io.write_line(
                f" ร้านรับเฉพาะระดับ {rarity_label(reg, _rank_to_id(reg, min_rk))}"
                f"–{rarity_label(reg, _rank_to_id(reg, max_rk))}"
            )
        rows = []
        if sell_cat == "card":
            for i, cid in enumerate(player.get("card_bag") or []):
                it = reg.cards.get(cid) or reg.items.get(cid) or {}
                shown = str(it.get("name") or cid)
                io.write_line(f"  {i + 1}. {shown} [การ์ด] — ขายประมาณถูก")
                rows.append(("card", i, cid, "common", "money_world", 8))
        else:
            ids = list(player.get("inventory_ids") or [])
            for i, iid in enumerate(ids):
                cat = item_category(str(iid), reg)
                if sell_cat and cat != sell_cat:
                    continue
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
                    from game.domain.rarity import rarity_price_mult

                    buy = max(
                        1, int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid)))
                    )
                    price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
                elif it.get("price_hell") and not it.get("price_world"):
                    cur = "money_hell"
                    from game.domain.rarity import rarity_price_mult

                    bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop)
                    buy = max(
                        1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid)))
                    )
                    price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
                else:
                    cur = "money_world"
                    bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop)
                    price = int(bd["net"])
                shown = display_item_name(str(it.get("name") or iid), rid, reg)
                if not accepted:
                    io.write_line(f"  · {shown} — ร้านไม่รับระดับนี้")
                    continue
                tax_pct = int(float(bd.get("tax_rate") or 0) * 100) if cur == "money_world" else 0
                io.write_line(
                    f"  {len(rows) + 1}. {shown} → ได้ {price} {_currency_name(cur)}"
                    + (f" (ภาษี ~{tax_pct}%)" if tax_pct else "")
                )
                rows.append(("inv", i, iid, rid, cur, price))

        if not rows:
            io.write_line("  (ไม่มีชิ้นที่ขายได้ในหมวดนี้)")
            io.read_line("Enter...")
            continue
        io.write_line("  0. กลับหมวด")
        ch2 = io.read_line("ขายหมายเลข: ").strip()
        if ch2 in ("0", ""):
            continue
        try:
            pick = int(ch2) - 1
            row = rows[max(0, min(len(rows) - 1, pick))]
        except Exception:
            io.write_line("ไม่ถูกต้อง")
            continue
        kind, idx, iid, rid, cur, price = row
        if kind == "card":
            bag = list(player.get("card_bag") or [])
            if idx < 0 or idx >= len(bag):
                continue
            bag.pop(idx)
            player["card_bag"] = bag
            player[cur] = int(player.get(cur, 0)) + int(price)
            io.write_line(f"ขายการ์ดได้ {price} {_currency_name(cur)}")
        else:
            # re-find current index by id (list may have shifted if filtered)
            ids_now = list(player.get("inventory_ids") or [])
            # prefer exact index if still matches
            live_idx = idx
            if live_idx >= len(ids_now) or ids_now[live_idx] != iid:
                try:
                    live_idx = ids_now.index(iid)
                except ValueError:
                    io.write_line("ของหายไปแล้ว")
                    continue
            rid_live = rarity_of_inventory_index(player, live_idx)
            rk = tier_rank(reg, rid_live)
            if not (min_rk <= rk <= max_rk):
                io.write_line("ร้านไม่รับระดับนี้")
                continue
            it = reg.items.get(iid) or {}
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
                    1,
                    int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid_live))),
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
            removed = remove_inventory_at_index(player, live_idx, reg)
            if not removed:
                continue
            player[cur] = int(player.get(cur, 0)) + price
            shown = display_item_name(str(it.get("name") or iid), rid_live, reg)
            io.write_line(f"ขาย {shown} ได้ {price} {_currency_name(cur)}")
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "shop_sales", 1)
        except Exception:
            pass
