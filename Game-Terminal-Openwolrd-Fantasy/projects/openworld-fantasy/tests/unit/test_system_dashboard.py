"""System evaluation dashboard — build/render/export (text only)."""
from pathlib import Path

from game.admin.dashboard import (
    DASHBOARD_YAML,
    build_report,
    export_report,
    gather_live_metrics,
    render_markdown,
    render_terminal,
)


def test_dashboard_yaml_exists():
    assert DASHBOARD_YAML.is_file()


def test_gather_live_metrics():
    m = gather_live_metrics()
    assert m["areas"] >= 1
    assert m["monsters"] >= 1
    assert m["app_version"]
    assert m["test_files"] >= 1


def test_build_report_overall_and_systems():
    report = build_report()
    assert 0 <= report["overall_score"] <= 10
    assert len(report["systems"]) >= 5
    assert report["improve_top"]
    assert report["recommended_order"]
    assert "combat" in {s["id"] for s in report["systems"]}


def test_render_terminal_contains_scores():
    report = build_report()
    text = render_terminal(report)
    assert "แดชบอร์ดระบบเกม" in text
    assert "คะแนนรวม" in text
    assert "แผนเฟส" in text
    assert "█" in text or "░" in text


def test_render_markdown_and_export_text(tmp_path: Path):
    report = build_report()
    md = render_markdown(report)
    assert "# แดชบอร์ดระบบเกม" in md
    assert "ควรพัฒนา" in md

    md_path, txt_path = export_report(report, tmp_path)
    assert md_path.is_file()
    assert txt_path.is_file()
    assert (tmp_path / "dashboard_latest.md").is_file()
    assert (tmp_path / "dashboard_latest.txt").is_file()
    assert not list(tmp_path.glob("*.svg"))
