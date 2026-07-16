#!/usr/bin/env python3
"""WO-032: verify mountain/crystal/city/void area loops."""
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


CHECKS = {
    "mountain_rock": {
        "quests": ["mountain_ridge_walk", "mountain_golem_cull", "mountain_titan_ready"],
        "boss": ("titan_fall", "mountain_titan_ready"),
    },
    "crystal_peak": {
        "quests": ["crystal_shard_cull", "crystal_peak_watch"],
        "boss": ("prism_sovereign_fall", "crystal_peak_watch"),
    },
    "ancient_city": {
        "quests": ["city_alley_patrol", "city_market_echo"],
        "boss": None,
    },
    "void_rift": {
        "quests": ["void_edge_walk", "void_whisper_cull"],
        "boss": None,
    },
}


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    report: dict = {"version": APP_VERSION, "wo": "WO-032", "areas": {}}
    ok = True
    for aid, cfg in CHECKS.items():
        area = (reg.areas or {}).get(aid) or {}
        tips = list(area.get("loop_soft") or [])
        missing = [q for q in cfg["quests"] if q not in (reg.quests or {})]
        boss_ok = True
        if cfg["boss"]:
            bq, need = cfg["boss"]
            deps = ((reg.quests or {}).get(bq) or {}).get("depends_on") or []
            boss_ok = need in deps
        p = create_player(reg, f"w32_{aid}", "warrior", "เมษ")
        p["location"] = aid
        soft = area_loop_soft_lines(p, reg)
        block = {
            "missing": missing,
            "loop_soft": tips,
            "boss_ok": boss_ok,
            "tips": soft,
            "pass": not missing and bool(tips) and boss_ok and bool(soft),
        }
        report["areas"][aid] = block
        ok = ok and block["pass"]
    # all 8 areas should have loop_soft now
    no_tip = [
        a
        for a in (reg.areas or {})
        if not ((reg.areas or {}).get(a) or {}).get("loop_soft")
    ]
    report["areas_without_loop_soft"] = no_tip
    report["all_pass"] = ok and not no_tip
    out = ROOT / "exports" / "wo032_area_loops.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        f"# WO-032 Area Loops",
        "",
        f"**version:** `{APP_VERSION}` · **all_pass:** {report['all_pass']}",
        "",
        "| area | pass |",
        "|------|:----:|",
    ]
    for aid, b in report["areas"].items():
        md.append(f"| {aid} | {'✅' if b['pass'] else '❌'} |")
    md.append("")
    md.append("## Full map")
    md.append("- forest/marsh (029) · cave/desert (031) · mountain/crystal/city/void (032)")
    (ROOT / "exports" / "WO032_AREA_LOOPS.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"all_pass": report["all_pass"], "no_tip": no_tip}, ensure_ascii=False, indent=2))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
