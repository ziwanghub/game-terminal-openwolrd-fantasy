"""Mission board + market tax fund."""
from __future__ import annotations

from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.market import buy_listing, get_tax_fund, list_item_on_market, load_market
from game.domain.mission_board import (
    accept_mission,
    check_mission_progress,
    complete_mission_if_done,
    list_visible_missions,
    player_rank,
)
from game.domain.progression import init_progression
from game.services.save_service import save_player
import game.domain.market as market_mod
import game.services.save_service as ss


def test_tax_fund_grows_on_sale(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr(market_mod, "SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    reg = DataRegistry.load(DATA_DIR)
    seller = create_player(reg, "S", "vagabond", "เมษ")
    seller["id"] = "s1"
    seller["world_id"] = "default"
    add_item(seller, "upgrade_mat", reg)
    idx = seller["inventory_ids"].index("upgrade_mat")
    list_item_on_market(seller, reg, idx, 100, world_id="default")
    save_player(seller, world_id="default")
    lid = load_market("default")["listings"][0]["listing_id"]
    buyer = create_player(reg, "B", "vagabond", "เมษ")
    buyer["id"] = "b1"
    buyer["money_world"] = 500
    buy_listing(buyer, reg, lid, world_id="default")
    assert get_tax_fund("default") > 0


def test_accept_f_mission_and_complete():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.mission_board
    p = create_player(reg, "M", "vagabond", "เมษ")
    init_progression(p, reg)
    p["id"] = "m1"
    p["world_id"] = "default"
    assert player_rank(p) == "F"
    visible = list_visible_missions(p, reg)
    assert any(m.get("rank") == "F" for m in visible)
    # cannot see high rank
    assert not any(m.get("rank") == "SSS" and not m.get("special") for m in visible)
    mid = next(m["id"] for m in visible if m.get("type") == "kill" and m.get("rank") == "F")
    ok, msg = accept_mission(p, reg, mid, world_id="default")
    assert ok, msg
    # simulate kills
    p.setdefault("stats", {})
    start = int(p["stats"].get("kills") or 0)
    target = int(p["board_mission"]["target"])
    p["stats"]["kills"] = start + target
    d, t, done = check_mission_progress(p)
    assert done
    notes = complete_mission_if_done(p, reg)
    assert any("เคลียร์" in n or "✔" in n for n in notes)
    assert p.get("board_mission") is None
    assert int(p.get("mission_completes") or 0) >= 1


def test_high_rank_blocked():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L", "vagabond", "เมษ")
    init_progression(p, reg)
    ok, msg = accept_mission(p, reg, "board_sss_end", world_id="default")
    assert not ok
