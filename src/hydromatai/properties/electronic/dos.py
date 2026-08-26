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

    def dos_at_fermi(self) -> float | None:
        """Return the DOS value closest to the Fermi energy."""

        if not self.energy or not self.values:
            return None

        if self.fermi_energy is None:
            return None

        index = min(
            range(len(self.energy)),
            key=lambda i: abs(self.energy[i] - self.fermi_energy),
        )

        return self.values[index]


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

    fermi_energy = None

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                match = re.search(
                    r"EFermi\s*=\s*([-+0-9.EeDd]+)",
                    line,
                    re.IGNORECASE,
                )
                if match:
                    value = match.group(1).replace("D", "E").replace("d", "e")
                    fermi_energy = float(value)
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
        fermi_energy=fermi_energy,
    )


@dataclass
class PDOSData:
    """Projected Density of States data."""

    energy: list[float]
    channels: dict[str, list[float]]
    fermi_energy: float | None = None


def parse_pdos_file(path: str | Path) -> PDOSData:
    """
    Parse un fichier PDOS Quantum ESPRESSO.

    Le premier champ numérique est considéré comme l'énergie.
    Les colonnes suivantes sont conservées comme canaux PDOS.
    """

    path = Path(path)

    energy = []
    columns = []
    fermi_energy = None

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            parts = line.split()

            try:
                values = [float(value) for value in parts]
            except ValueError:
                continue

            if len(values) < 2:
                continue

            energy.append(values[0])

            if not columns:
                columns = [[] for _ in values[1:]]

            for index, value in enumerate(values[1:]):
                if index < len(columns):
                    columns[index].append(value)

    channels = {
        f"channel_{index + 1}": values
        for index, values in enumerate(columns)
    }

    return PDOSData(
        energy=energy,
        channels=channels,
        fermi_energy=fermi_energy,
    )


def total_pdos(data: PDOSData) -> list[float]:
    """Calcule le PDOS total en additionnant tous les canaux."""

    if not data.channels:
        return []

    number_of_points = len(data.energy)

    return [
        sum(
            values[index]
            for values in data.channels.values()
            if index < len(values)
        )
        for index in range(number_of_points)
    ]


def find_pdos_band_gap(
    data: PDOSData,
    threshold: float = 1e-8,
) -> float | None:
    """Détermine le gap à partir du PDOS total."""

    dos = total_pdos(data)

    if not dos:
        return None

    return find_band_gap(
        data.energy,
        dos,
        threshold=threshold,
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
