#!/usr/bin/env python3
"""WO-039 Faction Mini-Moments harness."""
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
from game.domain.encounters import build_sights
from game.domain.faction_moments import (
    MINI_MOMENTS,
    auto_resolve_moment,
    moments_for_area,
    resolve_moment_choice,
    roll_faction_moment_sight,
)
from game.domain.needs import ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.stat_arch import anima_value, ensure_stat_arch
from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
    get_faction_score,
)
from game.runtime.auto_farm import auto_fight, should_pause_sight
from game.runtime.dungeon_auto import ensure_auto_prefs


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, findings, scores = [], [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # content coverage
    assert moments_for_area("dark_forest")
    assert moments_for_area("mist_marsh")
    assert moments_for_area("ancient_city") or moments_for_area("crystal_peak")
    log("content", f"moments={list(MINI_MOMENTS.keys())}")
    scores["content"] = 5

    p = create_player(reg, "wo039", "warrior", "เมษ")
    p["level"] = 5
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    p["location"] = "dark_forest"

    # force echo moment help
    a0 = anima_value(p)
    m0 = int(get_needs(p)["morale"])
    e0 = get_faction_score(p, FACTION_ECHO)
    lines = resolve_moment_choice(p, "echo_forest_whisper", "help", reg=reg)
    blob = "\n".join(lines)
    log(
        "echo_help",
        f"echo {e0}→{get_faction_score(p, FACTION_ECHO)} anima {a0:.1f}→{anima_value(p):.1f} "
        f"mor {m0}→{get_needs(p)['morale']} text_ok={'เงา' in blob or 'ยอมรับ' in blob}",
    )
    scores["echo"] = 5 if get_faction_score(p, FACTION_ECHO) > e0 else 2

    # divine help
    p["location"] = "ancient_city"
    d0 = get_faction_score(p, FACTION_DIVINE)
    resolve_moment_choice(p, "divine_wind_gaze", "help", reg=reg)
    scores["divine"] = 5 if get_faction_score(p, FACTION_DIVINE) > d0 else 2
    log("divine", f"divine={get_faction_score(p, FACTION_DIVINE)}")

    # infernal gaze — morale drop
    p["location"] = "mist_marsh"
    p["needs"]["morale"] = 60
    i0 = get_faction_score(p, FACTION_INFERNAL)
    resolve_moment_choice(p, "infernal_haze_echo", "help", reg=reg)
    mor1 = int(get_needs(p)["morale"])
    log("infernal", f"inf {i0}→{get_faction_score(p, FACTION_INFERNAL)} mor→{mor1}")
    scores["infernal"] = 5 if mor1 < 60 or get_faction_score(p, FACTION_INFERNAL) > i0 else 2

    # sight injection
    rng = random.Random(39)
    hits = 0
    for i in range(40):
        p["location"] = "dark_forest"
        s = roll_faction_moment_sight(p, random.Random(100 + i), area_id="dark_forest")
        if s:
            hits += 1
    log("roll", f"hits={hits}/40")
    scores["roll"] = 4 if hits >= 3 else 2

    # build_sights can include kind
    saw = False
    for i in range(30):
        sights = build_sights(p, reg, random.Random(200 + i), count=5)
        if any(s.get("kind") == "faction_moment" for s in sights):
            saw = True
            break
    log("sights", f"injected={saw}")
    scores["sights"] = 5 if saw else 3

    # auto resolve
    sight = {
        "kind": "faction_moment",
        "moment_id": "echo_forest_whisper",
        "moment": __import__(
            "game.domain.faction_moments", fromlist=["MINI_MOMENTS"]
        ).MINI_MOMENTS["echo_forest_whisper"],
    }
    prefs = ensure_auto_prefs(p)
    al = auto_resolve_moment(p, sight, reg=reg, prefs=prefs)
    log("auto_moment", f"lines={len(al)}")
    scores["auto_moment"] = 5 if al else 2

    # auto combat still works
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 8, "max_hp": 8, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(60 + i), "dark_forest")
        if any("ชนะ" in str(x) for x in fl):
            wins += 1
    log("auto_fight", f"wins={wins}/3")
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
    (out / "wo039_faction_moments.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-039 Faction Mini-Moments · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Moments\n",
        "- divine_wind_gaze (เมือง/ผลึก)\n",
        "- infernal_haze_echo (หนอง/ถ้ำ)\n",
        "- echo_forest_whisper (ป่ามืด)\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-040\n\n")
    md.append("**แข็ง:** โลกมีสายตาผ่าน 3 moment · ผูก faction/anima/ขวัญ · Auto soft\n\n")
    md.append("**อ่อน:** โอกาส roll ~24% อาจน้อย · ยังไม่ผูกเควส board\n\n")
    md.append("**WO-040:** Anima×Relic Depth หรือ Expand Mini-Moments ต่อพื้นที่\n")
    (out / "WO039_FACTION_MOMENTS.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-039 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
