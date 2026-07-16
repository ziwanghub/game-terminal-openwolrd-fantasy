#!/usr/bin/env python3
"""WO-045 Playtest Polish — aggregate smoke harness (Human guide companion)."""
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
from game.domain.faction_moments import (
    MINI_MOMENTS,
    moments_for_area,
    resolve_moment_choice,
)
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    BOND_CHORUS,
    BOND_RESONANCE,
    evaluate_relic_bonds,
    on_chamber_spar_with_relic,
    on_relic_bond_pulse,
    on_relic_equip_depth,
)
from game.domain.soft_foresight import (
    area_world_gaze_lines,
    soft_dungeon_entry_warnings,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs


AREAS = [
    "dark_forest",
    "mist_marsh",
    "cave_shadow",
    "desert_heat",
    "crystal_peak",
    "mountain_rock",
    "ancient_city",
    "void_rift",
]


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    scores: dict = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # H1 Needs smoke
    p = create_player(reg, "wo045", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    for _ in range(3):
        apply_needs_event(p, "explore")
    n = get_needs(p)
    log("needs", f"h={n.get('hunger')} f={n.get('fatigue')} m={n.get('morale')}")
    scores["needs"] = 5 if all(k in n for k in ("hunger", "fatigue", "morale")) else 1

    # Moments coverage
    missing = [a for a in AREAS if not moments_for_area(a)]
    log("moments", f"total={len(MINI_MOMENTS)} missing={missing}")
    scores["moments"] = 5 if not missing and len(MINI_MOMENTS) >= 9 else 1

    # Foresight full + brief
    p["location"] = "crystal_peak"
    full = area_world_gaze_lines(p, reg, area_id="crystal_peak", force=True)
    brief1 = area_world_gaze_lines(
        p, reg, area_id="crystal_peak", brief=True, include_moment_hint=True
    )
    p["auto_ticks"] = 10
    brief2 = area_world_gaze_lines(
        p, reg, area_id="crystal_peak", brief=True, include_moment_hint=True
    )
    # brief2 soon after brief1 should throttle empty or short
    log("foresight", f"full={len(full)} brief1={len(brief1)} brief2={len(brief2)}")
    scores["foresight"] = 5 if full and brief1 and len(full) >= len(brief1) else 2

    # Dungeon foresight panel
    dfl = soft_dungeon_entry_warnings(p, reg)
    blob = "\n".join(dfl)
    scores["dungeon_fs"] = (
        5 if ("กายใจ" in blob or "Foresight" in blob) and len(dfl) >= 4 else 2
    )
    log("dungeon_fs", f"lines={len(dfl)}")

    # Relic single equip depth
    p["anima"] = 50.0
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    a0 = anima_value(p)
    el = on_relic_equip_depth(p, reg, item_id="relic_storm_fang", item_name="เขี้ยว")
    log("relic_single", f"anima {a0:.1f}→{anima_value(p):.1f} lines={len(el)}")
    scores["relic_single"] = 5 if anima_value(p) >= a0 and el else 2

    # Bond 2
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    b2 = evaluate_relic_bonds(p, reg)
    on_relic_bond_pulse(p, reg, force=True)
    log("bond2", f"mode={b2.get('mode')}")
    scores["bond2"] = 5 if b2.get("mode") == BOND_RESONANCE else 1

    # Chorus 3
    p["equip_ids"]["head"] = "relic_divine_laurel"
    p["equip_rarities"]["head"] = "legendary"
    b3 = evaluate_relic_bonds(p, reg)
    a_c0 = anima_value(p)
    cl = on_relic_bond_pulse(p, reg, force=True)
    log("chorus3", f"mode={b3.get('mode')} lines={len(cl)} anima={anima_value(p):.1f}")
    scores["chorus3"] = (
        5
        if b3.get("mode") == BOND_CHORUS and b3.get("faction") == FACTION_DIVINE
        else 1
    )

    # Chamber spar
    sl = on_chamber_spar_with_relic(p, reg, rounds=2)
    log("spar", f"lines={len(sl)} anima={anima_value(p):.1f}")
    scores["spar"] = 5 if sl else 2

    # Moment resolve
    ml = resolve_moment_choice(p, "divine_mountain_gaze", "help", reg=reg)
    log("moment", f"lines={len(ml)}")
    scores["moment"] = 5 if ml else 1

    # Auto unequip soft cap / frail path
    p4 = create_player(reg, "wo045a", "warrior", "เมษ")
    p4["level"] = 1
    ensure_needs(p4)
    ensure_progression(p4, reg)
    ensure_stat_arch(p4)
    prefs = ensure_auto_prefs(p4)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p4["auto_prefs"] = prefs
    p4["anima"] = 12.0
    p4["needs"]["morale"] = 28
    p4["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
    }
    p4["equip_rarities"] = {k: "legendary" for k in p4["equip_ids"]}
    before = sum(1 for v in p4["equip_ids"].values() if v)
    uneq = try_auto_unequip_burden(p4, reg)
    after = sum(1 for v in (p4.get("equip_ids") or {}).values() if v)
    log("auto_uneq", f"before={before} after={after} notes={bool(uneq)}")
    scores["auto_uneq"] = 5 if uneq and after < before else 2

    # Auto fight
    wins = 0
    p["hp"] = int(p.get("max_hp") or 90)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(120 + i), "dark_forest")
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
            "travel re-visit brief gaze",
            "moment chance first/later curve",
            "equip multi less double text",
            "soft_cap / foresight throttle",
        ],
    }
    (out / "wo045_playtest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-045 Playtest Polish · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        f"**คู่มือมือ:** [`docs/WO045_HUMAN_PLAYTEST.md`](../docs/WO045_HUMAN_PLAYTEST.md)\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for nline in notes:
        md.append(f"- {nline}\n")
    md.append("\n## Polish applied (เฟส 2)\n\n")
    for x in payload["polish"]:
        md.append(f"- {x}\n")
    md.append("\n## จุดแข็ง / จุดอ่อน + WO-046\n\n")
    md.append(
        "**แข็ง:** วงจร Needs→Anima→Relic→Bond/Chorus→Moment→Foresight ครบ · "
        "Auto ถอด/ไฟต์ · harness ล็อก\n\n"
    )
    md.append(
        "**อ่อน:** feedback มือจริงยังรอผู้เล่นกรอกแบบฟอร์ม · "
        "Relic×Moment synergy ยังไม่มี · soft fail Anima ยังหายาก\n\n"
    )
    md.append(
        "**WO-046 แนะนำ:** Relic×Moment soft synergy lite "
        "**หรือ** Personal/ soft social ถัดไปถ้า DNA ล็อกแล้ว\n"
    )
    (out / "WO045_PLAYTEST_LOG.md").write_text("".join(md), encoding="utf-8")
    # feedback template stub for human
    fb = out / "WO045_HUMAN_FEEDBACK.md"
    if not fb.exists():
        fb.write_text(
            "# WO-045 Human Feedback (กรอกมือ)\n\n"
            "คัดลอกแบบฟอร์มจาก `docs/WO045_HUMAN_PLAYTEST.md` §2 มาวางที่นี่\n\n"
            f"เวอร์ชันตอน ship harness: `{APP_VERSION}`\n",
            encoding="utf-8",
        )
    print(f"WO-045 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
