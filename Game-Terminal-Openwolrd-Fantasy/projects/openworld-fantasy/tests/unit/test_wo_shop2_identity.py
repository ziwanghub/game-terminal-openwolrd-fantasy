"""WO-Shop-2: shop identity stock, content pack, tone UI, no cards."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.services.shop import (
    _eligible_buy_rows,
    _is_shop_banned_card,
    _normalize_stock,
    _stock_item_category,
    format_shop_hub_lines,
    shop_rank_window,
    shop_tone_line,
)


def _stock_ids(shop: dict) -> set:
    out = set()
    for row in shop.get("stock") or []:
        iid = row if isinstance(row, str) else (row or {}).get("id")
        if iid:
            out.add(str(iid))
    return out


def test_each_shop_has_distinct_tone():
    reg = DataRegistry.load(DATA_DIR)
    tones = {}
    for sid in (
        "traveling_merchant",
        "city_armory",
        "rare_exchange",
        "celestial_bazaar",
        "infernal_market",
        "legend_pavilion",
    ):
        shop = reg.shops.get(sid) or {}
        tone = shop_tone_line(shop, sid)
        assert tone
        tones[sid] = tone
    # tones should not all be identical
    assert len(set(tones.values())) >= 5
    assert "โรงตี" in tones["city_armory"] or "เกียร์" in tones["city_armory"] or "อาวุธ" in tones["city_armory"]
    assert "ผลึก" in tones["rare_exchange"] or "mat" in tones["rare_exchange"].lower()
    assert "สวรรค์" in tones["celestial_bazaar"] or "พร" in tones["celestial_bazaar"]
    assert "นรก" in tones["infernal_market"] or "เถ้า" in tones["infernal_market"]
    assert "ตำนาน" in tones["legend_pavilion"]


def test_identity_stock_roles():
    reg = DataRegistry.load(DATA_DIR)
    arm = _stock_ids(reg.shops["city_armory"])
    rare = _stock_ids(reg.shops["rare_exchange"])
    cel = _stock_ids(reg.shops["celestial_bazaar"])
    inf = _stock_ids(reg.shops["infernal_market"])
    leg = _stock_ids(reg.shops["legend_pavilion"])
    mer = _stock_ids(reg.shops["traveling_merchant"])

    # armory: gear + upgrade mats
    assert "upgrade_mat" in arm
    assert "shop_armory_whetstone" in arm
    assert "iron_sword" in arm or any(
        (reg.items.get(i) or {}).get("slot") for i in arm
    )
    assert "potion_hp" not in arm
    assert "hell_contract" not in arm

    # rare: mat + scroll + crystal, no gear
    assert "crystal_dust" in rare or "shop_rare_crystal_lens" in rare
    assert "scroll_guard_break" in rare or "shop_rare_bound_scroll" in rare
    for iid in rare:
        assert _stock_item_category(reg, iid) != "equipment"

    # celestial: charms / blessing
    assert "blessed_charm" in cel
    assert "shop_celestial_prayer_bead" in cel
    assert "hell_contract" not in cel

    # infernal: contract / void
    assert "hell_contract" in inf
    assert "void_ash" in inf
    assert "shop_infernal_ember_vial" in inf
    assert "blessed_charm" not in inf

    # legend light
    assert 1 <= len(leg) <= 6
    assert "shop_legend_memory_fragment" in leg
    assert "iron_sword" not in leg

    # merchant travel pack
    assert "shop_merchant_road_tea" in mer
    assert "potion_hp_small" in mer or "potion_hp" in mer


def test_shop_content_items_exist_with_flavor():
    reg = DataRegistry.load(DATA_DIR)
    need = [
        "shop_merchant_road_tea",
        "shop_merchant_mixed_ration",
        "shop_armory_whetstone",
        "shop_armory_temper_oil",
        "shop_armory_rivet_pack",
        "shop_rare_crystal_lens",
        "shop_rare_prism_vial",
        "shop_rare_bound_scroll",
        "shop_celestial_prayer_bead",
        "shop_celestial_soft_laurel",
        "shop_celestial_light_vial",
        "shop_infernal_ember_vial",
        "shop_infernal_void_token",
        "shop_infernal_smoke_oil",
        "shop_legend_memory_fragment",
        "shop_legend_soft_seal",
        "shop_legend_echo_thread",
    ]
    for iid in need:
        it = reg.items.get(iid)
        assert it, f"missing {iid}"
        desc = str(it.get("desc") or "")
        assert len(desc) >= 8, f"weak flavor {iid}"
        assert "โทน" in desc or "ร้าน" in desc or "ตลาด" in desc or "ศาลา" in desc or "โรง" in desc or "พ่อค้า" in desc or "ตำนาน" in desc


def test_hub_shows_tone_and_no_cards():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s2hub", "warrior", "เมษ")
    for sid in ("city_armory", "rare_exchange", "celestial_bazaar", "legend_pavilion"):
        shop = reg.shops[sid]
        stock = _normalize_stock(shop, reg=reg)
        min_rk, max_rk = shop_rank_window(shop)
        lines = format_shop_hub_lines(
            p,
            reg,
            title=str(shop.get("name") or sid),
            stock=stock,
            min_rk=min_rk,
            max_rk=max_rk,
            specialty=min_rk > 1 or max_rk < 8,
            tone=shop_tone_line(shop, sid),
            shop_id=sid,
        )
        blob = "\n".join(lines)
        assert "โทน" in blob
        assert "การ์ดไม่ขาย" in blob or "การ์ด" in blob
        # stock resolves
        for row in stock:
            assert not _is_shop_banned_card(reg, str(row.get("id") or ""))
        # legend rows eligible at min rank 5
        if sid == "legend_pavilion":
            rows = _eligible_buy_rows(
                p, reg, stock, min_rk=min_rk, max_rk=max_rk, category=None
            )
            assert rows, "legend stock should appear for legendary items"
            assert all(not str(r[0]).startswith("card_") for r in rows)


def test_no_shop_sells_cards():
    reg = DataRegistry.load(DATA_DIR)
    for sid, shop in (reg.shops or {}).items():
        for row in shop.get("stock") or []:
            iid = row if isinstance(row, str) else (row or {}).get("id")
            assert not str(iid or "").startswith("card_")
            assert iid not in (reg.cards or {})
