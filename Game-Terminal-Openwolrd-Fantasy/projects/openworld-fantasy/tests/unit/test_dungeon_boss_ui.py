"""Dungeon floor-boss challenge / spawn panels — proportional UI."""
from __future__ import annotations

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import begin_dungeon, count_escape_shards, get_run
from game.domain.equipment import add_item, recompute_stats
from game.services.dungeon_session import _confirm_floor_boss
from game.ui_terminal.layout import display_width


class _IO:
    def __init__(self, answers=None):
        self.answers = list(answers or ["0"])
        self.lines: list[str] = []

    def write_line(self, text: str = "") -> None:
        self.lines.append(str(text))

    def read_line(self, prompt: str = "") -> str:
        if self.answers:
            return self.answers.pop(0)
        return "0"

    def joined(self) -> str:
        return "\n".join(self.lines)


def test_version_dungeon_boss_ui():
    assert "2.2" in APP_VERSION  # 2.20+ line incl. 2.21 worthiness
    assert PHASE
    assert any(
        k in PHASE for k in ("dungeon-boss", "skill-ui", "appraise", "storage", "wo-storage")
    ) or "-" in PHASE


def test_confirm_floor_boss_panel_sections():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dbu", "warrior", "เมษ")
    recompute_stats(p, reg)
    # enter any dungeon if available
    d_ids = list((reg.dungeons_cfg or {}).get("dungeons") or [])
    if not d_ids and hasattr(reg, "dungeons"):
        pass
    # begin via data
    from game.data_load.loader import load_list_file
    from pathlib import Path

    dpath = Path(DATA_DIR) / "dungeons" / "dungeons.yaml"
    # soft begin
    import random

    from game.domain.dungeon import begin_dungeon as bd

    # pick first dungeon id from yaml list structure
    import yaml

    raw = yaml.safe_load(dpath.read_text())
    if isinstance(raw, dict):
        dlist = raw.get("dungeons") or []
    else:
        dlist = raw or []
    if not dlist:
        return
    did = str(dlist[0].get("id") or dlist[0])
    bd(p, reg, did, random.Random(1))
    add_item(p, "escape_shard", reg)  # may not exist — ignore
    io = _IO(["0"])
    assert _confirm_floor_boss(p, reg, io) is False
    text = io.joined()
    assert "ท้าทาย" in text
    assert "กติกา" in text
    assert "เศษหนี" in text or "ทางหนี" in text
    assert "1" in text and "0" in text
    for ln in text.splitlines():
        if ln.startswith("┌") or ln.startswith("│") or ln.startswith("└") or ln.startswith("├"):
            assert display_width(ln) <= 62


def test_confirm_accepts_challenge():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db1", "warrior", "เมษ")
    recompute_stats(p, reg)
    import random
    import yaml
    from pathlib import Path
    from game.domain.dungeon import begin_dungeon as bd

    raw = yaml.safe_load((Path(DATA_DIR) / "dungeons" / "dungeons.yaml").read_text())
    dlist = (raw.get("dungeons") if isinstance(raw, dict) else raw) or []
    if not dlist:
        return
    did = str(dlist[0].get("id") or dlist[0])
    bd(p, reg, did, random.Random(2))
    io = _IO(["1"])
    assert _confirm_floor_boss(p, reg, io) is True
