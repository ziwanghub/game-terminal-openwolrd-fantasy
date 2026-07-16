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
                "min_rep": entry.get("min_rep"),
                "always_show": entry.get("always_show") or entry.get("rep_free"),
                "rep_free": entry.get("rep_free"),
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


def shop_id_of_safe(shop: Optional[Any]) -> str:
    if not shop:
        return ""
    return str(shop.get("id") or "")


def _price_tuple(
    it: Dict[str, Any],
    reg: DataRegistry,
    player: Dict[str, Any],
    rarity: Optional[str],
    *,
    shop: Optional[Dict[str, Any]] = None,
    shop_id: str = "",
) -> Tuple[str, int]:
    if it.get("price_heaven"):
        base = int(it["price_heaven"])
        from game.domain.rarity import rarity_price_mult

        mult = rarity_price_mult(reg, rarity or "common") if rarity else 1.0
        price = max(1, int(round(base * mult)))
    elif it.get("price_hell"):
        base = int(it["price_hell"])
        from game.domain.rarity import rarity_price_mult

        mult = rarity_price_mult(reg, rarity or "common") if rarity else 1.0
        price = max(1, int(round(base * mult)))
        # WO-Shop-3 dynamic on specialty currency too
        try:
            from game.domain.shop_experience import apply_dynamic_to_price

            price = apply_dynamic_to_price(
                price, player, shop, side="buy", shop_id=shop_id
            )
        except Exception:
            pass
        return "money_hell", price
    else:
        base = int(it.get("price_world", 50))
        price = scaled_price(base, reg, player, rarity=rarity)
        try:
            from game.domain.shop_experience import apply_dynamic_to_price

            price = apply_dynamic_to_price(
                price, player, shop, side="buy", shop_id=shop_id
            )
        except Exception:
            pass
        return "money_world", price
    # heaven path
    try:
        from game.domain.shop_experience import apply_dynamic_to_price

        price = apply_dynamic_to_price(
            price, player, shop, side="buy", shop_id=shop_id
        )
    except Exception:
        pass
    return "money_heaven", price


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
    shop: Optional[Dict[str, Any]] = None,
    shop_id: str = "",
) -> List[Tuple[str, str, int, Dict[str, Any], str, str]]:
    """
    Build buy rows: (iid, currency, price, it, rarity, bag_cat)
    """
    from game.domain.rarity import tier_rank

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
        # WO-Shop-4: reputation stock gate (uncommon/rare unlock)
        try:
            from game.domain.shop_experience import get_shop_rep, stock_unlocked_for_rep

            rep = get_shop_rep(player, shop_id or shop_id_of_safe(shop))
            if not stock_unlocked_for_rep(rid, rep, entry=entry, player=player):
                continue
        except Exception:
            pass
        cat = _stock_item_category(reg, iid)
        if category and cat != category:
            continue
        cur, price = _price_tuple(
            it, reg, player, rid, shop=shop, shop_id=shop_id
        )
        if entry.get("price_override") is not None:
            price = int(entry["price_override"])
        rows.append((iid, cur, price, it, rid, cat))
    # sort: category soft order already filtered · then price · name
    def _sk(r: Tuple[str, str, int, Dict[str, Any], str, str]) -> Tuple:
        it = r[3]
        return (
            int(it.get("food_tier") or 99),
            int(r[2]),  # price asc — cheaper first, easier to scan
            str(it.get("name") or r[0]),
        )

    rows.sort(key=_sk)
    return rows


def _count_stock_by_category(
    player: Dict[str, Any],
    reg: DataRegistry,
    stock: Sequence[Dict[str, Any]],
    min_rk: int,
    max_rk: int,
    *,
    shop: Optional[Dict[str, Any]] = None,
    shop_id: str = "",
) -> Dict[str, int]:
    counts = {c: 0 for c in SHOP_CAT_ORDER}
    for row in _eligible_buy_rows(
        player,
        reg,
        stock,
        min_rk=min_rk,
        max_rk=max_rk,
        category=None,
        shop=shop,
        shop_id=shop_id,
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


# WO-Shop-1: page size for long stock lists
SHOP_BUY_PAGE = 10


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
    page = 0
    page_size = SHOP_BUY_PAGE
    n_pages = max(1, (len(rows) + page_size - 1) // page_size)

    while True:
        start = page * page_size
        chunk = rows[start : start + page_size]
        lines: List[str] = [
            f" ซื้อ · {short_label}",
            "---",
            f" เงินคุณ  โลก {player.get('money_world', 0)}"
            f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
            f"  ·  นรก {player.get('money_hell', 0)}",
            "---",
            f" รายการ  {len(rows)} ชิ้น"
            + (f"  ·  หน้า {page + 1}/{n_pages}" if n_pages > 1 else ""),
            "---",
        ]
        for j, (iid, cur, price, it, rid, cat) in enumerate(chunk):
            i = start + j + 1
            shown = display_item_name(str(it.get("name") or iid), rid, reg)
            detail = _buy_row_detail(it, cat)
            lines.append(f"  {i}. {shown}")
            price_line = f"      {price} {_currency_name(cur)}"
            if detail:
                price_line += f"  ·  {detail}"
            lines.append(price_line)
            if j < len(chunk) - 1:
                lines.append("")
        lines.append("---")
        if n_pages > 1:
            nav = []
            if page > 0:
                nav.append("P ก่อนหน้า")
            if page + 1 < n_pages:
                nav.append("N ถัดไป")
            if nav:
                lines.append("  " + "  ·  ".join(nav))
        lines.extend(
            [
                "  0  กลับหมวด",
                "---",
                f" พิมพ์ {start + 1}–{start + len(chunk)} เพื่อซื้อ",
            ]
        )
        io.write_line()
        io.write_line(render_box(lines, double=False))
        prompt = f"\n  ซื้อหมายเลข ({start + 1}–{start + len(chunk)}"
        if n_pages > 1:
            prompt += " · N/P หน้า"
        prompt += " · 0 กลับ): "
        ch = io.read_line(prompt).strip().lower()
        if ch in ("0", ""):
            return
        if ch in ("n", "next", ">", "ถัดไป") and page + 1 < n_pages:
            page += 1
            continue
        if ch in ("p", "prev", "<", "ก่อน") and page > 0:
            page -= 1
            continue
        try:
            idx = int(ch) - 1
            if idx < 0 or idx >= len(rows):
                io.write_line("  หมายเลขนอกช่วง")
                continue
            iid, cur, price, it, rid, _cat = rows[idx]
        except Exception:
            io.write_line("  พิมพ์เลข / N / P / 0")
            continue
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
            continue
        # soft confirm for equipment / expensive
        conf_need = _cat == "equipment" or price >= 80
        if conf_need:
            conf = io.read_line(
                f"  ซื้อ「{shown}」 {price} {_currency_name(cur)}? (y/n): "
            ).strip().lower()
            if conf not in ("y", "yes", "ใช่", "1"):
                io.write_line("  ยกเลิก")
                continue
        # WO-INV-1: refuse purchase when bag cannot accept (before charging)
        from game.domain.bag_stack import can_accept_item

        if not can_accept_item(player, str(iid), reg, rarity=str(rid)):
            io.write_line("  กระเป๋าเต็ม — ขาย/ทิ้งของก่อน แล้วค่อยซื้อ")
            continue
        name = add_item(player, iid, reg, rarity=rid)
        if not name:
            io.write_line("  กระเป๋าเต็ม — ซื้อไม่สำเร็จ")
            continue
        player[cur] = have - price
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "shop_purchases", 1)
        except Exception:
            pass
        try:
            from game.domain.shop_experience import bump_shop_rep, shop_rep_soft_label, get_shop_rep

            sid = str(player.get("_shop_active_id") or "")
            bump_shop_rep(player, sid, amount=2, reason="buy")
            _rep_note = shop_rep_soft_label(get_shop_rep(player, sid))
        except Exception:
            _rep_note = ""
        result = [
            " ซื้อสำเร็จ",
            "---",
            f" ได้  {name}",
            f" จ่าย {price} {_currency_name(cur)}  ·  เหลือ {player.get(cur, 0)}",
        ]
        if _rep_note:
            result.append(f" ความคุ้นร้าน: 〔{_rep_note}〕")
        if _cat == "food":
            result.append(" → กระเป๋าหมวด「อาหาร」(5/I → 2)")
        elif _cat == "equipment":
            result.append(" → กระเป๋าหมวด「อุปกรณ์」· สวมที่ เกียร์")
        elif _cat == "healing":
            result.append(" → กระเป๋าหมวด「รักษา」")
        io.write_line()
        io.write_line(render_box(result, double=False))
        # stay on list for multi-buy
        continue


def _buy_browse(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    stock: List[Dict[str, Any]],
    *,
    min_rk: int,
    max_rk: int,
    shop: Optional[Dict[str, Any]] = None,
    shop_id: str = "",
) -> None:
    """Category-first buy menu — เลือกหมวดก่อน แล้วค่อยเลือกชิ้น."""
    from game.ui_terminal.layout import render_box
    from game.domain.shop_experience import category_order_for_shop, specialty_hint

    cat_order = category_order_for_shop(shop_id, shop)
    while True:
        counts = _count_stock_by_category(
            player, reg, stock, min_rk, max_rk, shop=shop, shop_id=shop_id
        )
        total = sum(counts.values())
        lines: List[str] = [
            " ซื้อ · เลือกหมวด",
            "---",
            f" สินค้าในร้านนี้ ~{total} ชิ้น",
        ]
        hint = specialty_hint(shop, shop_id)
        if hint:
            lines.append(f" {hint}")
        lines.append("---")
        menu: List[Tuple[str, str]] = []  # key, cat_id
        n = 0
        for cat in cat_order:
            c = counts.get(cat, 0)
            if c <= 0:
                continue
            n += 1
            label = SHOP_CAT_LABELS.get(cat, cat)
            featured = " ★" if n == 1 else ""
            lines.append(f"  {n}  {label}  ({c}){featured}")
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
                "  ★ = หมวดเด่นของร้านนี้",
                "  เลือกหมวดก่อน (แนะนำ) · A = ทั้งหมดแบบแบ่งหน้า",
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
                player,
                reg,
                stock,
                min_rk=min_rk,
                max_rk=max_rk,
                category=None,
                shop=shop,
                shop_id=shop_id,
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
            player,
            reg,
            stock,
            min_rk=min_rk,
            max_rk=max_rk,
            category=cat_id,
            shop=shop,
            shop_id=shop_id,
        )
        _buy_from_rows(
            player, reg, io, rows, cat_label=SHOP_CAT_LABELS.get(cat_id, cat_id)
        )


# WO-Shop-2: default soft tone if shop yaml omits tone
SHOP_TONE_DEFAULTS: Dict[str, str] = {
    "traveling_merchant": "รถเร่ริมทาง — ยา อาหาร เสบียงเดินทาง",
    "city_armory": "โรงตีเมือง — อาวุธ เกราะ และวัสดุอัปเกรด",
    "celestial_bazaar": "แสงบางและพรแผ่ว — เครื่องราง / blessing",
    "infernal_market": "เถ้าและสัญญา — สัญญานรก / สุญญะ",
    "rare_exchange": "ผลึก ม้วน และ mat หายาก — ไม่ขายเกียร์",
    "legend_pavilion": "ศาลาเงียบ — รับซื้อแรงก์สูง · ตำนานเบา",
}


def shop_tone_line(shop: Optional[Dict[str, Any]], shop_id: str = "") -> str:
    """Soft identity line for hub (never % or prices)."""
    if shop:
        for key in ("tone", "soft_hint", "flavor", "identity"):
            raw = shop.get(key)
            if raw:
                return str(raw).strip()
    sid = str(shop_id or (shop or {}).get("id") or "")
    return SHOP_TONE_DEFAULTS.get(sid, "ร้านระบบ — ซื้อขายของใช้ทั่วไป")


def format_shop_hub_lines(
    player: Dict[str, Any],
    reg: DataRegistry,
    *,
    title: str,
    stock: List[Dict[str, Any]],
    min_rk: int,
    max_rk: int,
    specialty: bool,
    tone: str = "",
    shop_id: str = "",
    greeting: str = "",
    specialty_line: str = "",
    market_day: str = "",
    rep_label: str = "",
    rep_hint: str = "",
) -> List[str]:
    """Sectioned shop front desk for box UI."""
    from game.domain.rarity import rarity_label
    from game.domain.shop_experience import category_order_for_shop

    lines: List[str] = [
        f" ร้าน · {title}",
        "---",
    ]
    if greeting:
        lines.append(f" {greeting}")
        lines.append("---")
    tone_txt = (tone or "").strip() or shop_tone_line(None, shop_id)
    if tone_txt:
        lines.append(f" โทน  {tone_txt}")
    if specialty_line:
        lines.append(f" เด่น  {specialty_line}")
    if rep_label:
        lines.append(f" ความคุ้น  〔{rep_label}〕")
    if market_day:
        lines.append(f" วันนี้  {market_day}")
    if rep_hint:
        lines.append(f" ใบ้  {rep_hint}")
    if tone_txt or specialty_line or market_day or rep_label:
        lines.append("---")
    lines.append(
        f" เงิน  โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}"
    )
    if specialty:
        lo = rarity_label(reg, _rank_to_id(reg, min_rk))
        hi = rarity_label(reg, _rank_to_id(reg, max_rk))
        lines.append(f" ระดับที่รับ  {lo} – {hi}")
    lines.append("---")
    lines.append(" สต็อกตามหมวด (เรียงตามโทนร้าน)")
    counts = _count_stock_by_category(
        player, reg, stock, min_rk, max_rk, shop_id=shop_id
    )
    short = {
        "food": "อาหาร",
        "healing": "ยา",
        "equipment": "อุปกรณ์",
        "material": "วัตถุดิบ",
        "card": "การ์ด",
        "other": "อื่นๆ",
    }
    any_stock = False
    first = True
    for c in category_order_for_shop(shop_id):
        n = int(counts.get(c, 0) or 0)
        if n <= 0:
            continue
        any_stock = True
        star = " ★" if first else ""
        first = False
        lines.append(f"  · {short.get(c, c):<8}  {n} ชิ้น{star}")
    if not any_stock:
        lines.append("  (ว่าง)")
    lines.append("---")
    lines.append(" หมายเหตุ soft")
    lines.append("  · ราคาขยับตามความคุ้นร้าน/วัน (ไม่โชว์ % · ไม่เกินแผ่ว)")
    lines.append("  · คุ้นขึ้น → ราคาดีขึ้น · ของหายากเปิดมากขึ้น")
    lines.append("  · เศษ/mat มีพื้นรับซื้อ · เลือกหมวดก่อน")
    lines.append("  · การ์ดไม่ขายที่นี่ — ดรอปจากมอน/หีบเท่านั้น")
    if not any_stock:
        lines.append("  · ร้านนี้รับซื้อเป็นหลัก (stock ระบบเบา/ว่าง)")
    lines.append("---")
    if any_stock:
        lines.append("  1 / B   ซื้อ (เลือกหมวดก่อน)")
    else:
        lines.append("  1 / B   (ไม่มีของขายระบบ)")
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
    from game.domain.shop_experience import (
        pick_greeting,
        specialty_hint,
        soft_market_day_line,
        ensure_shop_rep,
        get_shop_rep,
        shop_rep_soft_label,
        rep_progress_hint,
        KNOWN_SHOP_IDS,
    )

    shop = dict(reg.shops.get(shop_id) or {})
    shop["id"] = shop_id
    title = str(shop.get("name") or shop_id)
    # seed rep for known shops
    ensure_shop_rep(player, list(KNOWN_SHOP_IDS) + [shop_id])
    # WO-Shop-5: try deliver-item quests for this shop on enter
    try:
        from game.domain.shop_rep_content import try_deliver_shop_quests, friend_bonus_lines

        for ln in try_deliver_shop_quests(player, reg, shop_id):
            io.write_line(ln)
    except Exception:
        pass
    # WO-Shop-6: Anima warmth when rep high
    try:
        from game.domain.shop_experience import shop_anima_warmth_on_visit

        for ln in shop_anima_warmth_on_visit(player, shop_id, reg=reg):
            io.write_line(ln)
    except Exception:
        pass
    # WO-Shop-1/2: buy_stock false → no system catalog
    if shop.get("buy_stock") is False:
        stock = []
    else:
        stock = _normalize_stock(shop if shop else None, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    specialty = min_rk > 1 or max_rk < 8
    tone = shop_tone_line(shop, shop_id)
    player["_shop_active_id"] = shop_id
    greet = pick_greeting(shop, shop_id, player=player)
    spec = specialty_hint(shop, shop_id)
    day_line = soft_market_day_line(player)
    rep_v = get_shop_rep(player, shop_id)
    rep_lab = shop_rep_soft_label(rep_v)
    rep_h = rep_progress_hint(player, shop_id)

    while True:
        # refresh soft lines each loop (rep may change)
        greet = pick_greeting(shop, shop_id, player=player)
        rep_v = get_shop_rep(player, shop_id)
        rep_lab = shop_rep_soft_label(rep_v)
        rep_h = rep_progress_hint(player, shop_id)
        try:
            from game.domain.shop_rep_content import friend_bonus_lines
            from game.domain.shop_experience import integration_hub_lines

            friend_bits = friend_bonus_lines(player, shop_id)
            integ = integration_hub_lines(player, shop_id)
            if friend_bits and rep_h:
                rep_h = rep_h + " · ลูกค้าประจำ"
        except Exception:
            friend_bits = []
            integ = []
        hub_lines = format_shop_hub_lines(
            player,
            reg,
            title=title,
            stock=stock,
            min_rk=min_rk,
            max_rk=max_rk,
            specialty=specialty,
            tone=tone,
            shop_id=shop_id,
            greeting=greet,
            specialty_line=spec,
            market_day=day_line,
            rep_label=rep_lab,
            rep_hint=rep_h,
        )
        extra = list(friend_bits[:1]) + list(integ[:2])
        for fb in extra:
            hub_lines.insert(min(7, len(hub_lines)), fb)
        io.write_line()
        io.write_line(render_box(hub_lines, double=False))
        top = io.read_line("\n  เลือก (1 ซื้อ · 2 ขาย · 0 ออก): ").strip().lower()
        if top in ("0", "", "q"):
            player.pop("_shop_active_id", None)
            break
        if top in ("2", "s", "sell", "ขาย"):
            _run_sell(player, reg, io, shop=shop)
            continue
        if top not in ("1", "b", "buy", "ซื้อ"):
            io.write_line("  พิมพ์ 1=ซื้อ · 2=ขาย · 0=ออก")
            continue
        _buy_browse(
            player,
            reg,
            io,
            stock,
            min_rk=min_rk,
            max_rk=max_rk,
            shop=shop,
            shop_id=shop_id,
        )


def _rank_to_id(reg: DataRegistry, rank: int) -> str:
    for t in (getattr(reg, "rarity", None) or {}).get("tiers") or []:
        if int(t.get("rank") or 0) == rank:
            return str(t.get("id"))
    return "common"


def _confirm_and_bulk_sell(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    shop: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    common_only: bool = False,
    label: str = "",
) -> None:
    """WO-INV bulk sell with preview + y/n confirm."""
    from game.domain.bag_sell import execute_bulk_sell, preview_bulk_sell

    prev = preview_bulk_sell(
        player, reg, category=category, common_only=common_only, shop=shop
    )
    units = int(prev.get("units") or 0)
    slots = int(prev.get("slots") or 0)
    by_cur = dict(prev.get("by_cur") or {})
    if units <= 0:
        io.write_line("  ไม่มีของที่ขายแบบกลุ่มได้ (เรลิก/unique/หีบ/rare+ ถูกกัน)")
        return
    gold_bits = []
    for cur, amt in by_cur.items():
        gold_bits.append(f"{amt} {_currency_name(cur)}")
    gold_txt = " · ".join(gold_bits) if gold_bits else "0"
    lab = label or ("common" if common_only else "หมวด")
    io.write_line(f"\n── ขายกลุ่ม · {lab} ──")
    io.write_line(f"  {slots} ช่อง · {units} ชิ้น · ได้ประมาณ {gold_txt}")
    io.write_line("  (ไม่ขายเรลิก · unique · หีบ · เกียร์ rare+)")
    ans = io.read_line("ยืนยันขายกลุ่ม? (y=ตกลง / n=ยกเลิก): ").strip().lower()
    if ans not in ("y", "yes", "ใช่", "1"):
        io.write_line("  ยกเลิกขายกลุ่ม")
        return
    sold, gains, notes = execute_bulk_sell(
        player, reg, category=category, common_only=common_only, shop=shop
    )
    if sold <= 0:
        io.write_line("  ขายกลุ่มไม่สำเร็จ")
        return
    gain_bits = [f"+{v} {_currency_name(k)}" for k, v in gains.items()]
    io.write_line(f"  ขายกลุ่มสำเร็จ · {sold} ชิ้น · {' · '.join(gain_bits)}")
    for ln in notes[:6]:
        io.write_line(f"   · {ln}")
    if len(notes) > 6:
        io.write_line(f"   · …อีก {len(notes) - 6} รายการ")


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
        for cat in ("food", "healing", "equipment", "material", "other", "card", "relic"):
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
        io.write_line("  J. ขายขยะ common ทั้งกระเป๋า (ยืนยัน)")
        io.write_line("  0. กลับ")
        ch = io.read_line("หมวดขาย: ").strip().lower()
        if ch in ("0", ""):
            return
        # WO-INV: bulk sell all common junk (any category)
        if ch in ("j", "junk", "ขยะ"):
            _confirm_and_bulk_sell(
                player, reg, io, shop=shop, category=None, common_only=True, label="ขยะ common ทั้งกระเป๋า"
            )
            continue
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
        io.write_line("  · การ์ดไม่ขายเป็นสินค้าในร้าน — ขายคืนได้ถูก (soft)")
        if min_rk > 1 or max_rk < 8:
            io.write_line(
                f" ร้านรับเฉพาะระดับ {rarity_label(reg, _rank_to_id(reg, min_rk))}"
                f"–{rarity_label(reg, _rank_to_id(reg, max_rk))}"
            )
        from game.domain.bag_stack import qty_at
        from game.domain.shop_experience import best_buyer_soft_line

        cur_sid = str(shop.get("id") or player.get("_shop_active_id") or "")
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
                # WO-Shop-6: legend soft-accepts relics even if rank edge
                try:
                    from game.domain.bag_sell import is_relic_item
                    from game.domain.shop_experience import (
                        legend_accepts_relic_sell,
                        relic_legend_sell_price,
                    )

                    is_rel = is_relic_item(str(iid), it)
                except Exception:
                    is_rel = False
                    legend_accepts_relic_sell = None  # type: ignore
                    relic_legend_sell_price = None  # type: ignore
                if is_rel and legend_accepts_relic_sell and legend_accepts_relic_sell(
                    cur_sid, shop
                ):
                    accepted = True
                base = int(
                    it.get("price_world")
                    or it.get("price_heaven")
                    or it.get("price_hell")
                    or 10
                )
                if (
                    is_rel
                    and relic_legend_sell_price
                    and legend_accepts_relic_sell
                    and legend_accepts_relic_sell(cur_sid, shop)
                ):
                    cur = "money_world"
                    price = int(
                        relic_legend_sell_price(
                            base, player, shop, rarity=str(rid)
                        )
                    )
                    bd = {"tax_rate": 0.0, "net": price}
                elif it.get("price_heaven") and not it.get("price_world"):
                    cur = "money_heaven"
                    bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                    from game.domain.rarity import rarity_price_mult

                    buy = max(
                        1, int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid)))
                    )
                    price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
                elif it.get("price_hell") and not it.get("price_world"):
                    cur = "money_hell"
                    from game.domain.rarity import rarity_price_mult

                    bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                    buy = max(
                        1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid)))
                    )
                    price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
                else:
                    cur = "money_world"
                    bd = sell_breakdown(base, reg, player, rarity=rid, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                    price = int(bd["net"])
                shown = display_item_name(str(it.get("name") or iid), rid, reg)
                q = qty_at(player, i)
                if q > 1:
                    shown = f"{shown} x{q}"
                if not accepted:
                    io.write_line(f"  · {shown} — ร้านไม่รับระดับนี้")
                    continue
                tax_pct = int(float(bd.get("tax_rate") or 0) * 100) if cur == "money_world" else 0
                extra = ""
                if is_rel and legend_accepts_relic_sell and legend_accepts_relic_sell(
                    cur_sid, shop
                ):
                    extra = " · เรลิก (รับเบา)"
                io.write_line(
                    f"  {len(rows) + 1}. {shown} → ได้ {price} {_currency_name(cur)}/ชิ้น"
                    + (f" (ภาษี ~{tax_pct}%)" if tax_pct else "")
                    + extra
                )
                # WO-Shop-3: soft best-buyer for mats (no %)
                if cat == "material" or str(it.get("kind") or "") == "material":
                    hint = best_buyer_soft_line(
                        str(iid), reg, current_shop_id=cur_sid, item=it
                    )
                    if hint:
                        io.write_line(f"      · {hint}")
                rows.append(("inv", i, iid, rid, cur, price))

        if not rows and sell_cat != "card":
            io.write_line("  (ไม่มีชิ้นที่ขายได้ในหมวดนี้)")
            io.read_line("Enter...")
            continue
        if not rows:
            io.write_line("  (ไม่มีชิ้นที่ขายได้ในหมวดนี้)")
            io.read_line("Enter...")
            continue
        io.write_line("  B. ขายทั้งหมวดนี้ (ทั้ง stack · ยืนยัน)")
        io.write_line("  C. ขายเฉพาะ common ในหมวด (ยืนยัน)")
        io.write_line("  0. กลับหมวด")
        ch2 = io.read_line("ขายหมายเลข / B / C: ").strip().lower()
        if ch2 in ("0", ""):
            continue
        # WO-INV bulk within category
        if ch2 in ("b", "bulk", "ทั้งหมวด"):
            _confirm_and_bulk_sell(
                player,
                reg,
                io,
                shop=shop,
                category=sell_cat,
                common_only=False,
                label="ทั้งหมวด" if sell_cat else "ทั้งหมด (ยกเว้นของป้องกัน)",
            )
            continue
        if ch2 in ("c", "common"):
            _confirm_and_bulk_sell(
                player,
                reg,
                io,
                shop=shop,
                category=sell_cat,
                common_only=True,
                label="common ในหมวด" if sell_cat else "common ทั้งถุง",
            )
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
            it = reg.items.get(iid) or {}
            from game.domain.bag_sell import is_relic_item
            from game.domain.shop_experience import (
                legend_accepts_relic_sell,
                relic_legend_sell_price,
            )

            is_rel = is_relic_item(str(iid), it)
            legend_ok = is_rel and legend_accepts_relic_sell(
                str(shop.get("id") or ""), shop
            )
            if not (min_rk <= rk <= max_rk) and not legend_ok:
                io.write_line("ร้านไม่รับระดับนี้")
                continue
            base = int(
                it.get("price_world")
                or it.get("price_heaven")
                or it.get("price_hell")
                or 10
            )
            if legend_ok:
                cur = "money_world"
                price = int(
                    relic_legend_sell_price(
                        base, player, shop, rarity=str(rid_live)
                    )
                )
                from game.domain.bag_stack import remove_units_at

                removed = remove_units_at(player, live_idx, reg, amount=1)
                if not removed:
                    continue
                player[cur] = int(player.get(cur, 0)) + price
                shown = display_item_name(str(it.get("name") or iid), rid_live, reg)
                io.write_line(f"ขาย {shown} ได้ {price} {_currency_name(cur)}")
                io.write_line("  (เรลิก · ศาลารับเบา — ไม่ bulk)")
                try:
                    from game.domain.shop_experience import bump_shop_rep, get_shop_rep, shop_rep_soft_label

                    sid = str(shop.get("id") or "")
                    bump_shop_rep(player, sid, amount=2, reason="sell")
                    io.write_line(
                        f" ความคุ้นร้าน: 〔{shop_rep_soft_label(get_shop_rep(player, sid))}〕"
                    )
                except Exception:
                    pass
                continue
            if it.get("price_heaven") and not it.get("price_world"):
                cur = "money_heaven"
                from game.domain.rarity import rarity_price_mult

                bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                buy = max(
                    1,
                    int(round(int(it["price_heaven"]) * rarity_price_mult(reg, rid_live))),
                )
                price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
            elif it.get("price_hell") and not it.get("price_world"):
                cur = "money_hell"
                from game.domain.rarity import rarity_price_mult

                bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                buy = max(
                    1, int(round(int(it["price_hell"]) * rarity_price_mult(reg, rid_live)))
                )
                price = max(1, int(round(buy * 0.4 * (1.0 - float(bd["tax_rate"])))))
            else:
                cur = "money_world"
                bd = sell_breakdown(base, reg, player, rarity=rid_live, shop=shop, item_kind=str(it.get('kind') or ''), item_id=str(iid))
                price = int(bd["net"])
            # WO-INV: sell one unit (not whole stack)
            from game.domain.bag_stack import remove_units_at

            removed = remove_units_at(player, live_idx, reg, amount=1)
            if not removed:
                continue
            player[cur] = int(player.get(cur, 0)) + price
            shown = display_item_name(str(it.get("name") or iid), rid_live, reg)
            io.write_line(f"ขาย {shown} ได้ {price} {_currency_name(cur)}")
            # WO-Shop-4: mat/sell builds shop reputation
            try:
                from game.domain.shop_experience import (
                    bump_shop_rep,
                    get_shop_rep,
                    shop_rep_soft_label,
                )

                sid = str(shop.get("id") or player.get("_shop_active_id") or "")
                is_mat = str(it.get("kind") or "") in ("material", "mat") or "mat" in str(
                    iid
                ).lower()
                bump_shop_rep(
                    player,
                    sid,
                    amount=2 if is_mat else 1,
                    reason="sell_mat" if is_mat else "sell",
                )
                io.write_line(
                    f" ความคุ้นร้าน: 〔{shop_rep_soft_label(get_shop_rep(player, sid))}〕"
                )
            except Exception:
                pass
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "shop_sales", 1)
        except Exception:
            pass
