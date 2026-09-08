from __future__ import annotations
"""Hydrogen-storage scoring from published literature."""


from dataclasses import dataclass
from typing import Iterable

from .models import LiteratureResult


@dataclass(frozen=True)
class HydrogenStorageScore:
    """Transparent literature-based hydrogen-storage score."""

    material: str

    gravimetric_score: float = 0.0
    volumetric_score: float = 0.0
    deliverable_score: float = 0.0
    surface_area_score: float = 0.0
    thermal_score: float = 0.0

    final_score: float = 0.0

    available_criteria: int = 0
    total_criteria: int = 5
    confidence: str = "LOW"

    @property
    def coverage(self) -> float:
        """Fraction of available screening criteria."""
        return self.available_criteria / self.total_criteria

    @property
    def screening_score(self) -> float:
        """Score adjusted for literature-data coverage."""
        return round(
            self.final_score * self.coverage,
            4,
        )


def _best(
    results: Iterable[LiteratureResult],
    properties: set[str],
    units: set[str],
) -> float | None:
    values = [
        result.value
        for result in results
        if result.property_name in properties
        and result.unit in units
    ]

    return max(values) if values else None


def _normalize(
    value: float | None,
    target: float,
) -> float:
    if value is None:
        return 0.0

    return min(value / target, 1.0)


def calculate_hydrogen_storage_score(
    material: str,
    results: Iterable[LiteratureResult],
) -> HydrogenStorageScore:
    """Calculate a transparent score from published measurements.

    The score is not a thermodynamic prediction. It is a normalized
    literature indicator intended for screening and comparison.
    """

    material_results = [
        result
        for result in results
        if result.material.strip().lower()
        == material.strip().lower()
    ]

    gravimetric = _best(
        material_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_storage_capacity",
            "h2_theoretical_capacity",
        },
        {"wt%"},
    )

    volumetric = _best(
        material_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_volumetric_capacity",
        },
        {"g/L"},
    )

    deliverable_wt = _best(
        material_results,
        {"h2_deliverable_capacity"},
        {"wt%"},
    )

    deliverable_gl = _best(
        material_results,
        {"h2_deliverable_capacity"},
        {"g/L"},
    )

    deliverable_values = [
        value
        for value in (
            deliverable_wt,
            deliverable_gl,
        )
        if value is not None
    ]

    deliverable = max(deliverable_values) if deliverable_values else None

    surface_area = _best(
        material_results,
        {"bet_surface_area"},
        {"m2/g"},
    )

    desorption_values = [
        result.value
        for result in material_results
        if result.property_name
        in {
            "desorption_temperature",
            "desorption_temperature_min",
            "desorption_temperature_max",
        }
        and result.unit == "degC"
    ]

    # For screening, a lower desorption temperature is preferable.
    thermal_score = 0.0

    if desorption_values:
        temperature = min(desorption_values)
        thermal_score = max(
            0.0,
            min((400.0 - temperature) / 300.0, 1.0),
        )

    gravimetric_score = _normalize(
        gravimetric,
        10.0,
    )

    volumetric_score = _normalize(
        volumetric,
        70.0,
    )

    deliverable_score = _normalize(
        deliverable,
        10.0,
    )

    surface_area_score = _normalize(
        surface_area,
        5000.0,
    )

    available = sum(
        value is not None
        for value in (
            gravimetric,
            volumetric,
            deliverable,
            surface_area,
            min(desorption_values)
            if desorption_values
            else None,
        )
    )

    weights = (
        gravimetric_score,
        volumetric_score,
        deliverable_score,
        surface_area_score,
        thermal_score,
    )

    if available:
        final = sum(weights) / available
    else:
        final = 0.0

    coverage = available / 5.0

    if coverage >= 0.8:
        confidence = "HIGH"
    elif coverage >= 0.6:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return HydrogenStorageScore(
        material=material,
        gravimetric_score=round(gravimetric_score, 4),
        volumetric_score=round(volumetric_score, 4),
        deliverable_score=round(deliverable_score, 4),
        surface_area_score=round(surface_area_score, 4),
        thermal_score=round(thermal_score, 4),
        final_score=round(final, 4),
        available_criteria=available,
        confidence=confidence,
    )
