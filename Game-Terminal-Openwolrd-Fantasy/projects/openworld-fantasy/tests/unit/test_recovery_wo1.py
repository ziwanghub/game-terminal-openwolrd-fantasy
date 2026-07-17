"""WO-Recovery-1: Recovery Rank F–S + multi-turn bottles (HP/MP/PY)."""
from __future__ import annotations

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.recovery import (
    ACTIVE_KEY,
    apply_recovery_item,
    clear_rank_cache,
    consume_recovery_from_bag,
    get_active,
    get_rank_table,
    parse_recovery_item,
    rank_spec,
    recovery_amount_table,
    tick_recovery,
)
from game.runtime.dungeon_auto import ensure_auto_prefs, use_items_by_thresholds
from game.services.consumables import quick_use_care_potion


def _player(reg=None):
    reg = reg or DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rec", "warrior", "เมษ")
    ensure_needs(p)
    return p, reg


def test_version_phase_recovery():
    # recovery shipped @ 2.18.0; current line is 2.20.x (storage WO phase)
    assert "2.2" in APP_VERSION  # 2.20+ line incl. 2.21 worthiness
    assert PHASE
    assert (
        ("recovery" in PHASE)
        or ("item-free" in PHASE)
        or ("combat-item" in PHASE)
        or ("storage" in PHASE)
        or ("-" in PHASE)
    )


def test_rank_table_matches_spec():
    clear_rank_cache()
    table = recovery_amount_table()
    assert table["F"]["amount"] == 15 and table["F"]["duration"] == 5
    assert table["E"]["amount"] == 20
    assert table["D"]["amount"] == 30
    assert table["C"]["amount"] == 50
    assert table["B"]["amount"] == 80
    assert table["A"]["amount"] == 100
    assert table["S"]["full"] is True and table["S"]["duration"] == 3
    # rank_spec helper
    assert rank_spec("c")["amount"] == 50
    assert rank_spec("S")["duration"] == 3


def test_recovery_items_loaded():
    reg = DataRegistry.load(DATA_DIR)
    for iid in (
        "recovery_hp_f",
        "recovery_mp_d",
        "recovery_py_a",
        "recovery_hp_s",
        "recovery_py_s",
    ):
        assert iid in reg.items, iid
        it = reg.items[iid]
        assert it.get("recovery_kind")
        assert it.get("recovery_rank")
        parsed = parse_recovery_item(it)
        assert parsed is not None


def test_hp_bottle_five_turns_per_tick():
    p, reg = _player()
    it = reg.items["recovery_hp_f"]
    p["max_hp"] = 200
    p["hp"] = 50
    notes = apply_recovery_item(p, it, item_id="recovery_hp_f", immediate_tick=True)
    assert notes
    # first pulse: +15
    assert int(p["hp"]) == 65
    act = get_active(p)["hp"]
    assert act["rank"] == "F"
    assert act["turns_left"] == 4  # 5 - 1 after immediate
    # four more field ticks
    for _ in range(4):
        tick_recovery(p, silent=True)
    assert int(p["hp"]) == 50 + 15 * 5
    assert "hp" not in get_active(p)


def test_s_rank_full_three_turns():
    p, reg = _player()
    it = reg.items["recovery_hp_s"]
    p["max_hp"] = 100
    p["hp"] = 10
    apply_recovery_item(p, it, item_id="recovery_hp_s", immediate_tick=True)
    assert int(p["hp"]) == 100
    assert get_active(p)["hp"]["turns_left"] == 2
    p["hp"] = 5
    tick_recovery(p, silent=True)
    assert int(p["hp"]) == 100
    p["hp"] = 1
    tick_recovery(p, silent=True)
    assert int(p["hp"]) == 100
    assert "hp" not in get_active(p)


def test_mp_and_py_kinds_separate():
    p, reg = _player()
    p["max_mana"] = 80
    p["mana"] = 10
    p["needs"]["fatigue"] = 70
    apply_recovery_item(
        p, reg.items["recovery_mp_d"], item_id="recovery_mp_d", immediate_tick=True
    )
    apply_recovery_item(
        p, reg.items["recovery_py_a"], item_id="recovery_py_a", immediate_tick=True
    )
    active = get_active(p)
    assert "mp" in active and "py" in active
    assert int(p["mana"]) == 10 + 30  # D
    # A=100 fatigue relief from 70 → clamp 0
    assert int(get_needs(p)["fatigue"]) == 0


def test_needs_event_ticks_recovery():
    p, reg = _player()
    p["max_hp"] = 200
    p["hp"] = 40
    apply_recovery_item(
        p, reg.items["recovery_hp_e"], item_id="recovery_hp_e", immediate_tick=True
    )
    hp1 = int(p["hp"])
    apply_needs_event(p, "explore", silent=True)
    assert int(p["hp"]) == hp1 + 20


def test_old_potion_still_oneshot():
    p, reg = _player()
    p["max_hp"] = 200
    p["hp"] = 50
    add_item(p, "potion_hp", reg)
    notes = quick_use_care_potion(p, reg, kind="hp")
    assert notes
    # potion_hp = 55 one-shot; no multi-turn buff unless recovery bottle
    assert int(p["hp"]) == 105
    assert "hp" not in get_active(p)


def test_hotkey_prefers_recovery_bottle():
    p, reg = _player()
    p["max_hp"] = 200
    p["hp"] = 50
    add_item(p, "potion_hp", reg)
    add_item(p, "recovery_hp_c", reg)
    notes = quick_use_care_potion(p, reg, kind="hp")
    assert any("กำลังฟื้น" in n or "Recovery" in n or "ขวด" in n for n in notes)
    assert "hp" in get_active(p)
    assert get_active(p)["hp"]["rank"] == "C"
    # potion still in bag
    assert "potion_hp" in (p.get("inventory_ids") or [])


def test_hotkey_y_py():
    p, reg = _player()
    p["needs"]["fatigue"] = 60
    add_item(p, "recovery_py_d", reg)
    notes = quick_use_care_potion(p, reg, kind="py")
    assert notes
    assert int(get_needs(p)["fatigue"]) == 60 - 30
    assert "py" in get_active(p)


def test_auto_uses_py_on_fatigue_threshold():
    p, reg = _player()
    prefs = ensure_auto_prefs(p)
    prefs["fatigue"] = 50
    p["auto_prefs"] = prefs
    p["needs"]["fatigue"] = 80
    p["needs"]["hunger"] = 10  # not hungry
    add_item(p, "recovery_py_f", reg)
    # also food so we can detect PY preferred
    add_item(p, "city_bread", reg)
    notes = use_items_by_thresholds(p, reg, force=False)
    assert notes
    assert any("ล้า" in n or "PY" in n or "คลาย" in n for n in notes)
    assert "py" in get_active(p) or int(get_needs(p)["fatigue"]) < 80


def test_clamp_hp_not_over_max():
    p, reg = _player()
    p["max_hp"] = 100
    p["hp"] = 95
    apply_recovery_item(
        p, reg.items["recovery_hp_c"], item_id="recovery_hp_c", immediate_tick=True
    )
    assert int(p["hp"]) == 100
    tick_recovery(p, silent=True)
    assert int(p["hp"]) == 100


def test_consume_from_bag_removes_item():
    p, reg = _player()
    add_item(p, "recovery_mp_f", reg)
    assert "recovery_mp_f" in (p.get("inventory_ids") or [])
    p["max_mana"] = 50
    p["mana"] = 5
    consume_recovery_from_bag(p, reg, kind="mp", immediate_tick=True)
    assert "recovery_mp_f" not in (p.get("inventory_ids") or [])
    assert "mp" in get_active(p)


def test_rank_table_loaded_on_registry():
    reg = DataRegistry.load(DATA_DIR)
    assert hasattr(reg, "recovery_ranks") or get_rank_table()
    table = get_rank_table()
    assert set(table.keys()) >= {"F", "E", "D", "C", "B", "A", "S"}
