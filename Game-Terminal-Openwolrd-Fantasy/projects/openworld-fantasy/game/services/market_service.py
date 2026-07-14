"""Central market UI — list, browse, buy, cancel, reports."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.equipment import ensure_gear_fields, recompute_stats
from game.domain.item_codes import item_code
from game.domain.item_instances import ensure_item_instances
from game.domain.market import (
    buy_listing,
    cancel_listing,
    claim_pending_payouts,
    format_market_listings,
    list_item_on_market,
    load_market,
    suggest_list_price,
)
from game.domain.rarity import display_item_name, rarity_of_inventory_index
from game.ports.io import IO
from game.services.save_service import save_player


def run_market(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    world_id: Optional[str] = None,
) -> None:
    """
    ตลาดกลาง — ฝากขายของจากคลัง · ผู้เล่นอื่นซื้อได้
    เมื่อขายได้: เงินเข้าผู้ขาย + รายงานชื่อผู้ซื้อ
    """
    world_id = world_id or str(player.get("world_id") or "default")
    ensure_gear_fields(player)
    ensure_item_instances(player, reg)

    # deliver pending mail / payouts
    for note in claim_pending_payouts(player, world_id):
        io.write_line(note)

    from game.domain.market import get_tax_fund
    from game.ui_terminal.layout import render_box

    while True:
        io.write_line()
        listings = format_market_listings(
            reg, world_id, exclude_seller_id=str(player.get("id") or "")
        )
        n_list = len(load_market(world_id).get("listings") or [])
        fund = get_tax_fund(world_id)
        hub = [
            " ตลาดกลาง",
            "---",
            f" เงินคุณ     โลก {player.get('money_world', 0)}",
            f" รายการตลาด  {n_list}",
            f" กองทุนภาษี  {fund}  (งบกระดานภารกิจ)",
            "---",
            " บอร์ด (ย่อ)",
        ]
        # first few listing lines only for overview
        for ln in listings[:8]:
            hub.append(f" {ln}" if not str(ln).startswith(" ") else ln)
        if len(listings) > 8:
            hub.append(f"  …และอีก {len(listings) - 8} บรรทัด (เมนู 1 ดูเต็ม)")
        hub.extend(
            [
                "---",
                "  1  ดู / ซื้อจากตลาด",
                "  2  ฝากขายจากคลัง",
                "  3  ถอนของที่ฝากเอง",
                "  4  รายงานขายล่าสุด",
                "  0  กลับ",
            ]
        )
        io.write_line(render_box(hub, double=False))
        ch = io.read_line("\n  ตลาด (1–4 · 0): ").strip()
        if ch in ("0", ""):
            try:
                save_player(player, world_id=world_id)
            except Exception:
                pass
            break
        if ch == "1":
            _buy_flow(player, reg, io, world_id)
        elif ch == "2":
            _list_flow(player, reg, io, world_id)
        elif ch == "3":
            _cancel_flow(player, reg, io, world_id)
        elif ch == "4":
            _sales_log(io, world_id)
        else:
            io.write_line("  เลือก 0–4")
        recompute_stats(player, reg)


def _buy_flow(player: Dict[str, Any], reg: DataRegistry, io: IO, world_id: str) -> None:
    market = load_market(world_id)
    listings = list(market.get("listings") or [])
    if not listings:
        io.write_line("ยังไม่มีของในตลาด")
        return
    for i, L in enumerate(listings, 1):
        io.write_line(
            f"  {i}. {L.get('listing_id')} · {L.get('name')} · "
            f"{L.get('price')} เงินโลก · โดย {L.get('seller_name')}"
        )
    raw = io.read_line("ซื้อหมายเลขหรือรหัสรายการ (0=กลับ): ").strip()
    if raw in ("0", ""):
        return
    listing_id = None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(listings):
            listing_id = str(listings[idx].get("listing_id"))
    else:
        listing_id = raw
    if not listing_id:
        io.write_line("ไม่พบรายการ")
        return
    # confirm
    target = next((L for L in listings if str(L.get("listing_id")) == listing_id), None)
    if not target:
        io.write_line("ไม่พบรายการ")
        return
    io.write_line(
        f" จะซื้อ {target.get('name')} จาก {target.get('seller_name')} "
        f"ราคา {target.get('price')} เงินโลก"
    )
    conf = io.read_line("ยืนยันซื้อ? (y/n): ").strip().lower()
    if conf not in ("y", "yes", "ใช่", "1"):
        io.write_line("ยกเลิก")
        return
    ok, msg = buy_listing(player, reg, listing_id, world_id=world_id)
    io.write_line(msg)
    if ok:
        try:
            save_player(player, world_id=world_id)
        except Exception:
            pass


def _list_flow(player: Dict[str, Any], reg: DataRegistry, io: IO, world_id: str) -> None:
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        io.write_line("คลังว่าง — ไม่มีของฝากขาย")
        return
    from game.ui_terminal.layout import render_box

    lines = [" ฝากขาย · ของในคลัง", "---"]
    for i, iid in enumerate(ids):
        it = reg.items.get(iid) or {}
        rid = rarity_of_inventory_index(player, i)
        name = display_item_name(str(it.get("name") or iid), rid, reg)
        code = item_code(iid, reg)
        sug = suggest_list_price(reg, world_id, iid, rid)
        lines.append(f"  {i + 1}. {code}  {name}")
        lines.append(f"      แนะนำราคา ~{sug}")
    lines.extend(["---", "  0  กลับ"])
    io.write_line()
    io.write_line(render_box(lines, double=False))
    raw = io.read_line("\n  เลือกหมายเลขฝากขาย (0=กลับ): ").strip()
    if raw in ("0", ""):
        return
    try:
        idx = int(raw) - 1
    except Exception:
        io.write_line("ใส่หมายเลข")
        return
    if idx < 0 or idx >= len(ids):
        io.write_line("นอกช่วง")
        return
    iid = str(ids[idx])
    rid = rarity_of_inventory_index(player, idx)
    sug = suggest_list_price(reg, world_id, iid, rid)
    io.write_line(f"ราคาแนะนำตลาด ~{sug} (อุปสงค์/อุปทานปรับให้อัตโนมัติ)")
    pr = io.read_line(f"ตั้งราคาเงินโลก (Enter={sug}): ").strip()
    try:
        price = int(pr) if pr else sug
    except Exception:
        price = sug
    conf = io.read_line(f"ฝากขายราคา {price}? (y/n): ").strip().lower()
    if conf not in ("y", "yes", "ใช่", "1"):
        io.write_line("ยกเลิก")
        return
    ok, msg = list_item_on_market(player, reg, idx, price, world_id=world_id)
    io.write_line(msg)
    if ok:
        try:
            save_player(player, world_id=world_id)
        except Exception:
            pass


def _cancel_flow(player: Dict[str, Any], reg: DataRegistry, io: IO, world_id: str) -> None:
    market = load_market(world_id)
    mine = [
        L
        for L in market.get("listings") or []
        if str(L.get("seller_id")) == str(player.get("id"))
    ]
    if not mine:
        io.write_line("คุณไม่มีของฝากขายอยู่ในตลาด")
        return
    for i, L in enumerate(mine, 1):
        io.write_line(
            f"  {i}. {L.get('listing_id')} {L.get('name')} ราคา {L.get('price')}"
        )
    raw = io.read_line("ถอนหมายเลข (0=กลับ): ").strip()
    if raw in ("0", ""):
        return
    try:
        idx = int(raw) - 1
        lid = str(mine[idx].get("listing_id"))
    except Exception:
        io.write_line("ไม่ถูกต้อง")
        return
    ok, msg = cancel_listing(player, reg, lid, world_id=world_id)
    io.write_line(msg)


def _sales_log(io: IO, world_id: str) -> None:
    from game.ui_terminal.layout import render_box

    market = load_market(world_id)
    log = list(market.get("sales_log") or [])[-12:]
    lines = [" รายงานขายล่าสุด", "---"]
    if not log:
        lines.append("  (ยังไม่มีการซื้อขาย)")
    else:
        for s in reversed(log):
            lines.append(f"  · {s.get('sold_at')}")
            lines.append(
                f"    {s.get('buyer_name')} ซื้อ {s.get('item_name')} "
                f"จาก {s.get('seller_name')}"
            )
            lines.append(
                f"    ราคา {s.get('price')} · ผู้ขายได้ {s.get('seller_gain')}"
            )
    io.write_line()
    io.write_line(render_box(lines, double=False))
    io.read_line("\n  Enter...")
