from __future__ import annotations
"""Ambient-temperature hydrogen benchmark from published literature."""


from dataclasses import dataclass
import re
from typing import Iterable

from .models import LiteratureResult
from .objective_score import calculate_objective_score


@dataclass(frozen=True)
class AmbientBenchmarkEntry:
    """Published near-ambient hydrogen result for one material."""

    material: str
    h2_uptake_wt_percent: float
    temperature_k: float
    pressure_mpa: float | None
    screening_score: float
    confidence: str


def _temperature_kelvin(result: LiteratureResult) -> float | None:
    """Extract temperature in kelvin from published conditions."""

    value = result.conditions.get("temperature")

    if value is None:
        return None

    text = str(value).strip().lower()

    if "room" in text or "ambient" in text:
        return 298.0

    match = re.search(
        r"([-+]?\d+(?:\.\d+)?)\s*k\b",
        text,
    )

    if match:
        return float(match.group(1))

    return None


def _pressure_mpa(result: LiteratureResult) -> float | None:
    """Extract pressure in MPa from published conditions."""

    value = result.conditions.get("pressure")

    if value is None:
        return None

    text = str(value).strip().lower()

    match = re.search(
        r"([-+]?\d+(?:\.\d+)?)",
        text,
    )

    if not match:
        return None

    pressure = float(match.group(1))

    if "kpa" in text:
        return pressure / 1000.0

    if "bar" in text:
        return pressure / 10.0

    if "pa" in text and "mpa" not in text and "kpa" not in text:
        return pressure / 1_000_000.0

    return pressure


def build_ambient_benchmark(
    results: Iterable[LiteratureResult],
) -> list[AmbientBenchmarkEntry]:
    """Build the best near-ambient published H2 benchmark per material.

    Only gravimetric H2 measurements between 280 K and 303 K are included.
    The highest uptake is selected for each material.
    """

    material_results: dict[str, list[LiteratureResult]] = {}

    for result in results:
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

        if temperature is None or not 280.0 <= temperature <= 303.0:
            continue

        material_results.setdefault(
            result.material,
            [],
        ).append(result)

    benchmark: list[AmbientBenchmarkEntry] = []

    all_results = list(results)

    for material, candidates in material_results.items():
        best = max(candidates, key=lambda result: result.value)

        temperature = _temperature_kelvin(best)
        if temperature is None:
            continue

        pressure = _pressure_mpa(best)

        score = calculate_objective_score(
            material,
            all_results,
            "AMBIENT",
        )

        benchmark.append(
            AmbientBenchmarkEntry(
                material=material,
                h2_uptake_wt_percent=best.value,
                temperature_k=temperature,
                pressure_mpa=pressure,
                screening_score=score.screening_score,
                confidence=score.confidence,
            )
        )

    return sorted(
        benchmark,
        key=lambda entry: entry.screening_score,
        reverse=True,
    )
