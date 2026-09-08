from __future__ import annotations
"""Global HydroMatAI platform workflow.

This module connects the main scientific engines without launching
real DFT calculations automatically.
"""


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

        # ============================================================
        # DFT
        # ============================================================
        #
        # dry_run=True  : validation uniquement, aucun calcul.
        # dry_run=False : exécution du moteur DFT fourni.
        #
        # Le workflow accepte volontairement plusieurs interfaces :
        #   - DFTPipeline / backend avec validate() + run()
        #   - objets DFT plus simples exposant directement run()
        #
        if dft is not None:

            try:

                if self.dry_run:

                    validate = getattr(
                        dft,
                        "validate",
                        None,
                    )

                    if callable(validate):

                        validation = validate()

                        if not getattr(
                            validation,
                            "success",
                            False,
                        ):
                            result.success = False

                else:

                    run = getattr(
                        dft,
                        "run",
                        None,
                    )

                    if not callable(run):
                        raise AttributeError(
                            "DFT object has no run() method."
                        )

                    dft_result = run()

                    # Conserver le résultat d'exécution dans result.dft.
                    result.dft = dft_result

                    if hasattr(
                        dft_result,
                        "success",
                    ):
                        result.success = bool(
                            dft_result.success
                        )

            except Exception as exc:

                result.success = False

                # Conserver l'objet DFT original pour faciliter
                # le diagnostic sans imposer une nouvelle API.
                result.dft = dft

                if hasattr(
                    result,
                    "error_type",
                ):
                    result.error_type = "DFT"

                if hasattr(
                    result,
                    "error_message",
                ):
                    result.error_message = str(exc)

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
