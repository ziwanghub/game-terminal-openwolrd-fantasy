"""W3 lite: file locks · world_meta · host heartbeat · client pointer."""
import json
import time
from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.file_lock import world_file_lock
from game.domain.market import load_market, save_market
from game.domain.world_meta import (
    format_host_status_lines,
    get_client_pointer,
    host_heartbeat,
    host_status,
    load_world_meta,
    rebuild_player_index,
    refresh_world_index,
    set_client_pointer,
)
from game.services.save_service import save_player


def test_file_lock_acquire(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    with world_file_lock("default", "testlock", timeout=2.0) as ok:
        assert ok is True
        lock = tmp_path / "saves" / "default" / ".locks" / "testlock.lock"
        assert lock.is_file()


def test_market_save_load_locked(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.market.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    m = load_market("default")
    m["tax_fund"] = 42
    save_market("default", m)
    m2 = load_market("default")
    assert int(m2.get("tax_fund") or 0) == 42


def test_world_meta_and_index(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_meta.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_social.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    p = create_player(reg, "HostP", "warrior", "สิงห์", world_id="default")
    p["id"] = "hostp1"
    save_player(p, world_id="default")
    meta = refresh_world_index("default")
    assert meta.get("schema") == 1
    idx = meta.get("player_index") or []
    assert any(x.get("id") == "hostp1" for x in idx)
    # no raw combat stats in index
    for row in idx:
        assert "bonus_atk" not in row
        assert "hp" not in row


def test_host_heartbeat_alive(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_meta.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    host_heartbeat("default", host_id="test-host")
    st = host_status("default")
    assert st["alive"] is True
    assert "host" in st.get("label") or st.get("alive")
    lines = format_host_status_lines("default")
    assert any("host" in x.lower() or "โลก" in x for x in lines)


def test_host_stale(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_meta.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    meta = load_world_meta("default")
    meta["host"] = {
        "id": "old",
        "last_beat_unix": time.time() - 120,
        "last_beat": "past",
    }
    from game.domain.world_meta import save_world_meta

    save_world_meta("default", meta)
    st = host_status("default")
    assert st["alive"] is False


def test_client_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.world_meta.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True)
    set_client_pointer("hardcore", prefer_host=True)
    ptr = get_client_pointer()
    assert ptr.get("world_id") == "hardcore"
    assert ptr.get("prefer_host") is True
    path = tmp_path / "saves" / "client_pointer.json"
    assert path.is_file()


def test_host_cli_status(tmp_path, monkeypatch):
    monkeypatch.setattr("game.domain.file_lock.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.domain.world_meta.SAVES_DIR", tmp_path / "saves")
    (tmp_path / "saves" / "default").mkdir(parents=True)
    from game.host import main

    rc = main(["status", "default"])
    assert rc == 0
