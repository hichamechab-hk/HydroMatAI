"""Optical dielectric-function utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math


@dataclass
class DielectricData:
    energy: list[float]
    epsilon_real: list[float]
    epsilon_imag: list[float]


def read_dielectric_file(path: str | Path) -> DielectricData:
    """Read optical data.

    Expected columns:
        energy  epsilon_real  epsilon_imag
    """

    path = Path(path)

    energy = []
    real = []
    imag = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                if len(parts) >= 3:
                    energy.append(float(parts[0]))
                    real.append(float(parts[1]))
                    imag.append(float(parts[2]))
            except ValueError:
                continue

    return DielectricData(
        energy=energy,
        epsilon_real=real,
        epsilon_imag=imag,
    )


def refractive_index(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    magnitude = math.sqrt(
        epsilon_real ** 2 +
        epsilon_imag ** 2
    )

    return math.sqrt(
        max(0.0, (magnitude + epsilon_real) / 2.0)
    )


def extinction_coefficient(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    magnitude = math.sqrt(
        epsilon_real ** 2 +
        epsilon_imag ** 2
    )

    return math.sqrt(
        max(0.0, (magnitude - epsilon_real) / 2.0)
    )


def reflectivity(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:

    n = refractive_index(
        epsilon_real,
        epsilon_imag,
    )

    k = extinction_coefficient(
        epsilon_real,
        epsilon_imag,
    )

    numerator = (n - 1.0) ** 2 + k ** 2
    denominator = (n + 1.0) ** 2 + k ** 2

    if denominator == 0:
        return 0.0

    return numerator / denominator


def energy_loss_function(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """
    Compute optical energy loss function:

        Im(-1/epsilon)

    """

    denominator = (
        epsilon_real ** 2 +
        epsilon_imag ** 2
    )

    if denominator == 0:
        return 0.0

    return epsilon_imag / denominator
