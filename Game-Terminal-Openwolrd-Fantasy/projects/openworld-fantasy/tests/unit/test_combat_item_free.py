"""Combat item use is free action (no beat) — same principle as appraisal I."""
from __future__ import annotations

import random

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, recompute_stats
from game.domain.mode_shell import MODE_COMBAT, render_mode_actions
from game.domain.needs import ensure_needs
from game.services.combat_session import _player_act


class _IO:
    def __init__(self, answers=None):
        self.answers = list(answers or [])
        self.lines: list[str] = []

    def write_line(self, text: str = "") -> None:
        self.lines.append(str(text))

    def read_line(self, prompt: str = "") -> str:
        if self.answers:
            return self.answers.pop(0)
        return "0"

    def joined(self) -> str:
        return "\n".join(self.lines)


def _mon():
    return {
        "id": "forest_wolf",
        "name": "Wolf",
        "level": 1,
        "hp": 80,
        "max_hp": 80,
        "atk": 3,
        "elements": ["physical"],
        "statuses": [],
        "attack_profiles": [{"id": "a", "power": 2, "weight": 1}],
    }


def test_version_phase_item_free():
    assert "2.2" in APP_VERSION  # 2.20+ line incl. 2.21 worthiness
    # free-item may be followed by later WO phase stamps
    assert PHASE
    assert any(
        k in PHASE
        for k in ("item-free", "combat-item", "skill-ui", "recovery", "storage", "wo-storage")
    ) or "-" in PHASE


def test_combat_menu_labels_item_free():
    text = render_mode_actions(MODE_COMBAT)
    assert "3" in text
    # soft: free-turn wording evolved (ฟรีเทิร์น / ลัดฟรี)
    assert (
        "ไม่เสียเทิร์น" in text
        or "ฟรีเทิร์น" in text
        or "ลัดฟรี" in text
    )


def _clear_bag_consumables(p: dict) -> None:
    """Start with empty bag so menu index 1 is deterministic."""
    p["inventory"] = []
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    p["inventory_qty"] = []
    p["inventory_items"] = []
    p["card_bag"] = list(p.get("card_bag") or [])


def test_use_potion_in_combat_returns_false_free_action():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cif", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    _clear_bag_consumables(p)
    p["hp"] = max(5, int(p["max_hp"]) // 4)
    hp0 = int(p["hp"])
    add_item(p, "potion_hp", reg)
    mon = _mon()
    rng = random.Random(1)
    # 3 = item menu, 1 = bag, 1 = first consumable in new list UI
    io = _IO(["3", "1", "1"])
    result = _player_act(
        p,
        mon,
        reg,
        io,
        rng,
        area_id="dark_forest",
        known=True,
        enemy_name="Wolf",
        combat_round=1,
    )
    assert result is False, "item use must not spend combat beat"
    assert int(p["hp"]) > hp0
    assert "ไม่เสียเทิร์น" in io.joined()
    assert "potion_hp" not in (p.get("inventory_ids") or [])


def test_use_recovery_in_combat_is_free_action():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cir", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    _clear_bag_consumables(p)
    p["max_hp"] = max(100, int(p.get("max_hp") or 100))
    p["hp"] = 20
    add_item(p, "recovery_hp_f", reg)
    mon = _mon()
    rng = random.Random(2)
    io = _IO(["3", "1", "1"])
    result = _player_act(
        p,
        mon,
        reg,
        io,
        rng,
        area_id="dark_forest",
        known=True,
        enemy_name="Wolf",
        combat_round=2,
    )
    assert result is False
    assert int(p["hp"]) > 20 or bool(p.get("active_recovery"))
    assert "ไม่เสียเทิร์น" in io.joined()


def test_quick_cleanse_in_combat_is_free_action():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cic", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    _clear_bag_consumables(p)
    add_item(p, "antidote", reg)
    p["statuses"] = [{"id": "poison", "turns": 2}]
    mon = _mon()
    rng = random.Random(3)
    io = _IO(["3", "2"])  # item menu → quick cleanse
    result = _player_act(
        p,
        mon,
        reg,
        io,
        rng,
        area_id="dark_forest",
        known=True,
        enemy_name="Wolf",
        combat_round=3,
    )
    assert result is False
    assert "ไม่เสียเทิร์น" in io.joined()


def test_cancel_item_menu_still_free():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cix", "warrior", "เมษ")
    recompute_stats(p, reg)
    mon = _mon()
    rng = random.Random(4)
    io = _IO(["3", "0"])
    result = _player_act(
        p,
        mon,
        reg,
        io,
        rng,
        area_id="dark_forest",
        known=True,
        enemy_name="Wolf",
        combat_round=4,
    )
    assert result is False
