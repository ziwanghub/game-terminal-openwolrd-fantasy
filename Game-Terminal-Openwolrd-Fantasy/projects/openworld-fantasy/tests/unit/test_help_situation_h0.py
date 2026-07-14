"""H0: situation on save + help consent (no helper yet)."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import begin_dungeon, exit_dungeon, in_dungeon, on_dungeon_boss_defeated
from game.domain.situation import (
    clear_situation,
    close_help_request,
    get_situation,
    help_is_open,
    open_help_request,
    sync_situation_from_dungeon,
)
from game.services.save_service import load_player, save_player


def test_begin_dungeon_creates_situation_closed():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0a", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    assert in_dungeon(p)
    sit = get_situation(p)
    assert sit is not None
    assert sit["kind"] == "dungeon"
    assert sit["ref_id"] == "dung_forest_root"
    assert help_is_open(p) is False
    assert sit["help"]["status"] == "closed"


def test_open_and_close_help_consent():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0b", "mage", "เมถุน")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(2))
    ok, notes = open_help_request(p, note="ช่วยด้วย")
    assert ok
    assert help_is_open(p)
    assert get_situation(p)["help"]["note"] == "ช่วยด้วย"
    assert any("ยินยอม" in n or "สัญญาณ" in n for n in notes)

    ok2, notes2 = open_help_request(p)
    assert ok2 is False

    ok3, notes3 = close_help_request(p)
    assert ok3
    assert help_is_open(p) is False
    assert any("ดับ" in n or "ปิด" in n for n in notes3)


def test_open_help_requires_situation():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0c", "warrior", "เมษ")
    ok, notes = open_help_request(p)
    assert ok is False
    assert not help_is_open(p)


def test_exit_dungeon_clears_situation_and_help():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0d", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(3))
    open_help_request(p, note="x")
    assert help_is_open(p)
    on_dungeon_boss_defeated(p, reg)
    exit_dungeon(p, reg, success=True)
    assert not in_dungeon(p)
    assert get_situation(p) is None
    assert help_is_open(p) is False


def test_help_flag_survives_save_load(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0e", "rogue", "พิจิก")
    p["id"] = "h0e_test"
    begin_dungeon(p, reg, "dung_forest_root", random.Random(4))
    open_help_request(p, note="persist")

    from game import config as cfg
    from game.services import save_service as ss

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    path = save_player(p, world_id="default")
    loaded = load_player(str(path))
    assert help_is_open(loaded)
    assert get_situation(loaded)["help"]["note"] == "persist"
    assert loaded.get("dungeon_run")


def test_sync_severity_updates():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h0f", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(5))
    run = p["dungeon_run"]
    run["turns_left"] = 1
    run["turns_max"] = 20
    sync_situation_from_dungeon(p, preserve_help=True)
    assert get_situation(p)["severity"] == "critical"
