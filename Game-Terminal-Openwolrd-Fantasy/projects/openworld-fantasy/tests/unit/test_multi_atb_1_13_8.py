"""1.13.8: simultaneous multi-enemy ATB + target pick + content bulk."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat_atb import (
    advance_until_ready_multi,
    format_pack_atb_strip,
    init_pack_atb,
)
from game.ports.io import ScriptedIO
from game.services.combat_session import (
    _alive_indices,
    _select_target,
    format_enemy_pack_roster,
    run_combat_wave,
)


def test_init_and_advance_multi():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Multi", "warrior", "เมษ")
    foes = [
        {"id": "a", "name": "A", "hp": 20, "max_hp": 20, "atk": 5, "level": 1},
        {"id": "b", "name": "B", "hp": 20, "max_hp": 20, "atk": 5, "level": 1},
    ]
    rng = random.Random(1)
    init_pack_atb(p, foes, reg, rng, ambush=False)
    assert "atb" in p
    assert all("atb" in f for f in foes)
    acts = advance_until_ready_multi(p, foes, reg, rng)
    assert acts
    assert any(a[0] in ("player", "monster") for a in acts)
    strip = format_pack_atb_strip(p, foes)
    assert "คุณ" in strip


def test_select_target_auto_and_pick():
    foes = [
        {"name": "A", "hp": 0, "max_hp": 10},
        {"name": "B", "hp": 5, "max_hp": 10},
        {"name": "C", "hp": 8, "max_hp": 10},
    ]
    io = ScriptedIO(["3"])
    idx = _select_target(io, foes)
    assert idx == 2
    io2 = ScriptedIO([""])
    assert _select_target(io2, foes) in _alive_indices(foes)


def test_roster_simultaneous_copy():
    pack = [
        {"name": "X", "hp": 10, "max_hp": 10, "atb": 100},
        {"name": "Y", "hp": 0, "max_hp": 10, "atb": 0},
    ]
    lines = format_enemy_pack_roster(pack)
    assert any("พร้อมกัน" in x or "เลือกเป้า" in x for x in lines)
    assert any("ล้ม" in x for x in lines)


def test_run_combat_wave_multi_smoke():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Wave", "warrior", "เมษ")
    p["hp"] = 400
    p["max_hp"] = 400
    p["mana"] = 200
    p["max_mana"] = 200
    p["bonus_atk"] = 50
    p["level"] = 5
    # target 1, attack spam; when second target pick enter; loot 0
    inputs = []
    for _ in range(30):
        inputs.extend(["1", "1"])  # pick target 1 or attack
        inputs.append("1")
    inputs.extend(["", "0", "n", "4", "1"] * 5)
    io = ScriptedIO(inputs, raise_on_empty=True)
    m1 = {
        "id": "city_rat",
        "name": "หนู1",
        "level": 1,
        "hp": 8,
        "max_hp": 8,
        "atk": 1,
        "elements": ["physical"],
        "xp_mult": 0.5,
        "attack_profiles": [{"telegraph": "กัด", "power": 1}],
    }
    m2 = dict(m1)
    m2["id"] = "city_rat2"
    m2["name"] = "หนู2"
    try:
        run_combat_wave(
            p,
            reg,
            io,
            random.Random(3),
            monsters=[m1, m2],
            ambush=False,
        )
    except EOFError:
        pass
    out = io.joined()
    assert "กลุ่ม" in out or "เป้า" in out or int(p.get("hp") or 0) > 0


def test_content_bulk_monsters_items():
    reg = DataRegistry.load(DATA_DIR)
    for mid in ("city_rat", "alley_thug", "crystal_mite", "void_mote"):
        assert mid in reg.monsters
    for iid in ("city_bread", "bandit_knife", "dust_veil", "void_thread"):
        assert iid in reg.items
    pools = (reg.areas.get("ancient_city") or {}).get("monster_pools") or []
    ids = [p.get("id") for p in pools]
    assert "city_rat" in ids
