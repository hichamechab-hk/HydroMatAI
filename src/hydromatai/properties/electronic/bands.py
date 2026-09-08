from __future__ import annotations
"""Band-structure data handling."""


import re
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


@dataclass
class BandData:
    kpoints: list[float]
    bands: list[list[float]]
    fermi_energy: float | None = None


# Quantum ESPRESSO:
# k = 0.0000 0.0000 0.0000 (...) bands (ev):
_QE_KPOINT_RE = re.compile(
    r"^\s*k\s*=\s*"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
)

_QE_BANDS_RE = re.compile(
    r"^\s*k\s*=\s*.*bands\s*\(\s*ev\s*\)",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


def _parse_numbers(line: str) -> list[float]:
    """Extract finite floating-point numbers from a line."""
    values: list[float] = []

    for token in _NUMBER_RE.findall(line):
        try:
            value = float(token)
        except ValueError:
            continue

        if isfinite(value):
            values.append(value)

    return values


def _parse_simple_band_data(
    lines: list[str],
) -> BandData:
    """
    Parse simple HydroMatAI band data.

    Expected format:

        # k band1 band2
        0.0 -2.0 1.0
        0.5 -1.5 1.5
        1.0 -1.0 2.0
    """

    rows: list[list[float]] = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#"):
            continue

        values = _parse_numbers(stripped)

        # A valid simple row needs k-point + at least one band.
        if len(values) >= 2:
            rows.append(values)

    if not rows:
        return BandData(
            kpoints=[],
            bands=[],
            fermi_energy=None,
        )

    kpoints = [row[0] for row in rows]

    band_count = max(len(row) - 1 for row in rows)

    bands: list[list[float]] = [
        [] for _ in range(band_count)
    ]

    for row in rows:
        energies = row[1:]

        for index, energy in enumerate(energies):
            bands[index].append(energy)

    return BandData(
        kpoints=kpoints,
        bands=bands,
        fermi_energy=None,
    )


def _parse_qe_bands_output(
    lines: list[str],
) -> BandData:
    """
    Parse raw Quantum ESPRESSO bands output.

    Example:

        k = 0.0000 0.0000 0.0000 (...) bands (ev):

           -6.3816  -1.2656  -1.2656  -0.1041

        k = 0.0250 0.0000 0.0000 (...) bands (ev):

           -6.3773  -1.2975  -1.2623  -0.0850
    """

    kpoints: list[float] = []
    rows: list[list[float]] = []

    current_kpoint: float | None = None
    collecting = False

    for line in lines:
        k_match = _QE_KPOINT_RE.search(line)

        if k_match:
            try:
                current_kpoint = float(k_match.group(1))
            except ValueError:
                current_kpoint = None

            collecting = bool(_QE_BANDS_RE.search(line))
            continue

        if not collecting or current_kpoint is None:
            continue

        stripped = line.strip()

        if not stripped:
            continue

        # Stop if another QE text section begins.
        if (
            stripped.startswith("Writing ")
            or stripped.startswith("writing ")
            or stripped.startswith("number of ")
            or stripped.startswith("Number of ")
        ):
            collecting = False
            continue

        values = _parse_numbers(stripped)

        if not values:
            continue

        # Ignore unrelated lines containing numbers.
        if any(
            token in stripped.lower()
            for token in (
                "cpu",
                "wall",
                "electrons",
                "bands",
                "k =",
            )
        ):
            continue

        rows.append(values)
        kpoints.append(current_kpoint)
        collecting = False

    if not rows:
        return BandData(
            kpoints=kpoints,
            bands=[],
            fermi_energy=None,
        )

    band_count = max(len(row) for row in rows)

    bands: list[list[float]] = [
        [] for _ in range(band_count)
    ]

    for row in rows:
        for index, energy in enumerate(row):
            bands[index].append(energy)

        # Keep dimensions consistent if QE blocks differ.
        for index in range(len(row), band_count):
            bands[index].append(float("nan"))

    # Remove bands that contain no finite values.
    bands = [
        band
        for band in bands
        if any(isfinite(value) for value in band)
    ]

    return BandData(
        kpoints=kpoints,
        bands=bands,
        fermi_energy=0.0,
    )


def read_band_data(
    path: str | Path,
) -> BandData:
    """Read HydroMatAI format or raw Quantum ESPRESSO output."""

    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as handle:
        lines = handle.readlines()

    if any(
        _QE_BANDS_RE.search(line)
        for line in lines
    ):
        return _parse_qe_bands_output(lines)

    return _parse_simple_band_data(lines)


def estimate_band_gap(
    bands: list[list[float]],
    fermi_energy: float = 0.0,
) -> float | None:
    """Estimate the electronic band gap.

    A system is metallic when a band crosses the Fermi level
    between consecutive k-points, or when a state lies at EF.
    """

    if not bands:
        return None

    occupied_max: float | None = None
    unoccupied_min: float | None = None

    tolerance = 1.0e-8

    for band in bands:
        finite_values = [
            energy
            for energy in band
            if isfinite(energy)
        ]

        if not finite_values:
            continue

        if any(
            abs(energy - fermi_energy) <= tolerance
            for energy in finite_values
        ):
            return 0.0

        for e1, e2 in zip(
            finite_values,
            finite_values[1:],
        ):
            if (
                e1 < fermi_energy < e2
                or e2 < fermi_energy < e1
            ):
                return 0.0

        for energy in finite_values:
            if energy < fermi_energy:
                occupied_max = (
                    energy
                    if occupied_max is None
                    else max(occupied_max, energy)
                )

            elif energy > fermi_energy:
                unoccupied_min = (
                    energy
                    if unoccupied_min is None
                    else min(unoccupied_min, energy)
                )

    if occupied_max is None or unoccupied_min is None:
        return None

    return max(
        0.0,
        unoccupied_min - occupied_max,
    )
