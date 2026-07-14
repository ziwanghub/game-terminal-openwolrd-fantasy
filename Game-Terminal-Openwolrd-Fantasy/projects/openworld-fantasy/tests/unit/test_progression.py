from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.leveling import grant_xp
from game.domain.progression import (
    allocate_stat,
    ensure_progression,
    library_can_access,
    library_visit,
    grant_library_key,
    recompute_powers,
    try_occupation_rank_up,
)


def test_level_gives_stat_points():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "prog", "warrior", "สิงห์")
    before = int(p.get("stat_points", 0))
    grant_xp(p, 5000, reg.levels)
    assert int(p["stat_points"]) > before
    assert p["level"] > 1


def test_latent_differs_by_class():
    reg = DataRegistry.load(DATA_DIR)
    w = create_player(reg, "w", "warrior", "เมษ")
    m = create_player(reg, "m", "mage", "เมษ")
    for _ in range(10):
        allocate_stat(w, reg, "atk", 1)
        allocate_stat(m, reg, "atk", 1)
    # same points into atk — warrior latent higher → higher power_atk
    assert float(w["power_atk"]) > float(m["power_atk"])


def test_library_key_and_visit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "lib", "mage", "เมถุน")
    ok, _ = library_can_access(p, reg)
    # may be false at start
    grant_library_key(p)
    assert p["flags"].get("library_key_item")
    notes = library_visit(p, reg)
    assert notes
    assert len(p.get("library_entries_read") or []) >= 1


def test_occupations_have_ranks():
    reg = DataRegistry.load(DATA_DIR)
    assert "warrior" in reg.occupations
    assert reg.occupations["warrior"].get("ranks")
    assert getattr(reg, "unit_classes", None)
    assert "unit_eclipse" in reg.unit_classes
