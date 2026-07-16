import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import (
    advance_floor,
    apply_dungeon_enemy_mods,
    begin_dungeon,
    can_advance_floor,
    current_depth,
    dungeon_by_id,
    dungeons_for_area,
    exit_dungeon,
    explore_floor_event,
    format_dungeon_panel,
    get_run,
    in_dungeon,
    on_dungeon_boss_defeated,
    on_floor_boss_defeated,
    roll_dungeon_sight,
    set_boss_encounter,
    soft_difficulty_text,
    spawn_floor_boss,
    try_boss_combat_escape,
    try_escape,
)


def test_dungeons_load_and_per_area():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.dungeons_cfg
    assert dungeons_for_area(reg, "dark_forest")
    d = dungeon_by_id(reg, "dung_forest_root")
    assert d and d.get("difficulty")


def test_v2_enter_free_exit_no_lock():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dg", "warrior", "เมษ")
    p["inventory_ids"] = []
    notes = begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    assert in_dungeon(p)
    assert any("เดินออก" in n or "ผู้เฝ้า" in n for n in notes)
    run = get_run(p)
    assert run and run.get("locked") is False
    assert run.get("ruleset") == "v2"
    assert run.get("depth") == 1
    assert int(run.get("max_depth_hidden") or 0) >= 2
    # free exit
    out = exit_dungeon(p, reg, success=True)
    assert not in_dungeon(p)
    assert any("ออก" in o or "กลับ" in o for o in out)


def test_boss_encounter_blocks_exit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "blk", "mage", "เมถุน")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(0))
    set_boss_encounter(p, True)
    out = exit_dungeon(p, reg, success=True)
    assert in_dungeon(p)
    assert any("บอส" in o or "วง" in o for o in out)
    set_boss_encounter(p, False)
    out2 = try_escape(p, reg, random.Random(1))
    assert not in_dungeon(p)


def test_floor_boss_gates_advance():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "gate", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(2))
    ok0, msg0 = can_advance_floor(p)
    assert not ok0
    assert "ผู้เฝ้า" in msg0 or "มืด" in msg0 or "ขวาง" in msg0
    notes = on_floor_boss_defeated(p, reg, random.Random(3), mon={"dungeon_floor_boss": True})
    assert any("ทางลง" in n or "ผู้เฝ้า" in n for n in notes)
    ok1, _ = can_advance_floor(p)
    # may be blocked if at max depth after clear on last floor — depth 1 usually not max
    run = get_run(p)
    if current_depth(run) < int(run.get("max_depth_hidden") or 2):
        assert ok1
        adv = advance_floor(p, reg, random.Random(4))
        assert any("ลงลึก" in a or "ชั้น" in a for a in adv)
        run2 = get_run(p)
        assert current_depth(run2) == 2
        assert run2.get("floor_boss_cleared") is False


def test_heart_boss_clear_rewards():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "clr", "warrior", "เมษ")
    p["money_world"] = 0
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    notes = on_dungeon_boss_defeated(p, reg, random.Random(42))
    assert any("หัวใจ" in n or "บอส" in n or "รางวัล" in n or "XP" in n or "+" in n for n in notes)
    assert get_run(p).get("boss_defeated") is True
    assert get_run(p).get("locked") is False
    out = exit_dungeon(p, reg, success=True)
    assert not in_dungeon(p)
    assert "dung_forest_root" in (p.get("dungeons_cleared") or [])


def test_depth_scales_monster():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sc", "rogue", "พิจิก")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    mon = {"hp": 100, "max_hp": 100, "atk": 10, "level": 3, "xp_mult": 1.0, "attack_profiles": []}
    m1 = apply_dungeon_enemy_mods(dict(mon), p)
    run = get_run(p)
    p["dungeon_run"] = {**run, "depth": 4, "floor": 4}
    m4 = apply_dungeon_enemy_mods(dict(mon), p)
    assert m4["hp"] > m1["hp"]
    assert m4["level"] > m1["level"]
    assert float(m4["xp_mult"]) > float(m1["xp_mult"])


def test_spawn_floor_boss_and_shard_escape():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sp", "priest", "มีน")
    from game.domain.equipment import add_item

    add_item(p, "dungeon_thread", reg, rarity="rare")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(5))
    boss = spawn_floor_boss(p, reg, random.Random(5))
    assert boss and boss.get("dungeon_floor_boss")
    assert boss.get("never_flee")
    set_boss_encounter(p, True)
    # force success by many seeds
    escaped = False
    for seed in range(50):
        p2 = create_player(reg, f"sh{seed}", "mage", "เมถุน")
        add_item(p2, "dungeon_thread", reg, rarity="rare")
        begin_dungeon(p2, reg, "dung_forest_root", random.Random(seed))
        set_boss_encounter(p2, True)
        left, notes = try_boss_combat_escape(p2, reg, random.Random(seed + 99))
        if left:
            escaped = True
            assert in_dungeon(p2)
            assert get_run(p2).get("boss_encounter_active") is False
            assert get_run(p2).get("floor_boss_cleared") is not True
            break
    assert escaped


def test_panel_hides_max_depth():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ui", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    lines = format_dungeon_panel(p, reg)
    text = "\n".join(lines)
    assert "ลงมาชั้นที่" in text
    assert "ทางออก" in text and "เปิด" in text
    # must not show 1/N style max
    run = get_run(p)
    mx = run.get("max_depth_hidden")
    assert f"/{mx}" not in text


def test_soft_difficulty_hidden_then_reveals():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "kn", "rogue", "พิจิก")
    d = dungeon_by_id(reg, "dung_void_maw")
    t0 = soft_difficulty_text(p, reg, d)
    assert "สุดขีด" not in t0
    p["dungeon_knowledge"] = {"dung_void_maw": {"visits": 5, "clears": 1, "fails": 0, "escapes": 0}}
    t1 = soft_difficulty_text(p, reg, d)
    assert "สุดขีด" in t1 or "เคลียร์" in t1 or len(t1) >= len(t0)


def test_sight_can_roll_dungeon():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "si", "priest", "มีน")
    p["location"] = "dark_forest"
    found = False
    for seed in range(80):
        s = roll_dungeon_sight(p, reg, random.Random(seed), "dark_forest")
        if s:
            assert s.get("kind") == "dungeon"
            assert s.get("dungeon_id")
            found = True
            break
    assert found


def test_floor_layout_and_explore():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.dungeon import compute_time_limit, generate_floor_layout, tick_dungeon_time

    d = dungeon_by_id(reg, "dung_forest_root")
    assert compute_time_limit(reg, d) >= 8
    lay = generate_floor_layout(reg, d, 1, random.Random(1))
    assert lay.get("label")
    p = create_player(reg, "fl", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    run = get_run(p)
    assert run.get("floor_layout")
    assert run.get("time_collapse_enabled") is False
    ev = explore_floor_event(p, reg, random.Random(3))
    assert ev.get("kind")
    # time tick does nothing when disabled
    notes = tick_dungeon_time(p, reg, random.Random(1), cost=1)
    assert notes == []


def test_clear_rewards_granted_once():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rw", "warrior", "เมษ")
    p["money_world"] = 0
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    notes = on_dungeon_boss_defeated(p, reg, random.Random(42))
    assert any("รางวัล" in n or "XP" in n or "เงิน" in n or "+" in n for n in notes)
    assert get_run(p).get("rewards_granted") is True
    notes2 = on_dungeon_boss_defeated(p, reg, random.Random(42))
    assert notes2 == [] or not any("รางวัลดันเจียน" in n for n in notes2)
