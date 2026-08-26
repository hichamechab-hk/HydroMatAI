"""Structured optical-property results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OpticalResult:

    success: bool = False

    absorption_peak_energy: float | None = None
    dielectric_peak_energy: float | None = None
    loss_peak_energy: float | None = None

    refractive_index_max: float | None = None
    extinction_max: float | None = None
    reflectivity_max: float | None = None

    classification: str = "unknown"
    explanation: str = ""

    points: int = 0

    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
