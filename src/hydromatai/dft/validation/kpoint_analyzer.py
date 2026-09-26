from __future__ import annotations

from dataclasses import dataclass

from .kpoint_audit import KPointResult, energy_spread, successive_energy_differences


THRESHOLD_RY = 1e-4


@dataclass(frozen=True)
class KPointConvergenceReport:
    results: tuple[KPointResult, ...]
    completed: tuple[KPointResult, ...]
    incomplete: tuple[KPointResult, ...]
    energy_spread_ry: float | None
    successive_differences: tuple[tuple[str, str, float], ...]
    threshold_ry: float
    status: str


def analyze_kpoint_convergence(
    results: list[KPointResult],
    threshold_ry: float = THRESHOLD_RY,
) -> KPointConvergenceReport:
    completed = tuple(
        result
        for result in results
        if result.energy_ry is not None
        and result.scf_converged
        and result.job_done
    )

    incomplete = tuple(
        result
        for result in results
        if result not in completed
    )

    spread = energy_spread(list(completed))

    differences = tuple(
        successive_energy_differences(list(completed))
    )

    if len(completed) < 2:
        status = "INSUFFICIENT_DATA"
    elif spread is not None and spread <= threshold_ry:
        status = "NUMERICAL_STABILITY_ESTABLISHED"
    else:
        status = "NUMERICAL_STABILITY_NOT_ESTABLISHED"

    return KPointConvergenceReport(
        results=tuple(results),
        completed=completed,
        incomplete=incomplete,
        energy_spread_ry=spread,
        successive_differences=differences,
        threshold_ry=threshold_ry,
        status=status,
    )
