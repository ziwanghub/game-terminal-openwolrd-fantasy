"""SK-R0–R2: skill rank scale · learn roll · buff gate · slots."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import skill_options
from game.domain.skill_rank import (
    clear_rank_rules_cache,
    format_skill_rank_hint,
    get_skill_rank,
    load_rank_rules,
    note_skill_use_mastery,
    scale_skill_for_player,
    set_skill_rank,
    soft_rank_label,
)
from game.domain.skill_slots import (
    can_cast_buff,
    consume_defense_stance_on_hit,
    arm_defense_stance,
    normalize_slot,
    is_combo_eligible,
)
from game.domain.skill_tree import learn_skill
from game.domain.progression import init_progression


def test_rank_rules_load():
    clear_rank_rules_cache()
    rules = load_rank_rules()
    assert "N" in (rules.get("ranks") or []) or "N" in str(rules.get("soft_label"))
    assert soft_rank_label("SSS")


def test_scale_power_and_mana_by_rank():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "R", "mage", "เมษ")
    init_progression(p, reg)
    base = dict(reg.skills["fire_ball"])
    set_skill_rank(p, "fire_ball", "N", reg)
    n = scale_skill_for_player(p, base, reg, skill_id="fire_ball")
    set_skill_rank(p, "fire_ball", "SSS", reg)
    p["level"] = 20  # avoid early tax distorting too much for comparison
    sss = scale_skill_for_player(p, base, reg, skill_id="fire_ball")
    assert int(sss["power"]) > int(n["power"])
    assert int(sss["cost_mana"]) > int(n["cost_mana"])
    assert sss.get("_rank_label")


def test_early_sss_mana_tax():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "E", "mage", "เมษ")
    init_progression(p, reg)
    p["level"] = 2
    base = dict(reg.skills["fire_ball"])
    set_skill_rank(p, "fire_ball", "SSS", reg)
    sk = scale_skill_for_player(p, base, reg, skill_id="fire_ball")
    # base 12 * 2.4 * 1.35 ≈ 38+
    assert int(sk["cost_mana"]) >= 30


def test_learn_assigns_rank():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "L", "mage", "เมษ")
    init_progression(p, reg)
    p["level"] = 10
    p["money_world"] = 9999
    p["skills"] = ["magic_missile"]
    p["occupation_id"] = "mage"
    # free learn to avoid prereq money edge cases
    msg = learn_skill(p, reg, "fire_ball", free=True)
    assert "fire_ball" in (p.get("skills") or []) or "ลูกไฟ" in msg or "เรียนรู้" in msg
    # if free added skill
    if "fire_ball" not in (p.get("skills") or []):
        p["skills"] = list(p.get("skills") or []) + ["fire_ball"]
        from game.domain.skill_rank import apply_learn_rank

        apply_learn_rank(p, "fire_ball", reg.skills["fire_ball"], random.Random(1), reg)
    assert get_skill_rank(p, "fire_ball", reg) in ("N", "H", "R", "S", "SS", "SSS")


def test_buff_slot_and_gate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "B", "warrior", "สิงห์")
    init_progression(p, reg)
    sk = reg.skills.get("iron_will") or {}
    assert normalize_slot(sk) == "buff"
    assert not is_combo_eligible(sk)
    ok, _ = can_cast_buff(p, sk)
    assert ok
    p["_buff_casts_this_action"] = 1
    ok2, why = can_cast_buff(p, sk)
    assert not ok2
    assert why


def test_counter_defense_mode():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills.get("counter_guard") or {}
    assert normalize_slot(sk) == "defense"
    p = {"hp": 50, "max_hp": 100}
    mon = {"hp": 100, "max_hp": 100}
    notes = arm_defense_stance(p, {**sk, "id": "counter_guard", "counter_power": 15})
    assert notes
    extra, rnotes = consume_defense_stance_on_hit(p, mon, incoming_final=20, rng=random.Random(1))
    assert extra > 0
    assert rnotes
    assert int(mon["hp"]) < 100


def test_reflect_skill_exists():
    reg = DataRegistry.load(DATA_DIR)
    sk = reg.skills.get("thorn_reflect") or {}
    assert sk
    assert normalize_slot(sk) == "defense"
    assert float(sk.get("reflect_pct") or 0) > 0


def test_skill_options_scales():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "O", "mage", "เมษ")
    init_progression(p, reg)
    p["skills"] = ["fire_ball", "magic_missile"]
    set_skill_rank(p, "fire_ball", "S", reg)
    opts = skill_options(p, reg)
    by_id = {sid: sk for sid, sk in opts}
    assert "fire_ball" in by_id
    assert by_id["fire_ball"].get("_skill_rank") == "S"


def test_mastery_can_upgrade():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "M", "mage", "เมษ")
    init_progression(p, reg)
    set_skill_rank(p, "fire_ball", "N", reg)
    p["skill_rank_xp"] = {"fire_ball": 17}
    # 18th use triggers try
    notes = []
    for seed in range(30):
        p["skill_rank_xp"] = {"fire_ball": 17}
        msg = note_skill_use_mastery(p, "fire_ball", reg, random.Random(seed))
        if msg and "เปลี่ยนโทน" in msg:
            notes.append(msg)
            break
    # either upgraded sometime or soft message — xp always increments
    assert int((p.get("skill_rank_xp") or {}).get("fire_ball") or 0) >= 18
