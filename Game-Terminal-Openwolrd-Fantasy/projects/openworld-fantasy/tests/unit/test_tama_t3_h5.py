"""T3 live Tama panel · H5 lite presence soft."""
import time

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import (
    apply_tama_panel_live_tick,
    close_tama_panel_session,
    get_needs,
    stamp_tama_panel_open,
    tama_enter_animation_frames,
)
from game.domain.situation import (
    format_board_lines,
    presence_soft_for_player,
)
from game.domain.ui_prefs import ensure_ui_prefs


def test_enter_animation_has_frames():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Tama", "warrior", "สิงห์")
    frames = tama_enter_animation_frames(p)
    assert len(frames) >= 2
    assert any("ลืมตา" in " ".join(f) or "หายใจ" in " ".join(f) for f in frames)


def test_live_tick_drips_hunger_with_cap():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Live", "mage", "เมถุน")
    ensure_ui_prefs(p)
    p["ui_prefs"]["live_tama"] = True
    stamp_tama_panel_open(p)
    n0 = get_needs(p)["hunger"]
    # simulate 90s on panel in one go
    p["_tama_panel_last_tick_unix"] = time.time() - 90
    notes = apply_tama_panel_live_tick(p, force=True)
    n1 = get_needs(p)["hunger"]
    assert n1 >= n0
    # capped soft
    assert n1 - n0 <= 5
    if n1 > n0:
        assert notes
        assert any("เวลา" in x or "ไหล" in x for x in notes)
    close_tama_panel_session(p)
    assert "_tama_panel_opened_unix" not in p


def test_live_tick_respects_pref_off():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Off", "warrior", "สิงห์")
    prefs = ensure_ui_prefs(p)
    prefs["live_tama"] = False
    stamp_tama_panel_open(p)
    p["_tama_panel_last_tick_unix"] = time.time() - 120
    notes = apply_tama_panel_live_tick(p)
    assert notes == []


def test_presence_fresh_from_unix():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Pres", "warrior", "สิงห์")
    p["saved_at_unix"] = time.time() - 60  # 1 min ago
    pr = presence_soft_for_player(p)
    assert pr["id"] == "fresh"
    assert "สด" in pr["label"]


def test_presence_stale():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Old", "warrior", "สิงห์")
    p["saved_at_unix"] = time.time() - 60 * 60 * 5  # 5h
    pr = presence_soft_for_player(p)
    assert pr["id"] == "stale"


def test_board_lines_include_presence():
    signals = [
        {
            "owner_name": "เมษ",
            "label": "ถ้ำเงา",
            "severity_label": "วิกฤต",
            "policy_label": "สาธารณะ",
            "claimable": True,
            "offer_line": "อาสา",
            "presence": "fresh",
            "presence_label": "ร่องรอยสด",
            "note": "",
        }
    ]
    text = "\n".join(format_board_lines(signals))
    assert "ร่องรอยสด" in text
    assert "เมษ" in text


def test_ui_prefs_have_t3_keys():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Pref", "warrior", "สิงห์")
    prefs = ensure_ui_prefs(p)
    assert "live_tama" in prefs
    assert "tama_enter_anim" in prefs
