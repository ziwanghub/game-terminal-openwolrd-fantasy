"""WO-PARTY-6: companion soft appraisal + bond labeling."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.appraisal import (
    appraise_companion_soft,
    format_companion_bond_line,
    format_party_appraisal_blurb,
    relic_vs_companion_bond_hint,
)
from game.domain.character import create_player
from game.domain.party import format_party_panel, set_relationship


def test_bond_line_says_companion_not_relic():
    line = format_companion_bond_line(70)
    assert "สัมพันธ์สหาย" in line
    assert "ไว้ใจ" in line or "█" in line
    assert "เรลิก" not in line
    hint = relic_vs_companion_bond_hint()
    assert "เรโซแนนซ์" in hint or "เรลิก" in hint


def test_appraise_companion_soft_base():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap1", "warrior", "เมษ")
    p["appraisal_tier"] = "base"
    m = {
        "id": "spirit_mist",
        "name": "ภูตหมอก",
        "kind": "spirit",
        "bonus_atk": 2,
        "flavor": "ไอหมอก",
    }
    set_relationship(p, "spirit_mist", 55)
    lines = appraise_companion_soft(p, m, reg)
    text = "\n".join(lines)
    assert "ภูตหมอก" in text
    assert "สัมพันธ์สหาย" in text
    assert "ATK" not in text
    assert "gift_likes" not in text


def test_appraise_depth_scales_with_tier():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap2", "mage", "เมถุน")
    m = {
        "id": "beast_forest",
        "name": "หมาป่า",
        "kind": "beast",
        "bonus_atk": 3,
    }
    set_relationship(p, "beast_forest", 80)
    p["appraisal_tier"] = "base"
    base_n = len(appraise_companion_soft(p, m, reg))
    p["appraisal_tier"] = "S"
    s_n = len(appraise_companion_soft(p, m, reg))
    p["appraisal_tier"] = "SS"
    ss_n = len(appraise_companion_soft(p, m, reg))
    p["appraisal_tier"] = "SSS"
    sss_lines = appraise_companion_soft(p, m, reg)
    sss_n = len(sss_lines)
    assert s_n >= base_n
    assert ss_n >= s_n
    assert sss_n >= ss_n
    text = "\n".join(sss_lines)
    assert "ซุ่ม" in text or "เรโซแนนซ์" in text or "เรลิก" in text


def test_panel_uses_companion_bond_label():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap3", "warrior", "เมษ")
    p["party"] = [
        {
            "id": "spirit_mist",
            "name": "ภูตหมอก",
            "kind": "spirit",
            "bonus_atk": 2,
        }
    ]
    set_relationship(p, "spirit_mist", 40)
    text = "\n".join(format_party_panel(p, reg))
    assert "สัมพันธ์สหาย" in text
    assert "เรโซแนนซ์เรลิก" in text or "≠" in text
    # no raw (40) score dump preferred — soft bar only
    assert "อ่าน:" in text or "เงา" in text


def test_blurb_one_line():
    p = {"appraisal_tier": "S"}
    m = {"id": "x", "kind": "spirit", "name": "A"}
    blurb = format_party_appraisal_blurb(p, m, None)
    assert "อ่าน" in blurb
    assert "\n" not in blurb
