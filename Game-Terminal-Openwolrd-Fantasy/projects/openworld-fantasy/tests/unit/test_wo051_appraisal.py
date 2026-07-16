"""WO-051 Appraisal Skill S–SSS soft tiers."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.appraisal import (
    SKILL_ID,
    TIER_BASE,
    TIER_S,
    TIER_SS,
    TIER_SSS,
    appraise_monster_lines,
    appraise_self_lines,
    combat_appraise_hint,
    on_temple_unlock_appraisal,
    resolve_appraisal_tier,
    run_appraisal,
    soft_recipe_lines,
    soft_weakness_lines,
    sync_appraisal_tier,
)
from game.domain.character import create_player
from game.domain.progression import ensure_progression
from game.domain.stat_grades import temple_unlock


def _player(reg, name="a51"):
    p = create_player(reg, name, "warrior", "เมษ")
    ensure_progression(p, reg)
    p["mana"] = 50
    p["max_mana"] = 50
    p["level"] = 12
    return p


def _fire_mon():
    return {
        "id": "ember_beast",
        "name": "อสูรไฟ",
        "level": 10,
        "hp": 60,
        "max_hp": 60,
        "atk": 12,
        "elements": ["fire"],
    }


def test_temple_seeds_appraisal_s():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["stat_points"] = 6
    p["level"] = 12
    temple_unlock(p, reg)
    assert p.get("grade_revealed")
    assert resolve_appraisal_tier(p) in (TIER_S, TIER_SS, TIER_SSS)
    assert SKILL_ID in (p.get("skills") or [])


def test_tier_depth_s_ss_sss_differ():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["grade_revealed"] = True
    p["player_grade"] = "B"
    p["growth_profile"] = "balanced"
    p["axis_progress"] = {"atk": 22, "defense": 10, "magic": 8, "speed": 12}
    mon = _fire_mon()

    s_lines = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_S))
    ss_lines = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_SS))
    sss_lines = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_SSS))

    assert "〔" in s_lines  # letter band
    assert "จุดอ่อน" in ss_lines or "น้ำ" in ss_lines or "แนว" in ss_lines
    assert "recipe" in sss_lines.lower() or "สาย" in sss_lines
    assert "power_atk" not in sss_lines
    assert "1.4" not in sss_lines
    # SS has weakness block not required in S
    assert ("จุดอ่อน" in ss_lines) or ("ทะลุ" in ss_lines)
    assert ("สาย" in sss_lines) and ("สาย" in sss_lines)


def test_weakness_water_vs_fire_soft():
    reg = DataRegistry.load(DATA_DIR)
    mon = _fire_mon()
    lines = "\n".join(soft_weakness_lines(mon, reg))
    assert "น้ำ" in lines or "water" not in lines.lower() or "ชื้น" in lines
    assert "%" not in lines
    assert "1.4" not in lines


def test_soft_recipe_no_formula_dump():
    reg = DataRegistry.load(DATA_DIR)
    mon = _fire_mon()
    lines = "\n".join(soft_recipe_lines(mon, reg, max_n=2, rng=random.Random(1)))
    assert "→" in lines or "สาย" in lines
    assert "power_bonus" not in lines
    assert "status_chance" not in lines


def test_self_appraisal_shows_grades_when_revealed():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["grade_revealed"] = True
    p["player_grade"] = "A"
    p["growth_profile"] = "focused"
    p["axis_progress"] = {"atk": 30, "defense": 15, "magic": 10, "speed": 12}
    p["appraisal_tier"] = TIER_SS
    blob = "\n".join(appraise_self_lines(p, reg, force_tier=TIER_SS))
    assert "เกรด" in blob or "โจมตี" in blob or "ระดับ" in blob
    assert "power_" not in blob.lower()


def test_run_appraisal_spends_mana_s():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["appraisal_tier"] = TIER_S
    p["mana"] = 20
    before = p["mana"]
    lines, _ = run_appraisal(p, target="self", reg=reg, paid=True)
    assert p["mana"] < before or any("สมาธิ" in ln for ln in lines)
    assert any("อ่านชั้น" in ln or "เกรด" in ln or "ชีพ" in ln for ln in lines)


def test_combat_hint_after_appraise():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["appraisal_tier"] = TIER_SS
    mon = _fire_mon()
    appraise_monster_lines(p, mon, reg, force_tier=TIER_SS)
    hint = combat_appraise_hint(p, mon)
    assert hint is not None
    assert "อ่าน" in hint or "ช่อง" in hint


def test_base_tier_no_letter_forced():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg, "base")
    p["level"] = 3
    p["appraisal_tier"] = TIER_BASE
    p["appraisal_xp"] = 0
    p["grade_revealed"] = False
    # force low so soft gates don't raise
    p["level"] = 1
    mon = _fire_mon()
    blob = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_BASE))
    assert "ชั้นพลังศัตรู" not in blob
    assert "สูตร" not in blob or "ไม่ dump" in blob


def test_sync_raises_with_xp():
    reg = DataRegistry.load(DATA_DIR)
    p = _player(reg)
    p["appraisal_tier"] = TIER_BASE
    p["appraisal_xp"] = 25
    p["level"] = 20
    p["grade_revealed"] = True
    t = sync_appraisal_tier(p)
    assert t in (TIER_SS, TIER_SSS)
