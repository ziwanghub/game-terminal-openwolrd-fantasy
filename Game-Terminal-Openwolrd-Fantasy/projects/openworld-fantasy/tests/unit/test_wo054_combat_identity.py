"""WO-054 Soft Combat Identity + Weakness Lite."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat_identity import (
    apply_identity_to_outbound,
    hit_identity_flavor,
    identity_outbound_mult,
    pre_fight_identity_lines,
    weakness_lite_hint_lines,
    weakness_lite_mult,
)
from game.domain.damage_pipeline import resolve_player_outbound
from game.domain.progression import ensure_progression


def _p(reg, name="c54"):
    p = create_player(reg, name, "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 20
    p["grade_revealed"] = True
    p["player_grade"] = "S"
    p["growth_profile"] = "balanced"
    p["location"] = "ancient_city"
    p["axis_progress"] = {"atk": 40.0, "defense": 20.0, "magic": 15.0, "speed": 18.0}
    p["power_atk"] = 25.0
    p["power_mag"] = 20.0
    p["bonus_atk"] = 4
    p["crit_chance"] = 0.0
    p["luck_score"] = 0.0
    p["area_mastery"] = {"ancient_city": 40, "dark_forest": 40}
    return p


def _fire_mon():
    return {
        "id": "fire_golem",
        "name": "โกเล็มไฟ",
        "level": 18,
        "hp": 80,
        "max_hp": 80,
        "atk": 12,
        "elements": ["fire"],
        "statuses": [],
    }


def test_pre_fight_identity_grade_and_bond():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    p["_relic_bond_mode"] = "resonance"
    p["_relic_bond_faction"] = "divine"
    mon = _fire_mon()
    lines = pre_fight_identity_lines(p, mon, reg, area_id="ancient_city", force=True)
    blob = "\n".join(lines)
    assert lines
    assert "power_" not in blob.lower()
    assert "1.02" not in blob
    # grade S or bond flavor
    assert "พลัง" in blob or "เรลิก" in blob or "เรโซแนนซ์" in blob or "จิต" in blob


def test_identity_mult_s_higher_than_f():
    reg = DataRegistry.load(DATA_DIR)
    p_s = _p(reg, "s")
    p_s["player_grade"] = "S"
    p_s["_relic_bond_mode"] = "chorus"
    p_f = _p(reg, "f")
    p_f["player_grade"] = "F"
    p_f["_relic_bond_mode"] = "none"
    ms, _ = identity_outbound_mult(p_s, area_id="ancient_city")
    mf, _ = identity_outbound_mult(p_f, area_id="ancient_city")
    assert ms > mf
    assert 0.94 <= mf <= 1.08
    assert 0.94 <= ms <= 1.08


def test_weakness_lite_requires_ss_appraisal():
    """WO-Mon-2: S = one soft band · SS+ = fuller · no % numbers."""
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    mon = _fire_mon()
    # no appraisal
    assert weakness_lite_hint_lines(p, mon, reg) == []
    m0, meta0 = weakness_lite_mult(p, mon, ["water"], reg)
    assert m0 == 1.0
    assert not meta0.get("active")

    # S — soft lite band (playable earlier than SS-only)
    p["_appraised_targets"] = {mon["id"]: "S"}
    s_hints = weakness_lite_hint_lines(p, mon, reg)
    assert s_hints
    assert len(s_hints) <= 1
    assert "ใบ้" in s_hints[0] or "แนว" in s_hints[0]
    assert "%" not in s_hints[0]
    m_s, meta_s = weakness_lite_mult(p, mon, ["water"], reg)
    assert meta_s.get("active")
    assert 1.0 < m_s <= 1.04

    # SS — hints + micro mult for water vs fire
    p["_appraised_targets"] = {mon["id"]: "SS"}
    hints = weakness_lite_hint_lines(p, mon, reg)
    blob = "\n".join(hints)
    assert hints
    assert "ใบ้" in blob or "น้ำ" in blob or "แนว" in blob
    assert "1.4" not in blob
    assert "%" not in blob
    m1, meta1 = weakness_lite_mult(p, mon, ["water"], reg)
    assert meta1.get("active")
    assert 1.0 < m1 <= 1.06
    # physical not soft-weak vs fire typically
    m2, meta2 = weakness_lite_mult(p, mon, ["physical"], reg)
    # may or may not match — fire weak to water mainly
    if not meta2.get("active"):
        assert m2 == 1.0


def test_apply_identity_changes_damage():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    p["player_grade"] = "SSS"
    p["_relic_bond_mode"] = "chorus"
    mon = _fire_mon()
    p["_appraised_targets"] = {mon["id"]: "SS"}
    amt, notes, meta = apply_identity_to_outbound(
        p,
        mon,
        dmg_class="physical",
        skill_elements=["water"],
        area_id="ancient_city",
        reg=reg,
        rng=random.Random(1),
        raw_amount=20,
    )
    assert amt >= 20  # identity/weak boost or equal floor
    assert meta.get("total_identity_mult", 1) >= 1.0


def test_pipeline_includes_identity_meta():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    mon = _fire_mon()
    p["_appraised_targets"] = {mon["id"]: "SS"}
    r = resolve_player_outbound(
        p,
        mon,
        reg,
        "ancient_city",
        {"power": 12, "elements": ["water"]},
        random.Random(5),
    )
    assert r.amount >= 1
    assert "identity" in r.meta
    assert "power_atk" not in (r.flavor or "").lower()


def test_hit_flavor_throttled_no_spam():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    mon = _fire_mon()
    got = 0
    for i in range(20):
        fl = hit_identity_flavor(p, mon, dmg_class="physical", rng=random.Random(i))
        if fl:
            got += 1
            assert "power" not in fl.lower()
    # not every hit
    assert got < 20
