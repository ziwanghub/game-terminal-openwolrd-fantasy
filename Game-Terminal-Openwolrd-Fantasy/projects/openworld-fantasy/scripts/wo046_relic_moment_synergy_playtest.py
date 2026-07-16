#!/usr/bin/env python3
"""WO-046 Relic × Moment Soft Synergy harness."""
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
from game.domain.faction_moments import resolve_moment_choice, roll_faction_moment_sight
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    SYN_AREA_TENSION,
    SYN_RESONATE,
    evaluate_relic_area_synergy,
    moment_chance_factor,
    on_chamber_spar_with_relic,
    relic_equipped_morale_mult,
    synergy_foresight_lines,
    try_area_synergy_presence_pulse,
)
from game.domain.soft_foresight import area_world_gaze_lines
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_INFERNAL
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    scores: dict = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # resonate divine mountain
    p = create_player(reg, "wo046", "warrior", "เมษ")
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
    syn = evaluate_relic_area_synergy(p, reg, area_id="mountain_rock")
    fac = moment_chance_factor(p, reg, area_id="mountain_rock")
    log("resonate", f"mode={syn.get('mode')} fac={fac:.2f}")
    scores["resonate"] = 5 if syn.get("mode") == SYN_RESONATE and fac > 1.2 else 1

    # tension hell on mountain
    p2 = create_player(reg, "wo046t", "warrior", "เมษ")
    ensure_stat_arch(p2)
    p2["location"] = "mountain_rock"
    p2["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p2["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}
    st = evaluate_relic_area_synergy(p2, reg, area_id="mountain_rock")
    mult = relic_equipped_morale_mult(p2, reg)
    log("tension", f"mode={st.get('mode')} mult={mult:.2f}")
    scores["tension"] = (
        5 if st.get("mode") == SYN_AREA_TENSION and mult > 1.05 else 1
    )

    # foresight
    fl = synergy_foresight_lines(p, reg, area_id="mountain_rock")
    gaze = area_world_gaze_lines(p, reg, area_id="mountain_rock", force=True)
    blob = "\n".join(gaze + fl)
    log("foresight", f"syn_lines={len(fl)} gaze={len(gaze)}")
    scores["foresight"] = 5 if fl and ("สะท้อน" in blob or "เรลิก" in blob) else 2

    # moment resolve boost
    a0 = anima_value(p)
    ml = resolve_moment_choice(p, "divine_mountain_gaze", "help", reg=reg)
    log("moment", f"anima {a0:.1f}→{anima_value(p):.1f} lines={len(ml)}")
    scores["moment"] = 5 if anima_value(p) > a0 + 1.0 and ml else 2

    # presence pulse
    p["anima"] = 48.0
    pl = try_area_synergy_presence_pulse(p, reg, area_id="mountain_rock", force=True)
    log("pulse", f"lines={len(pl)}")
    scores["pulse"] = 5 if pl else 2

    # spar synergy
    a_s0 = anima_value(p)
    sl = on_chamber_spar_with_relic(p, reg, rounds=2)
    log("spar", f"anima {a_s0:.1f}→{anima_value(p):.1f}")
    scores["spar"] = 5 if sl else 2

    # moment rolls with resonate
    hits = 0
    p["_faction_moments_seen"] = 0
    for i in range(50):
        if roll_faction_moment_sight(p, random.Random(i + 5), area_id="mountain_rock"):
            hits += 1
    log("rolls", f"hits={hits}/50")
    scores["rolls"] = 4 if hits >= 5 else 2

    # auto unequip area tension
    p3 = create_player(reg, "wo046a", "warrior", "เมษ")
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
    log("auto", f"before={before} after={after} notes={bool(uneq)}")
    scores["auto"] = 5 if uneq and after < before else 2

    # fight smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 90)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        flines = auto_fight(p, mon, reg, random.Random(130 + i), "mountain_rock")
        if any("ชนะ" in str(x) for x in flines):
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
    }
    (out / "wo046_relic_moment_synergy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-046 Relic × Moment Synergy · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-047\n\n")
    md.append(
        "**แข็ง:** เรลิก×พื้นที่ resonate/tension · moment chance · foresight · auto\n\n"
    )
    md.append(
        "**อ่อน:** synergy ยัง soft บาง · ยังไม่ผูก bond 3-piece กับ moment โดยตรงลึก\n\n"
    )
    md.append(
        "**WO-047:** Human feedback round หลัง synergy **หรือ** soft appraisal/feel layer\n"
    )
    (out / "WO046_RELIC_MOMENT_SYNERGY.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-046 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
