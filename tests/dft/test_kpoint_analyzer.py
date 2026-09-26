from pathlib import Path

import pytest

from hydromatai.dft.validation import (
    KPointResult,
    analyze_kpoint_convergence,
)


def result(
    grid: str,
    energy: float | None,
    converged: bool,
    job_done: bool,
) -> KPointResult:
    return KPointResult(
        grid=grid,
        path=Path(f"/tmp/{grid}.out"),
        energy_ry=energy,
        fermi_ev=None,
        irreducible_kpoints=None,
        scf_converged=converged,
        job_done=job_done,
    )


def test_incomplete_results_are_excluded():
    results = [
        result("3x3x3", -880.7345, True, True),
        result("4x4x4", -880.7173, False, False),
        result("5x5x5", None, False, False),
    ]

    report = analyze_kpoint_convergence(results)

    assert len(report.completed) == 1
    assert len(report.incomplete) == 2
    assert report.energy_spread_ry is None
    assert report.status == "INSUFFICIENT_DATA"


def test_two_completed_results_are_compared():
    results = [
        result("3x3x3", -880.73456845, True, True),
        result("4x4x4", -880.73450000, True, True),
        result("5x5x5", None, False, False),
    ]

    report = analyze_kpoint_convergence(results)

    assert len(report.completed) == 2
    assert len(report.incomplete) == 1
    assert report.energy_spread_ry == pytest.approx(0.00006845)
    assert report.status == "NUMERICAL_STABILITY_ESTABLISHED"


def test_two_completed_results_can_fail_threshold():
    results = [
        result("3x3x3", -880.73456845, True, True),
        result("4x4x4", -880.70000000, True, True),
    ]

    report = analyze_kpoint_convergence(results)

    assert report.energy_spread_ry == pytest.approx(0.03456845)
    assert report.status == "NUMERICAL_STABILITY_NOT_ESTABLISHED"


def test_successive_differences_are_preserved():
    results = [
        result("3x3x3", -880.70, True, True),
        result("4x4x4", -880.71, True, True),
        result("5x5x5", -880.715, True, True),
    ]

    report = analyze_kpoint_convergence(results)

    assert list(report.successive_differences) == [
        ("3x3x3", "4x4x4", pytest.approx(0.01)),
        ("4x4x4", "5x5x5", pytest.approx(0.005)),
    ]
