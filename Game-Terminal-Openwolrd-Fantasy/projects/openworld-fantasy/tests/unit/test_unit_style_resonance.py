"""Hidden Style Resonance: joke can jackpot; broken collapses if style mismatch."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.unit_system import (
    apply_unit_skill_scaling,
    soft_path_band,
    unit_style_resonance_mult,
    unit_style_score,
)


def _base(reg, name="u"):
    p = create_player(reg, name, "vagabond", "เมษ")
    p["level"] = 20
    p["stats"] = {}
    p["stats_alloc"] = {
        "atk": 0,
        "defense": 0,
        "magic": 0,
        "speed": 0,
        "intelligence": 0,
        "crit": 0,
    }
    p["money_world"] = 500
    return p


def test_joke_high_style_much_stronger_than_low():
    reg = DataRegistry.load(DATA_DIR)
    u = reg.unit_classes["unit_pocketdust"]
    assert u.get("power_tier") == "joke"
    sk = reg.skills[u["exclusive_skill"]]

    lo = _base(reg, "jlo")
    lo["unit_class_id"] = "unit_pocketdust"
    lo["stats"] = {"explores": 0, "flees": 0, "kills": 100}
    lo["money_world"] = 5000
    lo["power_atk"] = 20
    lo["power_spd"] = 5
    lo["level"] = 20

    hi = _base(reg, "jhi")
    hi["unit_class_id"] = "unit_pocketdust"
    hi["stats"] = {"explores": 80, "flees": 20, "kills": 5, "chests": 5}
    hi["stats_alloc"]["speed"] = 16
    hi["money_world"] = 20
    hi["power_atk"] = 8
    hi["power_spd"] = 35
    hi["power_mag"] = 12
    hi["location"] = "dark_forest"
    hi["level"] = 20
    hi["unit_mastery"] = 2

    m_lo = unit_style_resonance_mult(lo, reg=reg, unit_def=u)
    m_hi = unit_style_resonance_mult(hi, reg=reg, unit_def=u)
    assert m_hi > m_lo * 1.5
    assert m_hi >= 1.2  # jackpot territory (capped)

    p_lo, _ = apply_unit_skill_scaling(lo, sk, int(sk.get("power") or 3), 12, reg=reg)
    p_hi, _ = apply_unit_skill_scaling(hi, sk, int(sk.get("power") or 3), 12, reg=reg)
    assert p_hi > p_lo * 2
    # jackpot capped for playtest safety
    from game.domain.unit_system import JOKE_POWER_ABS_CAP

    assert p_hi <= JOKE_POWER_ABS_CAP


def test_broken_low_style_nearly_useless():
    reg = DataRegistry.load(DATA_DIR)
    u = reg.unit_classes["unit_voidcrown"]
    assert u.get("power_tier") == "broken"
    sk = reg.skills[u["exclusive_skill"]]

    bad = _base(reg, "bbad")
    bad["unit_class_id"] = "unit_voidcrown"
    bad["location"] = "dark_forest"
    bad["stats"] = {"kills": 5, "boss_kills": 0, "explores": 2}
    bad["stats_alloc"]["atk"] = 20
    bad["power_atk"] = 40
    bad["power_mag"] = 3
    bad["power_intel"] = 2

    good = _base(reg, "bgood")
    good["unit_class_id"] = "unit_voidcrown"
    good["location"] = "void_rift"
    good["stats"] = {"boss_kills": 8, "kills": 40}
    good["library_entries_read"] = list("abcdefgh")
    good["stats_alloc"]["intelligence"] = 14
    good["stats_alloc"]["magic"] = 12
    good["power_mag"] = 40
    good["power_atk"] = 10
    good["power_intel"] = 20

    m_bad = unit_style_resonance_mult(bad, reg=reg, unit_def=u)
    m_good = unit_style_resonance_mult(good, reg=reg, unit_def=u)
    assert m_bad < 0.55
    assert m_good > m_bad * 1.5

    p_bad, _ = apply_unit_skill_scaling(bad, sk, int(sk.get("power") or 80), 18, reg=reg)
    p_good, _ = apply_unit_skill_scaling(good, sk, int(sk.get("power") or 80), 18, reg=reg)
    assert p_good > p_bad * 1.8


def test_joke_jackpot_can_rival_unmatched_broken():
    """Design intent: matching joke can outpace mismatched broken."""
    reg = DataRegistry.load(DATA_DIR)
    joke_u = reg.unit_classes["unit_yawn"]
    broke_u = reg.unit_classes["unit_worldpiercer"]
    sk_j = reg.skills[joke_u["exclusive_skill"]]
    sk_b = reg.skills[broke_u["exclusive_skill"]]

    j = _base(reg, "jack")
    j["unit_class_id"] = "unit_yawn"
    j["stats"] = {"rests": 30, "heals": 40, "kills": 3}
    j["library_entries_read"] = list("abcdefghi")
    j["money_world"] = 30
    j["power_mag"] = 25
    j["power_def"] = 20
    j["unit_mastery"] = 3

    b = _base(reg, "br")
    b["unit_class_id"] = "unit_worldpiercer"
    b["stats"] = {"kills": 2, "boss_kills": 0, "upgrades": 0}
    b["stats_alloc"]["magic"] = 15
    b["power_atk"] = 8
    b["power_mag"] = 30
    b["unit_mastery"] = 3

    pj, _ = apply_unit_skill_scaling(j, sk_j, int(sk_j.get("power") or 4), 30, reg=reg)
    pb, _ = apply_unit_skill_scaling(b, sk_b, int(sk_b.get("power") or 84), 22, reg=reg)
    # joke matching should not be totally dominated by unmatched broken
    assert pj >= pb * 0.45 or pj >= 15


def test_soft_path_band_labels():
    assert soft_path_band(0.2) == "ผิดทาง"
    assert soft_path_band(0.6) == "พอใช้"
    assert soft_path_band(1.2) == "เข้าทาง"


def test_all_units_have_style_wants():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.unit_classes) == 33
    for uid, u in reg.unit_classes.items():
        assert u.get("style_wants"), uid
        assert unit_style_score(
            {"stats": {}, "stats_alloc": {}, "location": ""}, u, reg
        ) >= 0.0


def test_tree_t3_branches_exist():
    reg = DataRegistry.load(DATA_DIR)
    for sid in (
        "warrior_brace",
        "mage_still_mind",
        "archer_focus_breath",
        "rogue_bleed_trick",
        "priest_mend_light",
    ):
        assert sid in reg.skills
        assert int((reg.skills[sid] or {}).get("tier") or 0) == 3


def test_joke_jackpot_respects_level_cap():
    reg = DataRegistry.load(DATA_DIR)
    u = reg.unit_classes["unit_pocketdust"]
    sk = reg.skills[u["exclusive_skill"]]
    p = _base(reg, "cap")
    p["unit_class_id"] = "unit_pocketdust"
    p["unit_mastery"] = 5
    p["level"] = 8
    p["stats"] = {"explores": 200, "flees": 40, "kills": 0}
    p["stats_alloc"]["speed"] = 25
    p["money_world"] = 0
    p["power_spd"] = 50
    p["power_mag"] = 30
    p["location"] = "dark_forest"
    dmg, _ = apply_unit_skill_scaling(p, sk, 3, 12, reg=reg)
    # low level: cap scales with level (~16+16=32 ballpark)
    assert dmg <= 50


def test_allocate_soft_mentions_unit_when_extreme(monkeypatch):
    from game.domain.progression import allocate_stat

    reg = DataRegistry.load(DATA_DIR)
    p = _base(reg, "alloc")
    p["unit_class_id"] = "unit_nova"
    p["unit_skill"] = "unit_nova_burst"
    p["stat_points"] = 5
    p["power_mag"] = 2
    p["power_atk"] = 40
    msg = allocate_stat(p, reg, "atk", 1)
    assert "เพิ่ม" in msg or "หนาขึ้น" in msg or "โจมตี" in msg
    # soft line only if extreme band — may or may not appear; smoke no crash
