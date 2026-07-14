"""1.13.9: multi-target *, AoE skills, content bulk."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.ports.io import ScriptedIO
from game.services.combat_session import (
    _apply_splash_damage,
    _select_target,
    run_combat_wave,
)


def test_select_target_all():
    foes = [
        {"name": "A", "hp": 10, "max_hp": 10},
        {"name": "B", "hp": 10, "max_hp": 10},
    ]
    io = ScriptedIO(["*"])
    assert _select_target(io, foes) == -1
    io2 = ScriptedIO(["all"])
    assert _select_target(io2, foes) == -1


def test_splash_damage_reduces_secondaries():
    reg = DataRegistry.load(DATA_DIR)
    primary_dmg = 20
    splash = [
        {"name": "S1", "hp": 15, "max_hp": 15},
        {"name": "S2", "hp": 15, "max_hp": 15},
    ]
    io = ScriptedIO([])
    _apply_splash_damage(
        io, primary_dmg, splash, mult=0.5, reg=reg, rng=random.Random(1)
    )
    # balance may diminish below 0.5 when 2 splash targets
    assert int(splash[0]["hp"]) < 15
    assert int(splash[1]["hp"]) < 15
    assert int(splash[0]["hp"]) >= 15 - 10  # not full 20 dmg
    assert "กระแส" in io.joined()


def test_aoe_skills_loaded():
    reg = DataRegistry.load(DATA_DIR)
    for sid in (
        "open_sweep",
        "open_shockwave",
        "open_spark_fan",
        "open_void_ripple",
        "warrior_cleave",
        "warrior_whirl",
    ):
        sk = reg.skills.get(sid) or {}
        assert sk, sid
        if sid.startswith("open_") and sid != "open_mist_veil":
            assert sk.get("aoe") or sid == "open_mist_veil"


def test_content_quests_and_craft():
    reg = DataRegistry.load(DATA_DIR)
    for qid in ("rat_hunter", "pack_survivor", "forge_bread", "market_first_sale"):
        assert qid in reg.quests
    assert "craft_bandit_knife" in (reg.recipes or {})
    assert "craft_dust_veil" in (reg.recipes or {})
    assert "craft_city_ration" in (reg.recipes or {})


def test_multi_wave_all_target_smoke():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "AoE", "warrior", "เมษ")
    p["hp"] = 500
    p["max_hp"] = 500
    p["mana"] = 200
    p["bonus_atk"] = 40
    p["skills"] = list(p.get("skills") or []) + ["open_sweep"]
    # * all, attack 1; then more attacks
    inputs = ["*", "1"] * 20 + ["1", "1"] * 20 + ["0", ""] * 5
    io = ScriptedIO(inputs, raise_on_empty=True)
    m1 = {
        "id": "r1",
        "name": "R1",
        "level": 1,
        "hp": 12,
        "max_hp": 12,
        "atk": 1,
        "elements": ["physical"],
        "xp_mult": 0.5,
        "attack_profiles": [{"telegraph": "x", "power": 1}],
    }
    m2 = dict(m1)
    m2["id"] = "r2"
    m2["name"] = "R2"
    try:
        run_combat_wave(
            p, reg, io, random.Random(9), monsters=[m1, m2], ambush=False
        )
    except EOFError:
        pass
    out = io.joined()
    assert "กลุ่ม" in out or "กระแส" in out or "เป้า" in out
