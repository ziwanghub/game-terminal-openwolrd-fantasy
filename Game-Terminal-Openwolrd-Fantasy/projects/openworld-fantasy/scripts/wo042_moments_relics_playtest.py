#!/usr/bin/env python3
"""WO-042 Area Mini-Moments + Relic content harness."""
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
from game.domain.faction_moments import (
    MINI_MOMENTS,
    auto_resolve_moment,
    moments_for_area,
    resolve_moment_choice,
    roll_faction_moment_sight,
)
from game.domain.needs import ensure_needs
from game.domain.progression import ensure_progression
from game.domain.relic_anima import (
    BOND_RESONANCE,
    evaluate_relic_bonds,
    on_relic_bond_pulse,
    resolve_relic_faction,
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

    # moments coverage
    areas = {
        "cave_shadow": "infernal_cave_coal",
        "desert_heat": "echo_desert_mirage",
        "crystal_peak": "divine_crystal_prayer",
    }
    ok_areas = 0
    for aid, mid in areas.items():
        pool = moments_for_area(aid)
        if any(m.get("id") == mid for m in pool):
            ok_areas += 1
    log("moments", f"new_areas={ok_areas}/3 total_moments={len(MINI_MOMENTS)}")
    scores["moments"] = 5 if ok_areas == 3 and len(MINI_MOMENTS) >= 6 else 2

    # resolve each new moment help path
    p = create_player(reg, "wo042", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    resolved = 0
    for mid in (
        "infernal_cave_coal",
        "echo_desert_mirage",
        "divine_crystal_prayer",
    ):
        lines = resolve_moment_choice(p, mid, "help", reg=reg)
        if lines:
            resolved += 1
    log("resolve", f"{resolved}/3")
    scores["resolve"] = 5 if resolved == 3 else 2

    # roll sights in desert
    hits = 0
    for i in range(40):
        s = roll_faction_moment_sight(p, random.Random(i + 9), area_id="desert_heat")
        if s and s.get("moment_id") == "echo_desert_mirage":
            hits += 1
    log("roll_desert", f"mirage_hits={hits}/40")
    scores["roll"] = 4 if hits >= 1 else 2

    # new relics lean
    assert resolve_relic_faction("relic_hell_brand_charm", reg=reg) == FACTION_INFERNAL
    assert resolve_relic_faction("relic_echo_shroud", reg=reg) == FACTION_ECHO
    hell_it = (reg.items or {}).get("relic_hell_brand_charm")
    echo_it = (reg.items or {}).get("relic_echo_shroud")
    log("relics", f"hell={bool(hell_it)} echo={bool(echo_it)}")
    scores["relics"] = 5 if hell_it and echo_it else 1

    # Infernal bond
    p2 = create_player(reg, "wo042i", "warrior", "เมษ")
    ensure_stat_arch(p2)
    p2["level"] = 2
    p2["anima"] = 50.0
    p2["equip_ids"] = {
        "main_hand": "relic_hell_ember_blade",
        "acc_1": "relic_hell_brand_charm",
    }
    p2["equip_rarities"] = {"main_hand": "divine", "acc_1": "legendary"}
    b_inf = evaluate_relic_bonds(p2, reg)
    on_relic_bond_pulse(p2, reg, force=True)
    log("bond_inf", f"mode={b_inf.get('mode')} fac={b_inf.get('faction')}")
    scores["bond_infernal"] = (
        5 if b_inf.get("mode") == BOND_RESONANCE and b_inf.get("faction") == FACTION_INFERNAL else 1
    )

    # Echo bond
    p3 = create_player(reg, "wo042e", "warrior", "เมษ")
    ensure_stat_arch(p3)
    p3["level"] = 2
    p3["anima"] = 48.0
    p3["equip_ids"] = {
        "body": "relic_echo_shroud",
        "acc_1": "relic_void_whisper_ring",
    }
    p3["equip_rarities"] = {"body": "legendary", "acc_1": "legendary"}
    b_echo = evaluate_relic_bonds(p3, reg)
    on_relic_bond_pulse(p3, reg, force=True)
    log("bond_echo", f"mode={b_echo.get('mode')} fac={b_echo.get('faction')}")
    scores["bond_echo"] = (
        5 if b_echo.get("mode") == BOND_RESONANCE and b_echo.get("faction") == FACTION_ECHO else 1
    )

    # Divine bond still works
    p4 = create_player(reg, "wo042d", "warrior", "เมษ")
    ensure_stat_arch(p4)
    p4["equip_ids"] = {
        "main_hand": "relic_storm_fang",
        "body": "relic_aegis_sky",
    }
    p4["equip_rarities"] = {"main_hand": "legendary", "body": "legendary"}
    b_div = evaluate_relic_bonds(p4, reg)
    log("bond_div", f"mode={b_div.get('mode')} fac={b_div.get('faction')}")
    scores["bond_divine"] = (
        5 if b_div.get("mode") == BOND_RESONANCE and b_div.get("faction") == FACTION_DIVINE else 1
    )

    # auto moment
    prefs = ensure_auto_prefs(p)
    al = auto_resolve_moment(
        p,
        {
            "kind": "faction_moment",
            "moment_id": "divine_crystal_prayer",
            "moment": MINI_MOMENTS["divine_crystal_prayer"],
        },
        reg=reg,
        prefs=prefs,
    )
    log("auto_moment", f"lines={len(al)}")
    scores["auto_moment"] = 5 if al else 2

    # auto fight smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(90 + i), "desert_heat")
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
    (out / "wo042_moments_relics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-042 Moments + Relics · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-043\n\n")
    md.append("**แข็ง:** moments ถ้ำ/ทะเลทราย/ผลึก · Infernal+Echo Bond ครบ · Auto soft\n\n")
    md.append("**อ่อน:** ยังไม่มี 3-piece chorus · acc ช่องเดียวจำกัด multi-bond\n\n")
    md.append("**WO-043:** Bond Soft Cap / 3-piece Chorus หรือ Area loop flavor polish\n")
    (out / "WO042_MOMENTS_RELICS.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-042 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
