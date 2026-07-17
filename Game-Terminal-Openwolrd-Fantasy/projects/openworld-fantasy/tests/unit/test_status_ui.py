"""P0 unit tests for status rendering (no input)."""
from game.domain.bars import ratio_bar, xp_bar
from game.domain.narrative import emit_narrative
from game.ui_terminal.status import (
    render_combat_vitals,
    render_field_actions,
    render_mode_chrome,
    render_status_l0,
    render_status_l1,
    render_status_l1c,
)


def _sample_player():
    return {
        "name": "pep-test",
        "level": 2,
        "occupation": "โจรเงา",
        "zodiac": "สิงห์",
        "hp": 72,
        "max_hp": 90,
        "mana": 40,
        "max_mana": 50,
        "pressure": 18,
        "xp": 40,
        "xp_percent": 34,
        "xp_needed": 120,
        "money_world": 120,
        "money_heaven": 15,
        "money_hell": 40,
        "location": "cave_shadow",
        "area_mastery": {"cave_shadow": 33},
        "skills": ["shadow_strike", "fire_ball"],
        "equip": {"weapon": None, "armor": None},
        "cards": [],
        "blessings": [],
        "statuses": [],
        "disciple_of": None,
        "other_players": 1,
        "blessing_turns": 0,
        "party": [],
        "stat_points": 0,
        "personality_points": 0,
    }


def test_ratio_bar_full():
    assert ratio_bar(10, 10, width=5) == "█████"


def test_ratio_bar_empty():
    assert ratio_bar(0, 10, width=5) == "░░░░░"


def test_xp_bar():
    assert len(xp_bar(50, width=10)) == 10


def test_l0_contains_name_and_area():
    text = render_status_l0(_sample_player(), "ถ้ำเงา")
    assert "pep-test" in text
    assert "ถ้ำเงา" in text
    assert "72/90" in text
    assert "HP" in text


def test_l1_box_and_bars():
    text = render_status_l1(_sample_player(), "ถ้ำเงา")
    assert "pep-test" in text
    assert "ถ้ำเงา" in text
    assert "HP" in text
    assert "MP" in text
    assert "shadow_strike" in text
    assert "╔" in text or "+" in text
    # sectioned full status — proportional scan labels
    assert "ตัวตน" in text
    assert "ชีพ" in text
    assert "ลงทุน" in text
    assert "ที่ · เงิน · สกิล" in text or "สกิล" in text
    assert text.count("╠") >= 3 or text.count("+") >= 3


def test_l1c_compact_no_skill_list():
    p = _sample_player()
    p["needs"] = {"hunger": 42, "fatigue": 71, "morale": 28}
    text = render_status_l1c(p, "ถ้ำเงา")
    assert "pep-test" in text
    assert "ถ้ำเงา" in text
    assert "72/90" in text
    assert "ชำนาญ" in text
    # compact: full skill dump is L1 only
    assert "shadow_strike" not in text
    # WO-006: needs block prominent
    assert "สถานะกายใจ" in text or "หิว" in text
    assert "หิว" in text and "ล้า" in text and "ขวัญ" in text
    assert "พื้นที่" in text or "เงิน" in text
    # allow more lines for needs block
    assert text.count("\n") <= 28


def test_mode_chrome_and_field_actions():
    assert "สนาม" in render_mode_chrome("สนาม", "โลก default")
    act = render_field_actions(stat_points=2, boss_line=" ☠ บอส: ทดสอบ (B)")
    assert "ทำอะไรต่อ" in act
    assert act.count("ทำอะไรต่อ") == 1
    assert "0  ออก" in act or "0 ออก" in act
    assert "แต้มสถานะ" in act


def test_sights_panel_sections():
    from game.ui_terminal.status import format_sights_panel_lines

    lines = format_sights_panel_lines(
        [
            {
                "handle": "ch01",
                "kind": "chest",
                "label": "หีบเก่า",
                "hint": "สลักเลือน",
                "risk": "?",
            },
            {
                "handle": "mn01",
                "kind": "monster",
                "label": "???",
                "hint": "เงาร่าง",
                "risk": "?",
            },
        ],
        flavor="คุณหยุดมองรอบ",
    )
    text = "\n".join(lines)
    assert "สิ่งที่สังเกต" in text
    assert "ch01" in text
    assert "หีบ" in text
    assert "1." in text


def test_combat_vitals_known_and_unknown():
    p = _sample_player()
    mon = {
        "name": "หมาป่า",
        "hp": 40,
        "max_hp": 80,
        "statuses": [],
        "boss": False,
    }
    known = render_combat_vitals(p, mon, known=True, situation="คุณยังมั่น", round_no=2)
    assert "หมาป่า" in known
    assert "40/80" in known
    assert "▸" in known or "คุณยังมั่น" in known
    assert "จังหวะ" in known
    unk = render_combat_vitals(p, mon, known=False, situation="ระวัง")
    assert "???" in unk


def test_combat_vitals_shows_needs_compact():
    """WO-005 P1.5: soft needs line on combat vitals (proportional)."""
    p = _sample_player()
    p["needs"] = {"hunger": 20, "fatigue": 15, "morale": 80}
    mon = {"name": "มอน", "hp": 10, "max_hp": 10, "statuses": [], "boss": False}
    text = render_combat_vitals(p, mon, known=True, round_no=1)
    assert "กายใจ" in text
    # soft labels when good — not "หิว−หิว"
    assert "อิ่ม" in text or "หิว" in text
    assert "เบา" in text or "ล้า" in text
    assert "ขวัญ" in text
    assert "หิว−หิว" not in text


def test_combat_vitals_soft_warnings_when_stressed():
    p = _sample_player()
    p["needs"] = {"hunger": 90, "fatigue": 80, "morale": 15}
    mon = {"name": "มอน", "hp": 10, "max_hp": 10, "statuses": [], "boss": False}
    text = render_combat_vitals(p, mon, known=True, round_no=1)
    assert "หิว" in text
    # at least one soft warning line
    assert "วิกฤต" in text or "ขวัญ" in text or "ล้า" in text


def test_emit_narrative_max_lines():
    class _IO:
        def __init__(self):
            self.lines = []

        def write_line(self, text=""):
            self.lines.append(text)

    io = _IO()
    emit_narrative(io, ["a", "b", "c", "d"], max_lines=2)
    assert io.lines == ["a", "b"]
