#!/usr/bin/env python3
"""WO-031 quick check — cave + desert loops present and wired."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.soft_foresight import area_loop_soft_lines


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    report = {"version": APP_VERSION, "wo": "WO-031", "areas": {}}
    ok = True
    for aid, qids, boss_dep in (
        (
            "cave_shadow",
            ["cave_bat_cull", "cave_lantern_path"],
            ("shadow_slayer", "cave_lantern_path"),
        ),
        (
            "desert_heat",
            ["desert_dune_walk", "desert_scorpion_cull", "desert_sun_ready"],
            ("sun_end", "desert_sun_ready"),
        ),
    ):
        area = (reg.areas or {}).get(aid) or {}
        tips = list(area.get("loop_soft") or [])
        missing = [q for q in qids if q not in (reg.quests or {})]
        boss_q, need = boss_dep
        deps = ((reg.quests or {}).get(boss_q) or {}).get("depends_on") or []
        boss_ok = need in deps
        p = create_player(reg, f"c_{aid}", "warrior", "เมษ")
        p["location"] = aid
        soft = area_loop_soft_lines(p, reg)
        block = {
            "loop_soft": tips,
            "missing_quests": missing,
            "boss_dep_ok": boss_ok,
            "travel_tips": soft,
            "pass": not missing and bool(tips) and boss_ok and bool(soft),
        }
        report["areas"][aid] = block
        ok = ok and block["pass"]
    report["all_pass"] = ok
    out = ROOT / "exports" / "wo031_area_loops.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# WO-031 Area Loop Check",
        "",
        f"**version:** `{APP_VERSION}`  ",
        f"**all_pass:** {ok}",
        "",
        "| area | pass | notes |",
        "|------|:----:|-------|",
    ]
    for aid, b in report["areas"].items():
        md.append(
            f"| {aid} | {'✅' if b['pass'] else '❌'} | "
            f"quests_ok={not b['missing_quests']} boss_dep={b['boss_dep_ok']} |"
        )
    md.append("")
    md.append("## Chains")
    md.append("- cave: delver → bat cull → lantern path → **shadow_slayer**")
    md.append("- desert: dune walk → scorpion cull → sun ready → **sun_end** (+ titan/shadow)")
    (ROOT / "exports" / "WO031_AREA_LOOPS.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
