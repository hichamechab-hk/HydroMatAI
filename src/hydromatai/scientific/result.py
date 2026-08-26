"""Scientific analysis result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScientificResult:

    material: str

    total_energy: float | None = None

    band_gap: float | None = None

    electronic_classification: str = "unknown"

    optical_classification: str = "unknown"

    stability_score: float = 0.0

    hydrogen_score: float = 0.0

    final_score: float = 0.0

    summary: str = ""
