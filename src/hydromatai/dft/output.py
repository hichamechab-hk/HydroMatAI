from dataclasses import dataclass
from typing import Any


@dataclass
class DFTResult:
    """
    Résultat standardisé d'un calcul DFT.
    """

    success: bool

    total_energy: float | None = None
    band_gap: float | None = None
    vbm: float | None = None
    cbm: float | None = None
    fermi_energy: float | None = None
    forces: list | None = None

    # Structure obtenue après RELAX
    relaxed_structure: Any | None = None

    raw_output: str | None = None
