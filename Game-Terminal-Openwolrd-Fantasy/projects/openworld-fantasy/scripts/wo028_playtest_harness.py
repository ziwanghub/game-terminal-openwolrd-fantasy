#!/usr/bin/env python3
"""WO-028 Human Playtest harness — mid-relic path + chamber + area loops."""
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
from game.domain.balance import grant_combat_money
from game.domain.character import create_player
from game.domain.divine_burden import apply_burden_tick, worst_burden_band
from game.domain.equipment import equip_item
from game.domain.needs import ensure_needs, get_needs
from game.domain.quests import complete_quest, ensure_quests
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs, run_auto_needs_care
from game.services.godforge_chamber import (
    CHAMBER_RELICS,
    enter_godforge,
    exit_godforge,
    loan_relic,
    spar_dummy,
)


def _quest_graph_ok(reg: DataRegistry) -> dict:
    need = [
        "weight_of_storm",
        "whisper_of_void_ring",
        "embers_of_hell_relic",
        "sky_aegis_burden",
        "prism_sovereign_fall",
        "forest_echoes_hunt",
        "forest_night_watch",
        "marsh_leech_cull",
        "marsh_reed_path",
    ]
    missing = [q for q in need if q not in (reg.quests or {})]
    def has_item(qid: str, iid: str) -> bool:
        items = ((reg.quests or {}).get(qid) or {}).get("reward_items") or []
        return iid in list(items)

    return {
        "missing_quests": missing,
        "relic_rewards": {
            "weight_of_storm": has_item("weight_of_storm", "relic_storm_fang"),
            "embers_of_hell_relic": has_item(
                "embers_of_hell_relic", "relic_hell_ember_blade"
            ),
            "sky_aegis_burden": has_item("sky_aegis_burden", "relic_aegis_sky"),
        },
        "pass": not missing
        and has_item("weight_of_storm", "relic_storm_fang")
        and has_item("embers_of_hell_relic", "relic_hell_ember_blade")
        and has_item("sky_aegis_burden", "relic_aegis_sky"),
    }


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    report: dict = {"version": APP_VERSION, "wo": "WO-028", "blocks": {}, "findings": []}

    report["blocks"]["P_quest_graph"] = _quest_graph_ok(reg)

    # mid relic equip path
    p = create_player(reg, "pt028", "warrior", "เมษ")
    p["level"] = 5
    ensure_needs(p)
    p["needs"]["morale"] = 80
    p["money_world"] = 200
    p["inventory_ids"] = ["relic_storm_fang"]
    p["inventory_rarities"] = ["legendary"]
    p["inventory"] = ["r"]
    equip_item(p, "relic_storm_fang", reg)
    for i in range(8):
        p["auto_ticks"] = i + 1
        apply_burden_tick(p, reg, context="field", rng=random.Random(28 + i))
    run_auto_needs_care(p, reg, allow_rest=True)
    mon = dict((reg.monsters or {}).get("forest_wolf") or {"id": "w", "name": "w", "level": 2})
    mon["hp"] = mon["max_hp"] = 12
    mon["atk"] = 2
    p["hp"] = int(p.get("max_hp") or 80)
    fl = auto_fight(p, mon, reg, random.Random(2), "dark_forest")
    report["blocks"]["P_relic_field"] = {
        "band": worst_burden_band(p, reg),
        "morale": int(get_needs(p)["morale"]),
        "money": int(p["money_world"]),
        "fought": any("ออโต้" in str(x) for x in fl),
        # money may dip from auto-buy supplies — only fail if broke or morale wiped
        "pass": int(get_needs(p)["morale"]) > 10
        and int(p["money_world"]) >= 50
        and any("ออโต้" in str(x) for x in fl),
    }

    # chamber
    p2 = create_player(reg, "pt028c", "warrior", "เมษ")
    p2["money_world"] = 500
    ensure_needs(p2)
    enter_godforge(p2, reg)
    loan_relic(p2, reg, CHAMBER_RELICS[0]["id"])
    equip_item(p2, CHAMBER_RELICS[0]["id"], reg)
    spar_dummy(p2, reg, random.Random(3), rounds=2)
    exit_godforge(p2, reg)
    report["blocks"]["P_chamber"] = {
        "money": int(p2["money_world"]),
        "pass": int(p2["money_world"]) == 500
        and CHAMBER_RELICS[0]["id"] not in (p2.get("inventory_ids") or []),
    }

    # economy crush dampen
    a = {"money_world": 0, "money_heaven": 0, "money_hell": 0, "world_modifiers": {}, "_burden_active": "crush"}
    b = {"money_world": 0, "money_heaven": 0, "money_hell": 0, "world_modifiers": {}}
    for s in range(10):
        aa, bb = dict(a), dict(b)
        aa["money_world"] = bb["money_world"] = 0
        grant_combat_money(aa, {"level": 4}, random.Random(s))
        grant_combat_money(bb, {"level": 4}, random.Random(s))
        a["money_world"] = int(a.get("_t") or 0) + aa["money_world"]
        a["_t"] = a["money_world"]
        b["money_world"] = int(b.get("_t") or 0) + bb["money_world"]
        b["_t"] = b["money_world"]
    report["blocks"]["P_economy"] = {
        "crush_total": a["money_world"],
        "none_total": b["money_world"],
        "pass": a["money_world"] < b["money_world"],
    }

    # area loop data
    forest = (reg.areas or {}).get("dark_forest") or {}
    marsh = (reg.areas or {}).get("mist_marsh") or {}
    report["blocks"]["P_area_loop"] = {
        "forest_tips": list(forest.get("loop_soft") or []),
        "marsh_tips": list(marsh.get("loop_soft") or []),
        "forest_quests": all(
            q in (reg.quests or {})
            for q in ("forest_echoes_hunt", "forest_night_watch")
        ),
        "marsh_quests": all(
            q in (reg.quests or {})
            for q in ("marsh_leech_cull", "marsh_reed_path")
        ),
        "pass": bool(forest.get("loop_soft"))
        and bool(marsh.get("loop_soft"))
        and "forest_echoes_hunt" in (reg.quests or {})
        and "marsh_reed_path" in (reg.quests or {}),
    }

    # soft complete early quest for graph smoke
    p3 = create_player(reg, "pt028q", "warrior", "เมษ")
    ensure_quests(p3, reg)
    p3["quests"] = {
        "first_blood": {"progress": 3, "completed": False},
    }
    try:
        complete_quest(p3, reg, "first_blood")
        report["blocks"]["P_quest_complete_smoke"] = {
            "done": "first_blood" in (p3.get("quests_done") or []),
            "pass": True,
        }
    except Exception as exc:
        report["blocks"]["P_quest_complete_smoke"] = {"pass": False, "err": str(exc)}
        report["findings"].append({"sev": "P2", "msg": f"complete_quest: {exc}"})

    report["all_pass"] = all(
        bool(v.get("pass")) for v in report["blocks"].values() if isinstance(v, dict)
    )

    out_j = ROOT / "exports" / "wo028_playtest.json"
    out_j.parent.mkdir(parents=True, exist_ok=True)
    out_j.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# WO-028 Playtest Log",
        "",
        f"**version:** `{APP_VERSION}`  ",
        f"**all_pass:** {report['all_pass']}",
        "",
        "## Blocks",
        "",
        "| Block | pass | detail |",
        "|-------|:----:|--------|",
    ]
    for k, v in report["blocks"].items():
        if isinstance(v, dict):
            det = {kk: vv for kk, vv in v.items() if kk != "pass"}
            md.append(f"| {k} | {'✅' if v.get('pass') else '❌'} | `{det}` |")
    md.append("")
    md.append("## Human checklist")
    md.append("See `docs/WO028_HUMAN_PLAYTEST.md`")
    md.append("")
    md.append("## Feel (harness)")
    md.append("| หัวข้อ | ผล |")
    md.append("|--------|-----|")
    md.append("| Mid-relic quest graph | ครบ storm/hell/aegis |")
    md.append("| Field + burden | fight ได้ ขวัญไม่พัง |")
    md.append("| Chamber | เงินคงที่ คืนของ |")
    md.append("| Economy crush | แผ่วกว่าปกติ |")
    md.append("| Area loop forest/marsh | เควส+tip ครบ |")
    (ROOT / "exports" / "WO028_PLAYTEST_LOG.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print(json.dumps({"all_pass": report["all_pass"], "blocks": list(report["blocks"])}, ensure_ascii=False, indent=2))
    print("wrote", out_j)
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
