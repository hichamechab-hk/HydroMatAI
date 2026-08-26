"""Scientific interpretation layer."""

from __future__ import annotations

from .result import ScientificResult
from .ranking import calculate_material_score


def analyze_material(
    material: str,
    total_energy: float | None = None,
    band_gap: float | None = None,
    electronic_classification: str = "unknown",
    optical_classification: str = "unknown",
):

    stability = 1.0 if total_energy is not None else 0.5

    electronic_score = (
        1.0
        if band_gap is not None
        else 0.5
    )

    optical_score = (
        1.0
        if optical_classification != "unknown"
        else 0.5
    )

    hydrogen_score = 0.5


    final = calculate_material_score(
        stability,
        electronic_score,
        optical_score,
        hydrogen_score,
    )


    return ScientificResult(

        material=material,

        total_energy=total_energy,

        band_gap=band_gap,

        electronic_classification=
            electronic_classification,

        optical_classification=
            optical_classification,

        stability_score=stability,

        hydrogen_score=hydrogen_score,

        final_score=final,

        summary=(
            f"{material}: "
            f"scientific score={final}"
        )
    )
