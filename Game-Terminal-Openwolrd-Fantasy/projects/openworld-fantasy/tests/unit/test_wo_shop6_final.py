"""WO-Shop-6: final polish + Anima/Grade/Relic/Spar integration."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.shop_experience import (
    DYNAMIC_CLAMP_BUY,
    ensure_shop_rep,
    get_shop_rep,
    grade_shop_price_bias,
    integration_hub_lines,
    legend_accepts_relic_sell,
    on_arena_or_spar_win,
    pick_greeting,
    relic_legend_sell_price,
    shop_anima_warmth_on_visit,
    shop_rep_band,
    stock_unlocked_for_rep,
    dynamic_price_mult,
)
from game.services.shop import format_shop_hub_lines, shop_tone_line


def test_all_rep_bands_have_dialogue():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s6a", "warrior", "เมษ")
    shop = reg.shops.get("city_armory") or {}
    greets = set()
    for rep, band in ((15, "cold"), (30, "cool"), (50, "known"), (70, "warm"), (90, "friend")):
        p["shop_rep"] = {"city_armory": rep}
        assert shop_rep_band(rep) == band or (
            band == "cool" and shop_rep_band(rep) in ("cool", "known")
        )
        g = pick_greeting(shop, "city_armory", player=p)
        assert g
        greets.add(g)
    # friend should differ from cold
    p["shop_rep"] = {"city_armory": 15}
    cold = pick_greeting(shop, "city_armory", player=p)
    p["shop_rep"] = {"city_armory": 90}
    friend = pick_greeting(shop, "city_armory", player=p)
    assert cold != friend or "ลูกค้า" in friend or "ประจำ" in friend


def test_grade_affects_buy_price():
    reg = DataRegistry.load(DATA_DIR)
    shop = dict(reg.shops.get("city_armory") or {})
    shop["id"] = "city_armory"
    p_lo = create_player(reg, "s6b", "warrior", "เมษ")
    p_hi = create_player(reg, "s6c", "warrior", "เมษ")
    for p in (p_lo, p_hi):
        ensure_shop_rep(p, ["city_armory"])
        p["shop_rep"] = {"city_armory": 70}
        p["grade_revealed"] = True
    p_lo["player_grade"] = "F"
    p_hi["player_grade"] = "SSS"
    assert grade_shop_price_bias(p_hi, side="buy") < grade_shop_price_bias(
        p_lo, side="buy"
    )
    m_lo = dynamic_price_mult(p_lo, shop, side="buy")
    m_hi = dynamic_price_mult(p_hi, shop, side="buy")
    assert m_hi < m_lo
    assert DYNAMIC_CLAMP_BUY[0] <= m_hi <= DYNAMIC_CLAMP_BUY[1]


def test_grade_boosts_stock_unlock():
    p_lo = {"player_grade": "F", "grade_revealed": True}
    p_hi = {"player_grade": "SSS", "grade_revealed": True}
    # rep 55: rare needs 60 — high grade +12 → unlocked
    assert not stock_unlocked_for_rep("rare", 55, player=p_lo)
    assert stock_unlocked_for_rep("rare", 55, player=p_hi)


def test_anima_warmth_high_rep():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s6d", "warrior", "เมษ")
    ensure_shop_rep(p, ["rare_exchange"])
    p["shop_rep"] = {"rare_exchange": 75}
    p["time_units"] = 20
    from game.domain.stat_arch import anima_value, ensure_stat_arch

    ensure_stat_arch(p)
    before = float(anima_value(p))
    notes = shop_anima_warmth_on_visit(p, "rare_exchange", reg=reg)
    assert notes
    assert float(anima_value(p)) >= before
    # throttle
    notes2 = shop_anima_warmth_on_visit(p, "rare_exchange", reg=reg)
    assert notes2 == []


def test_legend_relic_sell_soft():
    assert legend_accepts_relic_sell("legend_pavilion")
    assert not legend_accepts_relic_sell("city_armory")
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s6e", "warrior", "เมษ")
    p["shop_rep"] = {"legend_pavilion": 80}
    shop = dict(reg.shops.get("legend_pavilion") or {})
    shop["id"] = "legend_pavilion"
    price = relic_legend_sell_price(500, p, shop, rarity="legendary")
    assert 5 <= price < 200  # soft, not dump


def test_spar_win_grants_shop_rep():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s6f", "warrior", "เมษ")
    ensure_shop_rep(p, ["city_armory", "traveling_merchant"])
    p["time_units"] = 30
    before_a = get_shop_rep(p, "city_armory")
    before_m = get_shop_rep(p, "traveling_merchant")
    notes = on_arena_or_spar_win(p, reg, source="spar", amount=10)
    assert notes
    assert get_shop_rep(p, "city_armory") > before_a
    assert get_shop_rep(p, "traveling_merchant") > before_m
    # throttle
    notes2 = on_arena_or_spar_win(p, reg, source="arena", amount=10)
    assert notes2 == []


def test_hub_integration_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s6g", "warrior", "เมษ")
    p["shop_rep"] = {"legend_pavilion": 90, "city_armory": 90}
    p["grade_revealed"] = True
    p["player_grade"] = "S"
    lines = integration_hub_lines(p, "legend_pavilion")
    assert any("เรลิก" in x or "ศาลา" in x or "ประจำ" in x for x in lines)
    hub = format_shop_hub_lines(
        p,
        reg,
        title="ศาลาตำนาน",
        stock=[],
        min_rk=5,
        max_rk=8,
        specialty=True,
        tone=shop_tone_line(reg.shops.get("legend_pavilion"), "legend_pavilion"),
        shop_id="legend_pavilion",
        greeting=pick_greeting(reg.shops.get("legend_pavilion"), "legend_pavilion", player=p),
        rep_label="ลูกค้าใจดี",
        rep_hint="ลูกค้าประจำ",
    )
    blob = "\n".join(hub)
    assert "ความคุ้น" in blob
    assert "การ์ดไม่ขาย" in blob
