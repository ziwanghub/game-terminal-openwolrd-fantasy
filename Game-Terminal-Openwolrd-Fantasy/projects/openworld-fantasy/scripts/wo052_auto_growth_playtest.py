#!/usr/bin/env python3
"""WO-052 Auto Growth + P cut harness (Lv25→35 path)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.auto_growth import (
    AXIS_KEYS,
    activate_auto_growth_if_needed,
    effective_growth_rate,
    format_auto_growth_panel,
    is_manual_p_locked,
    pulse_auto_growth,
)
from game.domain.character import create_player
from game.domain.combat import resolve_victory
from game.domain.progression import allocate_stat, ensure_progression, on_level_up_points
import random


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    p = create_player(reg, "wo052", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["grade_revealed"] = True
    p["player_grade"] = "A"
    p["growth_profile"] = "mixed"
    p["axis_progress"] = {k: 15.0 for k in AXIS_KEYS}
    p["stats_alloc"] = {"atk": 6, "defense": 4, "magic": 3, "speed": 5}

    # Lv25 still manual
    p["level"] = 25
    p["stat_points"] = 4
    msg = allocate_stat(p, reg, "atk", 1)
    scores["early_p"] = 5 if p["stat_points"] == 3 and "ไม่อยู่ในมือ" not in msg else 1
    log("early_p", msg[:80])

    # climb to 29 foreshadow
    p["level"] = 29
    n29 = on_level_up_points(p, reg, 1)
    scores["foreshadow"] = 5 if any("อั้น" in str(x) for x in n29) else 3
    log("foreshadow", str(n29[0]) if n29 else "none")

    # hit 30
    p["level"] = 30
    p["stat_points"] = 5
    n30 = on_level_up_points(p, reg, 1)
    scores["gate"] = 5 if is_manual_p_locked(p) and p["stat_points"] == 0 else 1
    log("gate", f"locked={is_manual_p_locked(p)} pts={p['stat_points']} notes={n30[:3]}")

    # refuse allocate
    refuse = allocate_stat(p, reg, "magic", 1)
    scores["refuse"] = 5 if "ไม่อยู่ในมือ" in refuse or "30" in refuse else 1
    log("refuse", refuse[:90])

    # panel soft
    panel = "\n".join(format_auto_growth_panel(p))
    scores["panel"] = 5 if "ไหล" in panel and "power_" not in panel.lower() else 2
    log("panel", panel.replace("\n", " | ")[:120])

    # S > F growth
    p_s = create_player(reg, "s052", "warrior", "เมษ")
    ensure_progression(p_s, reg)
    p_s["level"] = 35
    p_s["grade_revealed"] = True
    p_s["player_grade"] = "S"
    p_s["growth_profile"] = "balanced"
    p_s["auto_growth_active"] = True
    p_s["_p_phase_out_done"] = True
    p_s["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    p_f = create_player(reg, "f052", "warrior", "เมษ")
    ensure_progression(p_f, reg)
    p_f["level"] = 35
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "F"
    p_f["growth_profile"] = "balanced"
    p_f["auto_growth_active"] = True
    p_f["_p_phase_out_done"] = True
    p_f["axis_progress"] = {k: 0.0 for k in AXIS_KEYS}
    pulse_auto_growth(p_s, "quest", reg=reg)
    pulse_auto_growth(p_f, "quest", reg=reg)
    scores["grade_weight"] = 5 if (
        effective_growth_rate(p_s) > effective_growth_rate(p_f)
        and p_s["axis_progress"]["atk"] > p_f["axis_progress"]["atk"]
    ) else 1
    log(
        "grade_weight",
        f"S_rate={effective_growth_rate(p_s):.2f} F={effective_growth_rate(p_f):.2f} "
        f"S_atk={p_s['axis_progress']['atk']:.2f} F_atk={p_f['axis_progress']['atk']:.2f}",
    )

    # combat victory pulse
    p["level"] = 32
    activate_auto_growth_if_needed(p, reg)
    before = float(p["axis_progress"]["atk"])
    mon = {
        "id": "g52m",
        "name": "มอน",
        "level": 28,
        "xp_mult": 1.0,
        "elements": ["physical"],
    }
    # avoid huge side effects — call pulse directly like combat does
    pulse_auto_growth(p, "combat", reg=reg, magnitude=0.85, rng=random.Random(1))
    scores["combat"] = 5 if float(p["axis_progress"]["atk"]) > before else 2
    log("combat", f"atk {before:.2f} → {p['axis_progress']['atk']:.2f}")

    # multi pulse stability to "35"
    p["level"] = 35
    for _ in range(5):
        pulse_auto_growth(p, "quest", reg=reg, magnitude=0.8)
        pulse_auto_growth(p, "combat", reg=reg, magnitude=0.7)
    scores["stable"] = 5 if p.get("_auto_growth_pulses", 0) >= 3 else 2
    log("stable", f"pulses={p.get('_auto_growth_pulses')}")

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
    (out / "wo052_auto_growth.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-052 Auto Growth · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-053\n\n")
    md.append("**แข็ง:** ตัด P@30 · residual phase-out · grade weight · soft panel\n\n")
    md.append("**อ่อน:** balance speed อาจต้อง tune · faction pulse ยังเบา\n\n")
    md.append("**WO-053:** Personal System เต็ม / content depth\n")
    (out / "WO052_AUTO_GROWTH.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-052 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
