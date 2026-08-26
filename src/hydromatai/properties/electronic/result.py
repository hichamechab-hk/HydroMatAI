"""Structured electronic-property results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ElectronicResult:
    """Unified result of an electronic-property analysis."""

    success: bool = False

    band_gap: float | None = None
    vbm: float | None = None
    cbm: float | None = None
    fermi_energy: float | None = None

    dos_at_fermi: float | None = None

    classification: str = "unknown"
    explanation: str = ""

    band_points: int = 0
    band_count: int = 0
    dos_points: int = 0
    pdos_channels: int = 0

    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
