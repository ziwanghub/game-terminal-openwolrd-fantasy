"""WO-037 Anima Presence & Soft Moments."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import get_catalog
from game.domain.character import create_player
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.stat_arch import (
    anima_presence_lines,
    anima_skill_soft_fail_chance,
    anima_value,
    ensure_stat_arch,
    try_anima_skill_soft_fail,
)
from game.domain.status_fx import resist_chance


def test_anima_catalog_codes():
    cat = get_catalog()
    for code in (
        "anima.relic_touch",
        "anima.chamber_echo",
        "anima.learn_glow",
        "anima.mana_flow",
        "anima.thin",
        "anima.skill_waver",
    ):
        assert code in cat


def test_presence_sets_felt_flag():
    p: dict = {"auto_ticks": 1}
    lines = anima_presence_lines(p, "relic_equip", force=True)
    assert lines
    assert p.get("_anima_presence_felt") is True
    assert "จิต" in "\n".join(lines) or "สั่น" in "\n".join(lines)
    # no raw number dump
    assert "anima=" not in "\n".join(lines).lower()


def test_high_anima_slows_morale_loss():
    reg = DataRegistry.load(DATA_DIR)

    def loss(ani: float) -> int:
        p = create_player(reg, f"a{ani}", "warrior", "เมษ")
        ensure_needs(p)
        ensure_stat_arch(p)
        p["anima"] = ani
        p["needs"]["morale"] = 70
        for _ in range(5):
            apply_needs_event(p, "combat_loss", silent=True)
        return 70 - int(get_needs(p)["morale"])

    assert loss(80) <= loss(12)


def test_skill_fail_only_when_frail():
    p_hi = {"anima": 60.0, "needs": {"morale": 20, "hunger": 20, "fatigue": 20}}
    p_lo = {"anima": 12.0, "needs": {"morale": 15, "hunger": 20, "fatigue": 20}}
    ensure_needs(p_hi)
    ensure_needs(p_lo)
    assert anima_skill_soft_fail_chance(p_hi) == 0.0
    assert anima_skill_soft_fail_chance(p_lo) > 0.0


def test_try_skill_fail_returns_lines():
    p = {
        "anima": 10.0,
        "needs": {"morale": 10, "hunger": 20, "fatigue": 20},
        "auto_ticks": 1,
    }
    ensure_needs(p)
    ensure_stat_arch(p)

    class R:
        def random(self):
            return 0.0  # always fail if chance > 0

    failed, lines = try_anima_skill_soft_fail(p, skill_name="ลูกไฟ", rng=R())
    assert failed is True
    assert lines


def test_mental_resist_uses_anima():
    p_hi = {"anima": 80.0, "power_def": 5, "power_intel": 5}
    p_lo = {"anima": 10.0, "power_def": 5, "power_intel": 5}
    r_hi = resist_chance(p_hi, "stun", None)
    r_lo = resist_chance(p_lo, "stun", None)
    assert r_hi >= r_lo
