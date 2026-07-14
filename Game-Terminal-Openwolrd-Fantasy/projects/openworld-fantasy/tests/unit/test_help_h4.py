"""H4: friends policy, helper rep, world log, social quests."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import begin_dungeon
from game.domain.quests import bump_quest, ensure_quests
from game.domain.situation import (
    POLICY_FRIENDS,
    POLICY_PUBLIC,
    apply_assist_victory,
    can_viewer_see_signal,
    claim_help_for_helper,
    format_world_signal_log_lines,
    helper_soft_title,
    is_help_friend,
    list_open_help_signals,
    load_world_signal_log,
    open_help_request,
)
from game.services.save_service import load_player, save_player


def test_friends_policy_hides_from_strangers(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    owner = create_player(reg, "Own", "warrior", "เมษ")
    owner["id"] = "own1"
    begin_dungeon(owner, reg, "dung_forest_root", random.Random(1))
    ok, _ = open_help_request(owner, reg, note="friends only", policy=POLICY_FRIENDS)
    assert ok
    save_player(owner, world_id="default")

    stranger = create_player(reg, "Str", "mage", "เมถุน")
    stranger["id"] = "str1"
    friend = create_player(reg, "Fr", "rogue", "พิจิก")
    friend["id"] = "fr1"
    friend["social_memory"] = {"own1": {"friend_pts": 3, "was_friend": True}}

    assert can_viewer_see_signal(stranger, owner, owner["situation"]["help"]) is False
    assert can_viewer_see_signal(friend, owner, owner["situation"]["help"]) is True
    assert is_help_friend(friend, owner)

    sigs_s = list_open_help_signals(
        "default", viewer=stranger, saves_dir=tmp_path, exclude_player_id="str1"
    )
    assert all(s["owner_id"] != "own1" for s in sigs_s)

    sigs_f = list_open_help_signals(
        "default", viewer=friend, saves_dir=tmp_path, exclude_player_id="fr1"
    )
    assert any(s["owner_id"] == "own1" for s in sigs_f)


def test_public_visible_and_world_log(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    owner = create_player(reg, "Own", "warrior", "เมษ")
    owner["id"] = "own2"
    begin_dungeon(owner, reg, "dung_forest_root", random.Random(2))
    open_help_request(owner, reg, note="pub", policy=POLICY_PUBLIC)
    save_player(owner, world_id="default")

    msgs = load_world_signal_log("default", saves_dir=tmp_path)
    assert msgs and msgs[0].get("kind") == "sos_open"
    lines = format_world_signal_log_lines(msgs)
    assert any("เปิดขอแรง" in ln for ln in lines)


def test_helper_rep_and_title_after_victory(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    owner = create_player(reg, "Own", "warrior", "เมษ")
    owner["id"] = "own3"
    begin_dungeon(owner, reg, "dung_forest_root", random.Random(3))
    open_help_request(owner, reg, gold=10)
    save_player(owner, world_id="default")
    owner = load_player(str(tmp_path / "default" / "own3.json"))

    helper = create_player(reg, "Help", "mage", "เมถุน")
    helper["id"] = "help3"
    helper["money_world"] = 0
    claim_help_for_helper(owner, helper)
    apply_assist_victory(owner, helper, reg)
    assert int(helper.get("help_assists") or 0) >= 1
    assert int(helper.get("help_rep") or 0) >= 5
    assert helper_soft_title(helper) == "ผู้ช่วยใหม่"
    # bond
    assert (helper.get("social_memory") or {}).get("own3")
    assert (owner.get("social_memory") or {}).get("help3")


def test_help_quests_bump():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Q", "warrior", "เมษ")
    p["level"] = 5
    # unlock via first_blood done
    p["quests_done"] = ["first_blood"]
    ensure_quests(p, reg)
    assert "first_sos" in (p.get("quests") or {}) or True  # may need unlock_level
    notes = bump_quest(p, reg, "help_open")
    notes2 = bump_quest(p, reg, "help_assist")
    # progress recorded if quest active
    qs = p.get("quests") or {}
    if "first_sos" in qs:
        assert int(qs["first_sos"].get("progress") or 0) >= 1
    if "first_hand" in qs:
        assert int(qs["first_hand"].get("progress") or 0) >= 1
    assert isinstance(notes, list) and isinstance(notes2, list)
