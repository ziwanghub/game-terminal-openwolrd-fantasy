"""WO-Shop-1: price balance, identity stock, card ban, category UI helpers."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import (
    MAT_SELL_RATIO_CAP,
    is_junk_item,
    scaled_price,
    sell_breakdown,
    sell_price,
)
from game.domain.character import create_player
from game.services.shop import (
    SHOP_BUY_PAGE,
    _eligible_buy_rows,
    _is_shop_banned_card,
    _normalize_stock,
    _stock_item_category,
    format_shop_hub_lines,
    shop_rank_window,
)


def test_junk_cheaper_than_mat():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s1a", "warrior", "เมษ")
    base = 50
    buy = scaled_price(base, reg, p, rarity="common")
    mat = sell_price(
        base, reg, p, rarity="common", item_kind="material", item_id="upgrade_mat"
    )
    junk = sell_price(
        base, reg, p, rarity="common", item_kind="material", item_id="goblin_scrap"
    )
    assert is_junk_item("goblin_scrap", item_kind="material", rarity="common")
    assert not is_junk_item("upgrade_mat", item_kind="material", rarity="common")
    assert junk < mat
    # junk ~20–25% of buy
    assert junk / buy <= 0.26
    assert junk / buy >= 0.18
    # mat default ~28% still under cap
    assert mat / buy <= MAT_SELL_RATIO_CAP + 0.001
    assert mat / buy >= 0.24


def test_specialty_mat_cap():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s1b", "warrior", "เมษ")
    rare = reg.shops.get("rare_exchange") or {}
    legend = reg.shops.get("legend_pavilion") or {}
    base = 100
    buy = scaled_price(base, reg, p, rarity="common")
    for shop in (rare, legend):
        bd = sell_breakdown(
            base,
            reg,
            p,
            rarity="common",
            shop=shop,
            item_kind="material",
            item_id="upgrade_mat",
        )
        # pre-tax eff_ratio capped; net may be slightly lower with tax
        assert float(bd.get("eff_ratio") or 0) <= MAT_SELL_RATIO_CAP + 0.001
        assert bd["net"] / buy <= 0.34 + 0.02  # allow tiny tax/round soft
    # rare mat at specialty still capped
    bd_r = sell_breakdown(
        base,
        reg,
        p,
        rarity="rare",
        shop=rare,
        item_kind="material",
        item_id="rare_mat",
    )
    assert float(bd_r.get("eff_ratio") or 0) <= MAT_SELL_RATIO_CAP + 0.001


def test_shop_identity_no_overlap_heavy():
    """WO-Shop-1/2: armory = gear + upgrade mats · rare = no gear · no potions in armory."""
    reg = DataRegistry.load(DATA_DIR)
    mer = set()
    arm = set()
    rare = set()
    for row in (reg.shops.get("traveling_merchant") or {}).get("stock") or []:
        iid = row if isinstance(row, str) else (row or {}).get("id")
        if iid:
            mer.add(str(iid))
    for row in (reg.shops.get("city_armory") or {}).get("stock") or []:
        iid = row if isinstance(row, str) else (row or {}).get("id")
        if iid:
            arm.add(str(iid))
    for row in (reg.shops.get("rare_exchange") or {}).get("stock") or []:
        iid = row if isinstance(row, str) else (row or {}).get("id")
        if iid:
            rare.add(str(iid))
    # armory: no potions / mon scrap (upgrade mats OK in Shop-2)
    for bad in (
        "balm_nature",
        "potion_hp",
        "wolf_fang",
        "goblin_scrap",
        "herb_bundle",
    ):
        assert bad not in arm
    assert "upgrade_mat" in arm  # Shop-2: gear + upgrade mats
    for iid in arm:
        it = reg.items.get(iid) or {}
        cat = _stock_item_category(reg, iid)
        ok = cat in ("equipment", "material") or it.get("slot") or "armory" in (
            it.get("tags") or []
        )
        assert ok, f"armory unexpected: {iid} cat={cat}"
    # rare_exchange = no equipment gear pieces
    for iid in rare:
        it = reg.items.get(iid) or {}
        cat = _stock_item_category(reg, iid)
        assert cat != "equipment", f"rare sold gear: {iid}"
        assert not it.get("slot") or cat == "other"
    # merchant still has consumables + starter gear
    assert "potion_hp_small" in mer or "potion_hp" in mer
    assert "upgrade_mat" in mer


def test_legend_light_stock_no_cards():
    """WO-Shop-2: legend has light stock · still no cards anywhere."""
    reg = DataRegistry.load(DATA_DIR)
    leg = reg.shops.get("legend_pavilion") or {}
    stock_ids = []
    for row in leg.get("stock") or []:
        iid = row if isinstance(row, str) else (row or {}).get("id")
        if iid:
            stock_ids.append(str(iid))
    assert stock_ids, "legend light stock expected"
    assert all("legend" in iid or iid.startswith("shop_legend") for iid in stock_ids)
    assert len(stock_ids) <= 6  # light, not dump
    for sid, shop in (reg.shops or {}).items():
        for row in shop.get("stock") or []:
            iid = row if isinstance(row, str) else (row or {}).get("id")
            assert not _is_shop_banned_card(reg, str(iid or ""))
            assert not str(iid or "").startswith("card_")


def test_cards_never_in_normalized_stock():
    reg = DataRegistry.load(DATA_DIR)
    for sid in ("traveling_merchant", "city_armory", "rare_exchange"):
        shop = reg.shops.get(sid) or {}
        stock = _normalize_stock(shop, reg=reg)
        for row in stock:
            assert not _is_shop_banned_card(reg, str(row.get("id") or ""))


def test_buy_rows_sorted_and_paged_constant():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s1c", "warrior", "เมษ")
    shop = reg.shops.get("city_armory") or {}
    stock = _normalize_stock(shop, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    rows = _eligible_buy_rows(
        p, reg, stock, min_rk=min_rk, max_rk=max_rk, category="equipment"
    )
    assert len(rows) >= 1
    prices = [r[2] for r in rows]
    assert prices == sorted(prices)
    assert SHOP_BUY_PAGE >= 8
    # hub shows categories
    lines = format_shop_hub_lines(
        p,
        reg,
        title=str(shop.get("name") or "armory"),
        stock=stock,
        min_rk=min_rk,
        max_rk=max_rk,
        specialty=False,
    )
    blob = "\n".join(lines)
    assert "หมวด" in blob or "อุปกรณ์" in blob
    assert "1 / B" in blob or "ซื้อ" in blob
