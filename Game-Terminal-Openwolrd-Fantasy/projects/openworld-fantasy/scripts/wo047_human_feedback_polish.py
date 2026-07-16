#!/usr/bin/env python3
"""WO-047 Human Feedback companion harness + feel polish verify."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.divine_burden import try_auto_unequip_burden
from game.domain.faction_moments import moments_for_area, resolve_moment_choice
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    SYN_AREA_TENSION,
    SYN_RESONATE,
    evaluate_relic_area_synergy,
    evaluate_relic_bonds,
    BOND_CHORUS,
    BOND_RESONANCE,
    on_chamber_spar_with_relic,
    on_relic_bond_pulse,
    relic_area_synergy_morale_factor,
    synergy_foresight_lines,
    try_area_synergy_presence_pulse,
)
from game.domain.soft_foresight import area_world_gaze_lines, soft_dungeon_entry_warnings
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    scores: dict = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    areas_ok = sum(1 for a in (
        "dark_forest", "mist_marsh", "cave_shadow", "desert_heat",
        "crystal_peak", "mountain_rock", "ancient_city", "void_rift",
    ) if moments_for_area(a))
    log("areas", f"moments_areas={areas_ok}/8")
    scores["areas"] = 5 if areas_ok == 8 else 2

    # H3 synergy contrast
    p = create_player(reg, "wo047", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    p["location"] = "mountain_rock"
    p["anima"] = 50.0
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    syn_ok = evaluate_relic_area_synergy(p, reg, area_id="mountain_rock")
    fl_ok = synergy_foresight_lines(p, reg, area_id="mountain_rock", brief=False)
    p_bad = create_player(reg, "wo047b", "warrior", "เมษ")
    ensure_stat_arch(p_bad)
    p_bad["location"] = "mountain_rock"
    p_bad["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p_bad["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}
    syn_bad = evaluate_relic_area_synergy(p_bad, reg, area_id="mountain_rock")
    fl_bad = synergy_foresight_lines(p_bad, reg, area_id="mountain_rock", brief=True)
    log(
        "synergy",
        f"ok={syn_ok.get('mode')} bad={syn_bad.get('mode')} "
        f"mor_ok={relic_area_synergy_morale_factor(p, reg):.2f} "
        f"mor_bad={relic_area_synergy_morale_factor(p_bad, reg):.2f}",
    )
    scores["synergy"] = (
        5
        if syn_ok.get("mode") == SYN_RESONATE
        and syn_bad.get("mode") == SYN_AREA_TENSION
        and fl_ok
        and fl_bad
        else 2
    )

    # H4 moment feel
    a0 = anima_value(p)
    ml = resolve_moment_choice(p, "divine_mountain_gaze", "help", reg=reg)
    log("moment", f"anima {a0:.1f}→{anima_value(p):.1f}")
    scores["moment"] = 5 if anima_value(p) > a0 + 1.0 and ml else 2

    # H5–H7 bond / chorus
    b2 = evaluate_relic_bonds(p, reg)
    p["equip_ids"]["head"] = "relic_divine_laurel"
    p["equip_rarities"]["head"] = "legendary"
    b3 = evaluate_relic_bonds(p, reg)
    on_relic_bond_pulse(p, reg, force=True)
    log("bond", f"2={b2.get('mode')} 3={b3.get('mode')}")
    scores["bond"] = (
        5
        if b2.get("mode") == BOND_RESONANCE and b3.get("mode") == BOND_CHORUS
        else 2
    )

    # H5 pulse anima feel
    p["anima"] = 48.0
    pl = try_area_synergy_presence_pulse(p, reg, area_id="mountain_rock", force=True)
    log("pulse", f"lines={len(pl)} anima={anima_value(p):.1f}")
    scores["pulse"] = 5 if pl and anima_value(p) > 48.0 else 2

    # H8 spar
    a_s0 = anima_value(p)
    sl = on_chamber_spar_with_relic(p, reg, rounds=2)
    log("spar", f"{a_s0:.1f}→{anima_value(p):.1f}")
    scores["spar"] = 5 if sl else 2

    # H3 foresight panel
    gaze = area_world_gaze_lines(p, reg, area_id="mountain_rock", force=True)
    dfl = soft_dungeon_entry_warnings(p, reg)
    log("foresight", f"gaze={len(gaze)} dungeon={len(dfl)}")
    scores["foresight"] = 5 if gaze and len(dfl) >= 4 else 2

    # H9 auto area tension
    p3 = create_player(reg, "wo047a", "warrior", "เมษ")
    p3["level"] = 1
    ensure_needs(p3)
    ensure_progression(p3, reg)
    ensure_stat_arch(p3)
    prefs = ensure_auto_prefs(p3)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p3["auto_prefs"] = prefs
    p3["location"] = "crystal_peak"
    p3["anima"] = 34.0
    p3["needs"]["morale"] = 30
    p3["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p3["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}
    before = sum(1 for v in p3["equip_ids"].values() if v)
    uneq = try_auto_unequip_burden(p3, reg)
    after = sum(1 for v in (p3.get("equip_ids") or {}).values() if v)
    log("auto", f"{before}→{after} notes={bool(uneq)}")
    scores["auto"] = 5 if uneq and after < before else 2

    # fight
    wins = 0
    p["hp"] = int(p.get("max_hp") or 90)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(140 + i), "mountain_rock")
        if any("ชนะ" in str(x) for x in fl):
            wins += 1
    log("fight", f"wins={wins}/3")
    scores["auto_fight"] = 5 if wins >= 2 else 1

    avg = sum(scores.values()) / len(scores)
    all_pass = all(v >= 3 for v in scores.values())
    out = ROOT / "exports"
    out.mkdir(exist_ok=True)
    payload = {
        "version": APP_VERSION,
        "scores": scores,
        "notes": notes,
        "all_pass": all_pass,
        "avg": avg,
        "polish": [
            "synergy foresight tone (less jargon)",
            "presence pulse more present (24% · throttle 3 · band soft)",
            "area tension morale 1.09 · resonate 0.96",
            "soft cap medium feel · clearer soft_cap text",
        ],
        "human_feedback": "fill exports/WO047_HUMAN_FEEDBACK.md",
    }
    (out / "wo047_playtest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-047 Human Feedback Polish · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        f"**คู่มือ:** [`docs/WO047_HUMAN_PLAYTEST.md`](../docs/WO047_HUMAN_PLAYTEST.md)\n\n",
        f"**แบบฟอร์มมือ:** [`exports/WO047_HUMAN_FEEDBACK.md`](WO047_HUMAN_FEEDBACK.md)\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## Feel polish applied\n\n")
    for x in payload["polish"]:
        md.append(f"- {x}\n")
    md.append("\n## Feedback มือ (session นี้)\n\n")
    md.append(
        "Harness ยืนยัน synergy contrast + anima pulse + auto ถอด — "
        "คะแนน Feel 1–5 จากผู้เล่น **รอกรอก** ใน `WO047_HUMAN_FEEDBACK.md`\n\n"
    )
    md.append("## จุดแข็ง / อ่อน + WO-048\n\n")
    md.append(
        "**แข็ง:** ตรง/ขัดพื้นที่ต่างชัด · Anima pulse รู้สึกขึ้น · Auto tension · DNA ล็อก\n\n"
    )
    md.append(
        "**อ่อน:** ยังรอฟอร์มมือจริง · appraisal ยังไม่มี · chorus×moment tone ยังบาง\n\n"
    )
    md.append(
        "**WO-048 แนะนำ:** Soft Appraisal / Feel layer lite "
        "**หรือ** hotfix จากฟอร์มมือถัดไป\n"
    )
    (out / "WO047_PLAYTEST_LOG.md").write_text("".join(md), encoding="utf-8")
    fb = out / "WO047_HUMAN_FEEDBACK.md"
    if not fb.exists():
        fb.write_text(
            "# WO-047 Human Feedback (กรอกมือ)\n\n"
            "คัดลอกแบบฟอร์มจาก `docs/WO047_HUMAN_PLAYTEST.md` §2 มาวางที่นี่\n\n"
            f"เวอร์ชันตอน ship harness: `{APP_VERSION}`\n\n"
            "## Feel 1–5 (สรุป)\n\n"
            "| หัวข้อ | คะแนน |\n|--------|:------:|\n"
            "| Anima | __/5 |\n"
            "| Relic×Area Synergy | __/5 |\n"
            "| Auto + Synergy | __/5 |\n"
            "| โลกมีชีวิต | __/5 |\n\n"
            "## Hotfix ที่ต้องการ\n\n1. …\n2. …\n3. …\n",
            encoding="utf-8",
        )
    print(f"WO-047 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
