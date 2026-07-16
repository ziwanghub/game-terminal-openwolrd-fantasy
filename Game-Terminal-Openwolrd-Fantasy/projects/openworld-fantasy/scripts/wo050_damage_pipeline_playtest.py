#!/usr/bin/env python3
"""WO-050 Damage Pipeline + Grade Soft Mult harness."""
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
from game.domain.combat import player_attack_damage
from game.domain.damage_pipeline import (
    grade_outbound_mult,
    resolve_player_inbound,
    resolve_player_outbound,
)
from game.domain.progression import ensure_progression
from game.domain.stat_grades import AXIS_KEYS


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    mon = {
        "id": "h50",
        "name": "เงา",
        "elements": ["physical"],
        "statuses": [],
        "atk": 10,
    }

    def mk(name, grade, axis_score):
        p = create_player(reg, name, "warrior", "เมษ")
        ensure_progression(p, reg)
        p["area_mastery"] = {"dark_forest": 50}
        p["bonus_atk"] = 4
        p["power_atk"] = 22.0
        p["power_mag"] = 20.0
        p["crit_chance"] = 0.0
        p["luck_score"] = 0.0
        p["grade_revealed"] = True
        p["player_grade"] = grade
        p["growth_profile"] = "balanced"
        p["axis_progress"] = {k: float(axis_score) for k in AXIS_KEYS}
        p["stats_alloc"] = {k: 5 for k in AXIS_KEYS}
        return p

    # mult tables
    p_s, p_f = mk("s", "S", 40), mk("f", "F", 2)
    ms, _ = grade_outbound_mult(p_s, "physical")
    mf, _ = grade_outbound_mult(p_f, "physical")
    scores["grade_mult"] = 5 if ms > mf and ms >= 1.05 else 1
    log("grade_mult", f"S={ms:.3f} F={mf:.3f}")

    # physical adapter
    sk = {"power": 12, "elements": ["physical"]}
    rs = resolve_player_outbound(p_s, mon, reg, "dark_forest", sk, random.Random(11))
    rf = resolve_player_outbound(p_f, mon, reg, "dark_forest", sk, random.Random(11))
    scores["phys"] = 5 if rs.amount >= rf.amount and rs.meta.get("raw") else 2
    log("phys", f"S_dmg={rs.amount} F_dmg={rf.amount} class={rs.damage_class}")

    # magic adapter
    skm = {"power": 12, "elements": ["arcane", "fire"]}
    rm = resolve_player_outbound(p_s, mon, reg, "dark_forest", skm, random.Random(11))
    scores["magic"] = 5 if rm.amount >= 1 and rm.damage_class in ("arcane", "light", "physical") else 2
    log("magic", f"dmg={rm.amount} class={rm.damage_class}")

    # wrapper
    d, fl = player_attack_damage(p_s, mon, reg, "dark_forest", sk, random.Random(11))
    scores["wrapper"] = 5 if d == rs.amount else 2
    log("wrapper", f"wrapper_dmg={d}")

    # inbound
    p_s["dodge_chance"] = 0.0
    p_f["dodge_chance"] = 0.0
    p_s["axis_progress"]["defense"] = 50.0
    p_f["axis_progress"]["defense"] = 1.0
    ih = resolve_player_inbound(p_s, 25, random.Random(2))
    il = resolve_player_inbound(p_f, 25, random.Random(2))
    scores["inbound"] = 5 if ih.amount <= il.amount else 1
    log("inbound", f"high_def_taken={ih.amount} low_def_taken={il.amount}")

    # soft no leak
    leak = any(
        x in (rs.flavor + rm.flavor + fl).lower()
        for x in ("power_atk", "1.12", "grade_mult=", "axis_progress")
    )
    scores["soft"] = 5 if not leak else 1
    log("soft", "no raw leak" if not leak else "LEAK")

    # auto-ish spam stability
    ok = True
    for i in range(20):
        try:
            player_attack_damage(p_s, mon, reg, "dark_forest", sk, random.Random(i))
            resolve_player_inbound(p_s, 10 + i, random.Random(i))
        except Exception as e:
            ok = False
            log("stable", str(e))
            break
    scores["stable"] = 5 if ok else 1
    if ok:
        log("stable", "20 hits ok")

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
    (out / "wo050_damage_pipeline.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-050 Damage Pipeline · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-051\n\n")
    md.append("**แข็ง:** adapter ทางเดียว · grade soft mult · soft log · สูตรเก่าเป็น backend\n\n")
    md.append("**อ่อน:** ยังไม่มี weakness recipes · volatility SSS · appraisal ชั้น\n\n")
    md.append("**WO-051:** Appraisal Skill S–SSS (อ่านเกรด/จุดอ่อน soft)\n")
    (out / "WO050_DAMAGE_PIPELINE.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-050 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
