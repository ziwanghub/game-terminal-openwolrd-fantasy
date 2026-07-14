"""DD2 guard groups + class soft match · DD3 matchups expanded."""
from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combo import apply_defense, defense_skills
from game.domain.guard_groups import (
    format_guard_group_box_lines,
    group_menu_rows,
    pick_skill_in_group,
    resolve_guard_class,
    skills_by_guard_group,
)


def test_guard_basic_is_physical():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["guard_basic"]
    assert resolve_guard_class(sk) == "physical"


def test_water_veil_elemental():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["guard_water_veil"]
    assert resolve_guard_class(sk) == "elemental"


def test_mana_shield_arcane():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["mage_mana_shield"]
    assert resolve_guard_class(sk) == "arcane"


def test_group_menu_has_physical_for_new_player():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g1", "warrior", "กัน")
    rows = group_menu_rows(p, reg)
    keys = [r["key"] for r in rows]
    assert "physical" in keys
    labels = "\n".join(format_guard_group_box_lines(p, reg))
    assert "กันกาย" in labels
    assert "ไม่ป้องกัน" in labels
    # soft — no raw skill ids in top menu
    assert "guard_basic" not in labels


def test_pick_physical_defaults_to_guard_basic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g2", "warrior", "เบสิก")
    picked = pick_skill_in_group(p, reg, "physical")
    assert picked is not None
    sid, sk = picked
    assert sid == "guard_basic"
    assert int(sk.get("cost_mana") or 0) == 0


def test_owned_elemental_appears_in_group():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g3", "warrior", "ดิน")
    p["skills"] = list(p.get("skills") or []) + ["guard_earth", "guard_basic"]
    by = skills_by_guard_group(p, reg)
    ids = [s for s, _ in by.get("elemental") or []]
    assert "guard_earth" in ids


def test_physical_guard_vs_arcane_attack_class_miss():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["guard_basic"]
    # fire not in strong_vs of guard_basic (weak has fire) → weak path
    dmg, grade, msg = apply_defense(
        40, ["fire", "magic"], sk, damage_class="arcane", reg=reg
    )
    assert dmg > 20  # weak mitigation
    assert grade in ("weak", "class_miss")


def test_physical_guard_vs_physical_strong():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills["guard_basic"]
    dmg, grade, msg = apply_defense(
        40, ["physical"], sk, damage_class="physical", reg=reg
    )
    assert dmg < 20
    assert grade == "strong"
    assert "★" in msg or "ได้ผล" in msg


def test_defense_skills_includes_basic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "g4", "mage", "รายการ")
    skills = defense_skills(p, reg)
    assert any(sid == "guard_basic" for sid, _ in skills)


def test_matchups_expanded_dd3():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.matchups) >= 10
    # fire vs water
    assert reg.element_mult(["fire"], ["water"]) < 1.0
    assert reg.element_mult(["water"], ["fire"]) > 1.0
    # light/dark aliases
    assert reg.element_mult(["holy"], ["shadow"]) > 1.0
    assert reg.element_mult(["lightning"], ["water"]) > 1.0
    # ice
    assert reg.element_mult(["fire"], ["ice"]) > 1.0
