"""Material ranking utilities."""

from __future__ import annotations


def calculate_material_score(
    stability: float,
    electronic: float,
    optical: float,
    hydrogen: float,
) -> float:

    score = (
        0.30 * stability +
        0.20 * electronic +
        0.20 * optical +
        0.30 * hydrogen
    )

    return round(score, 4)
