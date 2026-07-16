"""WO-013: structured turn log + fight report + continuous auto flag."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.fight_log import (
    clear_fight_log,
    damage_tag,
    format_fight_report,
    format_turn_line,
    log_fight_event,
)
from game.domain.needs import ensure_needs
from game.ports.io import ScriptedIO
from game.services.combat_session import _confirm_combat_auto_play, _maybe_stop_combat_auto


def test_turn_line_format():
    line = format_turn_line(
        3,
        outbound=True,
        actor="คุณ",
        action="Fire Ball",
        target="???",
        dmg=24,
        tag="เวท",
    )
    assert "T3" in line
    assert "▸" in line
    assert "Fire Ball" in line or "「Fire Ball」" in line
    assert "24" in line
    assert "เวท" in line


def test_damage_tag_physical_and_arcane():
    assert damage_tag(damage_class="physical") == "กาย"
    assert damage_tag(damage_class="arcane") == "เวท"
    assert damage_tag(elements=["fire"]) in ("เวท", "ไฟ")


def test_fight_report_win_and_loss():
    p: dict = {"needs": {"hunger": 30, "fatigue": 40, "morale": 50}}
    clear_fight_log(p)
    log_fight_event(
        p, 1, outbound=True, actor="คุณ", action="โจมตีปกติ", target="Wolf", dmg=12, tag="กาย"
    )
    log_fight_event(
        p, 1, outbound=False, actor="Wolf", action="กรงเล็บ", target="คุณ", dmg=8, tag="กาย"
    )
    win = format_fight_report(p, outcome="win", enemy_name="Wolf")
    text = "\n".join(win)
    assert "สรุปไฟต์" in text
    assert "ชนะ" in text
    assert "T1" in text
    p["_last_defeat"] = {"line": "สาเหตุหลัก: ไฟต์หนัก (ปะทะ)"}
    loss = format_fight_report(p, outcome="loss", enemy_name="Wolf")
    assert any("แพ้" in x or "สลบ" in x for x in loss)
    assert any("สาเหตุ" in x for x in loss)


def test_continuous_skips_step_prompt():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c1", "warrior", "เมษ")
    ensure_needs(p)
    p["auto_prefs"] = {"low_morale_policy": "caution", "skill_plan": [1]}
    io = ScriptedIO(["1"])  # Continuous
    assert _confirm_combat_auto_play(p, reg, io) is True
    assert p.get("_combat_auto_continuous") is True
    # continuous: no read_line — would raise if it tried with empty inputs
    io2 = ScriptedIO([])
    _maybe_stop_combat_auto(p, io2)
    assert p.get("_combat_auto_play") is True
    # step mode asks
    p["_combat_auto_continuous"] = False
    io3 = ScriptedIO(["0"])
    _maybe_stop_combat_auto(p, io3)
    assert p.get("_combat_auto_play") is not True
