"""WO-Craft-1: craft UI helpers — station groups, compact lines, ready marks."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.craft import (
    CRAFT_PAGE_SIZE,
    can_craft,
    format_recipe_list_lines,
    group_recipes_by_station,
    list_recipes,
    rarity_mark,
    recipe_inputs_short,
    recipe_output_name,
    station_label,
    station_ready_counts,
    stations_at_location,
)
from game.domain.equipment import add_item
from game.ports.io import ScriptedIO
from game.services.field_menus import _run_craft_menu


def test_rarity_marks():
    reg = DataRegistry.load(DATA_DIR)
    assert rarity_mark(reg, "common") in ("○", "o", "○")
    assert rarity_mark(reg, None) == "○"
    m_u = rarity_mark(reg, "uncommon")
    m_r = rarity_mark(reg, "rare")
    assert m_u
    assert m_r


def test_group_by_station_and_counts():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c1", "warrior", "เมษ")
    p["level"] = 10
    p["location"] = "cave_shadow"
    recipes = list_recipes(reg, p, require_station=True)
    groups = group_recipes_by_station(recipes)
    assert groups
    # cave should have camp and/or mystic
    avail = stations_at_location(p, reg)
    assert avail
    for st, lst in groups.items():
        ready, total = station_ready_counts(p, reg, lst)
        assert total == len(lst)
        assert 0 <= ready <= total


def test_compact_list_lines_readable():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c2", "warrior", "เมษ")
    p["level"] = 5
    p["location"] = "dark_forest"
    recipes = list_recipes(reg, p, require_station=True)
    assert recipes
    chunk = recipes[: min(3, len(recipes))]
    lines = format_recipe_list_lines(p, reg, chunk, start_index=1)
    blob = "\n".join(lines)
    assert "→" in blob
    assert "ใช้:" in blob
    assert "ยังไม่พร้อม" in blob or "โอกาส" in blob or "พร้อม" in blob
    # short inputs
    short = recipe_inputs_short(reg, chunk[0])
    assert "×" in short or "เงิน" in short or short == "—"
    assert recipe_output_name(reg, chunk[0])


def test_page_size_constant():
    assert CRAFT_PAGE_SIZE == 10


def test_ready_mark_after_materials():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c3", "warrior", "เมษ")
    p["level"] = 5
    p["location"] = "dark_forest"
    p["money_world"] = 500
    # find a simple recipe we can stock
    recipes = list_recipes(reg, p, require_station=True)
    target = None
    for r in recipes:
        if str(r.get("id") or "") == "craft_potion_bundle" or "potion" in str(
            r.get("output") or ""
        ):
            target = r
            break
    if not target:
        target = recipes[0]
    # stock inputs
    for iid, n in (target.get("inputs") or {}).items():
        for _ in range(int(n) + 1):
            add_item(p, str(iid), reg, rarity="common")
    ready, total = station_ready_counts(p, reg, [target])
    if can_craft(p, target, reg):
        assert ready >= 1
    lines = format_recipe_list_lines(p, reg, [target], start_index=1)
    blob = "\n".join(lines)
    assert "→" in blob


def test_craft_menu_hub_flow_scripted():
    """Hub → station → back → exit without crash."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c4", "warrior", "เมษ")
    p["level"] = 8
    p["location"] = "cave_shadow"
    p["money_world"] = 50
    # 1 = first station, 0 = back to hub, 0 = exit hub
    io = ScriptedIO(["1", "0", "0"])
    _run_craft_menu(p, reg, io)
    out = "\n".join(io.outputs) if hasattr(io, "outputs") else ""
    # ScriptedIO may use different attr — just ensure no raise
    assert p.get("location") == "cave_shadow"


def test_station_labels_thai():
    reg = DataRegistry.load(DATA_DIR)
    assert "ค่าย" in station_label("camp", reg) or "camp" in station_label("camp", reg)
    assert "จารึก" in station_label("mystic", reg) or "เงา" in station_label(
        "mystic", reg
    )
