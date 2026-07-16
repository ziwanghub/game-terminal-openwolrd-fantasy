#!/usr/bin/env python3
"""
WO-036: Stat Architecture playtest harness (scripted human-like actor).
Covers Soft P · self assess · anima · needs · relic · chamber · economy · assist · luck.
Produces exports/WO036_PLAYTEST_LOG.md
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
from game.domain.character import create_player
from game.domain.divine_burden import apply_burden_tick, worst_burden_band
from game.domain.equipment import equip_item
from game.domain.needs import apply_needs_event, ensure_needs, get_needs
from game.domain.progression import allocate_stat, ensure_progression, format_alloc_panel
from game.domain.stat_arch import (
    anima_value,
    ensure_stat_arch,
    recompute_anima,
    self_assess_lines,
    soft_hp_condition,
)
from game.domain.inventory_sys import upgrade_success_chance
from game.domain.party import assist_chance_for_member, assist_chance_from_relationship
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import ensure_auto_prefs, run_auto_needs_care
from game.services.godforge_chamber import (
    enter_godforge,
    exit_godforge,
    loan_relic,
    spar_dummy,
)


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes: list = []
    findings: list = []
    scores: dict = {}
    feedback: dict = {}

    def log(block: str, msg: str, sev: str = "info"):
        notes.append({"block": block, "sev": sev, "msg": msg})

    def find(sev: str, msg: str):
        findings.append({"sev": sev, "msg": msg})

    # ── S0 Bootstrap ──
    p = create_player(reg, "wo036", "warrior", "เมษ")
    p["location"] = "dark_forest"
    p["level"] = 5
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["auto_buy_supplies"] = True
    p["auto_prefs"] = prefs
    log("S0", f"version={APP_VERSION} soft_hp={soft_hp_condition(p)}")
    scores["S0"] = 5

    # ── S1 Soft P ──
    p["stat_points"] = 6
    msg_atk = allocate_stat(p, reg, "atk", 2)
    msg_def = allocate_stat(p, reg, "defense", 2)
    panel = "\n".join(format_alloc_panel(p))
    soft_ok = "×" not in panel or "×2" not in panel
    soft_msg = "รู้สึก" in msg_atk or "〔" in msg_atk
    log("S1", f"alloc_msg={msg_atk!r:.80} soft_panel={soft_ok} soft_msg={soft_msg}")
    if not soft_msg:
        find("P2", "allocate message not soft enough")
    if "×2" in panel or "×3" in panel:
        find("P2", "P panel still shows raw ×N invest counts")
    scores["S1_soft_p"] = 5 if soft_ok and soft_msg else 3
    feedback["soft_p"] = (
        "ผ่าน soft" if soft_ok and soft_msg else "ข้อความ/แผงยังแข็ง"
    )

    # ── S2 Self assess ──
    a1 = self_assess_lines(p, force=True, reg=reg)
    a2 = self_assess_lines(p, force=False, reg=reg)  # throttle
    blob = "\n".join(a1)
    has_facets = "กาย" in blob and ("เวท" in blob or "จิต" in blob)
    has_needs = "หิว" in blob or "ขวัญ" in blob
    throttle_ok = any("เพิ่ง" in x or "รอ" in x for x in a2) or len(a2) < len(a1)
    log(
        "S2",
        f"assess_lines={len(a1)} facets={has_facets} needs={has_needs} "
        f"throttle={throttle_ok}",
    )
    if not has_facets:
        find("P1", "self assess missing core facets")
    if "power_" in blob or "crit_chance" in blob:
        find("P1", "self assess leaked raw power keys")
    scores["S2_assess"] = 5 if has_facets and has_needs else 2
    feedback["assess_v"] = "ใช้งานได้ (soft bands)" if has_facets else "อ่านยาก/ไม่ครบ"

    # ── S3 Needs balance (explore ticks) ──
    ensure_needs(p)
    n0 = dict(get_needs(p))
    for _ in range(8):
        apply_needs_event(p, "explore", silent=True)
    n1 = dict(get_needs(p))
    hun_d = n1["hunger"] - n0["hunger"]
    fat_d = n1["fatigue"] - n0["fatigue"]
    mor_d = n1["morale"] - n0["morale"]
    log("S3", f"explore×8 Δhunger={hun_d} Δfatigue={fat_d} Δmorale={mor_d}")
    needs_ok = 5 <= hun_d <= 80 and 5 <= fat_d <= 80 and mor_d <= 5
    if hun_d > 90 or fat_d > 90:
        find("P2", "needs climb too fast on explore×8")
    scores["S3_needs"] = 4 if needs_ok else 2
    feedback["needs"] = (
        f"หิว+{hun_d} ล้า+{fat_d} ขวัญ{mor_d:+d} ใน 8 สำรวจ — "
        + ("สมดุลพอ" if needs_ok else "ต้องจูน")
    )

    # ── S4 Combat auto ──
    wins = 0
    money0 = int(p.get("money_world") or 0)
    for i in range(5):
        mon = dict(
            (reg.monsters or {}).get("forest_wolf")
            or {"id": "fw", "name": "หมาป่า", "level": 2, "hp": 20, "max_hp": 20, "atk": 4}
        )
        mon["hp"] = mon["max_hp"] = max(10, int(mon.get("hp") or 20) // 2)
        mon["atk"] = max(1, int(mon.get("atk") or 4) // 2)
        p["hp"] = int(p.get("max_hp") or 80)
        fl = auto_fight(p, mon, reg, random.Random(36 + i), "dark_forest")
        if any("ชนะ" in str(x) for x in fl):
            wins += 1
        run_auto_needs_care(p, reg, allow_rest=True)
    money1 = int(p.get("money_world") or 0)
    log("S4", f"auto_wins={wins}/5 money_delta={money1 - money0}")
    if wins < 3:
        find("P1", f"auto combat weak: {wins}/5")
    scores["S4_auto"] = 5 if wins >= 4 else (3 if wins >= 3 else 1)
    feedback["auto"] = f"ชนะ {wins}/5 · เงิน Δ{money1 - money0}"

    # ── S5 Relic + Anima ──
    mor0 = int(get_needs(p)["morale"])
    a0 = anima_value(p)
    p["inventory_ids"] = list(p.get("inventory_ids") or []) + ["relic_storm_fang"]
    p["inventory_rarities"] = list(p.get("inventory_rarities") or []) + ["legendary"]
    p["inventory"] = list(p.get("inventory") or []) + ["fang"]
    equip_item(p, "relic_storm_fang", reg)
    band = worst_burden_band(p, reg)
    for i in range(12):
        p["auto_ticks"] = 50 + i
        apply_burden_tick(p, reg, context="field", rng=random.Random(200 + i))
    mor1 = int(get_needs(p)["morale"])
    recompute_anima(p, reg)
    a1v = anima_value(p)
    assess_relic = "\n".join(self_assess_lines(p, force=True, reg=reg))
    anima_mentioned = "จิตวิญญาณ" in assess_relic or "anima" in assess_relic.lower()
    log(
        "S5",
        f"band={band} morale {mor0}→{mor1} anima {a0:.1f}→{a1v:.1f} "
        f"assess_anima={anima_mentioned}",
    )
    if band == "fit" and p.get("level", 1) < 10:
        find("P3", "low-level legendary expected strain/crush")
    # anima should not mirror morale 1:1
    if abs(a1v - mor1) < 0.5:
        find("P2", "anima too tightly equal to morale")
    scores["S5_relic_anima"] = 4 if band != "fit" and anima_mentioned else 2
    feedback["anima"] = (
        f"band={band} ขวัญ−{mor0 - mor1} anima={a1v:.0f} "
        + ("รู้สึกแยกชั้น" if abs(a1v - mor1) > 5 else "ยังแยกชั้นไม่ชัด")
    )

    # ── S6 Chamber ──
    money_c0 = int(p.get("money_world") or 0)
    try:
        enter_godforge(p, reg)
        loan_relic(p, reg, 0)
        spar_dummy(p, reg, rng=random.Random(7))
        exit_godforge(p, reg)
        money_c1 = int(p.get("money_world") or 0)
        chamber_ok = money_c1 <= money_c0 + 5
        log("S6", f"chamber money {money_c0}→{money_c1} ok={chamber_ok}")
        if not chamber_ok:
            find("P1", "chamber granted money")
        scores["S6_chamber"] = 5 if chamber_ok else 1
    except Exception as e:
        log("S6", f"chamber error: {e}", "warn")
        find("P2", f"chamber exception: {e}")
        scores["S6_chamber"] = 2

    # ── S7 Assist + luck ──
    p["party"] = [{"id": "c_test", "name": "เงา", "kind": "spirit", "bonus_atk": 3}]
    p["party_bonds"] = {"c_test": 55}
    p["luck_score"] = 0.0
    base = assist_chance_for_member(p, "c_test", p["party"][0])
    p["luck_score"] = 0.45
    lucky = assist_chance_for_member(p, "c_test", p["party"][0])
    p["luck_score"] = -0.25
    unlucky = assist_chance_for_member(p, "c_test", p["party"][0])
    log("S7", f"assist base={base:.3f} lucky={lucky:.3f} unlucky={unlucky:.3f}")
    # luck should not dominate: delta < 0.15 absolute ideally
    if abs(lucky - unlucky) > 0.20:
        find("P2", "assist luck bias too strong")
    scores["S7_assist"] = 4 if lucky >= unlucky and abs(lucky - base) < 0.15 else 2

    # ── S8 Upgrade luck + economy ──
    p["luck_score"] = 0.4
    hi = upgrade_success_chance(
        "main_hand", 3, reg=reg, rarity_id="rare", player=p
    )
    p["luck_score"] = -0.2
    lo = upgrade_success_chance(
        "main_hand", 3, reg=reg, rarity_id="rare", player=p
    )
    # baseline without luck dominance vs rank
    no_luck = upgrade_success_chance(
        "main_hand", 3, reg=reg, rarity_id="rare", player=None
    )
    log("S8", f"upgrade hi={hi:.3f} lo={lo:.3f} base={no_luck:.3f}")
    if hi - lo > 0.18:
        find("P2", "upgrade luck bias too heavy")
    scores["S8_luck_econ"] = 4 if hi >= lo and (hi - lo) <= 0.18 else 2
    feedback["luck_upgrade"] = f"Δ luck effect ~{hi - lo:.3f} (เป้า ≤0.15–0.18)"

    # ── Aggregate ──
    avg = sum(scores.values()) / max(1, len(scores))
    all_pass = all(v >= 3 for v in scores.values()) and not any(
        f["sev"] == "P1" for f in findings
    )

    # synthetic human-feel notes from harness (stand-in until hand log filled)
    feedback["summary"] = {
        "soft_p": feedback.get("soft_p"),
        "assess_v": feedback.get("assess_v"),
        "anima": feedback.get("anima"),
        "needs": feedback.get("needs"),
        "auto": feedback.get("auto"),
        "avg_score": round(avg, 2),
        "all_pass": all_pass,
    }

    out_dir = ROOT / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": APP_VERSION,
        "scores": scores,
        "notes": notes,
        "findings": findings,
        "feedback": feedback,
        "all_pass": all_pass,
    }
    (out_dir / "wo036_playtest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = []
    md.append(f"# WO-036 Playtest Log · `{APP_VERSION}`\n")
    md.append("## แหล่ง\n")
    md.append("| ชนิด | |\n|------|--|\n")
    md.append("| Harness | `scripts/wo036_stat_playtest.py` |\n")
    md.append("| คู่มือ | `docs/WO036_HUMAN_PLAYTEST.md` |\n")
    md.append(f"| all_pass | **{all_pass}** · avg **{avg:.2f}** |\n\n")
    md.append("## Scores\n\n")
    md.append("| Block | Score |\n|-------|------:|\n")
    for k, v in scores.items():
        md.append(f"| {k} | {v} |\n")
    md.append("\n## Feedback (harness + เกณฑ์มือ)\n\n")
    for k in ("soft_p", "assess_v", "anima", "needs", "auto", "luck_upgrade"):
        if k in feedback:
            md.append(f"- **{k}:** {feedback[k]}\n")
    md.append("\n## Findings\n\n")
    if not findings:
        md.append("- (none critical)\n")
    else:
        for f in findings:
            md.append(f"- **{f['sev']}** {f['msg']}\n")
    md.append("\n## Notes\n\n")
    for n in notes:
        md.append(f"- [{n['block']}] {n['msg']}\n")
    md.append("\n## Hotfix targets (auto from harness)\n\n")
    md.append("1. ปรับข้อความ soft P / ประเมินให้อ่านง่ายขึ้น\n")
    md.append("2. Anima soft ชัดขึ้น (ไม่ปนขวัญ) บน assess + status\n")
    md.append("3. เพดาน luck บน assist/upgrade ถ้า bias สูง\n")
    md.append("4. ประเมินศัตรู soft (เฟส 3)\n")
    md.append("\n## มือจริง\n\n")
    md.append("กรอกแบบฟอร์มใน `docs/WO036_HUMAN_PLAYTEST.md` §2 หลังเล่น 60–90 นาที\n")

    (out_dir / "WO036_PLAYTEST_LOG.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-036 harness done · all_pass={all_pass} avg={avg:.2f}")
    print(f"  → exports/WO036_PLAYTEST_LOG.md")
    for f in findings:
        print(f"  ! {f['sev']}: {f['msg']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
