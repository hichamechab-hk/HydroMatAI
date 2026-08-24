"""Automatic interpretation of optical spectra."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OpticalInterpretation:
    absorption_peak_energy: float | None
    dielectric_peak_energy: float | None
    explanation: str


def interpret_optical_data(
    energy: list[float],
    epsilon_imag: list[float],
) -> OpticalInterpretation:

    if not energy or not epsilon_imag:
        return OpticalInterpretation(
            None,
            None,
            "Données optiques insuffisantes pour produire une interprétation.",
        )

    index = max(
        range(len(epsilon_imag)),
        key=lambda i: abs(epsilon_imag[i]),
    )

    peak_energy = energy[index]

    return OpticalInterpretation(
        absorption_peak_energy=peak_energy,
        dielectric_peak_energy=peak_energy,
        explanation=(
            "Le maximum de la partie imaginaire de la fonction "
            "diélectrique indique une région de forte réponse "
            "électronique aux excitations optiques. "
            f"Le maximum détecté se situe autour de "
            f"{peak_energy:.4f} eV."
        ),
    )
