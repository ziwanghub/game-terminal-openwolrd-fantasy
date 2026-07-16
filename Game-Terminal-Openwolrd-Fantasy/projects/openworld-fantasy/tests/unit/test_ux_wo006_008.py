"""WO-006 field layout · WO-007 menu index · WO-008 auto policy hub."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.mode_shell import MODE_PERSONAL, render_mode_actions
from game.domain.needs import format_field_needs_block
from game.ports.io import ScriptedIO
from game.services.auto_policy_hub import run_auto_policy_hub, soft_agent_summary
from game.ui_terminal.status import format_sights_panel_lines, render_status_l1c


def test_wo006_field_needs_block_labels():
    p = {"needs": {"hunger": 42, "fatigue": 71, "morale": 28}}
    lines = format_field_needs_block(p, width=6)
    text = "\n".join(lines)
    assert "สถานะกายใจ" in text
    assert "หิว" in text and "ล้า" in text and "ขวัญ" in text
    # soft warning present for low morale / high fatigue
    assert "ขวัญ" in text


def test_wo006_l1c_section_order():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ux6", "vagabond", "เมษ")
    p["needs"] = {"hunger": 50, "fatigue": 60, "morale": 40}
    text = render_status_l1c(p, "ป่ามืด")
    assert "ตัวตน" in text
    assert "สถานะกายใจ" in text
    i_id = text.find("ตัวตน")
    i_need = text.find("สถานะกายใจ")
    i_area = text.find("พื้นที่")
    assert 0 <= i_id < i_need < i_area


def test_wo006_sights_panel_separate():
    lines = format_sights_panel_lines(
        [{"handle": "mn01", "kind": "monster", "label": "???", "hint": "เงา", "risk": "สูง"}],
        flavor="ใบไม้กระซิบ",
    )
    text = "\n".join(lines)
    assert "สิ่งที่สังเกต" in text
    assert "ระยะสายตา" in text or "ดึงความสนใจ" in text


def test_wo007_personal_menu_is_index():
    text = render_mode_actions(MODE_PERSONAL)
    assert "เมนูตัวละคร" in text
    assert "สถานะโดยรวม" in text
    assert "กระเป๋า" in text
    assert "Auto Policy" in text or "A  " in text
    assert "ประวัติ" in text or "Log" in text


def test_wo009_care_section_with_stock_counts():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "wo9", "warrior", "ตุลย์")
    p["needs"] = {"hunger": 20, "fatigue": 70, "morale": 28}
    p["inventory_ids"] = list(p.get("inventory_ids") or []) + [
        "potion_hp_small",
        "potion_hp_small",
        "potion_mana",
    ]
    text = render_mode_actions(MODE_PERSONAL, player=p, reg=reg)
    assert "ดูแล & Auto Play" in text or "【ดูแล" in text
    assert "อาหาร" in text
    assert "[HP" in text or "HP " in text
    assert "Auto Policy" in text
    assert "→" in text or "Caution" in text or "ขวัญ" in text


def test_wo009_field_care_band_after_main():
    from game.domain.mode_shell import MODE_EXPLORE
    from game.services.auto_policy_hub import care_auto_oneliner

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "wo9f", "warrior", "ตุลย์")
    p["needs"] = {"hunger": 20, "fatigue": 25, "morale": 80}
    p["auto_prefs"] = {"low_morale_policy": "caution"}
    p["inventory_ids"] = list(p.get("inventory_ids") or []) + [
        "potion_hp_small",
        "potion_mana",
        "food_bread",
        "food_bread",
    ]
    text = render_mode_actions(MODE_EXPLORE, player=p, reg=reg, boss_line="บอส ล็อก — ต้องการเลเวล 5")
    # band order: หลัก then ดูแล then ระบบ
    i_main = text.find("หลัก")
    i_care = text.find("ดูแล")
    i_sys = text.find("ระบบ")
    assert 0 <= i_main < i_care < i_sys
    assert "กินเสบียง" in text
    assert "Auto Policy" in text
    assert "O" in text  # field Auto Policy key (A = rank)
    oneliner = care_auto_oneliner(p, reg)
    assert "ขวัญขวัญ" not in oneliner
    assert "ขวัญดี" in oneliner or "ขวัญ" in oneliner
    assert "→" in oneliner


def test_wo008_agent_summary_and_hub_exit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ux8", "warrior", "ตุลย์")
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 25}
    p["auto_prefs"] = {"low_morale_policy": "caution", "morale": 35}
    lines = soft_agent_summary(p, reg)
    text = "\n".join(lines)
    assert "Agent" in text or "ขวัญ" in text
    assert "หิว" in text
    io = ScriptedIO(["0"])
    run_auto_policy_hub(p, reg, io)
    out = io.joined()
    assert "Auto Policy" in out or "Agent" in out
