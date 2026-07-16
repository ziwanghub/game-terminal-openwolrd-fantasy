#!/usr/bin/env python3
"""WO-044 Area Moments + Soft Foresight harness."""
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
from game.domain.soft_foresight import (
    area_faction_lean,
    area_world_gaze_lines,
    soft_dungeon_entry_warnings,
)
from game.domain.stat_arch import ensure_stat_arch
from game.domain.world_relations import FACTION_DIVINE, FACTION_ECHO
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

    # every area has ≥1 moment
    missing = [a for a in AREAS if not moments_for_area(a)]
    log("coverage", f"missing={missing} total_moments={len(MINI_MOMENTS)}")
    scores["coverage"] = 5 if not missing and len(MINI_MOMENTS) >= 9 else 1

    # new moments resolve
    p = create_player(reg, "wo044", "warrior", "เมษ")
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    ok = 0
    for mid in ("divine_mountain_gaze", "divine_city_bell", "echo_void_pull"):
        if resolve_moment_choice(p, mid, "help", reg=reg):
            ok += 1
    log("resolve", f"{ok}/3")
    scores["resolve"] = 5 if ok == 3 else 2

    # rolls in void / mountain
    hits_v = hits_m = 0
    for i in range(45):
        if roll_faction_moment_sight(p, random.Random(i + 3), area_id="void_rift"):
            hits_v += 1
        if roll_faction_moment_sight(p, random.Random(i + 50), area_id="mountain_rock"):
            hits_m += 1
    log("roll", f"void={hits_v}/45 mountain={hits_m}/45")
    scores["roll"] = 4 if hits_v >= 1 and hits_m >= 1 else 2

    # foresight gaze per area
    gaze_ok = 0
    for aid in AREAS:
        p2 = create_player(reg, f"g{aid[:4]}", "warrior", "เมษ")
        ensure_stat_arch(p2)
        p2["location"] = aid
        lines = area_world_gaze_lines(p2, reg, area_id=aid, force=True)
        lean = area_faction_lean(aid)
        if lines and lean:
            gaze_ok += 1
    log("gaze", f"{gaze_ok}/{len(AREAS)}")
    scores["gaze"] = 5 if gaze_ok >= 7 else 2

    # dungeon foresight includes world
    p["location"] = "void_rift"
    fl = soft_dungeon_entry_warnings(p, reg)
    blob = "\n".join(fl)
    has_world = "ใบ้" in blob or "สายตา" in blob or "กระซิบ" in blob or "Mini-Moment" in blob
    log("dungeon_fs", f"lines={len(fl)} world={has_world}")
    scores["dungeon_fs"] = 5 if has_world and len(fl) >= 4 else 2

    # lean map spot check
    assert area_faction_lean("mountain_rock") == FACTION_DIVINE
    assert area_faction_lean("void_rift") == FACTION_ECHO
    scores["lean"] = 5

    # auto moment
    prefs = ensure_auto_prefs(p)
    al = auto_resolve_moment(
        p,
        {
            "kind": "faction_moment",
            "moment_id": "divine_city_bell",
            "moment": MINI_MOMENTS["divine_city_bell"],
        },
        reg=reg,
        prefs=prefs,
    )
    log("auto_moment", f"lines={len(al)}")
    scores["auto_moment"] = 5 if al else 2

    # fight smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        flines = auto_fight(p, mon, reg, random.Random(110 + i), "mountain_rock")
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
        "moments": len(MINI_MOMENTS),
    }
    (out / "wo044_area_foresight.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-044 Area + Foresight · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}** · moments **{len(MINI_MOMENTS)}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-045\n\n")
    md.append("**แข็ง:** ทุกพื้นที่มี moment · Soft Foresight ใบ้สายตา · Auto soft\n\n")
    md.append("**อ่อน:** foresight ซ้ำได้ถ้า force · ยังไม่มีผูก relic bond กับ moment โดยตรง\n\n")
    md.append("**WO-045:** Playtest polish รอบใหญ่ หรือ Relic×Moment soft synergy lite\n")
    (out / "WO044_AREA_FORESIGHT.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-044 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
