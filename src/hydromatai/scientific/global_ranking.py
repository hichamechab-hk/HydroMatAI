from __future__ import annotations
"""Global scientific ranking."""


from dataclasses import dataclass
from typing import Iterable

from .result import ScientificResult


@dataclass(frozen=True)
class GlobalRankingEntry:
    """Global ranking entry for one material."""

    material: str
    score: float
    hydrogen_score: float
    stability_score: float
    electronic_score: float
    optical_score: float
    literature_count: int


def _electronic_score(result: ScientificResult) -> float:
    return 1.0 if result.band_gap is not None else 0.5


def _optical_score(result: ScientificResult) -> float:
    return (
        1.0
        if result.optical_classification != "unknown"
        else 0.5
    )


def build_global_ranking(
    results: Iterable[ScientificResult],
) -> list[GlobalRankingEntry]:
    """Rank scientific results using their computed scientific scores."""

    entries: list[GlobalRankingEntry] = []

    for result in results:
        electronic = _electronic_score(result)
        optical = _optical_score(result)

        score = (
            0.30 * result.stability_score
            + 0.20 * electronic
            + 0.20 * optical
            + 0.30 * result.hydrogen_score
        )

        entries.append(
            GlobalRankingEntry(
                material=result.material,
                score=round(score, 4),
                hydrogen_score=round(result.hydrogen_score, 4),
                stability_score=round(result.stability_score, 4),
                electronic_score=round(electronic, 4),
                optical_score=round(optical, 4),
                literature_count=result.literature_count,
            )
        )

    return sorted(
        entries,
        key=lambda entry: (
            entry.score,
            entry.hydrogen_score,
            entry.literature_count,
        ),
        reverse=True,
    )
