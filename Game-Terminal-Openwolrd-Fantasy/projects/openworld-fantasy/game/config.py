"""P0 configuration — paths and UI defaults."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAVES_DIR = PROJECT_ROOT / "saves"
ART_DIR = DATA_DIR / "art"
PROTOTYPE_PATH = PROJECT_ROOT / "pixel_fantasy_openskill.py"

APP_NAME = "Open World Fantasy"
APP_VERSION = "2.17.0-alpha"
PHASE = "wo-arena-1"

# Terminal layout (RD-09)
UI_WIDTH = 60
UI_USE_UNICODE = True

# WO-002 world theme / custom-world UX — deferred (player preferred simple picker).
# Code kept in world_creation / world_service; set True to re-enable.
WORLD_THEME_UX_ENABLED = False
