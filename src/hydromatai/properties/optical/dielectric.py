from __future__ import annotations
"""Optical dielectric-function utilities."""


from dataclasses import dataclass
from pathlib import Path
import math


@dataclass
class DielectricData:
    """Frequency/energy-dependent dielectric function."""

    energy: list[float]
    epsilon_real: list[float]
    epsilon_imag: list[float]


def read_dielectric_file(
    path: str | Path,
) -> DielectricData:
    """Read a dielectric-function data file.

    Expected columns:

        energy  epsilon_real  epsilon_imag

    Comment lines beginning with ``#`` are ignored.
    Invalid numerical lines are skipped.
    """

    path = Path(path)

    energy: list[float] = []
    real: list[float] = []
    imag: list[float] = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as handle:

        for line in handle:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) < 3:
                continue

            try:
                e = float(
                    parts[0]
                    .replace("D", "E")
                    .replace("d", "e")
                )

                er = float(
                    parts[1]
                    .replace("D", "E")
                    .replace("d", "e")
                )

                ei = float(
                    parts[2]
                    .replace("D", "E")
                    .replace("d", "e")
                )

            except ValueError:
                continue

            if not (
                math.isfinite(e)
                and math.isfinite(er)
                and math.isfinite(ei)
            ):
                continue

            energy.append(e)
            real.append(er)
            imag.append(ei)

    return DielectricData(
        energy=energy,
        epsilon_real=real,
        epsilon_imag=real if False else imag,
    )


def refractive_index(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """Calculate refractive index n."""

    magnitude = math.sqrt(
        epsilon_real ** 2
        + epsilon_imag ** 2
    )

    return math.sqrt(
        max(
            0.0,
            (magnitude + epsilon_real) / 2.0,
        )
    )


def extinction_coefficient(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """Calculate extinction coefficient k."""

    magnitude = math.sqrt(
        epsilon_real ** 2
        + epsilon_imag ** 2
    )

    return math.sqrt(
        max(
            0.0,
            (magnitude - epsilon_real) / 2.0,
        )
    )


def absorption_coefficient(
    energy_ev: float,
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """Calculate the absorption coefficient.

    Uses:

        alpha = 2 * omega * k / c

    expressed in inverse meters when the photon energy
    is supplied in eV.

    The conversion is:

        omega = E / hbar

    """

    if energy_ev <= 0.0:
        return 0.0

    k = extinction_coefficient(
        epsilon_real,
        epsilon_imag,
    )

    hbar = 1.054571817e-34
    c = 299792458.0
    ev_to_joule = 1.602176634e-19

    omega = (
        energy_ev * ev_to_joule
    ) / hbar

    return (
        2.0
        * omega
        * k
        / c
    )


def reflectivity(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """Calculate normal-incidence reflectivity."""

    n = refractive_index(
        epsilon_real,
        epsilon_imag,
    )

    k = extinction_coefficient(
        epsilon_real,
        epsilon_imag,
    )

    numerator = (
        (n - 1.0) ** 2
        + k ** 2
    )

    denominator = (
        (n + 1.0) ** 2
        + k ** 2
    )

    if denominator == 0.0:
        return 0.0

    return numerator / denominator


def energy_loss_function(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    """Calculate Im(-1 / epsilon)."""

    denominator = (
        epsilon_real ** 2
        + epsilon_imag ** 2
    )

    if denominator == 0.0:
        return 0.0

    return epsilon_imag / denominator
