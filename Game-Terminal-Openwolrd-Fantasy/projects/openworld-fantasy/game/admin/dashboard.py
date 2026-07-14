"""Game systems evaluation dashboard — text overview of scores, improve hints, roadmap.

Usage:
  python3 -m game.admin.dashboard
  python3 -m game.admin.dashboard --no-export
  python3 -m game.admin.dashboard --export-dir path

Prints to terminal; optional export as .txt / .md only (no images).
Also available from in-game admin menu.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from game.config import APP_NAME, APP_VERSION, DATA_DIR, PHASE, PROJECT_ROOT, UI_WIDTH
from game.data_load.registry import get_registry
from game.ports.io import IO, get_io

DASHBOARD_YAML = DATA_DIR / "meta" / "system_dashboard.yaml"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports"

MATURITY_TH = {
    "vision": "วิสัยทัศน์",
    "stub": "โครงเบา",
    "alpha": "อัลฟ่า",
    "solid": "แน่น",
    "polished": "ขัดเงา",
}

STATUS_TH = {
    "queued": "คิว",
    "optional": "optional",
    "planned": "แผนแล้ว",
    "later": "ทีหลัง",
    "done": "เสร็จ",
    "active": "กำลังทำ",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"ไม่พบ dashboard data: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("system_dashboard.yaml ต้องเป็น mapping")
    return data


def gather_live_metrics() -> Dict[str, Any]:
    """Counts from DataRegistry + rough test/file presence."""
    reg = get_registry()
    board = reg.mission_board or {}
    missions = board.get("missions") or board.get("entries") or []
    if isinstance(missions, dict):
        n_missions = len(missions)
    else:
        n_missions = len(missions) if isinstance(missions, list) else 0

    tests_dir = PROJECT_ROOT / "tests"
    test_files = list(tests_dir.rglob("test_*.py")) if tests_dir.is_dir() else []

    docs_dir = PROJECT_ROOT / "docs"
    doc_files = list(docs_dir.glob("*.md")) if docs_dir.is_dir() else []

    return {
        "areas": len(reg.areas),
        "monsters": len(reg.monsters),
        "items": len(reg.items),
        "skills": len(reg.skills),
        "quests": len(reg.quests),
        "recipes": len(reg.recipes),
        "worlds": len(reg.worlds),
        "missions": n_missions,
        "statuses": len(reg.statuses),
        "test_files": len(test_files),
        "doc_files": len(doc_files),
        "app_version": APP_VERSION,
        "phase": PHASE,
    }


def _bar(score: float, width: int = 10) -> str:
    score = max(0.0, min(10.0, float(score)))
    filled = int(round(score / 10.0 * width))
    return "█" * filled + "░" * (width - filled)


def _score_band(score: float) -> str:
    if score >= 8.0:
        return "ดี"
    if score >= 6.5:
        return "พอใช้"
    if score >= 4.0:
        return "ต้องดูแล"
    if score >= 1.5:
        return "เริ่มต้น/vision"
    return "ยังไม่ทำ"


def _weighted_average(systems: Sequence[Dict[str, Any]], weights: Dict[str, float]) -> float:
    total_w = 0.0
    acc = 0.0
    for s in systems:
        sid = str(s.get("id") or "")
        w = float(weights.get(sid, 1.0))
        sc = float(s.get("score") or 0)
        acc += sc * w
        total_w += w
    if total_w <= 0:
        return 0.0
    return round(acc / total_w, 2)


def build_report(cfg: Optional[Dict[str, Any]] = None, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or _load_yaml(DASHBOARD_YAML)
    metrics = metrics or gather_live_metrics()
    systems = list(cfg.get("systems") or [])
    weights = dict(cfg.get("weights") or {})
    overall = _weighted_average(systems, weights)

    # Systems to improve: high priority (1–2) first, then lowest scores among non-vision optional
    improve = sorted(
        systems,
        key=lambda s: (
            int(s.get("priority_improve") or 5),
            float(s.get("score") or 0),
        ),
    )
    improve_top = improve[:6]

    roadmap = cfg.get("roadmap") or {}
    recommended_order = list(cfg.get("recommended_order") or [])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "app_name": APP_NAME,
        "app_version": metrics.get("app_version", APP_VERSION),
        "phase": metrics.get("phase", PHASE),
        "version_note": cfg.get("version_note") or "",
        "updated": cfg.get("updated") or "",
        "overall_blurb": (cfg.get("overall_blurb") or "").strip(),
        "overall_score": overall,
        "overall_band": _score_band(overall),
        "systems": systems,
        "improve_top": improve_top,
        "roadmap": roadmap,
        "recommended_order": recommended_order,
        "metrics": metrics,
        "source": _rel_to_project(DASHBOARD_YAML),
    }


def _rel_to_project(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def render_terminal(report: Dict[str, Any], width: int = UI_WIDTH) -> str:
    w = max(40, width)
    lines: List[str] = []
    sep = "═" * w
    thin = "─" * w

    lines.append(sep)
    lines.append(f" แดชบอร์ดระบบเกม · {report['app_name']}")
    lines.append(f" {report['app_version']} · {report['phase']}")
    lines.append(f" สร้าง: {report['generated_at']}")
    lines.append(sep)

    ov = report["overall_score"]
    lines.append(f" คะแนนรวม (ถ่วงน้ำหนัก): {ov}/10  {_bar(ov, 12)}  [{report['overall_band']}]")
    if report.get("overall_blurb"):
        for chunk in _wrap(str(report["overall_blurb"]), w - 2):
            lines.append(f" {chunk}")
    lines.append(thin)

    m = report["metrics"]
    lines.append(
        f" เนื้อหาสด: พื้นที่ {m.get('areas')} · มอน {m.get('monsters')} · "
        f"ไอเทม {m.get('items')} · สกิล {m.get('skills')}"
    )
    lines.append(
        f"          เควส {m.get('quests')} · กระดาน {m.get('missions')} · "
        f"คราฟ {m.get('recipes')} · โลก {m.get('worlds')}"
    )
    lines.append(f" เทสไฟล์ ~{m.get('test_files')} · docs {m.get('doc_files')}")
    lines.append(thin)

    lines.append(" ▸ ประเมินแต่ละระบบ")
    lines.append(f" {'ระบบ':<28} {'คะแนน':>5}  แถบ        วุฒิ     ปรับ")
    for s in report["systems"]:
        name = str(s.get("name") or s.get("id"))[:28]
        sc = float(s.get("score") or 0)
        mat = MATURITY_TH.get(str(s.get("maturity") or ""), str(s.get("maturity") or "?"))[:6]
        pri = int(s.get("priority_improve") or 5)
        lines.append(f" {name:<28} {sc:>4.1f}  {_bar(sc)}  {mat:<6} P{pri}")
    lines.append(thin)

    lines.append(" ▸ ควรพัฒนา/ปรับปรุงก่อน (priority + คะแนน)")
    for i, s in enumerate(report["improve_top"], 1):
        name = s.get("name") or s.get("id")
        sc = s.get("score")
        rec = s.get("recommend") or ""
        lines.append(f"  {i}. [{sc}/10 · P{s.get('priority_improve')}] {name}")
        if rec:
            for chunk in _wrap(f"→ {rec}", w - 4):
                lines.append(f"     {chunk}")
        gaps = s.get("gaps") or []
        if gaps:
            lines.append(f"     ช่องว่าง: {gaps[0]}")
    lines.append(thin)

    lines.append(" ▸ แผนเฟสที่จะทำต่อ")
    order = report.get("recommended_order") or []
    if order:
        lines.append("  ลำดับแนะนำ:")
        for j, step in enumerate(order, 1):
            lines.append(f"   {j}. {step}")

    rd = report.get("roadmap") or {}
    for section, title in (
        ("near", "ใกล้ (near)"),
        ("tama", "UX-Tama"),
        ("world", "World Server"),
        ("help", "Help Situation"),
        ("later", "V Later"),
    ):
        items = rd.get(section) or []
        if not items:
            continue
        lines.append(f"  · {title}")
        for it in items:
            st = STATUS_TH.get(str(it.get("status") or ""), str(it.get("status") or ""))
            tid = it.get("id") or ""
            title_i = it.get("title") or ""
            lines.append(f"     [{st}] {tid}: {title_i}")

    lines.append(sep)
    lines.append(f" แหล่งคะแนน: {report.get('source')}")
    lines.append(" แก้ YAML แล้วรันใหม่: python3 -m game.admin.dashboard")
    lines.append(sep)
    return "\n".join(lines)


def _wrap(text: str, width: int) -> List[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    out: List[str] = []
    while len(text) > width:
        cut = text.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        out.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        out.append(text)
    return out


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# แดชบอร์ดระบบเกม — {report['app_name']}")
    lines.append("")
    lines.append(f"**สร้าง:** {report['generated_at']}  ")
    lines.append(f"**เวอร์ชัน:** `{report['app_version']}` · phase `{report['phase']}`  ")
    lines.append(f"**คะแนนรวม (ถ่วงน้ำหนัก):** **{report['overall_score']}/10** ({report['overall_band']})  ")
    lines.append(f"**แหล่ง:** `{report.get('source')}`")
    lines.append("")
    if report.get("overall_blurb"):
        lines.append(f"> {report['overall_blurb']}")
        lines.append("")

    m = report["metrics"]
    lines.append("## เมตริกเนื้อหา (สดจาก registry)")
    lines.append("")
    lines.append("| ชนิด | จำนวน |")
    lines.append("|------|------:|")
    for k, label in (
        ("areas", "พื้นที่"),
        ("monsters", "มอน"),
        ("items", "ไอเทม"),
        ("skills", "สกิล"),
        ("quests", "เควส"),
        ("missions", "กระดาน"),
        ("recipes", "คราฟ"),
        ("worlds", "โลก"),
        ("statuses", "สถานะ"),
        ("test_files", "test_*.py"),
        ("doc_files", "docs/*.md"),
    ):
        lines.append(f"| {label} | {m.get(k, 0)} |")
    lines.append("")

    lines.append("## ประเมินแต่ละระบบ")
    lines.append("")
    lines.append("| ระบบ | คะแนน | แถบ | วุฒิ | ปรับ (1=สูง) | แนะนำ |")
    lines.append("|------|------:|:----|:-----|-------------:|--------|")
    for s in report["systems"]:
        sc = float(s.get("score") or 0)
        mat = MATURITY_TH.get(str(s.get("maturity") or ""), str(s.get("maturity")))
        rec = str(s.get("recommend") or "").replace("|", "/")
        lines.append(
            f"| {s.get('name')} | {sc:.1f} | `{_bar(sc)}` | {mat} | "
            f"{s.get('priority_improve')} | {rec} |"
        )
    lines.append("")

    lines.append("## ควรพัฒนา/ปรับปรุงก่อน")
    lines.append("")
    for i, s in enumerate(report["improve_top"], 1):
        lines.append(f"### {i}. {s.get('name')} — {s.get('score')}/10 (P{s.get('priority_improve')})")
        lines.append("")
        if s.get("recommend"):
            lines.append(f"**แนะนำ:** {s['recommend']}")
            lines.append("")
        gaps = s.get("gaps") or []
        if gaps:
            lines.append("**ช่องว่าง:**")
            for g in gaps:
                lines.append(f"- {g}")
            lines.append("")
        strengths = s.get("strengths") or []
        if strengths:
            lines.append("**จุดแข็ง:**")
            for g in strengths:
                lines.append(f"- {g}")
            lines.append("")

    lines.append("## แผนเฟสพัฒนาต่อ")
    lines.append("")
    if report.get("recommended_order"):
        lines.append("**ลำดับแนะนำ**")
        lines.append("")
        for j, step in enumerate(report["recommended_order"], 1):
            lines.append(f"{j}. {step}")
        lines.append("")

    rd = report.get("roadmap") or {}
    labels = {
        "near": "ใกล้",
        "tama": "UX-Tama (T0–T3)",
        "world": "World Server (W0–W4)",
        "help": "Help Situation (H0–H5)",
        "later": "V Later",
    }
    for key, title in labels.items():
        items = rd.get(key) or []
        if not items:
            continue
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| id | งาน | สถานะ | หมายเหตุ |")
        lines.append("|----|-----|--------|----------|")
        for it in items:
            st = STATUS_TH.get(str(it.get("status") or ""), str(it.get("status") or ""))
            note = str(it.get("note") or "").replace("|", "/")
            lines.append(f"| {it.get('id')} | {it.get('title')} | {st} | {note} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("รันใหม่: `python3 -m game.admin.dashboard` · แก้คะแนน: `data/meta/system_dashboard.yaml`")
    lines.append("")
    return "\n".join(lines)


def export_report(
    report: Dict[str, Any],
    export_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    """Export text only: terminal dump (.txt) + markdown report (.md)."""
    export_dir = Path(export_dir or DEFAULT_EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = export_dir / f"dashboard_{stamp}.md"
    txt_path = export_dir / f"dashboard_{stamp}.txt"
    latest_md = export_dir / "dashboard_latest.md"
    latest_txt = export_dir / "dashboard_latest.txt"

    md = render_markdown(report)
    txt = render_terminal(report, width=72)

    md_path.write_text(md, encoding="utf-8")
    txt_path.write_text(txt, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")
    latest_txt.write_text(txt, encoding="utf-8")
    return md_path, txt_path


def run_dashboard(
    io: Optional[IO] = None,
    *,
    do_export: bool = True,
    export_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    io = io or get_io()
    report = build_report()
    text = render_terminal(report)
    for line in text.splitlines():
        io.write_line(line)

    if do_export:
        md_path, txt_path = export_report(report, export_dir)
        out = Path(export_dir or DEFAULT_EXPORT_DIR)
        io.write_line("")
        io.write_line(f" export txt: {txt_path}")
        io.write_line(f" export md : {md_path}")
        io.write_line(f" latest    : {out / 'dashboard_latest.txt'}")
        io.write_line(f"             {out / 'dashboard_latest.md'}")
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Open World Fantasy — system evaluation dashboard")
    parser.add_argument("--no-export", action="store_true", help="พิมพ์เทอร์มินัลอย่างเดียว")
    parser.add_argument("--export-dir", type=Path, default=None, help="โฟลเดอร์ export (default: exports/)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    run_dashboard(do_export=not args.no_export, export_dir=args.export_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
