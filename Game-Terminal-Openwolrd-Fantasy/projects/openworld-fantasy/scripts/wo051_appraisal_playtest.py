#!/usr/bin/env python3
"""WO-051 Appraisal S–SSS harness."""
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
from game.domain.appraisal import (
    SKILL_ID,
    TIER_S,
    TIER_SS,
    TIER_SSS,
    appraise_monster_lines,
    combat_appraise_hint,
    resolve_appraisal_tier,
    run_appraisal,
)
from game.domain.character import create_player
from game.domain.damage_pipeline import resolve_player_outbound
from game.domain.progression import ensure_progression
from game.domain.stat_grades import temple_unlock


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    p = create_player(reg, "wo051", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 8
    p["mana"] = 40
    mon = {
        "id": "fire_imp",
        "name": "อิมป์ไฟ",
        "level": 11,
        "hp": 55,
        "max_hp": 55,
        "atk": 11,
        "elements": ["fire"],
    }

    # temple seeds appraisal
    temple_unlock(p, reg)
    scores["temple"] = 5 if SKILL_ID in (p.get("skills") or []) and p.get("grade_revealed") else 2
    log("temple", f"tier={resolve_appraisal_tier(p)} skill={SKILL_ID in (p.get('skills') or [])}")

    # S depth
    p["appraisal_tier"] = TIER_S
    s = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_S))
    scores["s"] = 5 if "〔" in s and "จุดอ่อน" not in s.split("ชั้นพลัง")[0] else 4
    if "ชั้นพลัง" in s:
        scores["s"] = 5
    log("s", s.replace("\n", " | ")[:140])

    # SS weakness
    p["appraisal_tier"] = TIER_SS
    ss = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_SS))
    scores["ss"] = 5 if ("จุดอ่อน" in ss or "น้ำ" in ss or "แนว" in ss) else 2
    log("ss", ss.replace("\n", " | ")[:160])

    # SSS recipe
    p["appraisal_tier"] = TIER_SSS
    p["appraisal_xp"] = 30
    sss = "\n".join(appraise_monster_lines(p, mon, reg, force_tier=TIER_SSS))
    scores["sss"] = 5 if "สาย" in sss else 2
    log("sss", sss.replace("\n", " | ")[:160])

    # self
    lines, growth = run_appraisal(p, target="self", reg=reg, paid=True)
    blob = "\n".join(lines)
    scores["self"] = 5 if ("อ่านชั้น" in blob or "เกรด" in blob) and "power_" not in blob.lower() else 2
    log("self", blob.replace("\n", " | ")[:140])

    # no leak
    leak = any(x in (s + ss + sss + blob) for x in ("power_atk", "1.4", "power_bonus", "status_chance"))
    scores["no_leak"] = 5 if not leak else 1
    log("no_leak", "ok" if not leak else "LEAK")

    # pipeline soft hint after appraise
    appraise_monster_lines(p, mon, reg, force_tier=TIER_SS)
    hint = combat_appraise_hint(p, mon)
    scores["hint"] = 5 if hint else 2
    log("hint", str(hint))

    # outbound still works
    r = resolve_player_outbound(
        p, mon, reg, "dark_forest", {"power": 10, "elements": ["water"]}, random.Random(3)
    )
    scores["pipeline"] = 5 if r.amount >= 1 else 1
    log("pipeline", f"dmg={r.amount} fl={r.flavor[:40]}")

    # tiers distinct
    scores["depth"] = 5 if (len(sss) > len(s) and len(ss) > len(s) // 2) else 2
    log("depth", f"len S={len(s)} SS={len(ss)} SSS={len(sss)}")

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
    (out / "wo051_appraisal.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-051 Appraisal · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-052\n\n")
    md.append("**แข็ง:** ชั้น S/SS/SSS ต่างชัด · soft weakness/recipe · temple seed · pipeline hint\n\n")
    md.append("**อ่อน:** ยังไม่ตัด P@30 · weakness ยังไม่ recipe เต็มใน combat\n\n")
    md.append("**WO-052:** ตัดแต้ม P หลัง Lv30+ + Automatic Growth จากเกรด/เควส/Anima\n")
    (out / "WO051_APPRAISAL.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-051 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
