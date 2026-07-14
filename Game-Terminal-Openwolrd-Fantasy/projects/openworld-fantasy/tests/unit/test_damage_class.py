"""DD0–DD1 damage class + EL3 loadout soft bias."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.damage_class import (
    apply_class_mitigation,
    class_mitigation_mult,
    infer_damage_class_from_elements,
    outbound_power_bonus,
    resolve_damage_class,
)
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.progression import init_progression, recompute_powers


def test_registry_loads_damage_classes():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.damage_classes_cfg
    assert "classes" in reg.damage_classes_cfg or "element_to_class" in reg.damage_classes_cfg


def test_infer_elements():
    reg = DataRegistry.load(DATA_DIR)
    assert infer_damage_class_from_elements(["physical"], reg) == "physical"
    assert infer_damage_class_from_elements(["fire"], reg) == "arcane"
    assert infer_damage_class_from_elements(["shadow"], reg) == "dark"
    assert infer_damage_class_from_elements(["holy"], reg) == "light"


def test_skill_damage_class_explicit():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills.get("magic_missile") or {}
    assert resolve_damage_class(sk, reg=reg) == "arcane"
    sk2 = reg.skills.get("basic_strike") or {}
    assert resolve_damage_class(sk2, reg=reg) == "physical"
    sk3 = reg.skills.get("shadow_strike") or {}
    assert resolve_damage_class(sk3, reg=reg) == "dark"


def test_physical_vs_arcane_mitigation_differs():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "mit", "warrior", "กัน")
    init_progression(p, reg)
    # stack physical def, low magic
    p["stats_alloc"] = {"atk": 0, "defense": 12, "magic": 0, "speed": 0, "intelligence": 0}
    recompute_powers(p, reg)
    p["gear_def_bias"] = 0
    p["gear_mdef_bias"] = 0
    recompute_powers(p, reg)
    m_phys = class_mitigation_mult(p, "physical", reg)
    m_arc = class_mitigation_mult(p, "arcane", reg)
    # warrior with high def should mitigate physical better (or equal soft) than arcane
    assert m_phys <= m_arc + 0.02

    p2 = create_player(reg, "mit2", "mage", "เวท")
    init_progression(p2, reg)
    p2["stats_alloc"] = {"atk": 0, "defense": 0, "magic": 12, "speed": 0, "intelligence": 0}
    recompute_powers(p2, reg)
    m2_phys = class_mitigation_mult(p2, "physical", reg)
    m2_arc = class_mitigation_mult(p2, "arcane", reg)
    assert m2_arc <= m2_phys + 0.02


def test_apply_class_mitigation_reduces():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "red", "warrior", "ลด")
    init_progression(p, reg)
    p["power_def"] = 40.0
    p["power_mdef"] = 5.0
    dmg, fl = apply_class_mitigation(40, p, "physical", reg)
    assert dmg < 40
    assert dmg >= 0


def test_shield_raises_physical_def_bias():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sh", "warrior", "โล่")
    init_progression(p, reg)
    recompute_powers(p, reg)
    def0 = float(p.get("power_def") or 0)
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "wood_shield", reg)
    recompute_stats(p, reg)
    assert float(p.get("gear_def_bias") or 0) > 0
    assert float(p.get("power_def") or 0) > def0
    notes = p.get("loadout_soft_notes") or []
    assert any("โล่" in n for n in notes)


def test_dual_vs_shield_def_bias():
    reg = DataRegistry.load(DATA_DIR)
    # shield build
    p1 = create_player(reg, "s1", "warrior", "เอ")
    init_progression(p1, reg)
    add_item(p1, "iron_sword", reg)
    add_item(p1, "wood_shield", reg)
    equip_item(p1, "iron_sword", reg)
    equip_item(p1, "wood_shield", reg)
    recompute_stats(p1, reg)
    # dual build
    p2 = create_player(reg, "s2", "warrior", "บี")
    init_progression(p2, reg)
    add_item(p2, "iron_sword", reg)
    add_item(p2, "bandit_knife", reg)
    equip_item(p2, "iron_sword", reg)
    equip_item(p2, "bandit_knife", reg)
    recompute_stats(p2, reg)
    assert float(p1.get("gear_def_bias") or 0) > float(p2.get("gear_def_bias") or 0)
    assert float(p2.get("gear_atk_bias") or 0) >= float(p1.get("gear_atk_bias") or 0) - 0.5


def test_robe_mdef_bias():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "robe", "mage", "คลุม")
    init_progression(p, reg)
    recompute_powers(p, reg)
    m0 = float(p.get("power_mdef") or 0)
    add_item(p, "mage_robe", reg)
    equip_item(p, "mage_robe", reg)
    recompute_stats(p, reg)
    assert float(p.get("gear_mdef_bias") or 0) > 0
    assert float(p.get("power_mdef") or 0) >= m0


def test_outbound_arcane_uses_mag():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "out", "mage", "ยิง")
    init_progression(p, reg)
    p["power_mag"] = 30.0
    p["power_atk"] = 5.0
    b_arc = outbound_power_bonus(p, "arcane", reg)
    b_phys = outbound_power_bonus(p, "physical", reg)
    assert b_arc > b_phys
