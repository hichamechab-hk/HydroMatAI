"""Band-structure data handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BandData:
    kpoints: list[float]
    bands: list[list[float]]
    fermi_energy: float | None = None


def read_band_data(path: str | Path) -> BandData:
    """Read a whitespace-separated band data file.

    Expected format:
        k  band1  band2  band3 ...

    Blank lines, comments and invalid lines are ignored.
    """

    path = Path(path)

    kpoints: list[float] = []
    rows: list[list[float]] = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                values = [float(x) for x in parts]
            except ValueError:
                continue

            if len(values) < 2:
                continue

            kpoints.append(values[0])
            rows.append(values[1:])

    if not rows:
        return BandData([], [])

    number_of_bands = max(len(row) for row in rows)

    bands = [
        [
            row[i] if i < len(row) else float("nan")
            for row in rows
        ]
        for i in range(number_of_bands)
    ]

    return BandData(
        kpoints=kpoints,
        bands=bands,
    )


def estimate_band_gap(
    bands: list[list[float]],
    fermi_energy: float = 0.0,
) -> float | None:
    """Estimate a band gap relative to a supplied Fermi level."""

    if not bands:
        return None

    occupied_max = None
    unoccupied_min = None

    for band in bands:
        for energy in band:
            if energy <= fermi_energy:
                occupied_max = (
                    energy
                    if occupied_max is None
                    else max(occupied_max, energy)
                )

            if energy >= fermi_energy:
                unoccupied_min = (
                    energy
                    if unoccupied_min is None
                    else min(unoccupied_min, energy)
                )

    if occupied_max is None or unoccupied_min is None:
        return None

    return max(0.0, unoccupied_min - occupied_max)
