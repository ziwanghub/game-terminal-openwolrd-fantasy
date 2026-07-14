
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import apply_world_enemy_mods, pick_monster
from game.domain.stats import bump_stat, ensure_stats, format_stats_lines
from game.services.save_service import export_player, import_player, load_player
import random


def test_three_worlds():
    reg = DataRegistry.load(DATA_DIR)
    assert set(reg.worlds) >= {"default", "hardcore", "nightmare"}


def test_hardcore_start_money_and_mods():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "h", "warrior", "เมษ", world_id="hardcore")
    assert p["world_modifiers"]["enemy_hp_mult"] > 1.0
    assert p["money_world"] < 150


def test_enemy_mods_scale_hp():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "m", "warrior", "เมษ", world_id="nightmare")
    mon = pick_monster(reg, "dark_forest", random.Random(1))
    base_hp = mon["hp"]
    mon2 = apply_world_enemy_mods(mon, p)
    assert mon2["hp"] > base_hp


def test_stats_and_export(tmp_path):
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s", "mage", "เมถุน", world_id="default")
    ensure_stats(p)
    bump_stat(p, "kills", 3)
    lines = format_stats_lines(p)
    assert any("ฆ่ามอน 3" in x for x in lines)
    path = export_player(p, dest=tmp_path / "exp.json")
    assert path.is_file()
    data = load_player(str(path))
    assert data["stats"]["kills"] == 3
