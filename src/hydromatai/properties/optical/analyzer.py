"""Automatic optical-property interpretation."""

from __future__ import annotations

from dataclasses import dataclass

from .dielectric import energy_loss_function
from .result import OpticalResult


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
            "Données optiques insuffisantes."
        )

    index = max(
        range(len(epsilon_imag)),
        key=lambda i: abs(epsilon_imag[i])
    )

    peak = energy[index]

    return OpticalInterpretation(
        peak,
        peak,
        (
            "La réponse optique maximale est associée "
            "au maximum de ε₂(ω). "
            f"Pic détecté à {peak:.4f} eV."
        )
    )



def analyze_optical(
    energy: list[float],
    epsilon_real: list[float],
    epsilon_imag: list[float],
    refractive_index: list[float] | None = None,
    extinction: list[float] | None = None,
    reflectivity: list[float] | None = None,
) -> OpticalResult:


    if not energy:
        return OpticalResult(
            success=False,
            explanation="Aucune donnée optique."
        )


    absorption_peak = None
    dielectric_peak = None
    loss_peak = None


    if epsilon_imag:
        i = max(
            range(len(epsilon_imag)),
            key=lambda x: abs(epsilon_imag[x])
        )
        absorption_peak = energy[i]
        dielectric_peak = energy[i]


    losses = [
        energy_loss_function(r, im)
        for r, im in zip(
            epsilon_real,
            epsilon_imag
        )
    ]

    if losses:
        j = max(
            range(len(losses)),
            key=lambda x: abs(losses[x])
        )
        loss_peak = energy[j]


    return OpticalResult(

        success=True,

        absorption_peak_energy=absorption_peak,
        dielectric_peak_energy=dielectric_peak,
        loss_peak_energy=loss_peak,

        refractive_index_max=(
            max(refractive_index)
            if refractive_index else None
        ),

        extinction_max=(
            max(extinction)
            if extinction else None
        ),

        reflectivity_max=(
            max(reflectivity)
            if reflectivity else None
        ),

        classification="optically_active",

        explanation=(
            "Analyse optique terminée."
        ),

        points=len(energy)
    )
