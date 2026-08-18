from dataclasses import dataclass


@dataclass
class DFTResult:
    """
    Résultat standardisé d'un calcul DFT.
    """

    success: bool

    total_energy: float | None = None
    band_gap: float | None = None
    forces: list | None = None

    raw_output: str | None = None
