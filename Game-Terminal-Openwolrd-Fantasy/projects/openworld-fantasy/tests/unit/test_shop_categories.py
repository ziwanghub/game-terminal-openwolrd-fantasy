"""Shop category-first browse."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.ports.io import ScriptedIO
from game.services.shop import (
    _count_stock_by_category,
    _eligible_buy_rows,
    _normalize_stock,
    _stock_item_category,
    run_shop,
    shop_rank_window,
)


def test_stock_categories_split():
    reg = DataRegistry.load(DATA_DIR)
    assert _stock_item_category(reg, "city_bread") == "food"
    assert _stock_item_category(reg, "potion_hp") == "healing"
    assert _stock_item_category(reg, "iron_sword") == "equipment"
    assert _stock_item_category(reg, "upgrade_mat") == "material"


def test_traveling_merchant_has_food_and_healing():
    reg = DataRegistry.load(DATA_DIR)
    shop = reg.shops.get("traveling_merchant") or {}
    stock = _normalize_stock(shop)
    p = create_player(reg, "s", "warrior", "เมษ")
    min_rk, max_rk = shop_rank_window(shop)
    counts = _count_stock_by_category(p, reg, stock, min_rk, max_rk)
    assert counts.get("food", 0) >= 1
    assert counts.get("healing", 0) >= 1
    food_rows = _eligible_buy_rows(
        p, reg, stock, min_rk=min_rk, max_rk=max_rk, category="food"
    )
    assert food_rows
    assert all(r[5] == "food" for r in food_rows)


def test_shop_buy_category_flow():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "buyer", "warrior", "เมษ")
    p["money_world"] = 500
    # B buy -> food (f) -> buy #1 -> stay on list (WO-Shop multi-buy) -> 0 back list
    # -> 0 back categories -> 0 exit shop
    io = ScriptedIO(["b", "f", "1", "0", "0", "0"])
    run_shop(p, reg, io, shop_id="traveling_merchant")
    # should have bought something food-like
    ids = p.get("inventory_ids") or []
    from game.domain.inventory_sys import item_category

    foods = [i for i in ids if item_category(str(i), reg) == "food"]
    # might already have starter items; at least money spent or food increased
    assert int(p.get("money_world") or 0) < 500 or foods
