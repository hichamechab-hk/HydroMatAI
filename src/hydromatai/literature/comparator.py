from __future__ import annotations
"""Comparison and ranking of published hydrogen-storage results."""


from dataclasses import dataclass
from typing import Iterable

from .models import LiteratureResult


@dataclass(frozen=True)
class LiteratureComparison:
    """Published-data comparison for one material."""

    material: str
    best_h2_uptake_wt_percent: float | None = None
    best_h2_uptake_g_per_l: float | None = None
    best_deliverable_wt_percent: float | None = None
    best_deliverable_g_per_l: float | None = None
    best_surface_area_m2_g: float | None = None
    result_count: int = 0


def _best(
    results: Iterable[LiteratureResult],
    property_names: set[str],
    units: set[str],
) -> float | None:
    values = [
        result.value
        for result in results
        if result.property_name in property_names
        and result.unit in units
    ]

    return max(values) if values else None


def compare_material(
    material: str,
    results: Iterable[LiteratureResult],
) -> LiteratureComparison:
    """Extract comparable published hydrogen-storage indicators."""

    material_results = [
        result
        for result in results
        if result.material.strip().lower() == material.strip().lower()
    ]

    return LiteratureComparison(
        material=material,
        best_h2_uptake_wt_percent=_best(
            material_results,
            {"h2_uptake", "h2_saturation_uptake"},
            {"wt%"},
        ),
        best_h2_uptake_g_per_l=_best(
            material_results,
            {"h2_uptake", "h2_saturation_uptake"},
            {"g/L"},
        ),
        best_deliverable_wt_percent=_best(
            material_results,
            {"h2_deliverable_capacity"},
            {"wt%"},
        ),
        best_deliverable_g_per_l=_best(
            material_results,
            {"h2_deliverable_capacity"},
            {"g/L"},
        ),
        best_surface_area_m2_g=_best(
            material_results,
            {"bet_surface_area"},
            {"m2/g"},
        ),
        result_count=len(material_results),
    )


def rank_by_published_h2_uptake(
    results: Iterable[LiteratureResult],
) -> list[LiteratureComparison]:
    """Rank materials by best published gravimetric H2 uptake."""

    material_names = sorted({
        result.material
        for result in results
    })

    comparisons = [
        compare_material(material, results)
        for material in material_names
    ]

    comparisons = [
        comparison
        for comparison in comparisons
        if comparison.best_h2_uptake_wt_percent is not None
    ]

    return sorted(
        comparisons,
        key=lambda item: item.best_h2_uptake_wt_percent,
        reverse=True,
    )


def rank_by_property(
    results: Iterable[LiteratureResult],
    property_name: str,
    unit: str,
) -> list[LiteratureComparison]:
    """Rank materials by a specific published property and unit."""

    material_names = sorted({
        result.material
        for result in results
        if result.property_name == property_name
        and result.unit == unit
    })

    comparisons: list[LiteratureComparison] = []

    for material in material_names:
        comparison = compare_material(material, results)
        comparisons.append(comparison)

    def value(comparison: LiteratureComparison) -> float:
        if property_name in {
            "h2_uptake",
            "h2_saturation_uptake",
        } and unit == "wt%":
            return comparison.best_h2_uptake_wt_percent or float("-inf")

        if property_name in {
            "h2_uptake",
            "h2_saturation_uptake",
        } and unit == "g/L":
            return comparison.best_h2_uptake_g_per_l or float("-inf")

        if property_name == "h2_deliverable_capacity" and unit == "wt%":
            return comparison.best_deliverable_wt_percent or float("-inf")

        if property_name == "h2_deliverable_capacity" and unit == "g/L":
            return comparison.best_deliverable_g_per_l or float("-inf")

        if property_name == "bet_surface_area" and unit == "m2/g":
            return comparison.best_surface_area_m2_g or float("-inf")

        return float("-inf")

    return sorted(
        comparisons,
        key=value,
        reverse=True,
    )


def summarize_by_family(
    results: Iterable[LiteratureResult],
) -> dict[str, list[LiteratureComparison]]:
    """Group published-material comparisons by material family."""

    grouped: dict[str, list[LiteratureResult]] = {}

    for result in results:
        family = result.family or "OTHER"
        grouped.setdefault(family, []).append(result)

    output: dict[str, list[LiteratureComparison]] = {}

    for family, family_results in grouped.items():
        materials = sorted({
            result.material
            for result in family_results
        })

        output[family] = [
            compare_material(material, family_results)
            for material in materials
        ]

    return output
