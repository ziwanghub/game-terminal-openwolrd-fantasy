"""EQ-W weight · EQ-G stance · EQ-A climate×material · N5 soft flags."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.loadout_context import (
    area_climates,
    bump_stance_meter,
    detect_stance,
    loadout_combat_mults,
    on_combat_victory_stance,
    recompute_loadout_context,
    soft_weight_label,
    weight_class_from_score,
)
from game.domain.needs import (
    combat_needs_mults,
    note_n5_hunger_survived,
    note_n5_morale_boss,
)


def test_weight_class_thresholds():
    assert weight_class_from_score(5) == "light"
    assert weight_class_from_score(10) == "medium"
    assert weight_class_from_score(15) == "heavy"


def test_heavy_plate_shield_weight():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w1", "warrior", "หนัก")
    add_item(p, "iron_sword", reg)
    add_item(p, "iron_plate", reg)
    add_item(p, "iron_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "iron_plate", reg)
    equip_item(p, "iron_shield", reg)
    recompute_stats(p, reg)
    assert p.get("weight_class") == "heavy"
    assert "หนัก" in soft_weight_label(p) or soft_weight_label(p) == "ก้าวหนัก"


def test_light_robe_weight():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w2", "mage", "เบา")
    add_item(p, "mage_robe", reg)
    equip_item(p, "mage_robe", reg)
    recompute_stats(p, reg)
    assert p.get("weight_class") in ("light", "medium")


def test_stance_shield_detect():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "st", "warrior", "โล่")
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "wood_shield", reg)
    assert detect_stance(p, reg) == "one_hand_shield"


def test_stance_two_hand_detect():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "2h", "warrior", "สอง")
    add_item(p, "oak_greatsword", reg)
    equip_item(p, "oak_greatsword", reg)
    assert detect_stance(p, reg) == "two_hand"


def test_stance_meter_improves_mult():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "aff", "warrior", "ชิน")
    add_item(p, "oak_greatsword", reg)
    equip_item(p, "oak_greatsword", reg)
    recompute_loadout_context(p, reg)
    p["stance_meters"] = {"two_hand": 10, "one_hand": 25, "dual": 25, "one_hand_shield": 25, "focus": 25}
    recompute_loadout_context(p, reg)
    low = float(p.get("stance_combat_mult") or 1)
    for _ in range(12):
        bump_stance_meter(p, "two_hand", amount=8)
    recompute_loadout_context(p, reg)
    high = float(p.get("stance_combat_mult") or 1)
    assert high >= low


def test_victory_trains_stance():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "vic", "warrior", "ชนะ")
    add_item(p, "iron_sword", reg)
    add_item(p, "wood_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "wood_shield", reg)
    recompute_loadout_context(p, reg)
    before = float((p.get("stance_meters") or {}).get("one_hand_shield") or 0)
    on_combat_victory_stance(p, reg)
    after = float((p.get("stance_meters") or {}).get("one_hand_shield") or 0)
    assert after > before


def test_areas_have_climate():
    reg = DataRegistry.load(DATA_DIR)
    cl = area_climates(reg, "mist_marsh")
    assert "wet" in cl or "cold" in cl
    cl2 = area_climates(reg, "desert_heat")
    assert "hot" in cl2 or "arid" in cl2


def test_metal_in_wet_climate_note():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "wet", "warrior", "ชื้น")
    p["location"] = "mist_marsh"
    add_item(p, "iron_sword", reg)
    add_item(p, "iron_plate", reg)
    add_item(p, "iron_shield", reg)
    equip_item(p, "iron_sword", reg)
    equip_item(p, "iron_plate", reg)
    equip_item(p, "iron_shield", reg)
    recompute_loadout_context(p, reg, area_id="mist_marsh")
    notes = " ".join(p.get("climate_soft_notes") or [])
    # metal + wet should produce soft note
    assert "ชื้น" in notes or "สนิม" in notes or float((p.get("climate_mults") or {}).get("atb") or 1) < 1.0


def test_heavy_hungry_worse_than_light():
    reg = DataRegistry.load(DATA_DIR)
    heavy = create_player(reg, "h", "warrior", "หิวหนัก")
    light = create_player(reg, "l", "mage", "หิวเบา")
    for p, gear in (
        (heavy, ("iron_sword", "iron_plate", "iron_shield")),
        (light, ("mage_robe",)),
    ):
        for g in gear:
            add_item(p, g, reg)
            equip_item(p, g, reg)
        p["needs"] = {"hunger": 92, "fatigue": 85, "morale": 50}
        recompute_stats(p, reg)
    mh = loadout_combat_mults(heavy)
    ml = loadout_combat_mults(light)
    # heavy + หิว/ล้า → ATB ช้ากว่าชุดเบาชัด
    assert mh["atb_mult"] < ml["atb_mult"]
    assert mh["incoming_mult"] >= ml["incoming_mult"]


def test_n5_hunger_flag():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n5", "warrior", "อด")
    notes = note_n5_hunger_survived(p)
    assert notes
    assert (p.get("flags") or {}).get("n5_hunger_memory")
    # second time silent
    assert note_n5_hunger_survived(p) == []


def test_n5_reduces_hunger_atk_penalty():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n5b", "warrior", "จำ")
    p["needs"] = {"hunger": 95, "fatigue": 20, "morale": 70}
    m0 = combat_needs_mults(p)["atk_mult"]
    note_n5_hunger_survived(p)
    m1 = combat_needs_mults(p)["atk_mult"]
    assert m1 >= m0


def test_n5_morale_boss():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "n5c", "warrior", "ใจ")
    p["needs"] = {"hunger": 20, "fatigue": 20, "morale": 5}  # crit
    notes = note_n5_morale_boss(p)
    assert notes
    assert (p.get("flags") or {}).get("n5_unbroken_heart")
