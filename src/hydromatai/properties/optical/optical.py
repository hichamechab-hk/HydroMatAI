"""Automatic optical-property calculations."""

from __future__ import annotations

from .dielectric import (
    DielectricData,
    refractive_index,
    extinction_coefficient,
    reflectivity,
)


def calculate_optical_properties(
    data: DielectricData,
) -> dict[str, list[float]]:

    n = []
    k = []
    r = []

    for er, ei in zip(
        data.epsilon_real,
        data.epsilon_imag,
    ):

        n.append(
            refractive_index(er, ei)
        )

        k.append(
            extinction_coefficient(er, ei)
        )

        r.append(
            reflectivity(er, ei)
        )

    return {
        "energy": data.energy,
        "epsilon_real": data.epsilon_real,
        "epsilon_imag": data.epsilon_imag,
        "refractive_index": n,
        "extinction_coefficient": k,
        "reflectivity": r,
    }
