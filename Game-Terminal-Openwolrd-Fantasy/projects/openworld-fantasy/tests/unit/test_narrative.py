import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.narrative import (
    damage_band,
    narrate,
    narrate_battle_open,
    narrate_damage_in,
    narrate_damage_out,
    narrate_player_action,
    situation_strip,
    status_display_name,
)


def test_narrative_loads():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.narrative
    assert reg.narrative.get("enabled") is True
    assert "player_skill" in reg.narrative


def test_narrate_skill_and_damage():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(1)
    lines = narrate_player_action(
        reg, "skill", rng, skill="ลูกไฟ", enemy="หมาป่า"
    )
    assert lines
    assert any("ลูกไฟ" in x or "ปล่อย" in x or "ท่า" in x for x in lines)

    out = narrate_damage_out(reg, 40, 100, "หมาป่า", rng, elements=["fire"])
    assert out
    assert any("40" in x or "หมาป่า" in x for x in out)

    inn = narrate_damage_in(
        reg, 15, 100, "หมาป่า", rng, guard_grade="strong", guard_skill_name="ม่านน้ำ"
    )
    assert inn


def test_damage_bands():
    reg = DataRegistry.load(DATA_DIR)
    assert damage_band(2, 100, reg) == "scratch"
    assert damage_band(20, 100, reg) == "solid"
    assert damage_band(80, 100, reg) in ("heavy", "devastating")


def test_battle_open_and_status_names():
    reg = DataRegistry.load(DATA_DIR)
    lines = narrate_battle_open(reg, "ราชาป่า", random.Random(0), boss=True)
    assert lines
    assert status_display_name("poison", reg) == "พิษ"


def test_situation_strip():
    reg = DataRegistry.load(DATA_DIR)
    p = {"hp": 20, "max_hp": 100, "statuses": [{"id": "poison"}], "blessings": ["พร"]}
    m = {"hp": 10, "max_hp": 100, "statuses": [{"id": "freeze"}]}
    s = situation_strip(p, m, known=True, reg=reg)
    assert "พิษ" in s or "คุณ" in s
    assert "แช่แข็ง" in s or "ศัตรู" in s


def test_field_narrative_merged():
    reg = DataRegistry.load(DATA_DIR)
    assert "field_rest" in reg.narrative
    assert "field_explore" in reg.narrative
    assert "area_mood_dark_forest" in reg.narrative
    from game.domain.narrative import area_mood, narrate_field

    lines = narrate_field(reg, "rest", random.Random(1), area_id="dark_forest")
    assert lines
    assert any("พัก" in x or "ลม" in x or "dark" in x.lower() or "ป่า" in x or "กล้ามเนื้อ" in x for x in lines)
    mood = area_mood(reg, "void_rift", random.Random(2))
    assert mood
