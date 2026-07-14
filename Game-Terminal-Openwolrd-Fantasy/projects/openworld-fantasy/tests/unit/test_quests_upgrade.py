from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, upgrade_equipped, count_materials
from game.domain.quests import bump_quest, ensure_quests, list_quest_lines


def test_quest_kill_progress_and_complete():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "q", "warrior", "เมษ")
    ensure_quests(p, reg)
    assert "first_blood" in p["quests"]
    notes = []
    for _ in range(3):
        notes.extend(bump_quest(p, reg, "kill", area_id="dark_forest"))
    assert "first_blood" in p["quests_done"]
    assert any("สำเร็จ" in n for n in notes)


def test_upgrade_consumes_mats():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "u", "warrior", "สิงห์")
    add_item(p, "iron_sword", reg)
    equip_item(p, "iron_sword", reg)
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    p["money_world"] = 500
    before = int(p["bonus_atk"])
    msg = upgrade_equipped(p, "weapon", reg)
    assert "สำเร็จ" in msg
    assert int(p["upgrade_levels"]["weapon"]) == 1
    assert int(p["bonus_atk"]) > before
    assert count_materials(p, "upgrade_mat") < 3


def test_quests_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.quests) >= 5
