"""Global HydroMatAI platform workflow.

This module connects the main scientific engines without launching
real DFT calculations automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformResult:
    """Structured result of the global platform workflow."""

    success: bool = False
    material: str | None = None

    discovery: Any | None = None
    dft: Any | None = None
    electronic: Any | None = None
    optical: Any | None = None
    scientific: Any | None = None

    final_score: float | None = None
    classification: str = "unknown"

    stages_completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"

        return (
            f"HydroMatAI Platform [{status}] "
            f"material={self.material!r}, "
            f"score={self.final_score}, "
            f"classification={self.classification}"
        )


class PlatformWorkflow:
    """Orchestrate HydroMatAI scientific modules.

    The default mode is dry-run/platform mode.
    No real QE calculation is launched here.
    """

    STAGES = (
        "discovery",
        "dft",
        "electronic",
        "optical",
        "scientific",
        "report",
    )

    def __init__(
        self,
        material: str | None = None,
        dry_run: bool = True,
    ) -> None:

        self.material = material
        self.dry_run = dry_run

    def describe(self) -> dict[str, Any]:
        return {
            "material": self.material,
            "dry_run": self.dry_run,
            "stages": list(self.STAGES),
            "real_dft": not self.dry_run,
        }

    def run(
        self,
        discovery: Any | None = None,
        dft: Any | None = None,
        electronic: Any | None = None,
        optical: Any | None = None,
        scientific: Any | None = None,
    ) -> PlatformResult:

        result = PlatformResult(
            success=True,
            material=self.material,
        )

        result.discovery = discovery
        result.dft = dft
        result.electronic = electronic
        result.optical = optical
        result.scientific = scientific

        result.stages_completed.extend(
            [
                "discovery",
                "dft",
                "electronic",
                "optical",
                "scientific",
                "report",
            ]
        )

        if scientific is not None:
            score = getattr(scientific, "final_score", None)

            if score is not None:
                result.final_score = score

            classification = getattr(
                scientific,
                "electronic_classification",
                None,
            )

            if classification:
                result.classification = classification

        return result
