"""SHOP mode hub — Mode Shell Phase B (separate from bag)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.mode_shell import MODE_SHOP, render_mode_actions
from game.ports.io import IO
from game.services.field_menus import _run_craft_menu
from game.services.market_service import run_market
from game.services.shop import run_shop
from game.ui_terminal.status import render_mode_chrome, render_status_l1c


def _default_local_shop_id(player: Dict[str, Any]) -> str:
    loc = str(player.get("location") or "")
    if loc in ("ancient_city", "crystal_peak"):
        return "city_armory"
    return "traveling_merchant"


def run_shop_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    area_name: str = "",
) -> None:
    """
    〔ร้าน〕 — ร้าน NPC · ตลาดสวรรค์/นรก · ตลาดผู้เล่น · คราฟ
    ไม่อยู่ใต้กระเป๋าเป็นทางเข้าหลักแล้ว (bag ยังมีทางลัด 7)
    """
    area_name = area_name or str(player.get("location") or "")
    while True:
        io.write_line()
        io.write_line(render_mode_chrome("ร้าน", area_name))
        io.write_line(render_status_l1c(player, area_name))
        io.write_line(
            f" เงิน โลก {player.get('money_world', 0)} · "
            f"สวรรค์ {player.get('money_heaven', 0)} · "
            f"นรก {player.get('money_hell', 0)}"
        )
        io.write_line(render_mode_actions(MODE_SHOP))
        ch = io.read_line("\n〔ร้าน〕 เลือก: ").strip()
        if ch in ("0", "", "q", "Q"):
            break
        if ch == "1":
            sid = _default_local_shop_id(player)
            run_shop(player, reg, io, shop_id=sid)
        elif ch == "2":
            io.write_line(" 1 ตลาดสวรรค์  2 ตลาดนรก  0 กลับ")
            sub = io.read_line("เลือก: ").strip()
            if sub == "1":
                run_shop(player, reg, io, shop_id="celestial_bazaar")
            elif sub == "2":
                run_shop(player, reg, io, shop_id="infernal_market")
        elif ch == "3":
            io.write_line(" 1 ตลาดของหายาก  2 ศาลาตำนาน  0 กลับ")
            sub = io.read_line("เลือก: ").strip()
            if sub == "1":
                run_shop(player, reg, io, shop_id="rare_exchange")
            elif sub == "2":
                run_shop(player, reg, io, shop_id="legend_pavilion")
        elif ch == "4" or ch in ("m", "M"):
            run_market(player, reg, io)
        elif ch == "5":
            _run_craft_menu(player, reg, io)
        elif ch == "6":
            # quick peek money only
            from game.domain.mode_shell import money_summary_lines

            for line in money_summary_lines(player):
                io.write_line(line)
            io.read_line("Enter...")
        else:
            io.write_line("เลือก 0–6")
