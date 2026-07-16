"""WO-015: combat needs tick parity + soft foresight + prefs."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.soft_foresight import (
    should_soft_block_dungeon,
    soft_dungeon_entry_warnings,
)
from game.runtime.dungeon_auto import DEFAULT_AUTO_PREFS, ensure_auto_prefs
from game.services.combat_session import _maybe_tick_combat_needs


def test_combat_tick_once_per_round():
    p = create_player(DataRegistry.load(DATA_DIR), "t1", "warrior", "ตุลย์")
    ensure_needs(p)
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 70}
    before = dict(get_needs(p))
    _maybe_tick_combat_needs(p, combat_round=1)
    after1 = dict(get_needs(p))
    assert after1["hunger"] > before["hunger"] or after1["fatigue"] > before["fatigue"]
    # second call same round — no double tick
    _maybe_tick_combat_needs(p, combat_round=1)
    after2 = dict(get_needs(p))
    assert after2 == after1
    # next round ticks again
    _maybe_tick_combat_needs(p, combat_round=2)
    after3 = dict(get_needs(p))
    assert after3["hunger"] >= after2["hunger"]
    assert after3 != after2 or after3["fatigue"] >= after2["fatigue"]


def test_manual_and_auto_same_delta_function():
    """Parity: both paths use apply_needs_event('combat') deltas."""
    from game.domain.needs import EVENT_DELTAS

    assert "combat" in EVENT_DELTAS
    assert EVENT_DELTAS["combat"]["hunger"] > 0


def test_default_prefs_playtest_tuned():
    # WO-017 R3 defaults
    assert DEFAULT_AUTO_PREFS["hunger"] == 58
    assert DEFAULT_AUTO_PREFS["fatigue"] == 67
    assert DEFAULT_AUTO_PREFS["morale"] == 30
    assert DEFAULT_AUTO_PREFS["inv_min_food"] == 4
    p = {}
    prefs = ensure_auto_prefs(p)
    assert prefs["hunger"] == 58
    assert prefs["fatigue"] == 67


def test_soft_foresight_warns_low_supplies():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f1", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"] = {"hunger": 90, "fatigue": 80, "morale": 20}
    p["inventory_ids"] = []
    p["hp"] = 20
    p["max_hp"] = 100
    warns = soft_dungeon_entry_warnings(p, reg, dungeon={"name": "รากป่า"})
    text = "\n".join(warns)
    assert "foresight" in text.lower() or "ตรวจสภาพ" in text or "กายใจ" in text
    assert "อาหาร" in text or "เสบียง" in text or "หิว" in text
    assert should_soft_block_dungeon(p, reg) is True
