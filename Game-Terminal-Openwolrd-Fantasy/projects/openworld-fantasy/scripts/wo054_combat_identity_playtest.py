#!/usr/bin/env python3
"""WO-054 Soft Combat Identity + Weakness Lite harness."""
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
from game.domain.combat_identity import (
    identity_outbound_mult,
    pre_fight_identity_lines,
    weakness_lite_hint_lines,
    weakness_lite_mult,
)
from game.domain.damage_pipeline import resolve_player_outbound
from game.domain.progression import ensure_progression


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    mon = {
        "id": "h54_fire",
        "name": "เงาไฟ",
        "level": 16,
        "hp": 70,
        "max_hp": 70,
        "atk": 11,
        "elements": ["fire"],
        "statuses": [],
    }

    def mk(name, grade="S", bond="resonance"):
        p = create_player(reg, name, "warrior", "เมษ")
        ensure_progression(p, reg)
        p["level"] = 18
        p["grade_revealed"] = True
        p["player_grade"] = grade
        p["growth_profile"] = "balanced"
        p["location"] = "ancient_city"
        p["_relic_bond_mode"] = bond
        p["_relic_bond_faction"] = "divine"
        p["power_atk"] = 22.0
        p["bonus_atk"] = 3
        p["crit_chance"] = 0.0
        p["area_mastery"] = {"ancient_city": 45, "dark_forest": 40}
        p["axis_progress"] = {"atk": 35.0, "defense": 15.0, "magic": 12.0, "speed": 14.0}
        return p

    p = mk("wo054")
    # pre-fight
    pre = pre_fight_identity_lines(p, mon, reg, area_id="ancient_city", force=True)
    scores["pre_fight"] = 5 if pre and "power_" not in "\n".join(pre).lower() else 2
    log("pre_fight", " | ".join(pre)[:140])

    # identity S > F
    ms, _ = identity_outbound_mult(mk("s", "S", "chorus"), area_id="ancient_city")
    mf, _ = identity_outbound_mult(mk("f", "F", "none"), area_id="ancient_city")
    scores["id_mult"] = 5 if ms > mf else 1
    log("id_mult", f"S/chorus={ms:.3f} F={mf:.3f}")

    # weakness lite gate
    p["_appraised_targets"] = {}
    scores["weak_gate"] = 5 if not weakness_lite_hint_lines(p, mon, reg) else 1
    p["_appraised_targets"] = {mon["id"]: "SS"}
    weak = weakness_lite_hint_lines(p, mon, reg)
    scores["weak_ss"] = 5 if weak and "1.4" not in "\n".join(weak) else 2
    log("weak_ss", " | ".join(weak)[:120])

    wm, wmeta = weakness_lite_mult(p, mon, ["water"], reg)
    scores["weak_mult"] = 5 if wmeta.get("active") and 1.0 < wm <= 1.06 else 2
    log("weak_mult", f"m={wm:.3f} active={wmeta.get('active')}")

    # pipeline
    r = resolve_player_outbound(
        p, mon, reg, "ancient_city", {"power": 12, "elements": ["water"]}, random.Random(7)
    )
    scores["pipeline"] = 5 if r.amount >= 1 and "identity" in r.meta else 2
    log("pipeline", f"dmg={r.amount} fl={r.flavor[:50]}")

    # wrapper + auto stability
    ok = True
    for i in range(15):
        try:
            player_attack_damage(
                p, mon, reg, "ancient_city", {"power": 10, "elements": ["physical"]}, random.Random(i)
            )
        except Exception as e:
            ok = False
            log("stable", str(e))
            break
    scores["stable"] = 5 if ok else 1
    if ok:
        log("stable", "15 hits ok")

    # soft no leak
    blob = "\n".join(pre) + "\n".join(weak) + r.flavor
    leak = any(x in blob.lower() for x in ("power_atk", "1.03", "grade_mult=", "total_identity"))
    scores["soft"] = 5 if not leak else 1
    log("soft", "ok" if not leak else "LEAK")

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
    (out / "wo054_combat_identity.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-054 Soft Combat Identity · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-055\n\n")
    md.append("**แข็ง:** identity pre-fight/hit · weakness lite SS+ · auto stable\n\n")
    md.append("**อ่อน:** mult เบามาก · ยังไม่ fusion recipes เต็ม\n\n")
    md.append("**WO-055:** Content Moments / Relic depth / playtest polish รอบใหญ่\n")
    (out / "WO054_COMBAT_IDENTITY.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-054 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
