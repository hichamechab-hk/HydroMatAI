from __future__ import annotations
"""Scientific interpretation layer."""


from hydromatai.literature import (
    LiteratureResult,
    calculate_hydrogen_storage_score,
    calculate_objective_score,
)

from .ranking import calculate_material_score
from .result import ScientificResult


def analyze_material(
    material: str,
    total_energy: float | None = None,
    band_gap: float | None = None,
    electronic_classification: str = "unknown",
    optical_classification: str = "unknown",
    literature_results: list[LiteratureResult] | None = None,
) -> ScientificResult:
    """Analyze a material and optionally attach published results."""

    stability = 1.0 if total_energy is not None else 0.5

    electronic_score = 1.0 if band_gap is not None else 0.5

    optical_score = (
        1.0
        if optical_classification != "unknown"
        else 0.5
    )

    hydrogen_score = 0.5

    attached_literature = list(literature_results or [])

    # Use published near-ambient hydrogen performance when available.
    # Otherwise preserve the historical neutral hydrogen score.
    ambient_score = (
        calculate_objective_score(
            material,
            attached_literature,
            "AMBIENT",
        )
        if attached_literature
        else None
    )

    if ambient_score is not None and ambient_score.coverage > 0.0:
        hydrogen_score = ambient_score.screening_score

    final = calculate_material_score(
        stability,
        electronic_score,
        optical_score,
        hydrogen_score,
    )

    hydrogen_literature_score = (
        calculate_hydrogen_storage_score(
            material,
            attached_literature,
        )
        if attached_literature
        else None
    )

    literature_note = (
        f"; published results={len(attached_literature)}"
        if attached_literature
        else "; published results=0"
    )

    return ScientificResult(
        material=material,
        total_energy=total_energy,
        band_gap=band_gap,
        electronic_classification=electronic_classification,
        optical_classification=optical_classification,
        stability_score=stability,
        hydrogen_score=hydrogen_score,
        final_score=final,
        summary=(
            f"{material}: scientific score={final}{literature_note}"
        ),
        literature_results=attached_literature,
        hydrogen_literature_score=hydrogen_literature_score,
    )
