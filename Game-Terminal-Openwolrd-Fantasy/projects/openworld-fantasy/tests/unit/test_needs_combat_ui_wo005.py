"""WO-005 P1.5: combat needs compact + soft warnings vocabulary."""
from __future__ import annotations

from game.domain.needs import (
    combat_needs_soft_warnings,
    format_combat_needs_compact,
    needs_pressure_hint,
)
from game.domain.narrative import situation_strip


def test_format_combat_needs_uses_standard_labels():
    # good bands → soft words only (no "หิว หิว" / "ขวัญ ขวัญดี")
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 80}}
    line = format_combat_needs_compact(p)
    assert "อิ่ม" in line
    assert "เบา" in line
    assert "ขวัญดี" in line
    assert "หิว−หิว" not in line
    # stressed → soft + mark, still no double axis
    bad = format_combat_needs_compact(
        {"needs": {"hunger": 70, "fatigue": 70, "morale": 30}}
    )
    assert "หิว−" in bad or "หิว" in bad
    assert "ล้า−" in bad or "ล้า" in bad
    assert "หิว−หิว" not in bad
    assert "ล้า−ล้า" not in bad


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
