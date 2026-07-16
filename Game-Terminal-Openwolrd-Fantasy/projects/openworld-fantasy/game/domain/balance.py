"""Central balance helpers — death penalty, shop prices, drops."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple  # Dict used in sell_breakdown

from game.data_load.registry import DataRegistry


def death_penalties(reg: DataRegistry) -> Tuple[float, float]:
    cfg = reg.levels or {}
    return (
        float(cfg.get("death_money_loss_pct", 0.08)),
        float(cfg.get("death_xp_loss_pct", 0.05)),
    )


def grant_combat_money(
    player: MutableMapping[str, Any],
    monster: Mapping[str, Any],
    rng: Any,
    *,
    auto: bool = False,
    money_factor: float = 1.0,
) -> List[str]:
    """
    WO-021: combat loot money — always grant money_world, optional heaven/hell bonus.

    Manual (auto=False): world base ~10–40+Lv; ~40% chance extra special currency.
    Auto (auto=True): world base closer to manual (~10–32+Lv/2); same bonus chance
    (slightly lower). money_factor scales world only (field auto XP penalty soft).
    """
    import random as _random

    if rng is None:
        rng = _random
    mon_lv = int(monster.get("level") or 1)
    if auto:
        # closer to manual: was randint(3,12) only-world
        world = int(rng.randint(10, 32) + max(0, mon_lv // 2))
    else:
        world = int(rng.randint(10, 40) + mon_lv)
    money_m = float((player.get("world_modifiers") or {}).get("money_mult", 1.0))
    mf = max(0.55, min(1.25, float(money_factor or 1.0)))
    # WO-027/030: soft economy dampen while carrying divine burden
    ba = str(player.get("_burden_active") or "")
    if ba == "crush":
        mf *= 0.87  # playtest: keep ~12% softer than free
    elif ba == "strain":
        mf *= 0.93
    world = max(1, int(round(world * money_m * mf)))

    player["money_world"] = int(player.get("money_world") or 0) + world
    lines: List[str] = [f"เงินโลก +{world}"]
    if ba in ("crush", "strain") and world > 0:
        try:
            if rng.random() < 0.20:
                lines.append("  (เรลิกกด — เงินโลกได้แผ่วลงเล็กน้อย)")
        except Exception:
            pass
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "money_gained_total", world)
    except Exception:
        pass

    # Bonus special currency ON TOP of world (not instead-of)
    bonus_p = 0.42 if not auto else 0.32
    if monster.get("boss") or monster.get("dungeon_boss"):
        bonus_p = min(0.85, bonus_p + 0.25)
    if rng.random() < bonus_p:
        if rng.random() < 0.5:
            g = max(1, world // 7)
            player["money_heaven"] = int(player.get("money_heaven") or 0) + g
            lines.append(f"เงินสวรรค์ +{g}")
        else:
            g = max(1, world // 5)
            player["money_hell"] = int(player.get("money_hell") or 0) + g
            lines.append(f"เงินนรก +{g}")
    return lines


def apply_soft_death(player: MutableMapping[str, Any], reg: DataRegistry) -> str:
    """
    Soft death (WO-012): half HP + % money_world + % current XP bar.
    Same function for manual combat_session and auto_fight — keep symmetric.
    """
    money_pct, xp_pct = death_penalties(reg)
    notes = []
    money = int(player.get("money_world", 0))
    loss_m = int(money * money_pct)
    if loss_m > 0:
        player["money_world"] = money - loss_m
        notes.append(f"เสียเงินโลก {loss_m} (~{int(money_pct * 100)}%)")
    xp = int(player.get("xp", 0))
    loss_x = int(xp * xp_pct)
    if loss_x > 0:
        player["xp"] = max(0, xp - loss_x)
        notes.append(f"เสีย XP แถบปัจจุบัน {loss_x} (~{int(xp_pct * 100)}%)")
    # Symmetric floor with combat_session path (half max, at least 10)
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
    # dungeon shadow shop / in-dungeon pricing
    if str(loc).startswith("dungeon:") or player.get("dungeon_run"):
        try:
            from game.domain.dungeon import dungeon_shop_price_mult

            mult = float(dungeon_shop_price_mult(player))
        except Exception:
            mult = 1.45
    else:
        mult = area_price_mult(reg, loc)
    # explicit override (session flag)
    if player.get("_dungeon_shop_mult"):
        mult = float(player.get("_dungeon_shop_mult") or mult)
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


# WO-Shop-1: junk / mat sell soft caps (of buy-equivalent; never shown as % in UI)
JUNK_SELL_RATIO = 0.22  # 20–25% band center
MAT_SELL_RATIO_CAP = 0.34  # specialty shops cannot pay more than this for mats
_CRAFT_MAT_IDS = frozenset({"upgrade_mat", "rare_mat"})
_JUNK_ID_HINTS = (
    "scrap",
    "junk",
    "rat_tail",
    "goblin_scrap",
    "stone_chip",
    "bird_quill",
    "undead_ash",
    "void_ash",
    "marsh_slime",
)


def is_junk_item(
    item_id: Optional[str] = None,
    *,
    item_kind: Optional[str] = None,
    rarity: Optional[str] = None,
    item: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    Soft junk for sell ratio — scrap/trash mats, not core craft mats.
    Equipment / potions / food / upgrade_mat are never junk.
    """
    iid = str(item_id or "").lower()
    it = dict(item or {})
    kind = str(item_kind or it.get("kind") or "").lower()
    rid = str(rarity or it.get("rarity") or "common").lower()
    if iid in _CRAFT_MAT_IDS:
        return False
    if kind in ("equipment", "weapon", "armor", "accessory", "relic", "key", "quest", "consumable", "food"):
        return False
    if it.get("slot") or it.get("heal_hp") or it.get("heal_mana") or it.get("food_tier"):
        return False
    tags = it.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tag_l = {str(t).lower() for t in tags}
    if kind in ("junk", "scrap") or "junk" in tag_l or "scrap" in tag_l:
        return True
    if any(h in iid for h in _JUNK_ID_HINTS):
        return True
    # cheap common material scrap (price floor trash)
    if kind in ("material", "mat") or "mat" in iid:
        price = int(it.get("price_world") or 0)
        if rid in ("common", "") and 0 < price < 28 and iid not in _CRAFT_MAT_IDS:
            name = str(it.get("name") or "")
            if "เศษ" in name or "scrap" in name.lower() or price <= 18:
                return True
    return False


def _is_material_kind(item_kind: Optional[str], item_id: Optional[str]) -> bool:
    kind = str(item_kind or "").lower()
    iid = str(item_id or "").lower()
    return kind == "material" or kind == "mat" or "mat" in iid or iid in _CRAFT_MAT_IDS


def _apply_sell_ratio_modifiers(
    sell_ratio: float,
    *,
    shop: Optional[Mapping[str, Any]],
    item_kind: Optional[str],
    item_id: Optional[str],
    rarity: str,
    item: Optional[Mapping[str, Any]] = None,
) -> Tuple[float, str]:
    """
    Returns (ratio, band) band in junk|mat|default for debug/tests.
    WO-ITEM-3 mat sink · WO-Shop-1 junk + mat cap.
    """
    rid = str(rarity or "common")
    kind = str(item_kind or "").lower()
    iid = str(item_id or "").lower()
    band = "default"
    if is_junk_item(iid, item_kind=kind, rarity=rid, item=item):
        # absolute soft junk band 20–25%
        sell_ratio = float(JUNK_SELL_RATIO)
        if shop and shop.get("junk_sell_ratio") is not None:
            sell_ratio = float(shop["junk_sell_ratio"])
            sell_ratio = max(0.20, min(0.25, sell_ratio))
        band = "junk"
        return sell_ratio, band
    if _is_material_kind(kind, iid):
        if rid.lower() in ("common", "uncommon", ""):
            sell_ratio = float(sell_ratio) * 0.72
        elif rid.lower() == "rare":
            sell_ratio = float(sell_ratio) * 0.88
        # specialty shops: never pay more than cap for mats
        cap = MAT_SELL_RATIO_CAP
        if shop and shop.get("mat_sell_cap") is not None:
            cap = float(shop["mat_sell_cap"])
        sell_ratio = min(float(sell_ratio), cap)
        band = "mat"
    return float(sell_ratio), band


def sell_price(
    base: int,
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    rarity: Optional[str] = None,
    sell_ratio: Optional[float] = None,
    apply_tax: bool = True,
    shop: Optional[Mapping[str, Any]] = None,
    item_kind: Optional[str] = None,
    item_id: Optional[str] = None,
) -> int:
    """
    Player sells to shop.
    1) buy-equivalent price with rarity
    2) * sell_ratio (default from rarity config)
    3) price insurance floor (ประกันราคา)
    4) sell tax by rarity (ภาษี) — optional shop tax_mult
    5) WO-Shop-3: light dynamic mult + junk/mat soft floor

    WO-ITEM-3: common materials sell softer (economy sink) unless shop overrides.
    WO-Shop-1: junk ~22% · mat effective cap ≤34%.
    """
    rid = rarity or "common"
    buy = scaled_price(base, reg, player, rarity=rid)
    rcfg = getattr(reg, "rarity", None) or {}
    if sell_ratio is None:
        sell_ratio = float(rcfg.get("default_sell_ratio") or 0.4)
    if shop and shop.get("sell_ratio") is not None:
        sell_ratio = float(shop["sell_ratio"])
    kind = str(item_kind or "").lower()
    iid = str(item_id or "").lower()
    it = None
    try:
        it = (getattr(reg, "items", None) or {}).get(str(item_id or "")) or None
    except Exception:
        it = None
    sell_ratio, band = _apply_sell_ratio_modifiers(
        float(sell_ratio),
        shop=shop,
        item_kind=kind,
        item_id=iid,
        rarity=str(rid),
        item=it,
    )
    gross = max(1, int(round(buy * float(sell_ratio))))

    # ประกันราคา: อย่างน้อย floor * buy
    floor_tbl = rcfg.get("price_insurance_floor") or {}
    floor_ratio = float(floor_tbl.get(rid, floor_tbl.get("common", 0.25)))
    if shop and shop.get("price_insurance_floor") is not None:
        floor_ratio = float(shop["price_insurance_floor"])
    # WO-ITEM-3 / Shop-1: mat/junk floor soft so insurance doesn't cancel sink
    if band == "junk":
        floor_ratio = min(floor_ratio, 0.12)
    elif band == "mat" or _is_material_kind(kind, iid):
        floor_ratio = min(floor_ratio, 0.18)
    floor_amt = max(1, int(round(buy * floor_ratio)))
    insured = max(gross, floor_amt)

    if not apply_tax:
        try:
            from game.domain.shop_experience import apply_dynamic_to_price, soft_band_floor

            dyn = apply_dynamic_to_price(insured, player, shop, side="sell")
            return soft_band_floor(buy, dyn, band=band)
        except Exception:
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
    # WO-Shop-3: day/rep soft + hard floor band for junk/mat
    try:
        from game.domain.shop_experience import apply_dynamic_to_price, soft_band_floor

        net = apply_dynamic_to_price(net, player, shop, side="sell")
        net = soft_band_floor(buy, net, band=band)
    except Exception:
        pass
    return net


def sell_breakdown(
    base: int,
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    rarity: Optional[str] = None,
    shop: Optional[Mapping[str, Any]] = None,
    item_kind: Optional[str] = None,
    item_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Detail for UI: gross, floor, tax, net."""
    rid = rarity or "common"
    buy = scaled_price(base, reg, player, rarity=rid)
    rcfg = getattr(reg, "rarity", None) or {}
    ratio = float(rcfg.get("default_sell_ratio") or 0.4)
    if shop and shop.get("sell_ratio") is not None:
        ratio = float(shop["sell_ratio"])
    kind = str(item_kind or "").lower()
    iid = str(item_id or "").lower()
    it = None
    try:
        it = (getattr(reg, "items", None) or {}).get(str(item_id or "")) or None
    except Exception:
        it = None
    ratio, band = _apply_sell_ratio_modifiers(
        float(ratio),
        shop=shop,
        item_kind=kind,
        item_id=iid,
        rarity=str(rid),
        item=it,
    )
    gross = max(1, int(round(buy * ratio)))
    floor_tbl = rcfg.get("price_insurance_floor") or {}
    floor_ratio = float(floor_tbl.get(rid, 0.25))
    if shop and shop.get("price_insurance_floor") is not None:
        floor_ratio = float(shop["price_insurance_floor"])
    if band == "junk":
        floor_ratio = min(floor_ratio, 0.12)
    elif band == "mat" or _is_material_kind(kind, iid):
        floor_ratio = min(floor_ratio, 0.18)
    floor_amt = max(1, int(round(buy * floor_ratio)))
    insured = max(gross, floor_amt)
    tax_tbl = rcfg.get("sell_tax_rate") or {}
    tax = float(tax_tbl.get(rid, 0.0))
    if shop and shop.get("sell_tax_bonus") is not None:
        tax = min(0.9, tax + float(shop["sell_tax_bonus"]))
    tax_amt = max(0, insured - max(1, int(round(insured * (1.0 - tax)))))
    net = sell_price(
        base, reg, player, rarity=rid, shop=shop, item_kind=item_kind, item_id=item_id
    )
    dyn_m = 1.0
    try:
        from game.domain.shop_experience import dynamic_price_mult

        dyn_m = float(dynamic_price_mult(player, shop, side="sell"))
    except Exception:
        pass
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
        "sell_band": band,
        "eff_ratio": round(float(ratio), 4),
        "dynamic_mult": round(dyn_m, 4),
    }


def material_drop_chances(player: Mapping[str, Any]) -> Tuple[float, float]:
    """(upgrade_mat, rare_mat) — lower at high level if overfarming same tier."""
    lv = int(player.get("level", 1))
    # base chances reduced from earlier for balance
    up = max(0.12, 0.28 - lv * 0.004)
    rare = max(0.03, 0.06 - lv * 0.001)
    return up, rare
