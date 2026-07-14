"""Pure helpers for status bars (no I/O)."""
from __future__ import annotations


def ratio_bar(current: int, maximum: int, width: int = 10, fill: str = "█", empty: str = "░") -> str:
    if maximum <= 0:
        return empty * width
    ratio = max(0.0, min(1.0, float(current) / float(maximum)))
    filled = int(round(ratio * width))
    filled = max(0, min(width, filled))
    return fill * filled + empty * (width - filled)


def xp_bar(xp_percent: float, width: int = 10) -> str:
    return ratio_bar(int(xp_percent), 100, width=width)
