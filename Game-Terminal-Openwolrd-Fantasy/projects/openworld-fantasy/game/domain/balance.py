"""Central balance helpers — death penalty, shop prices, drops."""
from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple  # Dict used in sell_breakdown

from game.data_load.registry import DataRegistry


def death_penalties(reg: DataRegistry) -> Tuple[float, float]:
    cfg = reg.levels or {}
    return (
        float(cfg.get("death_money_loss_pct", 0.08)),
        float(cfg.get("death_xp_loss_pct", 0.05)),
    )


def apply_soft_death(player: MutableMapping[str, Any], reg: DataRegistry) -> str:
    """Soft death: half HP + lose % money_world + lose % of current XP bar."""
    money_pct, xp_pct = death_penalties(reg)
    notes = []
    money = int(player.get("money_world", 0))
    loss_m = int(money * money_pct)
    if loss_m > 0:
        player["money_world"] = money - loss_m
        notes.append(f"เสียเงินโลก {loss_m}")
    xp = int(player.get("xp", 0))
    loss_x = int(xp * xp_pct)
    if loss_x > 0:
        player["xp"] = max(0, xp - loss_x)
        notes.append(f"เสีย XP แถบปัจจุบัน {loss_x}")
    player["hp"] = max(10, int(player.get("max_hp", 20)) // 2)
    player["pressure"] = max(0, int(player.get("pressure", 0)) - 5)
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "deaths", 1)
    except Exception:
        pass
    # N5: survive soft death while starving → hunger memory
    try:
        from game.domain.needs import band, get_needs, note_n5_hunger_survived

        n = get_needs(player)
        if band("hunger", n["hunger"]) in ("crit", "bad"):
            for line in note_n5_hunger_survived(player):
                notes.append(line)
    except Exception:
        pass
    detail = " · ".join(notes) if notes else "ไม่เสียทรัพยากร (จนเกินไป)"
    return f"สลบ... ฟื้นครึ่งเลือด · {detail}"


def area_price_mult(reg: DataRegistry, area_id: str) -> float:
    area = reg.areas.get(area_id) or {}
    tier = int(area.get("world_tier", 1))
    return 1.0 + max(0, tier - 1) * 0.15


def scaled_price(
    base: int,
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    rarity: Optional[str] = None,
) -> int:
    loc = str(player.get("location") or "dark_forest")
    mult = area_price_mult(reg, loc)
    # slight level scaling so late game money sinks
    lv = int(player.get("level", 1))
    mult *= 1.0 + min(0.5, (lv - 1) * 0.01)
    if rarity:
        try:
            from game.domain.rarity import rarity_price_mult

            mult *= float(rarity_price_mult(reg, rarity))
        except Exception:
            pass
    return max(1, int(round(base * mult)))


def sell_price(
    base: int,
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    rarity: Optional[str] = None,
    sell_ratio: Optional[float] = None,
    apply_tax: bool = True,
    shop: Optional[Mapping[str, Any]] = None,
) -> int:
    """
    Player sells to shop.
    1) buy-equivalent price with rarity
    2) * sell_ratio (default from rarity config)
    3) price insurance floor (ประกันราคา)
    4) sell tax by rarity (ภาษี) — optional shop tax_mult
    """
    rid = rarity or "common"
    buy = scaled_price(base, reg, player, rarity=rid)
    rcfg = getattr(reg, "rarity", None) or {}
    if sell_ratio is None:
        sell_ratio = float(rcfg.get("default_sell_ratio") or 0.4)
    if shop and shop.get("sell_ratio") is not None:
        sell_ratio = float(shop["sell_ratio"])
    gross = max(1, int(round(buy * float(sell_ratio))))

    # ประกันราคา: อย่างน้อย floor * buy
    floor_tbl = rcfg.get("price_insurance_floor") or {}
    floor_ratio = float(floor_tbl.get(rid, floor_tbl.get("common", 0.25)))
    if shop and shop.get("price_insurance_floor") is not None:
        floor_ratio = float(shop["price_insurance_floor"])
    floor_amt = max(1, int(round(buy * floor_ratio)))
    insured = max(gross, floor_amt)

    if not apply_tax:
        return insured

    tax_tbl = rcfg.get("sell_tax_rate") or {}
    tax = float(tax_tbl.get(rid, 0.0))
    if shop and shop.get("sell_tax_bonus") is not None:
        tax = min(0.9, tax + float(shop["sell_tax_bonus"]))
    if shop and shop.get("sell_tax_rate") is not None:
        # shop can override entire tax table key
        override = shop.get("sell_tax_rate")
        if isinstance(override, dict):
            tax = float(override.get(rid, tax))
        else:
            tax = float(override)
    net = max(1, int(round(insured * (1.0 - tax))))
    return net


def sell_breakdown(
    base: int,
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    rarity: Optional[str] = None,
    shop: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Detail for UI: gross, floor, tax, net."""
    rid = rarity or "common"
    buy = scaled_price(base, reg, player, rarity=rid)
    rcfg = getattr(reg, "rarity", None) or {}
    ratio = float(rcfg.get("default_sell_ratio") or 0.4)
    if shop and shop.get("sell_ratio") is not None:
        ratio = float(shop["sell_ratio"])
    gross = max(1, int(round(buy * ratio)))
    floor_tbl = rcfg.get("price_insurance_floor") or {}
    floor_ratio = float(floor_tbl.get(rid, 0.25))
    if shop and shop.get("price_insurance_floor") is not None:
        floor_ratio = float(shop["price_insurance_floor"])
    floor_amt = max(1, int(round(buy * floor_ratio)))
    insured = max(gross, floor_amt)
    tax_tbl = rcfg.get("sell_tax_rate") or {}
    tax = float(tax_tbl.get(rid, 0.0))
    if shop and shop.get("sell_tax_bonus") is not None:
        tax = min(0.9, tax + float(shop["sell_tax_bonus"]))
    tax_amt = max(0, insured - max(1, int(round(insured * (1.0 - tax)))))
    net = sell_price(base, reg, player, rarity=rid, shop=shop)
    return {
        "buy_ref": buy,
        "gross": gross,
        "floor": floor_amt,
        "insured": insured,
        "tax_rate": tax,
        "tax": tax_amt,
        "net": net,
        "rarity": rid,
        "insurance_applied": insured > gross,
    }


def material_drop_chances(player: Mapping[str, Any]) -> Tuple[float, float]:
    """(upgrade_mat, rare_mat) — lower at high level if overfarming same tier."""
    lv = int(player.get("level", 1))
    # base chances reduced from earlier for balance
    up = max(0.12, 0.28 - lv * 0.004)
    rare = max(0.03, 0.06 - lv * 0.001)
    return up, rare
