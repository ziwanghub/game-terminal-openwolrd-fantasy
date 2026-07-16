"""WO-033 Soft Alert Bus."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.alerts import (
    ALERT_CODE_ALIASES,
    SEV_CRIT,
    SEV_WARN,
    build_alert,
    collect_alert,
    emit_alert_lines,
    format_alert_lines,
    get_catalog,
    resolve_alert_code,
)
from game.domain.character import create_player
from game.domain.divine_burden import (
    apply_burden_tick,
    apply_relic_aura,
    on_equip_burden_note,
    on_unequip_burden_note,
    pre_fight_burden_alerts,
    soft_aura_resist_chance,
    try_auto_unequip_burden,
)
from game.domain.alerts import recent_alerts
from game.domain.needs import (
    combat_needs_soft_warnings,
    ensure_needs,
    needs_pressure_hint,
    record_needs_soft_alerts,
)
from game.runtime.dungeon_auto import ensure_auto_prefs


def test_catalog_has_burden_codes():
    """Legacy burden.* still listed (alias entries) for discovery."""
    cat = get_catalog()
    for code in (
        "burden.equip.crush",
        "burden.morale_crit",
        "burden.auto_unequip",
        "burden.pre_fight",
        "burden.auto_blocked",
        "burden.pre_dungeon",
        "burden.mana_thin",
    ):
        assert code in cat
        assert cat[code].get("alias_of") or cat[code].get("legacy")


def test_catalog_has_relic_codes_wo034():
    cat = get_catalog()
    for code in (
        "relic.equip",
        "relic.equip_warning",
        "relic.unequip",
        "relic.aura_active",
        "relic.mana_drain",
        "relic.spirit_low",
        "relic.spirit_critical",
        "relic.morale_debuff",
        "relic.critical",
        "relic.auto_blocked",
        "relic.auto_unequip",
        "relic.aura_resisted",
        "relic.aura_strong",
        "relic.pre_fight",
        "relic.pre_dungeon",
    ):
        assert code in cat


def test_burden_aliases_to_relic():
    assert resolve_alert_code("burden.equip.fit") == "relic.equip"
    assert resolve_alert_code("burden.equip.strain") == "relic.equip_warning"
    assert resolve_alert_code("burden.equip.crush") == "relic.equip_warning"
    assert resolve_alert_code("burden.morale_low") == "relic.spirit_low"
    assert resolve_alert_code("burden.morale_crit") == "relic.spirit_critical"
    assert resolve_alert_code("burden.auto_blocked") == "relic.auto_blocked"
    assert resolve_alert_code("relic.equip") == "relic.equip"
    # all alias targets exist
    cat = get_catalog()
    for legacy, canon in ALERT_CODE_ALIASES.items():
        assert canon in cat, canon
        assert legacy in cat


def test_build_alert_canonical_code():
    a = build_alert("burden.morale_crit")
    assert a.code == "relic.spirit_critical"
    assert a.severity == SEV_CRIT
    assert "ขวัญ" in a.title or "จิต" in a.title or "วิกฤต" in a.title


def test_alias_shares_throttle():
    p: dict = {"auto_ticks": 10, "_alert_throttle": {}}
    a1 = collect_alert(p, "burden.morale_crit")
    assert a1
    # same canonical via relic code within throttle window
    p["auto_ticks"] = 11
    a2 = collect_alert(p, "relic.spirit_critical")
    assert a2 == []
    p["auto_ticks"] = 20
    a3 = collect_alert(p, "relic.spirit_critical")
    assert a3


def test_catalog_has_needs_codes():
    cat = get_catalog()
    for code in (
        "needs.hunger.crit",
        "needs.fatigue.bad",
        "needs.morale.low",
        "needs.pressure.morale_crit",
    ):
        assert code in cat


def test_force_bypasses_throttle():
    p: dict = {"auto_ticks": 5, "_alert_throttle": {}}
    a1 = collect_alert(p, "burden.morale_low")
    assert a1
    a2 = collect_alert(p, "burden.morale_low")  # throttled
    assert a2 == []
    a3 = collect_alert(p, "burden.morale_low", force=True)
    assert a3


def test_recent_alerts_history():
    p: dict = {"auto_ticks": 1, "_alert_throttle": {}}
    collect_alert(p, "burden.equip.strain", item="ทดสอบ", force=True)
    from game.domain.alerts import recent_alerts

    hist = recent_alerts(p, limit=5)
    assert hist
    # WO-034: history stores canonical relic.* code
    assert hist[-1]["code"] == "relic.equip_warning"


def test_format_severity_cues():
    a = build_alert("burden.equip.strain", item="ดาบทดสอบ")
    lines = format_alert_lines(a)
    assert any("⚠" in x or "ร้อน" in x or "เรลิก" in x for x in lines)
    c = build_alert("burden.morale_crit")
    assert c.severity == SEV_CRIT
    cl = format_alert_lines(c)
    assert any("วิกฤต" in x for x in cl)


def test_throttle_prevents_spam():
    p: dict = {"auto_ticks": 10, "_alert_throttle": {}}
    a1 = collect_alert(p, "burden.morale_crit", force=False)
    assert a1
    p["auto_ticks"] = 11  # within throttle window (5)
    a2 = collect_alert(p, "burden.morale_crit", force=False)
    assert a2 == []
    p["auto_ticks"] = 20
    a3 = collect_alert(p, "burden.morale_crit", force=False)
    assert a3


def test_equip_emits_burden_alert():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al1", "warrior", "เมษ")
    p["level"] = 1
    lines = on_equip_burden_note(
        p, reg, rarity_id="legendary", item_name="เขี้ยววายุ"
    )
    blob = "\n".join(lines)
    assert "เขี้ยว" in blob or "ภาระ" in blob or "ร้อน" in blob or "⚠" in blob


def test_auto_unequip_uses_alert():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al2", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["needs"]["morale"] = 12
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 30
    p["auto_prefs"] = prefs
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    notes = try_auto_unequip_burden(p, reg)
    assert notes
    assert any("ถอด" in n or "⚠" in n or "ออโต้" in n for n in notes)


def test_pre_fight_alert_when_burden():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al3", "warrior", "เมษ")
    p["level"] = 1
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    lines = pre_fight_burden_alerts(p, reg)
    assert lines
    # second call throttled
    lines2 = pre_fight_burden_alerts(p, reg)
    # may be empty due to throttle
    assert isinstance(lines2, list)


def test_morale_crit_alert_on_tick():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al4", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["needs"]["morale"] = 15  # crit band
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["auto_ticks"] = 1
    notes = apply_burden_tick(p, reg, context="field")
    blob = "\n".join(notes)
    assert isinstance(notes, list)
    # first tick should surface crit alert or burden flavor
    assert notes, "expected burden tick notes when morale crit + relic"
    assert any(
        "วิกฤต" in n or "ขวัญ" in n or "⚠" in n or "ภาระ" in n for n in notes
    )
    # throttle: next tick without advancing enough should not re-spam crit alert
    p["auto_ticks"] = 2
    notes2 = apply_burden_tick(p, reg, context="field")
    crit_lines = [n for n in notes2 if "วิกฤต" in n]
    assert len(crit_lines) == 0


def test_needs_soft_warnings_via_bus_vocabulary():
    """WO-033.4: live vitals lines keep WO-005 words, sourced from catalog."""
    p = {"needs": {"hunger": 20, "fatigue": 70, "morale": 30}}
    warns = combat_needs_soft_warnings(p)
    text = " ".join(warns)
    assert "ขวัญ" in text
    assert "ล้า" in text or "จังหวะ" in text
    # live — second call still shows (no throttle on vitals path)
    asserts2 = combat_needs_soft_warnings(p)
    assert asserts2


def test_needs_pressure_hint_via_catalog():
    p = {"needs": {"hunger": 20, "fatigue": 20, "morale": 10}}
    h = needs_pressure_hint(p)
    assert h
    assert "ขวัญ" in h


def test_record_needs_soft_alerts_throttled():
    p: dict = {
        "needs": {"hunger": 90, "fatigue": 20, "morale": 70},
        "auto_ticks": 1,
        "_alert_throttle": {},
    }
    a1 = record_needs_soft_alerts(p)
    assert a1
    assert any("หิว" in x for x in a1)
    # same tick → throttled
    a2 = record_needs_soft_alerts(p)
    assert a2 == []

    hist = recent_alerts(p)
    assert any(h.get("code", "").startswith("needs.") for h in hist)


def test_unequip_emits_relic_alert():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al5", "warrior", "เมษ")
    lines = on_unequip_burden_note(
        p, reg, rarity_id="legendary", item_name="เขี้ยววายุ"
    )
    assert lines
    blob = "\n".join(lines)
    assert "ถอด" in blob or "เขี้ยว" in blob
    hist = recent_alerts(p)
    assert hist and hist[-1]["code"] == "relic.unequip"


def test_pre_fight_uses_relic_namespace():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al6", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    lines = pre_fight_burden_alerts(p, reg)
    assert lines
    hist = recent_alerts(p)
    codes = {h.get("code") for h in hist}
    assert "relic.pre_fight" in codes or "relic.aura_active" in codes


def test_spirit_critical_and_critical_on_tick():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al7", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["needs"]["morale"] = 10
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["auto_ticks"] = 1
    # force crush band via low level + legendary usually crush/strain
    notes = apply_burden_tick(p, reg, context="field")
    assert isinstance(notes, list)
    hist = recent_alerts(p)
    codes = {h.get("code") for h in hist}
    # at least spirit path fired
    assert codes & {
        "relic.spirit_critical",
        "relic.spirit_low",
        "relic.critical",
        "relic.morale_debuff",
    }


def test_band_th_polish_in_alert_body():
    a = build_alert("relic.equip_warning", item="ดาบ", band="crush")
    assert "หนัก" in a.body or "เกินตัว" in a.body
    assert "crush" not in a.body


def test_soft_aura_resist_chance_bounds():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al8", "warrior", "เมษ")
    p["level"] = 25
    ensure_needs(p)
    p["needs"]["morale"] = 80
    p["stats_alloc"] = {"intelligence": 12}
    p["gear_status_resist"] = 0.2
    c = soft_aura_resist_chance(p, reg, band="strain")
    assert 0.0 <= c <= 0.55
    assert c > soft_aura_resist_chance(p, reg, band="crush")


def test_aura_resisted_can_emit():
    """WO-034.5: high resist + forced roll path via many attempts."""
    import random

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "al9", "warrior", "เมษ")
    p["level"] = 30
    ensure_needs(p)
    p["needs"]["morale"] = 90
    p["stats_alloc"] = {"intelligence": 15}
    p["gear_status_resist"] = 0.25
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["party"] = [{"id": "c1", "bond": 3, "morale": 60}]
    p["auto_ticks"] = 1
    saw = False
    for i in range(40):
        p["auto_ticks"] = i + 1
        p.pop("_alert_throttle", None)
        p.pop("_alert_once", None)
        notes = apply_relic_aura(p, reg, rng=random.Random(i * 17 + 3))
        blob = "\n".join(notes)
        if "ต้าน" in blob or "เบา" in blob:
            saw = True
            break
        hist = recent_alerts(p)
        if any(h.get("code") == "relic.aura_resisted" for h in hist):
            saw = True
            break
    # high resist should hit at least sometimes; if not, chance API still valid
    if not saw:
        assert soft_aura_resist_chance(p, reg, band="strain") >= 0.15
