"""SHOP mode hub — Mode Shell Phase B (separate from bag)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.mode_shell import MODE_SHOP, money_summary_lines, render_mode_actions
from game.ports.io import IO
from game.services.field_menus import _run_craft_menu
from game.services.market_service import run_market
from game.services.shop import run_shop
from game.ui_terminal.layout import render_box
from game.ui_terminal.status import render_mode_chrome


def _default_local_shop_id(player: Dict[str, Any]) -> str:
    loc = str(player.get("location") or "")
    if loc in ("ancient_city", "crystal_peak"):
        return "city_armory"
    return "traveling_merchant"


def _local_shop_label(player: Dict[str, Any], reg: DataRegistry) -> str:
    sid = _default_local_shop_id(player)
    shop = (reg.shops or {}).get(sid) or {}
    return str(shop.get("name") or sid)


def format_shop_mode_header(
    player: Dict[str, Any],
    reg: DataRegistry,
    area_name: str,
) -> list:
    """Compact header — money + where local shop points (no full status dump)."""
    local = _local_shop_label(player, reg)
    return [
        " ร้าน · ภาพรวม",
        "---",
        f" พื้นที่   {area_name or player.get('location') or '?'}",
        f" เงิน     โลก {player.get('money_world', 0)}"
        f"  ·  สวรรค์ {player.get('money_heaven', 0)}"
        f"  ·  นรก {player.get('money_hell', 0)}",
        "---",
        f" ร้านท้องถิ่นที่นี่  →  {local}",
    ]


def run_shop_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    area_name: str = "",
) -> None:
    """
    〔ร้าน〕 — ร้าน NPC · ตลาดสวรรค์/นรก · ตลาดผู้เล่น · คราฟ
    """
    area_name = area_name or str(player.get("location") or "")
    while True:
        io.write_line()
        io.write_line(render_mode_chrome("ร้าน", area_name))
        io.write_line(
            render_box(
                format_shop_mode_header(player, reg, area_name),
                double=False,
            )
        )
        io.write_line()
        io.write_line(render_mode_actions(MODE_SHOP))
        ch = io.read_line("\n  〔ร้าน〕 เลือก (1–6 · 0 กลับ): ").strip()
        if ch in ("0", "", "q", "Q"):
            break
        if ch == "1":
            sid = _default_local_shop_id(player)
            run_shop(player, reg, io, shop_id=sid)
        elif ch == "2":
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ตลาดสกุลเงินพิเศษ",
                        "---",
                        "  1  ตลาดสวรรค์   (เงินสวรรค์)",
                        "  2  ตลาดนรก     (เงินนรก)",
                        "  0  กลับ",
                    ],
                    double=False,
                )
            )
            sub = io.read_line("\n  เลือก (1/2/0): ").strip()
            if sub == "1":
                run_shop(player, reg, io, shop_id="celestial_bazaar")
            elif sub == "2":
                run_shop(player, reg, io, shop_id="infernal_market")
        elif ch == "3":
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ตลาดหายาก / ศาลา",
                        "---",
                        "  1  ตลาดวัสดุหายาก   mat · ยาพิเศษ",
                        "  2  ศาลาตำนาน        รับซื้อแรงก์สูง (stock ระบบว่าง)",
                        "  0  กลับ",
                    ],
                    double=False,
                )
            )
            sub = io.read_line("\n  เลือก (1/2/0): ").strip()
            if sub == "1":
                run_shop(player, reg, io, shop_id="rare_exchange")
            elif sub == "2":
                run_shop(player, reg, io, shop_id="legend_pavilion")
        elif ch == "4" or ch in ("m", "M"):
            run_market(player, reg, io)
        elif ch == "5":
            _run_craft_menu(player, reg, io)
        elif ch == "6":
            io.write_line()
            io.write_line(render_box(money_summary_lines(player), double=False))
            io.read_line("\n  Enter...")
        else:
            io.write_line("  เลือก 0–6")
