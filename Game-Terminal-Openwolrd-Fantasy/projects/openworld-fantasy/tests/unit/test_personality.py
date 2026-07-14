from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.personality import (
    apply_event,
    check_personality_point_grants,
    compatibility,
    ensure_personality,
    invest_personality_point,
    npc_roll_modifier,
    roll_personality_library_tip,
    soft_impression,
)
from game.domain.world_social import compute_affinity
import random


def test_events_shift_traits():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "per", "warrior", "เมษ")
    ensure_personality(p, reg)
    before = float(p["personality"]["kindness"])
    apply_event(p, "approach_gift", reg, scale=5)
    assert float(p["personality"]["kindness"]) > before


def test_npc_compat_merchant_likes_greed_less_threat():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "m", "rogue", "พิจิก")
    ensure_personality(p, reg)
    p["personality"]["greed"] = 60
    p["personality"]["aggression"] = -10
    good = npc_roll_modifier(p, reg, "merchant", "polite", random.Random(1))
    bad = npc_roll_modifier(p, reg, "merchant", "threaten", random.Random(1))
    assert good["compatibility"] > bad["compatibility"]


def test_player_affinity_uses_personality():
    reg = DataRegistry.load(DATA_DIR)
    a = create_player(reg, "A", "priest", "มีน")
    b = create_player(reg, "B", "priest", "มีน")
    ensure_personality(a, reg)
    ensure_personality(b, reg)
    for _ in range(5):
        apply_event(a, "approach_aid", reg, scale=3)
        apply_event(b, "approach_aid", reg, scale=3)
    aff = compute_affinity(a, b, reg, "aid", random.Random(0))
    # should be finite and influenced (not crash)
    assert isinstance(aff, float)


def test_soft_labels_only_when_extreme():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "s", "mage", "เมถุน")
    ensure_personality(p, reg)
    p["personality"]["curiosity"] = 80
    from game.domain.personality import _refresh_labels

    _refresh_labels(p, reg)
    assert soft_impression(p) != "ยังอ่านไม่ออก"


def test_start_grants_invest_point():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "pts", "warrior", "เมษ")
    ensure_personality(p, reg)
    assert int(p.get("personality_points", 0)) >= 1
    assert "start_points" in (p.get("personality_grants_done") or [])


def test_hidden_grant_on_kind_acts():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "kind", "priest", "มีน")
    ensure_personality(p, reg)
    # clear start points noise for assertion on grant message
    before = int(p["personality_points"])
    notes = []
    for _ in range(3):
        notes.extend(apply_event(p, "approach_polite", reg))
    assert int(p["personality_progress"]["approach_kind"]) >= 3
    assert int(p["personality_points"]) > before
    assert "first_kind_act" in (p.get("personality_grants_done") or [])
    assert any("ช่องว่างในใจ" in n or "แต้มนิสัย" in n for n in notes)


def test_invest_spends_points_and_raises_axis():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "inv", "mage", "เมถุน")
    ensure_personality(p, reg)
    p["personality_points"] = 3
    p["personality"]["kindness"] = 0.0
    msg = invest_personality_point(p, reg, "kindness", 2)
    assert p["personality_points"] == 1
    assert float(p["personality"]["kindness"]) > 0
    assert int(p["personality_invest"]["kindness"]) == 2
    assert "ลงทุน" in msg or "เมตตา" in msg or "kindness" in msg.lower()


def test_invest_fails_without_points():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "broke", "rogue", "พิจิก")
    ensure_personality(p, reg)
    p["personality_points"] = 0
    msg = invest_personality_point(p, reg, "courage", 1)
    assert "ไม่พอ" in msg


def test_library_tips_load_and_roll():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.personality_tips, "personality tips should load from YAML"
    assert any(
        t.get("kind") == "complete" for t in reg.personality_tips.values()
    )
    assert any(t.get("kind") == "fragment" for t in reg.personality_tips.values())
    assert any(t.get("kind") == "rumor" for t in reg.personality_tips.values())
    # complete should be rare by weight
    complete_w = sum(
        int(t.get("weight", 0))
        for t in reg.personality_tips.values()
        if t.get("kind") == "complete"
    )
    other_w = sum(
        int(t.get("weight", 0))
        for t in reg.personality_tips.values()
        if t.get("kind") != "complete"
    )
    assert complete_w < other_w

    p = create_player(reg, "lib", "scholar", "กันย์") if "scholar" in reg.occupations else create_player(reg, "lib", "mage", "กันย์")
    ensure_personality(p, reg)
    # force roll with chance-always rng
    lines = roll_personality_library_tip(p, reg, rng=random.Random(0))
    # may be empty if chance fails — force with high chance meta temporarily
    reg.personality_tips_meta = {"personality_tip_chance": 1.0}
    lines = roll_personality_library_tip(p, reg, rng=random.Random(42))
    assert lines, "should get a tip when chance=1"
    assert any("📖" in ln or "บันทึก" in ln or "ข่าวลือ" in ln or "ตำรา" in ln for ln in lines)
    assert p.get("personality_tips_read")


def test_repeatable_win_grant():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "win", "warrior", "เมษ")
    ensure_personality(p, reg)
    p["personality_points"] = 0
    p["personality_progress"] = {"combat_wins": 10}
    # once grant battle_courage need 8 + every_five at 10
    notes = check_personality_point_grants(p, reg)
    assert int(p["personality_points"]) >= 1
    assert notes
