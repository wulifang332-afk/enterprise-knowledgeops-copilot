from __future__ import annotations


def format_percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"
