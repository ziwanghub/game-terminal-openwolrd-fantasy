from game.data_load.registry import DataRegistry
from game.config import DATA_DIR


def test_load_registry():
    reg = DataRegistry.load(DATA_DIR)
    assert "dark_forest" in reg.areas
    assert "shadow_wraith" in reg.monsters
    assert "fire_ball" in reg.skills
    assert len(reg.occupations) >= 5


def test_element_mult():
    reg = DataRegistry.load(DATA_DIR)
    m = reg.element_mult(["water"], ["fire"])
    assert m > 1.0
