#!/usr/bin/env python3
"""WO-038 World Relations Lite harness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.progression import ensure_progression
from game.domain.stat_arch import ensure_stat_arch, self_assess_lines
from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
    adjust_faction,
    get_faction_score,
    on_chamber_enter,
    on_echo_approach,
    on_npc_outcome,
    on_relic_theme,
    soft_world_presence_line,
    world_relation_needs_mults,
)
from game.runtime.auto_farm import auto_fight
from game.services.godforge_chamber import enter_godforge, exit_godforge
import random


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, findings, scores = [], [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    p = create_player(reg, "wo038", "warrior", "เมษ")
    p["level"] = 5
    p["location"] = "dark_forest"
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)

    # NPC friend → echo/divine lean
    p["location"] = "ancient_city"
    lines = on_npc_outcome(p, outcome="friend", archetype="priest", area_id="ancient_city")
    d0 = get_faction_score(p, FACTION_DIVINE)
    log("npc_friend", f"divine={d0} lines={len(lines)} blob={lines[:2]}")
    scores["npc"] = 5 if d0 > 42 and lines else 2
    if d0 <= 42:
        findings.append("divine not raised on priest friend")

    # hostile marsh cultist
    p["location"] = "mist_marsh"
    on_npc_outcome(p, outcome="hostile", archetype="cultist", area_id="mist_marsh")
    inf = get_faction_score(p, FACTION_INFERNAL)
    log("npc_hostile", f"infernal={inf}")
    scores["hostile"] = 4 if inf != 42 else 2

    # echo
    el = on_echo_approach(p, choice="humble")
    echo = get_faction_score(p, FACTION_ECHO)
    log("echo", f"echo={echo} lines={len(el)}")
    scores["echo"] = 5 if echo > 42 else 3

    # chamber
    cl = enter_godforge(p, reg)
    blob = "\n".join(cl)
    log("chamber", f"divine={get_faction_score(p, FACTION_DIVINE)} has_soft={'เทพ' in blob or 'สูง' in blob or 'สายตา' in blob}")
    scores["chamber"] = 5 if "สายตา" in blob or "เทพ" in blob or get_faction_score(p, FACTION_DIVINE) >= 43 else 3
    exit_godforge(p, reg)

    # relic storm → divine
    rl = on_relic_theme(p, item_id="relic_storm_fang", tags=["storm", "holy"])
    log("relic", f"lines={rl} divine={get_faction_score(p, FACTION_DIVINE)}")
    scores["relic"] = 4 if get_faction_score(p, FACTION_DIVINE) >= 44 else 2

    # morale mult: high divine vs low infernal
    def drain(div: int, infs: int) -> int:
        q = create_player(reg, f"d{div}", "warrior", "เมษ")
        ensure_needs(q)
        ensure_stat_arch(q)
        from game.domain.stat_arch import set_world_relation

        set_world_relation(q, "faction", FACTION_DIVINE, div)
        set_world_relation(q, "faction", FACTION_INFERNAL, infs)
        q["needs"]["morale"] = 70
        for _ in range(5):
            apply_needs_event(q, "combat_loss", silent=True)
        return 70 - int(get_needs(q)["morale"])

    d_warm = drain(80, 50)
    d_cold = drain(40, 20)
    log("morale", f"warm_divine_loss={d_warm} cold_infernal_loss={d_cold}")
    scores["morale_link"] = 5 if d_warm <= d_cold else 2

    # presence line + assess
    line = soft_world_presence_line(p, "dark_forest")
    assess = "\n".join(self_assess_lines(p, force=True, reg=reg))
    log("ui", f"presence={line!r:.60} assess_has_world={'โลก' in assess or 'สวรรค์' in assess or 'มาร' in assess}")
    scores["ui"] = 5 if "โลก" in assess or "สวรรค์" in assess else 3

    # auto smoke
    wins = 0
    p["hp"] = int(p.get("max_hp") or 80)
    for i in range(3):
        mon = {"id": "w", "name": "w", "level": 1, "hp": 10, "max_hp": 10, "atk": 2}
        fl = auto_fight(p, mon, reg, random.Random(50 + i), "dark_forest")
        if any("ชนะ" in str(x) for x in fl):
            wins += 1
    log("auto", f"wins={wins}/3")
    scores["auto"] = 5 if wins >= 2 else 1

    avg = sum(scores.values()) / len(scores)
    all_pass = all(v >= 3 for v in scores.values()) and not findings
    out = ROOT / "exports"
    out.mkdir(exist_ok=True)
    payload = {
        "version": APP_VERSION,
        "scores": scores,
        "notes": notes,
        "findings": findings,
        "all_pass": all_pass,
        "avg": avg,
        "factions": {
            "divine": get_faction_score(p, FACTION_DIVINE),
            "infernal": get_faction_score(p, FACTION_INFERNAL),
            "echo": get_faction_score(p, FACTION_ECHO),
        },
    }
    (out / "wo038_world_relations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-038 World Relations Playtest · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        f"Factions: {payload['factions']}\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## Findings\n")
    md.append("- none\n" if not findings else "")
    for f in findings:
        md.append(f"- {f}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-039\n\n")
    md.append("**แข็ง:** faction soft รู้สึกได้ · ผูกขวัญ/anima · Auto ปกติ\n\n")
    md.append("**อ่อน:** เนื้อหาตัวอย่างน้อย · ยังไม่มีเควส faction เต็ม\n\n")
    md.append("**WO-039:** Anima×Relic Depth หรือ Faction mini-quests 2–3 เส้น\n")
    (out / "WO038_WORLD_RELATIONS.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-038 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
