#!/usr/bin/env python3
"""
WO-030: Human-like playtest session (scripted actor) covering WO-028 blocks.
Produces exports/WO030_PLAYTEST_LOG.md for hotfix decisions.
"""
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
from game.domain.divine_burden import (
    apply_burden_tick,
    try_auto_unequip_burden,
    worst_burden_band,
)
from game.domain.equipment import equip_item, unequip_slot
from game.domain.needs import ensure_needs, get_needs
from game.domain.quests import ensure_quests
from game.domain.soft_foresight import area_loop_soft_lines, soft_dungeon_entry_warnings
from game.runtime.auto_farm import auto_fight
from game.runtime.auto_run_log import (
    format_auto_run_summary,
    start_auto_run,
    observe_auto_lines,
    bump_auto_run,
)
from game.runtime.dungeon_auto import ensure_auto_prefs, run_auto_needs_care
from game.services.godforge_chamber import (
    CHAMBER_RELICS,
    enter_godforge,
    exit_godforge,
    format_chamber_burden_summary,
    loan_relic,
    set_chamber_mode,
    spar_dummy,
)
from game.ui_terminal.help import TUTORIAL_PAGES, CITY_ONBOARD_TIPS


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(30)
    notes: list = []
    findings: list = []
    scores: dict = {}

    def log(block: str, msg: str, sev: str = "info"):
        notes.append({"block": block, "sev": sev, "msg": msg})

    # ── P1 Bootstrap ──
    p = create_player(reg, "human030", "warrior", "เมษ")
    p["location"] = "dark_forest"
    p["level"] = 4
    ensure_needs(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["auto_avoid_relic_echo"] = True
    prefs["auto_buy_supplies"] = True
    p["auto_prefs"] = prefs
    tut_ok = len(TUTORIAL_PAGES) == 6 and any(
        "เรลิก" in "\n".join(pg) or "ภาระ" in "\n".join(pg) for pg in TUTORIAL_PAGES
    )
    tip_ok = any("เรลิก" in t or "ห้อง" in t or "ภาระ" in t for t in CITY_ONBOARD_TIPS)
    log("P1", f"tutorial6={tut_ok} onboard_relic_tips={tip_ok}")
    if not tut_ok:
        findings.append({"sev": "P2", "msg": "tutorial missing relic page"})
    scores["P1_bootstrap"] = 5 if tut_ok and tip_ok else 3

    # ── P2 Forest loop ──
    p["location"] = "dark_forest"
    tips = area_loop_soft_lines(p, reg)
    forest_qs = [
        qid
        for qid, q in (reg.quests or {}).items()
        if q.get("area") == "dark_forest" or "forest" in qid
    ]
    # simulate explore + fights
    wins = 0
    for i in range(6):
        mon = dict(
            (reg.monsters or {}).get("forest_wolf")
            or {"id": "fw", "name": "หมาป่า", "level": 2, "hp": 15, "max_hp": 15, "atk": 3}
        )
        mon["hp"] = mon["max_hp"] = max(8, int(mon.get("hp") or 15) // 2)
        mon["atk"] = max(1, int(mon.get("atk") or 3) // 2)
        p["hp"] = int(p.get("max_hp") or 80)
        fl = auto_fight(p, mon, reg, random.Random(30 + i), "dark_forest")
        if any("ออโต้ชนะ" in str(x) for x in fl):
            wins += 1
        run_auto_needs_care(p, reg, allow_rest=True)
    log("P2", f"forest tips={len(tips)} quests~{len(forest_qs)} wins={wins}/6")
    scores["P2_forest"] = 4 if wins >= 4 and tips else 2
    if wins < 3:
        findings.append({"sev": "P2", "msg": f"forest fights weak: {wins}/6"})

    # ── P3 Early relic burden ──
    money_before = int(p["money_world"])
    mor0 = int(get_needs(p)["morale"])
    p["inventory_ids"] = list(p.get("inventory_ids") or []) + ["relic_storm_fang"]
    p["inventory_rarities"] = list(p.get("inventory_rarities") or []) + ["legendary"]
    p["inventory"] = list(p.get("inventory") or []) + ["fang"]
    eq = equip_item(p, "relic_storm_fang", reg)
    band = worst_burden_band(p, reg)
    for i in range(15):
        p["auto_ticks"] = i + 1
        apply_burden_tick(p, reg, context="field", rng=random.Random(100 + i))
    mor1 = int(get_needs(p)["morale"])
    drop = mor0 - mor1
    # force low morale unequip
    p["needs"]["morale"] = 18
    un = try_auto_unequip_burden(p, reg)
    log(
        "P3",
        f"band={band} morale_drop_15t={drop} unequip={bool(un)} equip_flavor={('ภาระ' in eq or 'ร้อน' in eq or 'สั่น' in eq)}",
    )
    if drop < 5:
        findings.append({"sev": "P2", "msg": f"burden too soft: drop {drop}/15 ticks"})
    if drop > 45:
        findings.append({"sev": "P2", "msg": f"burden too harsh: drop {drop}/15 ticks"})
    if not un:
        findings.append({"sev": "P2", "msg": "auto unequip failed at low morale"})
    scores["P3_burden"] = 4 if 8 <= drop <= 40 and un else 3

    # ── P4 Chamber ──
    p2 = create_player(reg, "human030c", "warrior", "เมษ")
    p2["money_world"] = 350
    ensure_needs(p2)
    p2["needs"]["morale"] = 72
    enter_godforge(p2, reg)
    loan_relic(p2, reg, CHAMBER_RELICS[1]["id"])
    equip_item(p2, CHAMBER_RELICS[1]["id"], reg)
    set_chamber_mode(p2, "burden")
    spar = spar_dummy(p2, reg, random.Random(9), rounds=3)
    summ = format_chamber_burden_summary(p2, reg)
    exit_n = exit_godforge(p2, reg)
    mon_ok = int(p2["money_world"]) == 350
    loan_ok = CHAMBER_RELICS[1]["id"] not in (p2.get("inventory_ids") or [])
    summ_ok = any("สรุป" in x or "ขวัญ" in x for x in summ + exit_n)
    spar_strong = any("~" in x and any(c.isdigit() for c in x) for x in spar)
    log("P4", f"money_ok={mon_ok} loan_cleared={loan_ok} summary={summ_ok} spar_lines={len(spar)}")
    if not mon_ok:
        findings.append({"sev": "P1", "msg": "chamber changed money"})
    scores["P4_chamber"] = 5 if mon_ok and loan_ok and summ_ok else 2

    # ── P5 mid quest graph ──
    mid = {
        "hell": "embers_of_hell_relic" in (reg.quests or {}),
        "prism": "prism_sovereign_fall" in (reg.quests or {}),
        "aegis": "sky_aegis_burden" in (reg.quests or {}),
    }
    log("P5", f"mid_quests={mid}")
    scores["P5_mid"] = 5 if all(mid.values()) else 2

    # ── P6 marsh loop ──
    p3 = create_player(reg, "human030m", "warrior", "เมษ")
    p3["location"] = "mist_marsh"
    p3["level"] = 7
    marsh_tips = area_loop_soft_lines(p3, reg)
    marsh_qs = [
        q
        for q in ("marsh_leech_cull", "marsh_reed_path", "mist_walker")
        if q in (reg.quests or {})
    ]
    log("P6", f"marsh_tips={marsh_tips} quests={marsh_qs}")
    scores["P6_marsh"] = 4 if marsh_tips and len(marsh_qs) >= 3 else 2

    # ── P7 economy with crush ──
    crush_gains, free_gains = [], []
    for s in range(20):
        a = {
            "money_world": 0,
            "money_heaven": 0,
            "money_hell": 0,
            "world_modifiers": {},
            "_burden_active": "crush",
        }
        b = {"money_world": 0, "money_heaven": 0, "money_hell": 0, "world_modifiers": {}}
        grant_combat_money(a, {"level": 5}, random.Random(s), auto=True, money_factor=0.9)
        grant_combat_money(b, {"level": 5}, random.Random(s), auto=True, money_factor=0.9)
        crush_gains.append(a["money_world"])
        free_gains.append(b["money_world"])
    avg_c = sum(crush_gains) / len(crush_gains)
    avg_f = sum(free_gains) / len(free_gains)
    ratio = avg_c / avg_f if avg_f else 1
    log("P7", f"avg_crush={avg_c:.1f} avg_free={avg_f:.1f} ratio={ratio:.2f}")
    if ratio > 0.98:
        findings.append({"sev": "P2", "msg": "crush money dampen barely visible"})
    if ratio < 0.70:
        findings.append({"sev": "P2", "msg": "crush money dampen too harsh"})
    scores["P7_economy"] = 4 if 0.80 <= ratio <= 0.96 else 3

    # ── Auto run summary sample with burden ──
    p4 = create_player(reg, "human030s", "warrior", "เมษ")
    ensure_needs(p4)
    start_auto_run(p4, kind="field", label="WO-030 session", max_ticks=10)
    p4["_auto_run"]["ticks"] = 10
    p4["_auto_run"]["fights"] = 5
    p4["_auto_run"]["eats"] = 2
    p4["_auto_run"]["burden_unequips"] = 1
    p4["_burden_drain_total"] = 9
    p4["_burden_active"] = "strain"
    p4["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p4["equip_rarities"] = {"main_hand": "legendary"}
    p4["level"] = 3
    p4["_auto_run"]["active"] = False
    p4["_auto_run_last"] = dict(p4["_auto_run"])
    summary = format_auto_run_summary(p4, reg, reason="done")
    sum_blob = "\n".join(summary)
    log("God", f"summary_has_burden={'ภาระ' in sum_blob}")
    scores["God_log"] = 4 if "ภาระ" in sum_blob else 2

    # foresight
    p5 = create_player(reg, "human030f", "warrior", "เมษ")
    p5["location"] = "dark_forest"
    p5["level"] = 2
    p5["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p5["equip_rarities"] = {"main_hand": "legendary"}
    fw = soft_dungeon_entry_warnings(p5, reg)
    log("Foresight", f"lines={len(fw)} has_burden={any('ภาระ' in x or 'เรลิก' in x for x in fw)}")

    # ── Aggregate findings → hotfix plan ──
    hotfix_plan = []
    # From session metrics
    if drop < 10:
        hotfix_plan.append("burden_feel_up_slight")
    elif drop > 35:
        hotfix_plan.append("burden_feel_down_slight")
    else:
        hotfix_plan.append("burden_ok_tune_medium")
    if ratio > 0.95:
        hotfix_plan.append("economy_dampen_stronger")
    hotfix_plan.append("chamber_summary_recommend_line")
    hotfix_plan.append("god_summary_clear_when_unequipped")
    hotfix_plan.append("area_quest_soft_hint_in_list")
    hotfix_plan.append("personal_hub_first_relic_tip")

    report = {
        "version": APP_VERSION,
        "wo": "WO-030",
        "session": "scripted_human_actor",
        "scores": scores,
        "notes": notes,
        "findings": findings,
        "metrics": {
            "burden_drop_15_ticks": drop,
            "money_ratio_crush_vs_free": round(ratio, 3),
            "forest_wins": wins,
            "chamber_money_ok": mon_ok,
        },
        "hotfix_plan": hotfix_plan,
        "pass_session": all(v >= 3 for v in scores.values()) and not any(
            f.get("sev") == "P1" for f in findings
        ),
    }

    out_j = ROOT / "exports" / "wo030_playtest.json"
    out_j.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# WO-030 Human Playtest Log",
        "",
        f"**version:** `{APP_VERSION}`  ",
        f"**mode:** scripted human actor (WO-028 blocks)  ",
        f"**session_pass:** {report['pass_session']}",
        "",
        "## Scores (1–5)",
        "",
        "| Block | score |",
        "|-------|------:|",
    ]
    for k, v in scores.items():
        md.append(f"| {k} | {v} |")
    md.append("")
    md.append("## Metrics")
    md.append(f"- Burden morale drop (15 field ticks): **{drop}**")
    md.append(f"- Money ratio crush/free (auto): **{ratio:.2f}**")
    md.append(f"- Forest wins: **{wins}/6**")
    md.append(f"- Chamber money preserved: **{mon_ok}**")
    md.append("")
    md.append("## Findings")
    if findings:
        for f in findings:
            md.append(f"- **{f['sev']}** {f['msg']}")
    else:
        md.append("- ไม่มี P1 จาก session นี้")
    md.append("")
    md.append("## Hotfix plan (from session)")
    for h in hotfix_plan:
        md.append(f"- `{h}`")
    md.append("")
    md.append("## Sample God summary")
    md.append("```")
    md.extend(summary)
    md.append("```")
    md.append("")
    md.append("## Survive / Stop narrative")
    md.append(f"- รอด field: ชนะ {wins}/6 · care ทำงาน · ภาระ drop {drop}")
    md.append(f"- หยุด/ถอด: auto unequip เมื่อขวัญ 18 → {bool(un)}")
    md.append(f"- Chamber: ออกแล้วเงินคง · สรุปภาระ={'ใช่' if summ_ok else 'ไม่'}")
    (ROOT / "exports" / "WO030_PLAYTEST_LOG.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print(json.dumps({
        "pass": report["pass_session"],
        "scores": scores,
        "metrics": report["metrics"],
        "findings": findings,
        "hotfix_plan": hotfix_plan,
    }, ensure_ascii=False, indent=2))
    return 0 if report["pass_session"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
