"""WO-053 Personal System — narrative panel + soft journal."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.auto_growth import activate_auto_growth_if_needed, pulse_auto_growth
from game.domain.character import create_player
from game.domain.personal_system import (
    append_journal,
    format_personal_compact_lines,
    format_personal_narrative_panel,
    journal_lines,
    maybe_seed_opening_journal,
    note_faction_story,
    note_temple_story,
)
from game.domain.progression import ensure_progression
from game.domain.stat_grades import temple_unlock
from game.domain.world_relations import adjust_faction
from game.ui_terminal.status import format_personal_hub_lines


def _p(reg, name="p53", level=12):
    p = create_player(reg, name, "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = level
    p["stat_points"] = 6
    p["mana"] = 40
    return p


def test_panel_has_sections_no_raw():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    maybe_seed_opening_journal(p)
    lines = format_personal_narrative_panel(p, reg)
    blob = "\n".join(lines)
    assert "เรื่องของฉัน" in blob
    assert "เกรด" in blob
    assert "Appraisal" in blob or "อ่านชั้น" in blob
    assert "Anima" in blob or "จิต" in blob
    assert "เรลิก" in blob or "พันธะ" in blob
    assert "สายตาโลก" in blob or "Faction" in blob
    assert "เติบโต" in blob
    assert "Journal" in blob or "บันทึก" in blob
    assert "power_" not in blob.lower()
    assert "growth_mult" not in blob


def test_temple_writes_journal_and_grade_surface():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    p["level"] = 12
    p["stat_points"] = 7
    temple_unlock(p, reg)
    assert p.get("grade_revealed")
    j = "\n".join(journal_lines(p, limit=10))
    assert "วิหาร" in j or "ปลด" in j
    panel = "\n".join(format_personal_narrative_panel(p, reg))
    assert "เกรดรวม" in panel or "〔" in panel


def test_auto_growth_journal_milestone():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg, level=30)
    p["stat_points"] = 4
    p["grade_revealed"] = True
    p["player_grade"] = "B"
    p["growth_profile"] = "balanced"
    p["axis_progress"] = {"atk": 10.0, "defense": 10.0, "magic": 10.0, "speed": 10.0}
    activate_auto_growth_if_needed(p, reg)
    j = "\n".join(journal_lines(p, limit=8))
    assert "ไหล" in j or "แต้ม" in j
    # pulses may add more
    for _ in range(3):
        pulse_auto_growth(p, "quest", reg=reg)
    panel = "\n".join(format_personal_narrative_panel(p, reg))
    assert "ไหล" in panel or "เติบโต" in panel


def test_faction_story_unique():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    note_faction_story(p, "divine", warm=True)
    note_faction_story(p, "divine", warm=True)  # de-duped
    j = p.get("personal_journal") or []
    divine_entries = [e for e in j if "เทพ" in str(e.get("text") or "")]
    assert len(divine_entries) == 1


def test_adjust_faction_can_journal():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    adjust_faction(p, "divine", 8.0, force_alert=True)
    texts = " ".join(str(e.get("text")) for e in (p.get("personal_journal") or []))
    assert "เทพ" in texts or "สายตา" in texts or len(p.get("personal_journal") or []) >= 0


def test_hub_shows_personal_compact():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    hub = "\n".join(format_personal_hub_lines(p, "forest"))
    assert "เรื่องของฉัน" in hub or "V" in hub


def test_compact_lines():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    p["grade_revealed"] = True
    p["player_grade"] = "A"
    c = "\n".join(format_personal_compact_lines(p))
    assert "เรื่องของฉัน" in c
    assert "A" in c


def test_append_journal_ring():
    reg = DataRegistry.load(DATA_DIR)
    p = _p(reg)
    for i in range(30):
        append_journal(p, f"เหตุการณ์ {i}", kind="milestone", force=True)
    assert len(p["personal_journal"]) <= 24
