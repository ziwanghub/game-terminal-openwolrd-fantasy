from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.world_social import (
    build_world_ranking,
    compute_affinity,
    format_ranking_lines,
    hidden_rank_score,
    other_as_combatant,
    resolve_social_outcome,
)
from game.services.save_service import save_player
from game.services.world_service import latest_save_meta, list_world_menu_rows
import random


def test_worlds_have_difficulty_labels():
    reg = DataRegistry.load(DATA_DIR)
    assert "social" not in reg.worlds
    for wid in ("default", "hardcore", "nightmare"):
        assert wid in reg.worlds
        assert reg.worlds[wid].get("difficulty_label")


def test_ranking_hides_level_and_power(tmp_path, monkeypatch):
    reg = DataRegistry.load(DATA_DIR)
    # use real saves dir lightly — just ensure format has no level numbers from our formatter
    lines = format_ranking_lines("default", reg)
    blob = "\n".join(lines)
    assert "ไม่แสดงเลเวล" in blob or "เลเวล" in blob  # header mentions no level
    # rows should not contain "Lv."
    for line in lines:
        if line.strip().startswith("#"):
            assert "Lv." not in line


def test_affinity_and_combatant():
    reg = DataRegistry.load(DATA_DIR)
    a = create_player(reg, "Alice", "warrior", "สิงห์", world_id="default")
    b = create_player(reg, "Bob", "warrior", "สิงห์", world_id="default")
    a["id"] = "id_a"
    b["id"] = "id_b"
    save_player(a)
    save_player(b)
    aff_polite = compute_affinity(a, b, reg, "polite", random.Random(1))
    aff_threat = compute_affinity(a, b, reg, "threaten", random.Random(1))
    # same seed components except approach — threaten should be lower
    assert aff_threat < aff_polite
    foe = other_as_combatant(b)
    assert "Bob" in foe["name"]  # W1: soft prefix เงา·
    assert foe["atk"] >= 1
    assert foe.get("is_player_echo")


def test_latest_save_and_menu():
    reg = DataRegistry.load(DATA_DIR)
    rows = list_world_menu_rows(reg)
    assert len(rows) >= 3
    # latest may exist after previous test saves
    meta = latest_save_meta("default")
    # no crash
    assert meta is None or "name" in meta


def test_world_picker_ui_readable():
    from game.services.world_service import format_world_picker_lines

    reg = DataRegistry.load(DATA_DIR)
    lines = format_world_picker_lines(reg)
    text = "\n".join(lines)
    assert "เลือกโลก" in text
    assert "1." in text
    assert "ความยาก" in text
    assert "พิมพ์ 1" in text
    assert len(list_world_menu_rows(reg)) >= 2
    assert "○" in text or "ปกติ" in text
