"""H1 board · H2 escrow · H3 assist resolve (no full UI combat)."""
import random
from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import begin_dungeon, get_run, in_dungeon, on_dungeon_boss_defeated
from game.domain.equipment import add_item
from game.domain.situation import (
    apply_assist_failure,
    apply_assist_victory,
    claim_help_for_helper,
    close_help_request,
    format_board_lines,
    get_situation,
    help_is_open,
    list_open_help_signals,
    open_help_request,
    pay_escrow_to_helper,
    return_escrow_to_owner,
)
from game.services.save_service import load_player, save_player


def _owner_in_dungeon_with_help(reg, tmp_path, monkeypatch, *, gold=0, items=None, note="SOS"):
    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    owner = create_player(reg, "OwnerP1", "warrior", "เมษ")
    owner["id"] = "owner_p1"
    owner["money_world"] = 200
    if items:
        for iid in items:
            add_item(owner, iid, reg)
    begin_dungeon(owner, reg, "dung_forest_root", random.Random(1))
    ok, notes = open_help_request(
        owner, reg, note=note, gold=gold, item_ids=list(items or [])
    )
    assert ok, notes
    path = save_player(owner, world_id="default")
    return owner, path


def test_h1_list_open_signals(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    owner, path = _owner_in_dungeon_with_help(reg, tmp_path, monkeypatch, gold=20)
    helper = create_player(reg, "HelperP2", "mage", "เมถุน")
    helper["id"] = "helper_p2"
    save_player(helper, world_id="default")

    sigs = list_open_help_signals(
        "default", exclude_player_id="helper_p2", saves_dir=tmp_path
    )
    assert len(sigs) >= 1
    assert sigs[0]["owner_id"] == "owner_p1"
    assert sigs[0]["claimable"] is True
    assert "20G" in sigs[0]["offer_line"]
    lines = format_board_lines(sigs)
    assert any("OwnerP1" in ln or "ขอแรง" in ln for ln in lines)


def test_h2_escrow_lock_and_return(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)
    owner = create_player(reg, "OwnerP1", "warrior", "เมษ")
    owner["id"] = "owner_escrow"
    owner["money_world"] = 200
    owner["inventory_ids"] = ["potion_hp_small"]
    owner["inventory"] = ["ยา"]
    owner["inventory_rarities"] = ["common"]
    owner["inventory_items"] = []
    begin_dungeon(owner, reg, "dung_forest_root", random.Random(1))
    ok, notes = open_help_request(
        owner, reg, note="esc", gold=50, item_ids=["potion_hp_small"]
    )
    assert ok, notes
    assert int(owner["money_world"]) == 150
    assert "potion_hp_small" not in (owner.get("inventory_ids") or [])
    h = get_situation(owner)["help"]
    assert h["escrow"]["gold"] == 50
    assert "potion_hp_small" in (h["escrow"].get("item_ids") or [])

    ok, notes = close_help_request(owner, reg)
    assert ok
    assert int(owner["money_world"]) == 200
    assert "potion_hp_small" in (owner.get("inventory_ids") or [])


def test_h3_claim_and_victory_pays_helper(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    owner, path = _owner_in_dungeon_with_help(reg, tmp_path, monkeypatch, gold=40)
    helper = create_player(reg, "HelperP2", "mage", "เมถุน")
    helper["id"] = "helper_p2"
    helper["money_world"] = 10

    owner = load_player(str(path))
    ok, _ = claim_help_for_helper(owner, helper)
    assert ok
    assert get_situation(owner)["help"]["status"] == "claimed"

    notes = apply_assist_victory(owner, helper, reg)
    assert any("สำเร็จ" in n or "ฝ่า" in n for n in notes)
    # owner boss cleared
    assert get_run(owner).get("boss_defeated") is True
    # helper got escrow + soft tip
    assert int(helper["money_world"]) >= 10 + 40
    # owner inbox
    box = owner.get("world_inbox") or []
    assert box and box[0].get("type") == "sos_resolved"
    assert box[0].get("result") == "win"
    assert not help_is_open(owner)


def test_h3_failure_reopens_keeps_escrow(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    owner, path = _owner_in_dungeon_with_help(reg, tmp_path, monkeypatch, gold=30)
    helper = create_player(reg, "HelperP2", "rogue", "พิจิก")
    helper["id"] = "helper_p2"
    owner = load_player(str(path))
    claim_help_for_helper(owner, helper)
    notes = apply_assist_failure(owner, helper)
    assert help_is_open(owner)
    assert get_situation(owner)["help"]["status"] == "open"
    assert get_situation(owner)["help"]["escrow"]["gold"] == 30
    assert any("เปิดอีก" in n or "ไม่สำเร็จ" in n for n in notes)


def test_cannot_claim_self(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    owner, path = _owner_in_dungeon_with_help(reg, tmp_path, monkeypatch)
    owner = load_player(str(path))
    ok, notes = claim_help_for_helper(owner, owner)
    assert ok is False
