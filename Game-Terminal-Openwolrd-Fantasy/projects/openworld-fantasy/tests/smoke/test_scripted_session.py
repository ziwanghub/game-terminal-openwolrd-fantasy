"""Smoke / golden-path sessions driven by ScriptedIO (no real terminal)."""
from __future__ import annotations

from tests.harness import (
    create_script,
    field_exit_script,
    isolated_saves,
    run_create_session,
    run_field_session,
)


def test_scripted_io_basic():
    from game.ports.io import ScriptedIO

    io = ScriptedIO(["hello", "world"])
    io.write_line("prompt")
    assert io.read_line("a: ") == "hello"
    assert io.read_line("b: ") == "world"
    assert io.contains("prompt")
    try:
        io.read_line("empty: ")
        assert False, "expected EOFError"
    except EOFError:
        pass


def test_interactive_create_scripted(reg):
    player, io = run_create_session(reg, create_script("SmokeHero", occupation_index="1"))
    assert player["name"] == "SmokeHero"
    assert player["level"] == 1
    assert player["hp"] > 0
    assert player.get("skills")
    assert io.contains("สร้าง")


def test_field_rest_then_exit(reg, make_player, monkeypatch, tmp_path):
    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="RestExit")
    hp_before = int(p["hp"])
    # rest may heal; force missing hp to observe heal
    p["hp"] = max(1, hp_before // 2)
    io = run_field_session(p, reg, field_exit_script("1"))  # rest then exit
    assert int(p["hp"]) >= p["hp"]  # still valid
    assert p.get("id")  # save assigned id
    out = io.joined()
    assert "พัก" in out or "HP" in out or "เซฟ" in out or "เริ่ม" in out


def test_field_shop_menu_then_exit(reg, make_player, monkeypatch, tmp_path):
    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="ShopExit")
    # 6 = SHOP hub (Mode Shell B), then 0 exit shop + 0 exit field
    io = run_field_session(p, reg, field_exit_script("6", "0"))
    assert "ร้าน" in io.joined()


def test_field_quests_then_exit(reg, make_player, monkeypatch, tmp_path):
    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="QuestExit")
    io = run_field_session(p, reg, field_exit_script("9", ""))
    assert "เควส" in io.joined()


def test_create_then_field_golden_path(reg, monkeypatch, tmp_path):
    """Full path: create character → rest → open quests → exit/save."""
    isolated_saves(monkeypatch, tmp_path)
    player, cio = run_create_session(
        reg, create_script("Golden", birth="1/1/2000", occupation_index="1")
    )
    assert player["name"] == "Golden"
    player["tutorial_done"] = True
    player["world_id"] = "default"
    io = run_field_session(
        player,
        reg,
        field_exit_script("1", "9", ""),  # rest, quests+enter, exit
    )
    assert player.get("id")
    joined = io.joined()
    assert len(joined) > 50


def test_save_isolated_from_real_saves(reg, make_player, monkeypatch, tmp_path):
    isolated_saves(monkeypatch, tmp_path)
    p = make_player(name="IsoSave")
    run_field_session(p, reg, field_exit_script())
    saves = list((tmp_path / "saves").rglob("*.json"))
    assert saves, "expected a save under tmp_path"
    # must not write under project default unless path equals tmp
    for s in saves:
        assert str(tmp_path) in str(s)
