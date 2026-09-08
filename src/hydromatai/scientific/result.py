from __future__ import annotations
"""Scientific analysis result."""


from dataclasses import dataclass, field

from hydromatai.literature import LiteratureResult, HydrogenStorageScore


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

    literature_results: list[LiteratureResult] = field(default_factory=list)

    hydrogen_literature_score: HydrogenStorageScore | None = None

    @property
    def literature_count(self) -> int:
        """Number of published results attached to this analysis."""
        return len(self.literature_results)
