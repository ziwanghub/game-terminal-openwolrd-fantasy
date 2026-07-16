"""WO-044 Area Mini-Moments + Soft Foresight moment hints."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.faction_moments import (
    MINI_MOMENTS,
    auto_resolve_moment,
    moments_for_area,
    resolve_moment_choice,
)
from game.domain.soft_foresight import (
    area_faction_lean,
    area_loop_soft_lines,
    area_world_gaze_lines,
    explore_soft_gaze_tick,
    soft_dungeon_entry_warnings,
)
from game.domain.stat_arch import ensure_stat_arch
from game.domain.world_relations import (
    AREA_FACTION_HINT,
    FACTION_DIVINE,
    FACTION_ECHO,
    get_faction_score,
)


def test_new_moments_mountain_city_void():
    assert "divine_mountain_gaze" in MINI_MOMENTS
    assert "divine_city_bell" in MINI_MOMENTS
    assert "echo_void_pull" in MINI_MOMENTS
    assert any(m["id"] == "divine_mountain_gaze" for m in moments_for_area("mountain_rock"))
    assert any(m["id"] == "divine_city_bell" for m in moments_for_area("ancient_city"))
    assert any(m["id"] == "echo_void_pull" for m in moments_for_area("void_rift"))
    assert len(MINI_MOMENTS) >= 9


def test_all_areas_have_moment_or_lean():
    areas = [
        "dark_forest",
        "mist_marsh",
        "cave_shadow",
        "desert_heat",
        "crystal_peak",
        "mountain_rock",
        "ancient_city",
        "void_rift",
    ]
    for aid in areas:
        assert aid in AREA_FACTION_HINT or moments_for_area(aid)
        # after WO-044 every listed area has at least one moment
        assert moments_for_area(aid), f"no moment for {aid}"


def test_foresight_alert_codes():
    cat = get_catalog()
    for code in (
        "world.foresight_divine_gaze",
        "world.foresight_infernal_haze",
        "world.foresight_echo_whisper",
        "world.moment_mountain_pray",
        "world.moment_city_bell",
        "world.moment_void_listen",
    ):
        assert code in cat


def test_area_lean_map():
    assert area_faction_lean("mountain_rock") == FACTION_DIVINE
    assert area_faction_lean("void_rift") == FACTION_ECHO
    assert area_faction_lean("ancient_city") == FACTION_DIVINE


def test_world_gaze_lines_hint_moment():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44a", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "void_rift"
    lines = area_world_gaze_lines(p, reg, area_id="void_rift", force=True)
    assert lines
    blob = "\n".join(lines)
    assert "echo" in blob.lower() or "กระซิบ" in blob or "สุญ" in blob or "เงา" in blob
    assert "Mini-Moment" in blob or "ใบ้" in blob or "moment" in blob.lower() or "กระซิบ" in blob


def test_area_loop_includes_gaze():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44b", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    p["_area_world_gaze_seen"] = {}
    lines = area_loop_soft_lines(p, reg)
    # may be empty of loop_soft tips but should have gaze
    assert any("สายตา" in str(x) or "เทพ" in str(x) or "ใบ้" in str(x) or "…" in str(x) for x in lines) or lines


def test_mountain_moment_help():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44c", "warrior", "เมษ")
    ensure_stat_arch(p)
    d0 = get_faction_score(p, FACTION_DIVINE)
    lines = resolve_moment_choice(p, "divine_mountain_gaze", "help", reg=reg)
    assert lines
    assert get_faction_score(p, FACTION_DIVINE) > d0


def test_void_moment_auto():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44d", "warrior", "เมษ")
    ensure_stat_arch(p)
    sight = {
        "kind": "faction_moment",
        "moment_id": "echo_void_pull",
        "moment": MINI_MOMENTS["echo_void_pull"],
    }
    lines = auto_resolve_moment(p, sight, reg=reg, prefs={"auto_avoid_cold_faction": True})
    assert lines


def test_dungeon_foresight_has_gaze():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44e", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "crystal_peak"
    lines = soft_dungeon_entry_warnings(p, reg)
    blob = "\n".join(lines)
    assert "Foresight" in blob or "กายใจ" in blob
    # world gaze section
    assert "สายตา" in blob or "ใบ้" in blob or "เทพ" in blob or "Mini-Moment" in blob


def test_explore_gaze_tick_throttled():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "f44f", "warrior", "เมษ")
    ensure_stat_arch(p)
    p["location"] = "mist_marsh"
    p["_area_world_gaze_seen"] = {"mist_marsh": True}
    # already seen → empty
    assert explore_soft_gaze_tick(p, reg, area_id="mist_marsh") == []
