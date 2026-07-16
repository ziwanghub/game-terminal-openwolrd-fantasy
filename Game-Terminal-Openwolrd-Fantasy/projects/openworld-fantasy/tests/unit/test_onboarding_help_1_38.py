"""Tutorial / onboarding covers growth systems (C K P unit soft)."""
from __future__ import annotations

from game.ui_terminal.help import (
    CITY_ONBOARD_TIPS,
    HELP_LINES,
    TUTORIAL_PAGES,
    help_covers_keywords,
    maybe_onboarding_tip,
)
from game.ports.io import ScriptedIO


def test_tutorial_has_six_soft_pages():
    assert len(TUTORIAL_PAGES) == 6
    blob = "\n".join("\n".join(p) for p in TUTORIAL_PAGES)
    # soft DNA core topics (growth detail lives in onboard tips + H help)
    for key in ("หิว", "ขวัญ", "Anima", "Mini-Moment", "เรลิก", "ภาระ", "Auto"):
        assert key in blob


def test_onboard_tips_cover_c_k_p_upgrade_unit():
    blob = "\n".join(CITY_ONBOARD_TIPS)
    assert "C" in blob
    assert "K" in blob or "ต้นไม้" in blob
    assert "P" in blob or "แต้ม" in blob
    assert "อัป" in blob or "เกียร์" in blob
    assert "อาชีพลับ" in blob or "Unit" in blob or "ลับ" in blob


def test_help_lines_mention_growth():
    blob = "\n".join(HELP_LINES)
    assert "C" in blob and "K" in blob and "P" in blob


def test_maybe_onboarding_tip_advances():
    io = ScriptedIO([])
    player = {
        "tutorial_done": True,
        "onboard_tip_index": 0,
        "time_units": 5,  # 5 % 3 == 2
        "level": 2,
    }
    tip = maybe_onboarding_tip(player, io, area_id="ancient_city")
    assert tip
    assert player["onboard_tip_index"] == 1


def test_help_keywords_nonempty():
    assert len(help_covers_keywords()) > 20
