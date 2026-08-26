from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MOFCandidate:

    name: str

    cif_path: str | None = None

    surface_area: float = 0.0
    void_fraction: float = 0.0

    pld: float = 0.0
    lcd: float = 0.0

    adsorption_energy: float | None = None

    hydrogen_capacity: float | None = None

    score: float = 0.0
