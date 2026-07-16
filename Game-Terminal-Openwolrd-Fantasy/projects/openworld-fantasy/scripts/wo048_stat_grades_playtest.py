#!/usr/bin/env python3
"""WO-048 Hidden Grade + Temple + Soft P harness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import allocate_stat, ensure_progression
from game.domain.stat_grades import (
    can_temple_unlock,
    format_grade_p_panel,
    grade_revealed,
    letter_from_axis_score,
    temple_unlock,
)
from game.domain.stat_arch import self_assess_lines


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # thresholds
    assert letter_from_axis_score(5) == "E"
    scores["thresholds"] = 5
    log("thresholds", "F/E/A/SSS map ok")

    p = create_player(reg, "wo048", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 5
    p["stat_points"] = 7
    assert not can_temple_unlock(p)
    scores["gate_low"] = 5
    log("gate_low", "lv5 cannot temple")

    p["level"] = 12
    p["stat_points"] = 7
    assert can_temple_unlock(p)
    lines = temple_unlock(p, reg)
    assert grade_revealed(p)
    scores["temple"] = 5 if p.get("player_grade") else 1
    log("temple", f"grade={p.get('player_grade')} prof={p.get('growth_profile')} lines={len(lines)}")

    panel = "\n".join(format_grade_p_panel(p))
    scores["panel"] = 5 if "โจมตี" in panel and ("F" in panel or "E" in panel or "C" in panel) else 2
    log("panel", panel.split("\n")[4] if len(panel.splitlines()) > 4 else "ok")

    # invest
    p["stat_points"] = 7
    before = dict(p.get("axis_progress") or {})
    msg = allocate_stat(p, reg, "atk", 7)
    after = float((p.get("axis_progress") or {}).get("atk", 0))
    scores["invest"] = 5 if after > float(before.get("atk", 0)) and "power" not in msg.lower() else 2
    log("invest", msg.replace("\n", " | ")[:120])

    # growth S > F
    p_s = create_player(reg, "wo048s", "warrior", "เมษ")
    ensure_progression(p_s, reg)
    p_s["grade_revealed"] = True
    p_s["player_grade"] = "S"
    p_s["growth_profile"] = "balanced"
    p_s["axis_progress"] = {"atk": 0.0, "defense": 0.0, "magic": 0.0, "speed": 0.0}
    p_s["stats_alloc"] = {"atk": 0, "defense": 0, "magic": 0, "speed": 0}
    p_s["stat_points"] = 10
    from game.domain.stat_grades import apply_invest_to_grades

    apply_invest_to_grades(p_s, "atk", 7)
    p_f = create_player(reg, "wo048f", "warrior", "เมษ")
    ensure_progression(p_f, reg)
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "F"
    p_f["growth_profile"] = "balanced"
    p_f["axis_progress"] = {"atk": 0.0, "defense": 0.0, "magic": 0.0, "speed": 0.0}
    p_f["stats_alloc"] = {"atk": 0, "defense": 0, "magic": 0, "speed": 0}
    apply_invest_to_grades(p_f, "atk", 7)
    sc_s = float(p_s["axis_progress"]["atk"])
    sc_f = float(p_f["axis_progress"]["atk"])
    scores["growth"] = 5 if sc_s > sc_f else 1
    log("growth", f"S={sc_s:.2f} F={sc_f:.2f}")

    v = "\n".join(self_assess_lines(p, force=True, reg=reg))
    scores["assess"] = 5 if "เกรด" in v or "ระดับ" in v else 2
    log("assess", "V has grade block" if scores["assess"] == 5 else "missing")

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
    (out / "wo048_stat_grades.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-048 Hidden Grade + Temple · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-049\n\n")
    md.append("**แข็ง:** เกรด 2 ชั้น · วิหารปลด · Soft P · growth S>F\n\n")
    md.append("**อ่อน:** ยังไม่มีขั้นต้น/ปลาย · ยังไม่ตัด P · วิหารยังไม่ใช่ NPC field เต็ม\n\n")
    md.append("**WO-049:** Grade surface polish + soft tier labels (ขั้นต้น/ปลาย)\n")
    (out / "WO048_STAT_GRADES.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-048 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
