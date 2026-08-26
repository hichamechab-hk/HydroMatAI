"""Central scientific configuration for HydroMatAI.

This module contains platform-level defaults.
It does not launch calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ScientificConfig:
    """Reproducible scientific configuration."""

    qe_executable: str = "/home/hk/software/qe-7.5/bin/pw.x"

    ecutwfc: float = 60.0
    ecutrho: float = 240.0

    conv_thr: float = 1.0e-8
    electron_maxstep: int = 300
    mixing_beta: float = 0.10

    k_points: tuple[int, int, int] = (1, 1, 1)

    energy_unit: str = "Ry"
    adsorption_energy_unit: str = "eV"

    temperature_K: float = 300.0

    h2_molecule: str = "H2"

    calculation_policy: str = "production-ready-no-auto-launch"

    def validate(self) -> None:
        if self.ecutwfc <= 0:
            raise ValueError("ecutwfc must be positive")

        if self.ecutrho <= 0:
            raise ValueError("ecutrho must be positive")

        if self.conv_thr <= 0:
            raise ValueError("conv_thr must be positive")

        if self.electron_maxstep <= 0:
            raise ValueError("electron_maxstep must be positive")

        if not 0 < self.mixing_beta <= 1:
            raise ValueError("mixing_beta must be in (0, 1]")

        if any(k <= 0 for k in self.k_points):
            raise ValueError("k-points must be positive")

        if self.temperature_K <= 0:
            raise ValueError("temperature must be positive")

        if self.energy_unit != "Ry":
            raise ValueError("Reference total-energy unit must be Ry")

        if self.adsorption_energy_unit != "eV":
            raise ValueError("Adsorption-energy unit must be eV")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_default_config() -> ScientificConfig:
    config = ScientificConfig()
    config.validate()
    return config
