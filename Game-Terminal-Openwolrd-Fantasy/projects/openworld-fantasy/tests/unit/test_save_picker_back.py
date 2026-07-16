"""Character save picker: filter system JSON + 0 = back UX."""
from __future__ import annotations

import json
from pathlib import Path

from game.config import SAVES_DIR
from game.services.save_service import list_saves
from game.services.world_service import format_save_picker_lines


def test_list_saves_skips_world_system_files(tmp_path, monkeypatch):
    world = tmp_path / "w1"
    world.mkdir()
    # player
    (world / "p_hero.json").write_text(
        json.dumps(
            {
                "id": "p_hero",
                "name": "Hero",
                "level": 2,
                "location": "dark_forest",
                "occupation": "นักรบ",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # system noise
    for stem in ("market", "rank_board", "world_meta", "world_signals"):
        (world / f"{stem}.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path)
    saves = list_saves("w1")
    assert len(saves) == 1
    assert saves[0]["name"] == "Hero"
    assert all(s["name"] not in ("market", "rank_board") for s in saves)


def test_format_save_picker_shows_back_option(tmp_path, monkeypatch):
    world = tmp_path / "w2"
    world.mkdir()
    (world / "p_a.json").write_text(
        json.dumps(
            {
                "id": "p_a",
                "name": "Alice",
                "level": 1,
                "location": "dark_forest",
                "occupation": "นักรบ",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path)
    text = "\n".join(format_save_picker_lines("w2", "ทดสอบ"))
    assert "Alice" in text
    assert "0" in text and "ย้อนกลับ" in text
    assert "market" not in text
