"""High-level electronic-property workflow."""

from __future__ import annotations

from pathlib import Path

from .analyzer import analyze_electronic
from .bands import BandData, read_band_data
from .dos import DOSData, parse_dos_file
from .result import ElectronicResult


class ElectronicWorkflow:
    """
    Coordinate electronic analysis from already-produced data files.

    No Quantum ESPRESSO process is launched by this class.
    """

    def analyze_files(
        self,
        band_file: str | Path | None = None,
        dos_file: str | Path | None = None,
        fermi_energy: float | None = None,
    ) -> ElectronicResult:

        band_data: BandData | None = None
        dos_data: DOSData | None = None

        if band_file is not None:
            band_data = read_band_data(band_file)

        if dos_file is not None:
            dos_data = parse_dos_file(dos_file)

        return analyze_electronic(
            band_data=band_data,
            dos_data=dos_data,
            fermi_energy=fermi_energy,
        )
