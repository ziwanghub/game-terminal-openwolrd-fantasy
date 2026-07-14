"""W0 rank board soft enhancements."""
import json
from pathlib import Path

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.world_social import (
    build_world_ranking,
    format_ranking_lines,
    hidden_rank_score,
    soft_rank_band,
    write_rank_board_soft,
)
from game.services.save_service import save_player


def test_soft_rank_band():
    assert "เงาแรก" in soft_rank_band(1)
    assert soft_rank_band(10) == "นักเดินทาง"


def test_help_assists_boost_hidden_score():
    reg = DataRegistry.load(DATA_DIR)
    a = create_player(reg, "a", "warrior", "เมษ")
    b = create_player(reg, "b", "warrior", "เมษ")
    a["help_assists"] = 0
    b["help_assists"] = 5
    assert hidden_rank_score(b) > hidden_rank_score(a)


def test_rank_board_file_no_scores(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    from game import config as cfg
    from game.services import save_service as ss
    from game.domain import world_social as ws

    monkeypatch.setattr(ss, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)

    p = create_player(reg, "RankMe", "warrior", "เมษ")
    p["id"] = "rank_me"
    p["help_assists"] = 2
    save_player(p, world_id="default")

    board = build_world_ranking("default", reg)
    assert board
    assert "soft_band" in board[0]
    assert "_score" not in board[0]

    lines = format_ranking_lines("default", reg)
    joined = "\n".join(lines)
    assert "ไม่แสดงเลเวล" in joined or "คะแนน" in joined
    assert "เงา" in joined or "นักเดินทาง" in joined

    path = tmp_path / "default" / "rank_board.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "cards" in data
    assert all("score" not in c for c in data["cards"])
