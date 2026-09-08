from __future__ import annotations
"""Objective-oriented hydrogen storage screening."""


from dataclasses import dataclass
from typing import Iterable

from .hydrogen_score import calculate_hydrogen_storage_score
from .models import LiteratureResult


@dataclass(frozen=True)
class ObjectiveScore:
    material: str
    objective: str
    raw_score: float
    coverage: float
    screening_score: float
    confidence: str


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


def calculate_objective_score(
    material: str,
    results: Iterable[LiteratureResult],
    objective: str = "GLOBAL",
) -> ObjectiveScore:
    """Calculate an objective-oriented literature screening score."""

    objective = objective.strip().upper()

    if objective not in {"AMBIENT", "HIGH_DENSITY", "GLOBAL"}:
        raise ValueError(
            "objective must be AMBIENT, HIGH_DENSITY or GLOBAL"
        )

    material_results = [
        result
        for result in results
        if result.material.strip().lower()
        == material.strip().lower()
    ]

    base = calculate_hydrogen_storage_score(
        material,
        material_results,
    )

    h2_g_l = _best(
        material_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_volumetric_capacity",
            "h2_storage_capacity",
        },
        {"g/L"},
    )

    h2_wt = _best(
        material_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_storage_capacity",
            "h2_theoretical_capacity",
        },
        {"wt%"},
    )

    # --------------------------------------------------------
    # Explicit near-ambient measurements.
    #
    # AMBIENT is based on the actual measurement temperature,
    # not on cryogenic data or on desorption temperature alone.
    #
    # Accepted range: 285 K <= T <= 303 K.
    # This covers the experimental ambient references used by
    # HydroMatAI, including LaNi5 at 285 K and measurements
    # around 293-300 K.
    # --------------------------------------------------------

    def _temperature_kelvin(result: LiteratureResult) -> float | None:
        value = result.conditions.get("temperature")

        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().lower()

        if not text:
            return None

        if text in {"ambient", "room", "room temperature"}:
            return 298.15

        import re

        match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(?:k|kelvin)?", text)

        if not match:
            return None

        try:
            return float(match.group(1))
        except ValueError:
            return None

    ambient_results = [
        result
        for result in material_results
        if (
            _temperature_kelvin(result) is not None
            and 285.0 <= _temperature_kelvin(result) <= 303.0
        )
    ]

    ambient_wt = _best(
        ambient_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_deliverable_capacity",
            "h2_storage_capacity",
        },
        {"wt%"},
    )

    ambient_g_l = _best(
        ambient_results,
        {
            "h2_uptake",
            "h2_saturation_uptake",
            "h2_deliverable_capacity",
            "h2_storage_capacity",
        },
        {"g/L"},
    )

    desorption = _best(
        material_results,
        {
            "desorption_temperature",
            "desorption_temperature_min",
        },
        {"degC"},
    )

    thermal_score = 0.0

    if desorption is not None:
        thermal_score = max(
            0.0,
            min((400.0 - desorption) / 300.0, 1.0),
        )

    ambient_storage_score = 0.0

    if ambient_wt is not None:
        ambient_storage_score = max(
            ambient_storage_score,
            min(ambient_wt / 10.0, 1.0),
        )

    if ambient_g_l is not None:
        ambient_storage_score = max(
            ambient_storage_score,
            min(ambient_g_l / 70.0, 1.0),
        )

    density_score = (
        min(h2_g_l / 70.0, 1.0)
        if h2_g_l is not None
        else 0.0
    )

    if objective == "AMBIENT":
        # ----------------------------------------------------
        # AMBIENT objective
        #
        # Primary criterion:
        #   experimental H2 uptake close to room temperature.
        #
        # Secondary criteria:
        #   proximity to 298 K
        #   equilibrium/measurement pressure
        #
        # Cryogenic measurements are excluded.
        # ----------------------------------------------------

        ambient_candidates = []

        for result in ambient_results:
            if result.property_name not in {
                "h2_uptake",
                "h2_saturation_uptake",
                "h2_deliverable_capacity",
                "h2_storage_capacity",
            }:
                continue

            if result.unit != "wt%":
                continue

            temperature = _temperature_kelvin(result)
            if temperature is None:
                continue

            pressure = result.conditions.get("pressure")
            pressure_value = None

            if isinstance(pressure, (int, float)):
                pressure_value = float(pressure)
            elif pressure:
                import re
                match = re.search(
                    r"([-+]?\d+(?:\.\d+)?)",
                    str(pressure),
                )
                if match:
                    try:
                        pressure_value = float(match.group(1))
                    except ValueError:
                        pressure_value = None

            ambient_candidates.append(
                (result, temperature, pressure_value)
            )

        if not ambient_candidates:
            raw = 0.0
            criteria = 0

        else:
            best_result, best_temperature, best_pressure = max(
                ambient_candidates,
                key=lambda item: item[0].value,
            )

            storage_score = min(
                best_result.value / 10.0,
                1.0,
            )

            # 1.0 exactly at 298 K.
            # Gracefully decreases toward the limits 285/303 K.
            temperature_score = max(
                0.0,
                1.0 - abs(best_temperature - 298.0) / 15.0,
            )

            # Lower equilibrium pressure is preferable.
            # 0.1 MPa -> 1.0
            # 1 MPa   -> ~0.5
            # 3.3 MPa -> ~0.23
            pressure_score = 0.0

            if best_pressure is not None and best_pressure > 0:
                pressure_score = min(
                    0.1 / best_pressure,
                    1.0,
                )

            raw = (
                0.70 * storage_score
                + 0.20 * temperature_score
                + 0.10 * pressure_score
            )

            criteria = 1
            if best_temperature is not None:
                criteria += 1
            if best_pressure is not None:
                criteria += 1

    elif objective == "HIGH_DENSITY":
        components = []
        criteria = 0

        if h2_g_l is not None:
            components.append(density_score)
            criteria += 1

        if h2_wt is not None:
            components.append(base.gravimetric_score)
            criteria += 1

        surface = _best(
            material_results,
            {"bet_surface_area"},
            {"m2/g"},
        )

        if surface is not None:
            components.append(
                min(surface / 5000.0, 1.0)
            )
            criteria += 1

        raw = (
            0.50 * density_score
            + 0.30 * base.gravimetric_score
            + 0.20 * (
                min(surface / 5000.0, 1.0)
                if surface is not None
                else 0.0
            )
        ) if components else 0.0

    else:
        surface = _best(
            material_results,
            {"bet_surface_area"},
            {"m2/g"},
        )

        raw = (
            0.30 * base.gravimetric_score
            + 0.30 * density_score
            + 0.20 * thermal_score
            + 0.20 * (
                min(surface / 5000.0, 1.0)
                if surface is not None
                else 0.0
            )
        )

        criteria = sum(
            value is not None
            for value in (
                h2_wt,
                h2_g_l,
                desorption,
                surface,
            )
        )

    coverage = criteria / 4.0

    if coverage >= 0.75:
        confidence = "HIGH"
    elif coverage >= 0.50:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    screening = raw * coverage

    return ObjectiveScore(
        material=material,
        objective=objective,
        raw_score=round(raw, 4),
        coverage=round(coverage, 4),
        screening_score=round(screening, 4),
        confidence=confidence,
    )


def rank_by_objective(
    results: Iterable[LiteratureResult],
    objective: str = "GLOBAL",
) -> list[ObjectiveScore]:
    """Rank all materials for a selected objective."""

    material_names = sorted({
        result.material
        for result in results
    })

    scores = [
        calculate_objective_score(
            material,
            results,
            objective,
        )
        for material in material_names
    ]

    # Do not rank materials with no evidence for the selected
    # objective. They belong to the "insufficient data" category.
    if objective.strip().upper() == "AMBIENT":
        scores = [
            score
            for score in scores
            if score.coverage > 0.0
        ]

    return sorted(
        scores,
        key=lambda score: score.screening_score,
        reverse=True,
    )
