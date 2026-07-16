"""Combat party report + deeper dungeon + rest/shop hooks."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import (
    begin_dungeon,
    dungeon_menu_actions,
    dungeon_rest,
    get_run,
    has_dungeon_stealth,
    roll_max_depth,
    dungeon_by_id,
)
from game.domain.equipment import add_item
from game.domain.narrative import situation_strip
from game.domain.party import add_member, member_from_template, template_by_id
from game.ui_terminal.status import render_combat_vitals


def test_combat_vitals_shows_party():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cv", "warrior", "เมษ")
    tpl = template_by_id(reg, "spirit_leaf")
    add_member(p, member_from_template(tpl, reg, random.Random(1)), reg)
    mon = {"name": "Wolf", "hp": 40, "max_hp": 80, "statuses": [], "boss": False}
    text = render_combat_vitals(p, mon, known=True, round_no=2)
    assert "ทีมร่วม" in text
    assert "ภูต" in text or "spirit" in text.lower() or "ใบไม้" in text
    sit = situation_strip(p, mon, known=True, reg=reg)
    assert "ทีม:" in sit


def test_dungeon_deeper_than_before():
    reg = DataRegistry.load(DATA_DIR)
    d = dungeon_by_id(reg, "dung_forest_root")
    depths = [roll_max_depth(reg, d, random.Random(i)) for i in range(40)]
    assert min(depths) >= 4
    assert max(depths) >= 5


def test_dungeon_menu_bag_shop_rest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dm", "mage", "เมถุน")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    text = "\n".join(dungeon_menu_actions(p))
    assert "กระเป๋า" in text
    assert "ร้าน" in text
    assert "พัก" in text or "นอน" in text
    assert get_run(p).get("max_depth_hidden", 0) >= 4


def test_dungeon_rest_heals_and_stealth():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rs", "rogue", "พิจิก")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(2))
    p["hp"] = 20
    p["mana"] = 5
    r = dungeon_rest(p, reg, random.Random(1))
    assert p["hp"] > 20
    assert p["mana"] > 5
    assert r.get("notes")
    # stealth item lowers ambush (still random — just ensure API)
    add_item(p, "shadow_cloak", reg)
    assert has_dungeon_stealth(p)
