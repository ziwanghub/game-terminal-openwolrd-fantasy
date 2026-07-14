from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.skill_charges import is_skill_usable, set_lease, spend_charges
from game.domain.skill_tree import (
    check_learn_conditions,
    has_prereqs,
    learn_skill,
    list_visible_tree_nodes,
    teach_from_master,
)


def test_registry_loads_many_skills_and_masters():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.skills) >= 50
    assert "warrior_cleave" in reg.skills
    assert "master_steel" in reg.skill_masters
    assert reg.skills["basic_strike"].get("tree") == "warrior"


def test_prereq_blocks_learn():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t1", "warrior", "เมษ")
    # warrior_whirl needs warrior_cleave
    assert not has_prereqs(p, reg.skills["warrior_whirl"])
    ok, hints = check_learn_conditions(p, reg, "warrior_whirl")
    assert not ok
    assert hints


def test_learn_with_money_and_prereq():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t2", "warrior", "เมษ")
    p["level"] = 10
    p["money_world"] = 500
    assert "basic_strike" in p["skills"]
    msg = learn_skill(p, reg, "warrior_cleave")
    assert "กวาดฟัน" in msg or "เรียนรู้" in msg
    assert "warrior_cleave" in p["skills"]
    assert int(p["money_world"]) < 500


def test_master_lease_and_spend():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t3", "warrior", "เมษ")
    p["level"] = 15
    p["money_world"] = 1000
    p["skills"] = list(p["skills"]) + ["counter_guard"]
    msg = teach_from_master(p, reg, "master_steel", "master_steel_lesson")
    assert "10" in msg or "ครั้ง" in msg
    assert is_skill_usable(p, "master_steel_lesson")
    for _ in range(10):
        spend_charges(p, ["master_steel_lesson"])
    assert not is_skill_usable(p, "master_steel_lesson")
    # renew via teach again
    msg2 = teach_from_master(p, reg, "master_steel", "master_steel_lesson")
    assert is_skill_usable(p, "master_steel_lesson")
    assert "เติม" in msg2 or "ครั้ง" in msg2


def test_tree_visible_nodes_for_starter():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t4", "mage", "เมถุน")
    nodes = list_visible_tree_nodes(p, reg)
    # should see owned roots and some available T2
    statuses = {n["_status"] for n in nodes}
    assert "owned" in statuses
    ids = {n["id"] for n in nodes}
    assert "magic_missile" in ids


def test_set_lease_helper():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "t5", "rogue", "พิจิก")
    set_lease(p, "smoke_step", 3, source="test")
    assert is_skill_usable(p, "smoke_step")
    spend_charges(p, ["smoke_step", "smoke_step", "smoke_step"])
    assert not is_skill_usable(p, "smoke_step")
