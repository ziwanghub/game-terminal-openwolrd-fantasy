"""P0 configuration — paths and UI defaults."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAVES_DIR = PROJECT_ROOT / "saves"
ART_DIR = DATA_DIR / "art"
PROTOTYPE_PATH = PROJECT_ROOT / "pixel_fantasy_openskill.py"

APP_NAME = "Open World Fantasy"
APP_VERSION = "1.13.15-alpha"
PHASE = "t0-needs-w0-rank"

# Terminal layout (RD-09)
UI_WIDTH = 60
UI_USE_UNICODE = True
