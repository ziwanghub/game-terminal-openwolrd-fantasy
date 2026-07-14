"""Shared fixtures for unit / combat / smoke / data_validation tests."""
from __future__ import annotations

import pytest

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.ports.io import ScriptedIO


@pytest.fixture(scope="session")
def reg() -> DataRegistry:
    """Load game data once per test session."""
    return DataRegistry.load(DATA_DIR)


@pytest.fixture
def make_player(reg: DataRegistry):
    def _make(
        name: str = "TestHero",
        occupation_id: str = "warrior",
        zodiac: str = "เมษ",
        world_id: str = "default",
        **overrides,
    ):
        p = create_player(
            reg,
            name=name,
            occupation_id=occupation_id,
            zodiac=zodiac,
            world_id=world_id,
        )
        p["tutorial_done"] = True
        p.update(overrides)
        return p

    return _make


@pytest.fixture
def scripted_io():
    """Factory: scripted_io("1", "0") → ScriptedIO with those lines."""

    def _factory(*lines: str, raise_on_empty: bool = True) -> ScriptedIO:
        return ScriptedIO(list(lines), raise_on_empty=raise_on_empty)

    return _factory
