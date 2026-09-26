from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ENERGY_RE = re.compile(
    r"!\s+total energy\s+=\s+"
    r"([-+]?\d+(?:\.\d+)?)\s+Ry",
    re.IGNORECASE,
)

FERMI_RE = re.compile(
    r"Fermi energy\s+is\s+"
    r"([-+]?\d+(?:\.\d+)?)\s+ev",
    re.IGNORECASE,
)

KPOINT_RE = re.compile(
    r"number of k points=\s*(\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class KPointResult:
    grid: str
    path: Path
    energy_ry: float | None
    fermi_ev: float | None
    irreducible_kpoints: int | None
    scf_converged: bool
    job_done: bool


def _last_float(
    pattern: re.Pattern[str],
    text: str,
) -> float | None:
    values = pattern.findall(text)

    if not values:
        return None

    return float(values[-1])


def _last_int(
    pattern: re.Pattern[str],
    text: str,
) -> int | None:
    values = pattern.findall(text)

    if not values:
        return None

    return int(values[-1])


def parse_kpoint_output(
    grid: str,
    path: Path,
) -> KPointResult:
    text = path.read_text(errors="replace")
    lowered = text.lower()

    return KPointResult(
        grid=grid,
        path=path,
        energy_ry=_last_float(ENERGY_RE, text),
        fermi_ev=_last_float(FERMI_RE, text),
        irreducible_kpoints=_last_int(KPOINT_RE, text),
        scf_converged=(
            "convergence has been achieved" in lowered
            or "convergence achieved" in lowered
        ),
        job_done="JOB DONE." in text,
    )


def energy_spread(
    results: list[KPointResult],
) -> float | None:
    energies = [
        result.energy_ry
        for result in results
        if result.energy_ry is not None
    ]

    if len(energies) < 2:
        return None

    return max(energies) - min(energies)


def successive_energy_differences(
    results: list[KPointResult],
) -> list[tuple[str, str, float]]:
    values = [
        result
        for result in results
        if result.energy_ry is not None
    ]

    differences: list[tuple[str, str, float]] = []

    for previous, current in zip(values, values[1:]):
        assert previous.energy_ry is not None
        assert current.energy_ry is not None

        differences.append(
            (
                previous.grid,
                current.grid,
                abs(current.energy_ry - previous.energy_ry),
            )
        )

    return differences
