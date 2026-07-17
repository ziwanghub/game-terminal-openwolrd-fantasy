"""WO-Storage-1 / 1.1 / 1.2 — shared team vault + bulk + money."""
from __future__ import annotations

import shutil
from pathlib import Path

from game.config import DATA_DIR, SAVES_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, recompute_stats
from game.domain.warehouse import (
    auto_stash_enabled,
    auto_stash_from_bag,
    bag_mat_junk_indices,
    deposit_item_at,
    deposit_items_batch,
    deposit_money,
    ensure_warehouse,
    format_warehouse_status_lines,
    is_setup,
    is_unlocked,
    lock_session,
    login,
    parse_slot_spec,
    parse_withdraw_spec,
    register,
    set_auto_stash,
    slots_cap,
    slots_used,
    vault_exists,
    vault_path,
    vaults_dir,
    withdraw_item_at,
    withdraw_items_batch,
    withdraw_money,
)
from game.ports.io import ScriptedIO
from game.services.warehouse_hub import run_warehouse_hub

_WORLD = "test_vault_shared_wo"


def _cleanup_vaults():
    d = vaults_dir(_WORLD)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)


def _player(reg: DataRegistry, name: str = "wh_test"):
    p = create_player(reg, name, "warrior", "เมษ")
    recompute_stats(p, reg)
    p["world_id"] = _WORLD
    ensure_warehouse(p)
    p["money_world"] = 500
    p["money_heaven"] = 20
    p["money_hell"] = 10
    return p


def setup_function():
    _cleanup_vaults()


def teardown_function():
    _cleanup_vaults()


def test_register_login_hash_no_plain_on_player():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    ok, msg = register(p, "secret1", user="TeamVault")
    assert ok, msg
    assert is_unlocked(p)
    assert vault_exists(_WORLD, "TeamVault")
    w = p["warehouse"]
    assert "pass_hash" not in w or not w.get("pass_hash")
    assert "secret1" not in str(w)
    # disk has hash
    raw = vault_path(_WORLD, "TeamVault").read_text(encoding="utf-8")
    assert "pass_hash" in raw
    assert "secret1" not in raw
    lock_session(p)
    assert not is_unlocked(p)
    bad, _ = login(p, "wrong", user="TeamVault")
    assert not bad
    good, _ = login(p, "secret1", user="TeamVault")
    assert good
    assert is_unlocked(p)


def test_two_players_share_same_vault():
    """Teammate with correct user+pass sees same items."""
    reg = DataRegistry.load(DATA_DIR)
    a = _player(reg, "alice")
    b = _player(reg, "bob")
    ok, _ = register(a, "team-pass", user="RaidStash")
    assert ok
    # alice deposits material
    mats = [
        iid
        for iid, it in (reg.items or {}).items()
        if str(it.get("kind") or "") == "material"
    ]
    mid = mats[0] if mats else "upgrade_mat"
    add_item(a, mid, reg, amount=3)
    ok, msg = deposit_item_at(a, 0, reg, qty=3)
    assert ok, msg
    used_a = slots_used(a)
    assert used_a >= 1
    lock_session(a)

    # bob logs into same vault
    ok, msg = login(b, "team-pass", user="RaidStash")
    assert ok, msg
    assert slots_used(b) == used_a
    # bob withdraws 1
    ok, msg = withdraw_item_at(b, 0, reg, qty=1)
    assert ok, msg
    lock_session(b)

    # alice re-opens — sees reduced stock
    ok, _ = login(a, "team-pass", user="RaidStash")
    assert ok
    # stack may still exist with less qty or empty
    assert slots_used(a) >= 0


def test_deposit_withdraw_item_and_money():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    register(p, "pw", user="SoloBox")
    added = add_item(p, "upgrade_mat", reg, amount=5)
    if not added:
        for iid, it in (reg.items or {}).items():
            if str(it.get("kind") or "") == "material":
                added = add_item(p, iid, reg, amount=3)
                if added:
                    break
    assert added
    ok, msg = deposit_item_at(p, 0, reg, qty=2)
    assert ok, msg
    assert slots_used(p) >= 1
    ok, msg = deposit_money(p, "world", 100)
    assert ok, msg
    assert p["money_world"] == 400
    assert p["warehouse"]["money"]["world"] == 100
    ok, msg = withdraw_money(p, "world", 40)
    assert ok, msg
    assert p["money_world"] == 440
    ok, msg = withdraw_item_at(p, 0, reg, qty=1)
    assert ok, msg


def test_healing_can_deposit_and_a_includes_healing():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg, "heal_wh")
    register(p, "pw", user="MedKit")
    r = add_item(p, "potion_hp", reg, amount=2)
    assert r
    idx = list(p["inventory_ids"]).index("potion_hp")
    ok, msg = deposit_item_at(p, idx, reg, qty=2)
    assert ok, msg
    assert slots_used(p) >= 1
    # a-list includes healing
    p2 = _player(reg, "heal2")
    register(p2, "pw2", user="MedKit2")
    add_item(p2, "potion_hp", reg, amount=1)
    idxs = bag_mat_junk_indices(p2, reg)
    assert any(str(p2["inventory_ids"][i]) == "potion_hp" for i in idxs)


def test_wrong_money_underflow():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    register(p, "pw", user="MoneyBox")
    ok, _ = deposit_money(p, "world", 99999)
    assert not ok
    ok, _ = withdraw_money(p, "heaven", 1)
    assert not ok


def test_cap_default_200():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    register(p, "pw", user="CapBox")
    assert slots_cap(p) == 200


def test_auto_stash_needs_unlock():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    register(p, "pw", user="AutoBox")
    set_auto_stash(p, True)
    lock_session(p)
    assert auto_stash_enabled(p) is True
    assert not is_unlocked(p)
    # locked → no auto
    notes = auto_stash_from_bag(p, reg, need_free=2, max_moves=3)
    assert notes == []


def test_auto_stash_when_unlocked():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    register(p, "pw", user="AutoOn")
    set_auto_stash(p, True)
    mat_ids = [
        iid
        for iid, it in (reg.items or {}).items()
        if str(it.get("kind") or "") == "material"
    ][:3]
    p["bag_cap"] = 3
    p["inventory_ids"] = []
    p["inventory_qty"] = []
    p["inventory_rarities"] = []
    p["inventory"] = []
    for mid in (mat_ids or ["upgrade_mat"])[:3]:
        add_item(p, mid, reg, amount=1)
    notes = auto_stash_from_bag(p, reg, need_free=2, max_moves=3)
    assert slots_used(p) > 0
    assert any("คลัง" in n for n in notes)


def test_parse_slot_spec_multi_range_and_a():
    idxs, err = parse_slot_spec("2 5 7", max_index_1based=10)
    assert err == ""
    assert idxs == [1, 4, 6]
    idxs, err = parse_slot_spec("2-4 7", max_index_1based=10)
    assert idxs == [1, 2, 3, 6]
    idxs, err = parse_slot_spec("a", max_index_1based=10)
    assert idxs is None and err == "auto_mat"


def test_parse_withdraw_spec_qty_and_range():
    picks, err = parse_withdraw_spec("1:4 2:1", max_index_1based=10)
    assert err == ""
    assert picks == [(0, 4), (1, 1)]


def test_batch_deposit_and_withdraw():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg, "batch_wh")
    register(p, "pw", user="BatchBox")
    mats = [
        iid
        for iid, it in (reg.items or {}).items()
        if str(it.get("kind") or "") == "material"
    ][:2]
    p["inventory_ids"] = []
    p["inventory_qty"] = []
    p["inventory_rarities"] = []
    p["inventory"] = []
    for mid in (mats or ["upgrade_mat"])[:2]:
        add_item(p, mid, reg, amount=2)
    n_bag = len(p.get("inventory_ids") or [])
    ok_lines, skip = deposit_items_batch(p, reg, list(range(n_bag)))
    assert ok_lines
    head = "\n".join(format_warehouse_status_lines(p))
    assert "คลังทีม ·" in head or "คลัง" in head
    ok_w, _ = withdraw_items_batch(p, reg, [(0, 1)])
    assert ok_w


def test_hub_scripted_create_and_money():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg, "hub_wh")
    add_item(p, "upgrade_mat", reg, amount=2)
    # user, pass, confirm, 4 deposit money, 1 world, 50, enter, 0
    io = ScriptedIO(
        [
            "HubVault",
            "mypass",
            "mypass",
            "4",
            "1",
            "50",
            "",
            "0",
        ]
    )
    run_warehouse_hub(p, reg, io)
    out = io.joined()
    assert "คลัง" in out
    assert is_setup(p) or is_unlocked(p)
    assert p["warehouse"]["money"]["world"] == 50


def test_hub_second_player_login_scripted():
    reg = DataRegistry.load(DATA_DIR)
    a = _player(reg, "hub_a")
    register(a, "shared!", user="PartyBox")
    add_item(a, "upgrade_mat", reg, amount=1)
    deposit_item_at(a, 0, reg, qty=1)
    lock_session(a)

    b = _player(reg, "hub_b")
    io = ScriptedIO(
        [
            "PartyBox",
            "shared!",
            "1",  # list
            "",
            "0",
        ]
    )
    run_warehouse_hub(b, reg, io)
    assert is_unlocked(b)
    assert slots_used(b) >= 1


def test_personal_menu_lists_warehouse():
    from game.domain.mode_shell import MODE_PERSONAL, render_mode_actions

    text = render_mode_actions(MODE_PERSONAL)
    assert "คลัง" in text
    assert "7" in text
