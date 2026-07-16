"""WO-Shop-3: flavor dialogue, light dynamic price, best-buyer, cat order."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import sell_price, scaled_price
from game.domain.character import create_player
from game.domain.shop_experience import (
    DYNAMIC_CLAMP,
    DYNAMIC_CLAMP_BUY,
    best_buyer_shop_id,
    best_buyer_soft_line,
    bump_shop_rep,
    category_order_for_shop,
    dynamic_price_mult,
    ensure_shop_rep,
    game_day_index,
    pick_greeting,
    soft_band_floor,
    specialty_hint,
)
from game.services.shop import (
    _eligible_buy_rows,
    _normalize_stock,
    format_shop_hub_lines,
    shop_rank_window,
    shop_tone_line,
)


def test_greetings_differ_by_shop():
    reg = DataRegistry.load(DATA_DIR)
    greets = {}
    p = create_player(reg, "s3g", "warrior", "เมษ")
    for sid in (
        "traveling_merchant",
        "city_armory",
        "rare_exchange",
        "celestial_bazaar",
        "infernal_market",
        "legend_pavilion",
    ):
        shop = reg.shops.get(sid) or {}
        g = pick_greeting(shop, sid, player=p)
        assert g
        greets[sid] = g
        hint = specialty_hint(shop, sid)
        assert hint
        assert "การ์ด" not in hint or "ไม่" in hint
    # at least several unique greet openings
    assert len(set(greets.values())) >= 3


def test_dynamic_price_light_clamp():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s3d", "warrior", "เมษ")
    shop = dict(reg.shops.get("city_armory") or {})
    shop["id"] = "city_armory"
    ensure_shop_rep(p, ["city_armory"])
    m0 = dynamic_price_mult(p, shop, side="buy")
    assert DYNAMIC_CLAMP_BUY[0] <= m0 <= DYNAMIC_CLAMP_BUY[1]
    # rep soft: more rep → buy mult tends lower / sell higher
    p["shop_rep"] = {"city_armory": 90}
    p["help_rep"] = 40
    m_buy = dynamic_price_mult(p, shop, side="buy")
    m_sell = dynamic_price_mult(p, shop, side="sell")
    assert m_buy <= m0 + 0.02
    assert m_sell >= m_buy - 0.01
    # day changes mult softly
    p["time_units"] = 100
    m1 = dynamic_price_mult(p, shop, side="buy")
    assert DYNAMIC_CLAMP[0] <= m1 <= DYNAMIC_CLAMP[1]
    assert game_day_index(p) == 5


def test_junk_mat_soft_floor():
    buy = 50
    # junk floor ~18%
    assert soft_band_floor(buy, 1, band="junk") >= int(buy * 0.18)
    # mat floor ~22% min 2
    assert soft_band_floor(buy, 1, band="mat") >= max(2, int(buy * 0.22))
    # default passthrough
    assert soft_band_floor(buy, 33, band="default") == 33


def test_sell_price_dynamic_and_floor():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s3s", "warrior", "เมษ")
    p["time_units"] = 40
    shop = dict(reg.shops.get("rare_exchange") or {})
    shop["id"] = "rare_exchange"
    mat = sell_price(
        50, reg, p, rarity="common", shop=shop, item_kind="material", item_id="upgrade_mat"
    )
    junk = sell_price(
        50, reg, p, rarity="common", shop=shop, item_kind="material", item_id="goblin_scrap"
    )
    buy = scaled_price(50, reg, p, rarity="common")
    assert junk < mat
    assert junk >= max(1, int(buy * 0.17))
    assert mat >= max(2, int(buy * 0.20))


def test_best_buyer_hints():
    reg = DataRegistry.load(DATA_DIR)
    assert best_buyer_shop_id("upgrade_mat") == "city_armory"
    assert best_buyer_shop_id("crystal_dust") == "rare_exchange"
    assert best_buyer_shop_id("void_ash") == "infernal_market"
    line = best_buyer_soft_line("upgrade_mat", reg, current_shop_id="traveling_merchant")
    assert "ร้านอาวุธ" in line or "city_armory" in line or "รับซื้อ" in line
    here = best_buyer_soft_line("upgrade_mat", reg, current_shop_id="city_armory")
    assert "ร้านนี้" in here or "ดี" in here


def test_category_order_by_tone():
    arm = category_order_for_shop("city_armory")
    mer = category_order_for_shop("traveling_merchant")
    rare = category_order_for_shop("rare_exchange")
    assert arm[0] == "equipment"
    assert mer[0] in ("healing", "food")
    assert rare[0] == "material"


def test_hub_shows_experience_polish():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s3h", "warrior", "เมษ")
    p["time_units"] = 25
    shop = reg.shops["city_armory"]
    stock = _normalize_stock(shop, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    lines = format_shop_hub_lines(
        p,
        reg,
        title=str(shop.get("name")),
        stock=stock,
        min_rk=min_rk,
        max_rk=max_rk,
        specialty=False,
        tone=shop_tone_line(shop, "city_armory"),
        shop_id="city_armory",
        greeting=pick_greeting(shop, "city_armory", player=p),
        specialty_line=specialty_hint(shop, "city_armory"),
        market_day="ตลาดเงียบ — ราคารู้สึกนิ่ง",
    )
    blob = "\n".join(lines)
    assert "โทน" in blob
    assert "เด่น" in blob or "เกียร์" in blob
    assert "การ์ดไม่ขาย" in blob
    assert "★" in blob or "อุปกรณ์" in blob
    # buy rows use dynamic (just ensure eligible works)
    rows = _eligible_buy_rows(
        p,
        reg,
        stock,
        min_rk=min_rk,
        max_rk=max_rk,
        category="equipment",
        shop=dict(shop, id="city_armory"),
        shop_id="city_armory",
    )
    assert rows
