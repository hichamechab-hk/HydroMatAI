"""Density of States utilities for Quantum ESPRESSO outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class DOSData:
    energy: list[float]
    values: list[float]
    fermi_energy: float | None = None


def read_fermi_energy(text: str) -> float | None:
    patterns = [
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        r"highest occupied level.*?([-+0-9.EeDd]+)\s+ev",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).replace("D", "E").replace("d", "e")
            return float(value)

    return None


def parse_dos_file(path: str | Path) -> DOSData:
    path = Path(path)

    energies = []
    values = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                if len(parts) >= 2:
                    energies.append(float(parts[0]))
                    values.append(float(parts[1]))
            except ValueError:
                continue

    return DOSData(
        energy=energies,
        values=values,
    )


def find_band_gap(
    energy: list[float],
    dos: list[float],
    threshold: float = 1e-8,
) -> float | None:
    """Estimate a DOS gap around zero energy.

    Assumes the energy axis has already been shifted so that
    the Fermi level is approximately zero.
    """

    if not energy or not dos:
        return None

    occupied = [
        e for e, d in zip(energy, dos)
        if e <= 0.0 and abs(d) > threshold
    ]

    unoccupied = [
        e for e, d in zip(energy, dos)
        if e >= 0.0 and abs(d) > threshold
    ]

    if not occupied or not unoccupied:
        return None

    return max(0.0, min(unoccupied) - max(occupied))
