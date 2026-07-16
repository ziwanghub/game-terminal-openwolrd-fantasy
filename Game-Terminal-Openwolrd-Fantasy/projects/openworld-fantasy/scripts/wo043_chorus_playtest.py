#!/usr/bin/env python3
"""WO-043 Soft Chorus + Soft Cap harness."""
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
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    BOND_CHORUS,
    BOND_RESONANCE,
    evaluate_relic_bonds,
    on_chamber_spar_with_relic,
    on_relic_bond_pulse,
    relic_equipped_morale_mult,
    try_relic_explore_whisper,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO, FACTION_INFERNAL
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    scores: dict = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # 2-piece resonance baseline
    p2 = create_player(reg, "wo043r", "warrior", "เมษ")
    ensure_stat_arch(p2)
    p2["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p2["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    b2 = evaluate_relic_bonds(p2, reg)
    log("resonance", f"mode={b2.get('mode')} n={b2.get('count')}")
    scores["resonance"] = 5 if b2.get("mode") == BOND_RESONANCE else 1

    # 3-piece divine chorus
    p = create_player(reg, "wo043", "warrior", "เมษ")
    p["level"] = 2
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    p["anima"] = 48.0
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
    }
    p["equip_rarities"] = {k: "legendary" for k in p["equip_ids"]}
    b3 = evaluate_relic_bonds(p, reg)
    a0 = anima_value(p)
    lines = on_relic_bond_pulse(p, reg, force=True)
    mult = relic_equipped_morale_mult(p, reg)
    log(
        "chorus_div",
        f"mode={b3.get('mode')} n={b3.get('count')} anima {a0:.1f}→{anima_value(p):.1f} mult={mult:.2f} lines={len(lines)}",
    )
    scores["chorus_divine"] = (
        5
        if b3.get("mode") == BOND_CHORUS
        and b3.get("faction") == FACTION_DIVINE
        and anima_value(p) > a0
        and mult < 0.85
        else 2
    )

    # infernal + echo chorus
    pi = create_player(reg, "wo043i", "warrior", "เมษ")
    ensure_stat_arch(pi)
    pi["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
        "legs": "relic_hell_ash_greaves",
    }
    pi["equip_rarities"] = {
        "main_hand": "divine",
        "acc_1": "legendary",
        "legs": "legendary",
    }
    bi = evaluate_relic_bonds(pi, reg)
    on_relic_bond_pulse(pi, reg, force=True)
    log("chorus_inf", f"mode={bi.get('mode')} fac={bi.get('faction')}")
    scores["chorus_infernal"] = (
        5 if bi.get("mode") == BOND_CHORUS and bi.get("faction") == FACTION_INFERNAL else 1
    )

    pe = create_player(reg, "wo043e", "warrior", "เมษ")
    ensure_stat_arch(pe)
    pe["equip_ids"] = {
        "body": "relic_echo_shroud",
        "acc_1": "relic_void_whisper_ring",
        "feet": "relic_echo_sandals",
    }
    pe["equip_rarities"] = {k: "legendary" for k in pe["equip_ids"]}
    be = evaluate_relic_bonds(pe, reg)
    on_relic_bond_pulse(pe, reg, force=True)
    log("chorus_echo", f"mode={be.get('mode')} fac={be.get('faction')}")
    scores["chorus_echo"] = (
        5 if be.get("mode") == BOND_CHORUS and be.get("faction") == FACTION_ECHO else 1
    )

    # soft cap 4+
    pc = create_player(reg, "wo043c", "warrior", "เมษ")
    ensure_needs(pc)
    ensure_stat_arch(pc)
    pc["anima"] = 75.0
    pc["needs"]["morale"] = 48
    pc["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
        "off_hand": "relic_divine_laurel",
    }
    pc["equip_rarities"] = {k: "legendary" for k in pc["equip_ids"]}
    bc = evaluate_relic_bonds(pc, reg)
    clines = on_relic_bond_pulse(pc, reg, force=True)
    log(
        "soft_cap",
        f"mode={bc.get('mode')} cap={bc.get('soft_cap')} n={bc.get('count')} lines={len(clines)}",
    )
    scores["soft_cap"] = 5 if bc.get("soft_cap") and bc.get("mode") == BOND_CHORUS else 2

    # spar chorus
    a_s0 = anima_value(p)
    sl = on_chamber_spar_with_relic(p, reg, rounds=2)
    log("spar", f"anima {a_s0:.1f}→{anima_value(p):.1f} lines={len(sl)}")
    scores["spar"] = 5 if sl else 2

    # explore whisper under echo chorus
    hits = 0
    for i in range(35):
        pe["time_units"] = 3000 + i
        pe["auto_ticks"] = 300 + i
        if try_relic_explore_whisper(pe, reg, random.Random(i + 11), area_id="void_rift"):
            hits += 1
    log("whisper", f"hits={hits}/35")
    scores["whisper"] = 4 if hits >= 2 else 2

    # auto soft cap
    p4 = create_player(reg, "wo043a", "warrior", "เมษ")
    p4["level"] = 1
    ensure_needs(p4)
    ensure_progression(p4, reg)
    ensure_stat_arch(p4)
    prefs = ensure_auto_prefs(p4)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p4["auto_prefs"] = prefs
    p4["anima"] = 32.0
    p4["needs"]["morale"] = 28
    p4["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
        "head": "relic_divine_laurel",
        "off_hand": "relic_storm_fang",
    }
    p4["equip_rarities"] = {k: "legendary" for k in p4["equip_ids"]}
    sync_n = len(p4["equip_ids"])
    uneq = try_auto_unequip_burden(p4, reg)
    left = sum(1 for v in (p4.get("equip_ids") or {}).values() if v)
    log("auto", f"uneq={bool(uneq)} before={sync_n} left={left}")
    scores["auto"] = 5 if uneq and left < sync_n else 2

    # fight smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(100 + i), "crystal_peak")
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
    }
    (out / "wo043_chorus.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-043 Soft Chorus + Cap · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-044\n\n")
    md.append("**แข็ง:** 2=Resonance · 3+=Chorus ชัด · Soft Cap กัน stack · Auto บางคณะ\n\n")
    md.append("**อ่อน:** ชิ้นที่ 4 ต้องซ้อน slot แปลก · mountain/city ยัง moment บาง\n\n")
    md.append("**WO-044:** Area loop flavor polish + foresight ใบ้ moment\n")
    (out / "WO043_CHORUS.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-043 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
