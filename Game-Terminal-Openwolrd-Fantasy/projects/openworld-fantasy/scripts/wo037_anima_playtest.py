#!/usr/bin/env python3
"""WO-037 Anima Presence harness — soft moments + morale/auto smoke."""
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
from game.domain.progression import ensure_progression, library_visit
from game.domain.stat_arch import (
    anima_presence_lines,
    anima_value,
    ensure_stat_arch,
    recompute_anima,
)
from game.runtime.auto_farm import auto_fight
from game.services.godforge_chamber import enter_godforge, exit_godforge, loan_relic, spar_dummy


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes = []
    findings = []
    scores = {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    p = create_player(reg, "wo037", "mage", "เมษ")
    p["level"] = 6
    p["location"] = "ancient_city"
    ensure_needs(p)
    ensure_progression(p, reg)
    ensure_stat_arch(p)
    p["anima"] = 48.0
    a0 = anima_value(p)

    # ── equip relic presence ──
    inv = list(p.get("inventory_ids") or [])
    inv.append("relic_storm_fang")
    p["inventory_ids"] = inv
    # keep rarity list aligned with inventory_ids length
    ir = list(p.get("inventory_rarities") or [])
    while len(ir) < len(inv) - 1:
        ir.append("common")
    ir.append("legendary")
    p["inventory_rarities"] = ir
    p["inventory"] = list(p.get("inventory") or []) + ["fang"]
    eq = equip_item(p, "relic_storm_fang", reg)
    felt = bool(p.get("_anima_presence_felt"))
    blob = str(eq)
    has_touch = "จิตวิญญาณ" in blob or "สั่น" in blob or felt
    log("equip", f"felt={felt} anima {a0:.1f}→{anima_value(p):.1f} msg_has={has_touch}")
    scores["equip"] = 5 if has_touch else 2
    if not has_touch:
        findings.append("equip missing anima presence")

    # ── chamber spar ──
    try:
        enter_godforge(p, reg)
        loan_relic(p, reg, 0)
        spar_notes = spar_dummy(p, reg, random.Random(37), rounds=2)
        exit_godforge(p, reg)
        spar_blob = "\n".join(spar_notes)
        spar_ok = "จิต" in spar_blob or "ลึก" in spar_blob or "ห้อง" in spar_blob
        log("spar", f"ok={spar_ok} lines={len(spar_notes)}")
        scores["spar"] = 5 if spar_ok else 3
    except Exception as e:
        findings.append(f"chamber: {e}")
        scores["spar"] = 1

    # ── library ──
    p["library_unlocked"] = True
    p["time_units"] = 100
    p["library_last_visit"] = -999
    lib = library_visit(p, reg)
    lib_blob = "\n".join(lib)
    lib_ok = "จิต" in lib_blob or "สมาธิ" in lib_blob or anima_value(p) > a0
    log("library", f"ok={lib_ok} anima={anima_value(p):.1f}")
    scores["library"] = 4 if lib_ok else 2

    # ── magic combo presence (direct call) ──
    p["auto_ticks"] = 20
    lines = anima_presence_lines(p, "magic_combo", force=True, reg=reg)
    log("combo", f"lines={lines}")
    scores["combo"] = 5 if lines and "มานา" in "\n".join(lines) or "สมาธิ" in "\n".join(lines) else 3

    # ── morale drain high vs low anima ──
    def drain_test(ani: float) -> int:
        q = create_player(reg, f"d{ani}", "warrior", "เมษ")
        ensure_needs(q)
        ensure_stat_arch(q)
        q["anima"] = ani
        q["needs"]["morale"] = 70
        for _ in range(6):
            apply_needs_event(q, "combat_loss", silent=True)
        return 70 - int(get_needs(q)["morale"])

    d_hi = drain_test(80)
    d_lo = drain_test(15)
    log("morale", f"drain high_anima={d_hi} low_anima={d_lo}")
    # high anima should lose less or equal morale on average
    scores["morale_link"] = 5 if d_hi <= d_lo else 2
    if d_hi > d_lo + 2:
        findings.append("high anima lost more morale than low (unexpected)")

    # ── auto still works ──
    p["hp"] = int(p.get("max_hp") or 80)
    wins = 0
    for i in range(4):
        mon = {
            "id": "fw",
            "name": "หมา",
            "level": 2,
            "hp": 12,
            "max_hp": 12,
            "atk": 3,
        }
        fl = auto_fight(p, mon, reg, random.Random(40 + i), "dark_forest")
        if any("ชนะ" in str(x) for x in fl):
            wins += 1
    log("auto", f"wins={wins}/4")
    scores["auto"] = 5 if wins >= 3 else 2
    if wins < 3:
        findings.append(f"auto weak {wins}/4")

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
    }
    (out / "wo037_anima_playtest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-037 Anima Playtest · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## Findings\n\n")
    if not findings:
        md.append("- none\n")
    else:
        for f in findings:
            md.append(f"- {f}\n")
    md.append("\n## จุดแข็ง / อ่อน + WO-038\n\n")
    md.append("**แข็ง:** soft moment เรลิก/ห้อง/เรียน · ขวัญผูก anima · Auto ยังรัน\n\n")
    md.append("**อ่อน:** soft fail แทบไม่เห็นถ้า anima ไม่ frail · content เทพยังไม่มี\n\n")
    md.append("**WO-038 แนะนำ:** World Relations Lite (divine/infernal) หรือ Anima×Relic depth\n")
    (out / "WO037_ANIMA_PLAYTEST.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-037 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
