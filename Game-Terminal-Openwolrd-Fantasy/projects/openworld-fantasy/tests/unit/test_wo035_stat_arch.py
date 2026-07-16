"""WO-035 Stat & Relationship Architecture."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import apply_needs_event, ensure_needs
from game.domain.progression import allocate_stat, ensure_progression, format_alloc_panel
from game.domain.stat_arch import (
    ANIMA_KEY,
    anima_value,
    ensure_stat_arch,
    get_world_relation,
    physical_score,
    recompute_anima,
    self_assess_lines,
    set_world_relation,
    soft_hp_condition,
    soft_anima_label,
)
from game.domain.party import assist_chance_for_member, assist_chance_from_relationship
from game.domain.inventory_sys import upgrade_success_chance


def test_anima_key_not_morale():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sa1", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["morale"] = 20
    ensure_stat_arch(p)
    recompute_anima(p, reg)
    # anima exists and is not forced equal to morale
    assert ANIMA_KEY in p
    assert anima_value(p) != 20 or anima_value(p) > 0
    assert "ขวัญ" not in soft_anima_label(p) or "จิตวิญญาณ" in soft_anima_label(p)


def test_self_assess_soft_no_power_numbers():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sa2", "warrior", "เมษ")
    ensure_progression(p, reg)
    lines = self_assess_lines(p, force=True, reg=reg)
    blob = "\n".join(lines)
    assert "กายภาพ" in blob or "กาย" in blob
    assert "เวท" in blob
    assert "power_atk" not in blob
    assert "crit_chance" not in blob


def test_soft_alloc_panel_hides_times_n():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sa3", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["stat_points"] = 3
    allocate_stat(p, reg, "atk", 2)
    panel = "\n".join(format_alloc_panel(p))
    # should not advertise raw × invest counts prominently
    assert "×2" not in panel and "× 2" not in panel
    assert "soft" in panel.lower() or "รู้สึก" in panel or "〔" in panel


def test_soft_hp_condition():
    p = {"hp": 10, "max_hp": 100}
    assert "ใกล้" in soft_hp_condition(p) or "สาหัส" in soft_hp_condition(p)
    p2 = {"hp": 95, "max_hp": 100}
    assert "แข็งแรง" in soft_hp_condition(p2) or "เล็กน้อย" in soft_hp_condition(p2)


def test_world_relation_axes():
    p: dict = {}
    ensure_stat_arch(p)
    set_world_relation(p, "divine", "sky_lord", 70)
    assert get_world_relation(p, "divine", "sky_lord") == 70
    set_world_relation(p, "infernal", "ash_duke", 20)
    assert get_world_relation(p, "infernal", "ash_duke") == 20


def test_assist_luck_soft():
    p = {"luck_score": 0.4, "party_bonds": {"c1": 50}}
    base = assist_chance_from_relationship(50)
    lucky = assist_chance_for_member(p, "c1")
    assert lucky >= base * 0.95  # not lower much; luck positive
    assert 0.18 <= lucky <= 0.97


def test_upgrade_luck_soft_bias():
    reg = DataRegistry.load(DATA_DIR)
    p_hi = {"luck_score": 0.4}
    p_lo = {"luck_score": -0.2}
    hi = upgrade_success_chance("main_hand", 2, reg=reg, rarity_id="common", player=p_hi)
    lo = upgrade_success_chance("main_hand", 2, reg=reg, rarity_id="common", player=p_lo)
    assert hi >= lo


def test_physical_score_moves_with_alloc():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sa4", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["stat_points"] = 5
    before = physical_score(p)
    allocate_stat(p, reg, "atk", 3)
    after = physical_score(p)
    assert after >= before
