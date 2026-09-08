from __future__ import annotations
"""Automatic electronic-property analysis and interpretation."""


from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .bands import BandData, estimate_band_gap
from .dos import DOSData
from .result import ElectronicResult


@dataclass
class ElectronicInterpretation:
    classification: str
    band_gap: float | None
    explanation: str


def interpret_band_gap(
    band_gap: float | None,
) -> ElectronicInterpretation:
    """Classify the material from its estimated electronic gap."""

    if band_gap is None:
        return ElectronicInterpretation(
            classification="unknown",
            band_gap=None,
            explanation=(
                "Le gap électronique n'a pas pu être déterminé "
                "à partir des données disponibles."
            ),
        )

    if band_gap <= 0.05:
        return ElectronicInterpretation(
            classification="metallic_or_semimetallic",
            band_gap=band_gap,
            explanation=(
                f"Le gap estimé est très faible ({band_gap:.4f} eV). "
                "Le système présente un comportement métallique ou "
                "semi-métallique selon la précision du calcul."
            ),
        )

    if band_gap < 3.0:
        return ElectronicInterpretation(
            classification="semiconductor",
            band_gap=band_gap,
            explanation=(
                f"Le gap électronique estimé est de {band_gap:.4f} eV. "
                "Le matériau est compatible avec un comportement "
                "semi-conducteur."
            ),
        )

    return ElectronicInterpretation(
        classification="insulator",
        band_gap=band_gap,
        explanation=(
            f"Le gap électronique estimé est de {band_gap:.4f} eV. "
            "Le matériau présente un comportement de type isolant."
        ),
    )


def _finite_values(values: Iterable[float]) -> list[float]:
    return [float(v) for v in values if isfinite(float(v))]


def find_vbm_cbm(
    bands: list[list[float]],
    fermi_energy: float = 0.0,
) -> tuple[float | None, float | None]:
    """
    Determine VBM and CBM relative to the supplied Fermi energy.

    VBM = highest energy <= EF
    CBM = lowest energy >= EF
    """

    occupied: list[float] = []
    unoccupied: list[float] = []

    for band in bands:
        for energy in _finite_values(band):
            if energy <= fermi_energy:
                occupied.append(energy)
            if energy >= fermi_energy:
                unoccupied.append(energy)

    vbm = max(occupied) if occupied else None
    cbm = min(unoccupied) if unoccupied else None

    return vbm, cbm


def analyze_bands(
    data: BandData,
    fermi_energy: float | None = None,
) -> ElectronicResult:
    """Analyze a BandData object."""

    ef = (
        data.fermi_energy
        if fermi_energy is None
        else fermi_energy
    )

    if ef is None:
        ef = 0.0

    # Detect metallic behavior from the band dispersion.
    tolerance = 1.0e-8
    metallic = False

    for band in data.bands:
        values = _finite_values(band)

        # A state exactly at EF is metallic.
        if any(
            abs(energy - ef) <= tolerance
            for energy in values
        ):
            metallic = True
            break

        # A band crossing EF between consecutive k-points
        # is metallic.
        for e1, e2 in zip(values, values[1:]):
            if (
                e1 < ef < e2
                or
                e2 < ef < e1
            ):
                metallic = True
                break

        if metallic:
            break

    if metallic:
        return ElectronicResult(
            success=True,
            band_gap=0.0,
            vbm=None,
            cbm=None,
            fermi_energy=ef,
            classification="metal",
            explanation=(
                "Une ou plusieurs bandes traversent le niveau "
                "de Fermi. Le système présente un comportement "
                "métallique."
            ),
            band_points=len(data.kpoints),
            band_count=len(data.bands),
        )

    vbm, cbm = find_vbm_cbm(data.bands, ef)

    gap = None
    if vbm is not None and cbm is not None:
        gap = max(0.0, cbm - vbm)
    else:
        gap = estimate_band_gap(data.bands, ef)

    interpretation = interpret_band_gap(gap)

    return ElectronicResult(
        success=gap is not None,
        band_gap=gap,
        vbm=vbm,
        cbm=cbm,
        fermi_energy=ef,
        classification=interpretation.classification,
        explanation=interpretation.explanation,
        band_points=len(data.kpoints),
        band_count=len(data.bands),
    )

def analyze_dos(
    data: DOSData,
) -> ElectronicResult:
    """Analyze DOS information."""

    dos_ef = data.dos_at_fermi()

    return ElectronicResult(
        success=bool(data.energy),
        fermi_energy=data.fermi_energy,
        dos_at_fermi=dos_ef,
        dos_points=len(data.energy),
    )


def analyze_electronic(
    band_data: BandData | None = None,
    dos_data: DOSData | None = None,
    fermi_energy: float | None = None,
) -> ElectronicResult:
    """Combine band and DOS information into one result."""

    band_result = None
    dos_result = None

    if band_data is not None:
        band_result = analyze_bands(
            band_data,
            fermi_energy=fermi_energy,
        )

    if dos_data is not None:
        dos_result = analyze_dos(dos_data)

    if band_result is not None:
        result = band_result
    elif dos_result is not None:
        result = dos_result
    else:
        return ElectronicResult(
            success=False,
            explanation="Aucune donnée électronique disponible.",
        )

    if dos_result is not None:
        if result.fermi_energy is None:
            result.fermi_energy = dos_result.fermi_energy

        result.dos_at_fermi = dos_result.dos_at_fermi
        result.dos_points = dos_result.dos_points

    return result
