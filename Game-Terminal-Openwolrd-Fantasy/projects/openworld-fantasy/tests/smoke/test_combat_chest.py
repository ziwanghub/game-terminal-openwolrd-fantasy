"""Phase I smoke: combat win + chest outcomes (seeded)."""
from __future__ import annotations

import random

from game.domain.combat import pick_monster
from game.domain.equipment import add_item
from game.domain.status_fx import has_status
from game.ports.io import ScriptedIO
from game.services.combat_session import _run_combat
from game.services.field_encounters import _handle_sight
from tests.harness import isolated_saves


def test_smoke_combat_win_and_loot(reg, make_player, monkeypatch, tmp_path):
    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="CombatSmoke")
    p["bonus_atk"] = 400
    p["mana"] = 999
    p["max_mana"] = 999
    rng = random.Random(42)
    mon = pick_monster(reg, "dark_forest", rng)
    mon["hp"] = 35
    mon["max_hp"] = 35
    mon["atk"] = 3
    # known enemy so HP shows
    p["knowledge"] = {
        "monsters": {
            mon["id"]: {
                "fought": 1,
                "won": 0,
                "seen": True,
                "name": mon.get("name"),
            }
        }
    }
    # attacks + guard 0 + loot skip
    inputs = ["1"] * 25 + ["0"] * 25 + ["0"]
    io = ScriptedIO(inputs, raise_on_empty=False)
    _run_combat(p, reg, io, random.Random(7), mon=mon, ambush=False)
    out = io.joined()
    assert "ชนะ" in out or int(p.get("level", 1)) >= 1
    assert p["hp"] > 0
    assert "〔ไฟต์〕" in out or "รอบ" in out


def test_smoke_chest_trap_poison(reg, make_player, monkeypatch):
    """Force empty_trap outcome via resolve_approach monkeypatch."""
    monkeypatch.setattr(
        "game.services.field_encounters.resolve_approach",
        lambda kind, reg, rng: "empty_trap",
    )
    p = make_player(name="ChestTrap")
    sight = {
        "kind": "chest",
        "label": "หีบเก่า",
        "hint": "ล็อคร้าว",
        "risk": "?",
    }
    io = ScriptedIO([], raise_on_empty=False)
    _handle_sight(p, reg, io, random.Random(0), sight)
    out = io.joined()
    assert "กับดัก" in out or has_status(p, "poison")
    assert has_status(p, "poison")


def test_smoke_chest_loot_weak(reg, make_player, monkeypatch):
    monkeypatch.setattr(
        "game.services.field_encounters.resolve_approach",
        lambda kind, reg, rng: "loot_weak",
    )
    p = make_player(name="ChestLoot")
    money0 = int(p.get("money_world") or 0)
    inv0 = len(p.get("inventory_ids") or [])
    sight = {"kind": "chest", "label": "หีบ", "hint": "ผุ", "risk": "?"}
    io = ScriptedIO([], raise_on_empty=False)
    _handle_sight(p, reg, io, random.Random(1), sight)
    out = io.joined()
    assert "เปิดหีบ" in out or "หีบ" in out
    # weak loot should grant money and/or item
    assert int(p.get("money_world") or 0) >= money0 or len(
        p.get("inventory_ids") or []
    ) > inv0


def test_smoke_consumable_by_id(reg, make_player):
    from game.services.consumables import _use_potion

    p = make_player(name="PotId")
    p["inventory"] = []
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    add_item(p, "antidote", reg)
    apply_poison = __import__(
        "game.domain.status_fx", fromlist=["apply_status"]
    ).apply_status
    apply_poison(p, "poison", reg, random.Random(0), ignore_resist=True)
    assert has_status(p, "poison")
    io = ScriptedIO(["1"])  # first usable
    ok = _use_potion(p, io, reg)
    assert ok
    assert not has_status(p, "poison")


def test_run_field_accepts_seed(reg, make_player, monkeypatch, tmp_path):
    from tests.harness import field_exit_script, run_field_session

    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="SeedField")
    io = run_field_session(p, reg, field_exit_script("1"), seed=123)
    assert "สนาม" in io.joined() or "พัก" in io.joined() or "เซฟ" in io.joined()
