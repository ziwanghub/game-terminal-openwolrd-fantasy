"""World picker: 0 = back to main menu (do not force first world)."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.ports.io import ScriptedIO
from game.services.world_service import format_world_picker_lines
from game.app import pick_world


def test_format_world_picker_shows_back():
    reg = DataRegistry.load(DATA_DIR)
    text = "\n".join(format_world_picker_lines(reg))
    assert "เลือกโลก" in text
    assert "0" in text and "ย้อนกลับ" in text


def test_pick_world_zero_returns_none():
    reg = DataRegistry.load(DATA_DIR)
    io = ScriptedIO(["0"])
    assert pick_world(reg, io) is None
    out = io.joined()
    assert "ย้อนกลับ" in out


def test_pick_world_empty_returns_none():
    reg = DataRegistry.load(DATA_DIR)
    io = ScriptedIO([""])
    assert pick_world(reg, io) is None


def test_pick_world_first_selects_first_row():
    reg = DataRegistry.load(DATA_DIR)
    from game.services.world_service import list_world_menu_rows

    rows = list_world_menu_rows(reg)
    assert rows
    io = ScriptedIO(["1"])
    wid = pick_world(reg, io)
    assert wid == str(rows[0]["id"])
