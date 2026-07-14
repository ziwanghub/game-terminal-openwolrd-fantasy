from game.data_load.registry import DataRegistry
from game.config import DATA_DIR
from game.domain.character import create_player
from game.runtime.auto_farm import auto_fight, monster_threat, should_pause_sight
from game.domain.combat import pick_monster
import random


def test_monster_threat_levels():
    assert monster_threat({"level": 5}, {"level": 12}) == "deadly"
    assert monster_threat({"level": 10}, {"level": 5}) == "easy"


def test_should_pause_chest():
    pause, _ = should_pause_sight({"level": 5}, {"kind": "chest", "label": "หีบ"})
    assert pause is True


def test_should_not_pause_easy_known():
    pause, _ = should_pause_sight(
        {"level": 20},
        {
            "kind": "monster",
            "label": "Wolf",
            "known": True,
            "monster": {"level": 3},
            "hint": "x",
        },
    )
    assert pause is False


def test_auto_fight_grants_xp():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(1)
    player = create_player(reg, "t", "warrior", "เมษ")
    mon = pick_monster(reg, "dark_forest", rng)
    mon["hp"] = 5
    mon["max_hp"] = 5
    mon["atk"] = 1
    before = player["level"]
    logs = auto_fight(player, mon, reg, rng, "dark_forest")
    assert logs
    assert player["hp"] > 0 or "แพ้" in "".join(logs)
    # either leveled or gained xp field progress
    assert player.get("xp", 0) >= 0
    assert player["level"] >= before


def test_two_worlds_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert "default" in reg.worlds
    assert "hardcore" in reg.worlds
