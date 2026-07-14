import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import (
    begin_dungeon,
    dungeon_by_id,
    dungeons_for_area,
    exit_dungeon,
    get_run,
    in_dungeon,
    on_dungeon_boss_defeated,
    roll_dungeon_sight,
    soft_difficulty_text,
    try_escape,
)


def test_dungeons_load_and_per_area():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.dungeons_cfg
    assert dungeons_for_area(reg, "dark_forest")
    d = dungeon_by_id(reg, "dung_forest_root")
    assert d and d.get("difficulty")


def test_enter_locks_and_escape_without_item_fails():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dg", "warrior", "เมษ")
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    p["inventory"] = []
    notes = begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    assert in_dungeon(p)
    assert any("เข้า" in n or "ราก" in n for n in notes)
    run = get_run(p)
    assert run and run.get("locked") is True
    # free exit blocked
    out = exit_dungeon(p, reg, success=True)
    assert any("ล็อก" in o for o in out)
    assert in_dungeon(p)
    # escape without token drains / stays
    esc = try_escape(p, reg, random.Random(2))
    assert any("ปิด" in e or "เคลียร์" in e or "ทรัพยากร" in e for e in esc)


def test_escape_with_item_may_work():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "esc", "mage", "เมถุน")
    from game.domain.equipment import add_item

    add_item(p, "dungeon_thread", reg, rarity="rare")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(0))
    assert get_run(p).get("escape_ready")
    # force success by many tries or patch chance
    escaped = False
    for seed in range(40):
        p2 = create_player(reg, f"e{seed}", "mage", "เมถุน")
        add_item(p2, "dungeon_thread", reg, rarity="rare")
        begin_dungeon(p2, reg, "dung_forest_root", random.Random(seed))
        notes = try_escape(p2, reg, random.Random(seed + 99))
        if not in_dungeon(p2):
            escaped = True
            assert any("รอด" in n or "ออก" in n or "ฉีก" in n for n in notes)
            break
    assert escaped


def test_boss_clear_unlocks_exit():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "clr", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    notes = on_dungeon_boss_defeated(p, reg)
    assert any("เปิด" in n or "บอส" in n for n in notes)
    assert get_run(p).get("locked") is False
    out = exit_dungeon(p, reg, success=True)
    assert not in_dungeon(p)
    assert "dung_forest_root" in (p.get("dungeons_cleared") or [])


def test_soft_difficulty_hidden_then_reveals():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "kn", "rogue", "พิจิก")
    d = dungeon_by_id(reg, "dung_void_maw")
    t0 = soft_difficulty_text(p, reg, d)
    assert "สุดขีด" not in t0  # not accurate yet
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


def test_floor_layout_and_time_limit():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.dungeon import (
        compute_time_limit,
        explore_floor_event,
        generate_floor_layout,
        tick_dungeon_time,
    )

    d = dungeon_by_id(reg, "dung_forest_root")
    assert compute_time_limit(reg, d) >= 8
    lay = generate_floor_layout(reg, d, 1, random.Random(1))
    assert lay.get("label")
    p = create_player(reg, "fl", "warrior", "เมษ")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    run = get_run(p)
    assert run.get("floor_layout")
    assert run.get("turns_left") == run.get("turns_max")
    ev = explore_floor_event(p, reg, random.Random(3))
    assert ev.get("kind")
    # burn time until warn or collapse
    p2 = create_player(reg, "tm", "mage", "เมถุน")
    begin_dungeon(p2, reg, "dung_forest_root", random.Random(0))
    # force low turns
    r = get_run(p2)
    p2["dungeon_run"] = {**r, "turns_left": 1}
    notes = tick_dungeon_time(p2, reg, random.Random(1), cost=1)
    assert any("ยุบ" in n or "เหวี่ยง" or "ออก" in n for n in notes) or not in_dungeon(p2)


def test_clear_rewards_granted_once():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rw", "warrior", "เมษ")
    p["money_world"] = 0
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    before = int(p.get("money_world") or 0)
    notes = on_dungeon_boss_defeated(p, reg, random.Random(42))
    assert any("รางวัล" in n or "XP" in n or "เงิน" in n or "+" in n for n in notes)
    assert get_run(p).get("rewards_granted") is True
    # second call no double dip
    notes2 = on_dungeon_boss_defeated(p, reg, random.Random(42))
    assert notes2 == [] or not any("รางวัลดันเจียน" in n for n in notes2)
