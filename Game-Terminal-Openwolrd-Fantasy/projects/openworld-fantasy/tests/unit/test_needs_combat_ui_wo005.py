"""WO-005 P1.5: combat needs compact + soft warnings vocabulary."""
from __future__ import annotations

from game.domain.needs import (
    combat_needs_soft_warnings,
    format_combat_needs_compact,
    needs_pressure_hint,
)
from game.domain.narrative import situation_strip


def test_format_combat_needs_uses_standard_labels():
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 70}}
    line = format_combat_needs_compact(p)
    assert "หิว" in line
    assert "ล้า" in line
    assert "ขวัญ" in line


def test_soft_warnings_low_morale_and_fatigue():
    p = {"needs": {"hunger": 20, "fatigue": 70, "morale": 30}}
    warns = combat_needs_soft_warnings(p)
    text = " ".join(warns)
    assert "ขวัญ" in text
    assert "ล้า" in text or "จังหวะ" in text


def test_pressure_hint_uses_khwan_not_ambiguous():
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 10}}
    h = needs_pressure_hint(p)
    assert h
    assert "ขวัญ" in h


def test_situation_strip_includes_needs_tags():
    p = {
        "hp": 50,
        "max_hp": 100,
        "needs": {"hunger": 80, "fatigue": 20, "morale": 20},
        "statuses": [],
        "blessings": [],
        "party": [],
    }
    mon = {"hp": 50, "max_hp": 100, "statuses": [], "boss": False}
    s = situation_strip(p, mon, known=True)
    assert "หิว" in s or "ขวัญ" in s
