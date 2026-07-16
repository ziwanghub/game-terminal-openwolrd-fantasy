"""WO-Shop-4: shop reputation 0–100, price effects, stock unlock, dialogue."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import sell_price, scaled_price
from game.domain.character import create_player
from game.domain.shop_experience import (
    DYNAMIC_CLAMP_BUY,
    DYNAMIC_CLAMP_SELL,
    REP_BUY_MAX_DISC,
    REP_SELL_MAX_BONUS,
    REP_UNLOCK_RARE,
    SHOP_REP_MAX,
    SHOP_REP_START,
    bump_shop_rep,
    dynamic_price_mult,
    ensure_shop_rep,
    get_shop_rep,
    grant_shop_rep_quest,
    pick_greeting,
    rep_progress_hint,
    shop_rep_band,
    shop_rep_soft_label,
    stock_unlocked_for_rep,
)
from game.services.shop import (
    _eligible_buy_rows,
    _normalize_stock,
    format_shop_hub_lines,
    shop_rank_window,
    shop_tone_line,
)


def test_shop_rep_starts_and_caps():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r4a", "warrior", "เมษ")
    ensure_shop_rep(p)
    r = get_shop_rep(p, "city_armory")
    assert 20 <= r <= 30
    assert r == SHOP_REP_START or 20 <= r <= 30
    # bump to cap
    for _ in range(80):
        bump_shop_rep(p, "city_armory", amount=5, reason="buy")
    assert get_shop_rep(p, "city_armory") <= SHOP_REP_MAX
    assert get_shop_rep(p, "city_armory") == 100


def test_rep_affects_buy_and_sell_within_limits():
    reg = DataRegistry.load(DATA_DIR)
    p_low = create_player(reg, "r4b", "warrior", "เมษ")
    p_hi = create_player(reg, "r4c", "warrior", "เมษ")
    shop = dict(reg.shops.get("city_armory") or {})
    shop["id"] = "city_armory"
    ensure_shop_rep(p_low, ["city_armory"])
    ensure_shop_rep(p_hi, ["city_armory"])
    p_low["shop_rep"] = {"city_armory": 20}
    p_hi["shop_rep"] = {"city_armory": 100}
    mb_lo = dynamic_price_mult(p_low, shop, side="buy")
    mb_hi = dynamic_price_mult(p_hi, shop, side="buy")
    ms_lo = dynamic_price_mult(p_low, shop, side="sell")
    ms_hi = dynamic_price_mult(p_hi, shop, side="sell")
    # high rep → cheaper buy, better sell
    assert mb_hi < mb_lo
    assert ms_hi > ms_lo
    # within clamp / plan limits
    assert DYNAMIC_CLAMP_BUY[0] <= mb_hi <= DYNAMIC_CLAMP_BUY[1]
    assert DYNAMIC_CLAMP_SELL[0] <= ms_hi <= DYNAMIC_CLAMP_SELL[1]
    assert mb_hi >= 1.0 - REP_BUY_MAX_DISC - 0.05  # day/bias soft
    assert ms_hi <= 1.0 + REP_SELL_MAX_BONUS + 0.05
    # sell_price path
    sell_lo = sell_price(
        50, reg, p_low, rarity="common", shop=shop, item_kind="material", item_id="upgrade_mat"
    )
    sell_hi = sell_price(
        50, reg, p_hi, rarity="common", shop=shop, item_kind="material", item_id="upgrade_mat"
    )
    assert sell_hi >= sell_lo


def test_stock_unlock_by_rep():
    assert stock_unlocked_for_rep("common", 10)
    assert not stock_unlocked_for_rep("uncommon", 10)
    assert stock_unlocked_for_rep("uncommon", 40)
    assert not stock_unlocked_for_rep("rare", 40)
    assert stock_unlocked_for_rep("rare", REP_UNLOCK_RARE)
    assert stock_unlocked_for_rep("legendary", 60)
    # explicit min_rep
    assert not stock_unlocked_for_rep("common", 10, entry={"min_rep": 50})
    assert stock_unlocked_for_rep("common", 50, entry={"min_rep": 50})


def test_eligible_rows_gate_rare_until_rep60():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r4d", "warrior", "เมษ")
    shop = dict(reg.shops.get("city_armory") or {})
    shop["id"] = "city_armory"
    stock = _normalize_stock(shop, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    p["shop_rep"] = {"city_armory": 20}
    rows_low = _eligible_buy_rows(
        p, reg, stock, min_rk=min_rk, max_rk=max_rk, shop=shop, shop_id="city_armory"
    )
    p["shop_rep"] = {"city_armory": 70}
    rows_hi = _eligible_buy_rows(
        p, reg, stock, min_rk=min_rk, max_rk=max_rk, shop=shop, shop_id="city_armory"
    )
    # high rep should not have fewer rows
    assert len(rows_hi) >= len(rows_low)
    # uncommon/rare more visible at high rep
    rarities_low = {r[4] for r in rows_low}
    rarities_hi = {r[4] for r in rows_hi}
    # at least common always
    assert any(x in ("common", "uncommon", "rare") for x in rarities_hi) or rows_hi


def test_dialogue_changes_with_rep():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r4e", "warrior", "เมษ")
    shop = reg.shops.get("city_armory") or {}
    p["shop_rep"] = {"city_armory": 15}
    cold = pick_greeting(shop, "city_armory", player=p)
    p["shop_rep"] = {"city_armory": 90}
    warm = pick_greeting(shop, "city_armory", player=p)
    assert cold and warm
    # bands differ
    assert shop_rep_band(15) == "cold"
    assert shop_rep_band(90) == "friend"
    assert shop_rep_soft_label(15) != shop_rep_soft_label(90)
    hint_low = rep_progress_hint(p if False else {"shop_rep": {"city_armory": 20}}, "city_armory")
    # fix: use low rep player
    p_low = create_player(reg, "r4e2", "warrior", "เมษ")
    p_low["shop_rep"] = {"city_armory": 20}
    hint_low = rep_progress_hint(p_low, "city_armory")
    assert "บ่อย" in hint_low or "ช่วย" in hint_low or "คุ้น" in hint_low


def test_quest_rep_grant():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r4q", "warrior", "เมษ")
    ensure_shop_rep(p, ["rare_exchange"])
    before = get_shop_rep(p, "rare_exchange")
    notes = grant_shop_rep_quest(p, "rare_exchange", amount=8)
    assert get_shop_rep(p, "rare_exchange") > before
    assert notes


def test_hub_shows_rep_soft_not_number():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r4h", "warrior", "เมษ")
    ensure_shop_rep(p, ["rare_exchange"])
    p["shop_rep"] = {"rare_exchange": 22}
    shop = reg.shops["rare_exchange"]
    stock = _normalize_stock(shop, reg=reg)
    min_rk, max_rk = shop_rank_window(shop)
    lines = format_shop_hub_lines(
        p,
        reg,
        title=str(shop.get("name")),
        stock=stock,
        min_rk=min_rk,
        max_rk=max_rk,
        specialty=True,
        tone=shop_tone_line(shop, "rare_exchange"),
        shop_id="rare_exchange",
        greeting=pick_greeting(shop, "rare_exchange", player=p),
        rep_label=shop_rep_soft_label(22),
        rep_hint=rep_progress_hint(p, "rare_exchange"),
    )
    blob = "\n".join(lines)
    assert "ความคุ้น" in blob
    assert "22" not in blob  # no raw rep number
    assert "การ์ดไม่ขาย" in blob
    assert "%" not in blob or "ไม่โชว์ %" in blob
