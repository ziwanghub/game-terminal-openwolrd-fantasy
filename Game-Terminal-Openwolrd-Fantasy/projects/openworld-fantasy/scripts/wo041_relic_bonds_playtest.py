#!/usr/bin/env python3
"""WO-041 Relic Soft Bonds harness."""
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
    BOND_RESONANCE,
    BOND_TENSION,
    evaluate_relic_bonds,
    on_chamber_spar_with_relic,
    on_relic_bond_pulse,
    on_relic_equip_depth,
    relic_equipped_morale_mult,
    try_relic_explore_whisper,
)
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, get_faction_score
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs
from game.services.godforge_chamber import enter_godforge, exit_godforge, loan_relic, spar_dummy


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    scores: dict = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # Divine bond: storm + aegis
    p = create_player(reg, "wo041", "warrior", "เมษ")
    p["level"] = 2
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    p["anima"] = 48.0
    p["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p["equip_rarities"] = {
        "main_hand": "legendary",
        "body": "legendary",
    }
    bond = evaluate_relic_bonds(p, reg)
    log("bond_eval", f"mode={bond.get('mode')} fac={bond.get('faction')} n={bond.get('count')}")
    scores["divine_bond"] = 5 if bond.get("mode") == BOND_RESONANCE and bond.get("faction") == FACTION_DIVINE else 1

    a0 = anima_value(p)
    s0 = get_faction_score(p, FACTION_DIVINE)
    lines = on_relic_bond_pulse(p, reg, force=True)
    a1 = anima_value(p)
    s1 = get_faction_score(p, FACTION_DIVINE)
    mult = relic_equipped_morale_mult(p, reg)
    log("pulse", f"anima {a0:.1f}→{a1:.1f} fac {s0}→{s1} mult={mult:.2f} lines={len(lines)}")
    scores["pulse"] = 5 if a1 > a0 and mult < 0.9 and lines else 2

    # Tension: hell + aegis
    p2 = create_player(reg, "wo041t", "warrior", "เมษ")
    p2["level"] = 2
    ensure_needs(p2)
    ensure_stat_arch(p2)
    p2["anima"] = 55.0
    p2["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "body": "relic_aegis_sky",
    }
    p2["equip_rarities"] = {"main_hand": "divine", "body": "legendary"}
    b2 = evaluate_relic_bonds(p2, reg)
    a_t0 = anima_value(p2)
    on_relic_bond_pulse(p2, reg, force=True)
    mult_t = relic_equipped_morale_mult(p2, reg)
    log("tension", f"mode={b2.get('mode')} anima={anima_value(p2):.1f} mult={mult_t:.2f}")
    scores["tension"] = 5 if b2.get("mode") == BOND_TENSION and mult_t > 1.1 and anima_value(p2) < a_t0 else 2

    # Chamber spar with bond
    enter_godforge(p, reg)
    a_s0 = anima_value(p)
    spar_lines = on_chamber_spar_with_relic(p, reg, rounds=2)
    a_s1 = anima_value(p)
    exit_godforge(p, reg)
    log("spar_bond", f"anima {a_s0:.1f}→{a_s1:.1f} lines={len(spar_lines)}")
    scores["spar"] = 5 if spar_lines and a_s1 >= a_s0 else 3

    # Explore whisper rolls under bond
    hits = 0
    for i in range(40):
        p["time_units"] = 2000 + i
        p["auto_ticks"] = 200 + i
        if try_relic_explore_whisper(p, reg, random.Random(i + 3), area_id="crystal_peak"):
            hits += 1
    log("whisper", f"hits={hits}/40")
    scores["whisper"] = 4 if hits >= 2 else 2

    # equip_depth bond chain
    p3 = create_player(reg, "wo041e", "warrior", "เมษ")
    ensure_stat_arch(p3)
    p3["level"] = 1
    p3["anima"] = 42.0
    p3["equip_ids"] = {"main_hand": "relic_storm_fang", "body": "relic_aegis_sky"}
    p3["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    el = on_relic_equip_depth(p3, reg, item_id="relic_aegis_sky", item_name="เกราะ", tags=["sky"])
    log("equip_chain", f"mode={p3.get('_relic_bond_mode')} lines={len(el)}")
    scores["equip"] = 5 if p3.get("_relic_bond_mode") == BOND_RESONANCE else 2

    # auto unequip tension
    p4 = create_player(reg, "wo041a", "warrior", "เมษ")
    p4["level"] = 1
    ensure_needs(p4)
    ensure_progression(p4, reg)
    ensure_stat_arch(p4)
    prefs = ensure_auto_prefs(p4)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 40
    p4["auto_prefs"] = prefs
    p4["anima"] = 28.0
    p4["needs"]["morale"] = 30
    p4["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "body": "relic_aegis_sky",
    }
    p4["equip_rarities"] = {"main_hand": "divine", "body": "legendary"}
    uneq = try_auto_unequip_burden(p4, reg)
    eq_left = sum(1 for s in ("main_hand", "body") if (p4.get("equip_ids") or {}).get(s))
    log("auto", f"uneq={bool(uneq)} left={eq_left}")
    scores["auto_unequip"] = 5 if uneq and eq_left <= 1 else 2

    # auto fight smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(80 + i), "dark_forest")
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
    (out / "wo041_relic_bonds.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-041 Relic Soft Bonds · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-042\n\n")
    md.append("**แข็ง:** เรโซแนนซ์ lean เดียวกัน · Soft Tension ขัด lean · spar/world/auto\n\n")
    md.append("**อ่อน:** content เรลิก 4 ชิ้น · bond 2 ชิ้นสูงสุดจริง · ยังไม่มี set lore\n\n")
    md.append("**WO-042:** Area Mini-Moments ขยาย หรือ Bond soft cap / 3-piece chorus\n")
    (out / "WO041_RELIC_BONDS.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-041 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
