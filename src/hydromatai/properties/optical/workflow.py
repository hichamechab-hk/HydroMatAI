from __future__ import annotations
"""Optical workflow."""


from pathlib import Path

from .dielectric import read_dielectric_file
from .optical import calculate_optical_properties
from .analyzer import analyze_optical


class OpticalWorkflow:
    """High-level workflow for optical-property analysis."""

    def analyze_file(
        self,
        path: str | Path,
    ):
        data = read_dielectric_file(path)

        values = calculate_optical_properties(data)

        return analyze_optical(
            values["energy"],
            values["epsilon_real"],
            values["epsilon_imag"],
            values["refractive_index"],
            values["extinction_coefficient"],
            values["reflectivity"],
            values.get("absorption_coefficient"),
            values.get("energy_loss"),
        )
