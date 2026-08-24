"""Automatic electronic-property interpretation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ElectronicInterpretation:
    classification: str
    band_gap: float | None
    explanation: str


def interpret_band_gap(band_gap: float | None) -> ElectronicInterpretation:

    if band_gap is None:
        return ElectronicInterpretation(
            classification="unknown",
            band_gap=None,
            explanation=(
                "Le gap électronique n'a pas pu être déterminé "
                "à partir des données disponibles."
            ),
        )

    if band_gap <= 0.05:
        classification = "metallic_or_semimetallic"
        explanation = (
            f"Le gap estimé est très faible ({band_gap:.4f} eV). "
            "Le système présente un comportement métallique ou "
            "semi-métallique selon la précision du calcul."
        )

    elif band_gap < 3.0:
        classification = "semiconductor"
        explanation = (
            f"Le gap électronique estimé est de {band_gap:.4f} eV. "
            "Le matériau est compatible avec un comportement "
            "semi-conducteur."
        )

    else:
        classification = "insulator"
        explanation = (
            f"Le gap électronique estimé est de {band_gap:.4f} eV. "
            "Le matériau présente un comportement de type isolant."
        )

    return ElectronicInterpretation(
        classification=classification,
        band_gap=band_gap,
        explanation=explanation,
    )
