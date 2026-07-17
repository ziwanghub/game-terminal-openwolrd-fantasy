"""WO-010: Auto Play entry on combat screen."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.mode_shell import (
    MODE_COMBAT,
    combat_auto_play_soft_hints,
    render_mode_actions,
)
from game.domain.needs import ensure_needs
from game.ports.io import ScriptedIO
from game.services.combat_session import (
    _confirm_combat_auto_play,
    _execute_combat_auto_turn,
    _player_act,
)


def test_combat_menu_has_auto_play_option():
    text = render_mode_actions(MODE_COMBAT)
    assert "1" in text and "โจมตี" in text
    assert "7" in text
    assert "8" in text
    assert "Auto Play" in text
    assert "A" in text


def test_soft_hints_low_morale_and_fatigue():
    p = {"needs": {"hunger": 20, "fatigue": 80, "morale": 22}}
    hints = combat_auto_play_soft_hints(p)
    text = "\n".join(hints)
    assert "ขวัญหด" in text
    assert "Auto Play" in text
    assert "Caution" in text
    assert "อ่อนล้า" in text or "ล้า" in text


def test_soft_hints_quiet_when_healthy():
    p = {"needs": {"hunger": 10, "fatigue": 10, "morale": 80}}
    assert combat_auto_play_soft_hints(p) == []


def test_confirm_and_auto_turn_damages():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap1", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 70}
    p["auto_prefs"] = {"low_morale_policy": "caution", "skill_plan": [1], "hp_pct": 30}
    mon = {
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
    io = ScriptedIO(["1"])  # Continuous
    assert _confirm_combat_auto_play(p, reg, io) is True
    assert p.get("_combat_auto_play") is True
    assert p.get("_combat_auto_continuous") is True
    out = io.joined()
    assert "Auto Play" in out
    assert "Continuous" in out
    assert "สรุป" in out
    assert "Caution" in out or "caution" in out.lower()
    # proportional box chrome
    assert "┌" in out or "│" in out or "---" in out or "╔" in out

    hp_before = int(mon["hp"])
    rng = random.Random(3)
    io2 = ScriptedIO([])
    result = _execute_combat_auto_turn(
        p,
        mon,
        reg,
        io2,
        rng,
        area_id="dark_forest",
        known=True,
        enemy_name="Wolf",
        combat_round=1,
    )
    assert result is True
    assert int(mon["hp"]) < hp_before
    auto_out = io2.joined()
    # boxed Auto turn — no free-form 〔Auto Play〕 dump
    assert "Auto" in auto_out
    assert "โจมตี" in auto_out or "ท่า" in auto_out or "ดาเมจ" in auto_out
    assert "〔Auto Play〕" not in auto_out


def test_player_act_auto_key_and_stop():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap2", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["needs"] = {"hunger": 15, "fatigue": 15, "morale": 75}
    p["auto_prefs"] = {"skill_plan": [1], "low_morale_policy": "caution"}
    mon = {
        "id": "slime",
        "name": "Slime",
        "level": 1,
        "hp": 200,
        "max_hp": 200,
        "atk": 1,
        "elements": ["physical"],
        "statuses": [],
        "attack_profiles": [{"id": "a", "power": 1, "weight": 1}],
    }
    # 8 start auto → mode 2 Step → stop after first turn with 0
    io = ScriptedIO(["8", "2", "0"])
    result = _player_act(
        p,
        mon,
        reg,
        io,
        random.Random(1),
        area_id="dark_forest",
        known=True,
        enemy_name="Slime",
        combat_round=1,
    )
    assert result is True
    out = io.joined()
    assert "Auto Play" in out or "Auto" in out
    assert p.get("_combat_auto_play") is not True  # stopped after step prompt 0
    assert int(mon["hp"]) < 200
