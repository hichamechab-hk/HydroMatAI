from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hydromatai.scientific.result import ScientificResult


@dataclass(frozen=True)
class ScientificEvaluation:
    """Évaluation normalisée d'un résultat scientifique."""

    material: str
    score: float
    stability_score: float
    hydrogen_score: float
    electronic_score: float
    optical_score: float
    literature_count: int


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def evaluate_result(
    result: ScientificResult,
) -> ScientificEvaluation:
    """
    Transforme un ScientificResult en évaluation exploitable.

    Les scores sont bornés dans [0, 1].
    Aucun calcul DFT n'est effectué.
    """
    electronic_score = (
        1.0
        if result.band_gap is not None
        else 0.5
    )

    optical_score = (
        1.0
        if result.optical_classification != "unknown"
        else 0.5
    )

    stability_score = _clamp(result.stability_score)
    hydrogen_score = _clamp(result.hydrogen_score)

    score = (
        0.30 * stability_score
        + 0.20 * electronic_score
        + 0.20 * optical_score
        + 0.30 * hydrogen_score
    )

    return ScientificEvaluation(
        material=result.material,
        score=round(score, 4),
        stability_score=round(stability_score, 4),
        hydrogen_score=round(hydrogen_score, 4),
        electronic_score=round(electronic_score, 4),
        optical_score=round(optical_score, 4),
        literature_count=result.literature_count,
    )


def evaluate_results(
    results: Iterable[ScientificResult],
) -> list[ScientificEvaluation]:
    """Évalue une collection de résultats scientifiques."""
    evaluations = [
        evaluate_result(result)
        for result in results
    ]

    return sorted(
        evaluations,
        key=lambda item: (
            item.score,
            item.hydrogen_score,
            item.literature_count,
        ),
        reverse=True,
    )
