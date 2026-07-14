"""Central player market — list, buy, seller payout + report."""
from __future__ import annotations

from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.market import (
    buy_listing,
    claim_pending_payouts,
    list_item_on_market,
    load_market,
    suggest_list_price,
)
from game.domain.progression import init_progression
from game.services.save_service import save_player
import game.services.save_service as ss
import game.domain.market as market_mod


def test_list_and_buy_pays_seller(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr(market_mod, "SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)

    reg = DataRegistry.load(DATA_DIR)
    seller = create_player(reg, "Seller", "vagabond", "เมษ")
    seller["id"] = "seller_01"
    seller["world_id"] = "default"
    seller["money_world"] = 100
    init_progression(seller, reg)
    add_item(seller, "upgrade_mat", reg, rarity="common")
    # index of upgrade_mat
    idx = list(seller["inventory_ids"]).index("upgrade_mat")
    sug = suggest_list_price(reg, "default", "upgrade_mat", "common")
    ok, msg = list_item_on_market(seller, reg, idx, sug, world_id="default")
    assert ok, msg
    assert "upgrade_mat" not in (seller.get("inventory_ids") or [])
    save_player(seller, world_id="default")

    market = load_market("default")
    assert len(market["listings"]) == 1
    lid = market["listings"][0]["listing_id"]
    price = int(market["listings"][0]["price"])

    buyer = create_player(reg, "Buyer", "vagabond", "เมษ")
    buyer["id"] = "buyer_01"
    buyer["world_id"] = "default"
    buyer["money_world"] = price + 50
    init_progression(buyer, reg)
    ok2, msg2 = buy_listing(buyer, reg, lid, world_id="default")
    assert ok2, msg2
    assert "upgrade_mat" in (buyer.get("inventory_ids") or [])
    assert int(buyer["money_world"]) == 50

    # seller reloaded should have more money + inbox
    from game.services.save_service import load_player

    spath = tmp_path / "saves" / "default" / "seller_01.json"
    loaded = load_player(str(spath))
    assert int(loaded["money_world"]) > 100
    inbox = loaded.get("market_inbox") or []
    assert any(m.get("type") == "market_sold" for m in inbox)
    assert any(m.get("buyer_name") == "Buyer" for m in inbox)


def test_cannot_buy_own_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr(market_mod, "SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Solo", "vagabond", "เมษ")
    p["id"] = "solo_1"
    p["world_id"] = "default"
    add_item(p, "potion_hp", reg)
    idx = list(p["inventory_ids"]).index("potion_hp")
    sug = suggest_list_price(reg, "default", "potion_hp", "common")
    ok, _ = list_item_on_market(p, reg, idx, sug, world_id="default")
    assert ok
    lid = load_market("default")["listings"][0]["listing_id"]
    p["money_world"] = 9999
    ok2, msg = buy_listing(p, reg, lid, world_id="default")
    assert not ok2
    assert "ตัวเอง" in msg
