from __future__ import annotations
"""Platform adapter for real DFT workflows."""


from pathlib import Path
from typing import Any

from hydromatai.dft.runner import DFTRunner
from hydromatai.dft.workflow.relax_scf import RelaxSCFWorkflow
from hydromatai.dft.quantum_espresso.calculator import (
    QuantumEspressoCalculator,
)


class PlatformDFTAdapter:
    """Adapt a Material to the global PlatformWorkflow DFT interface.

    The adapter owns the complete real DFT sequence:

        RELAX -> transfer relaxed structure -> SCF

    It can also load an already completed RELAX calculation.
    """

    name = "quantum_espresso_relax_scf"

    def __init__(
        self,
        material: Any,
        relax_workdir: str | Path,
        scf_workdir: str | Path,
        qe_command: str = "/home/hk/software/qe-7.5/bin/pw.x",
    ) -> None:

        if material is None:
            raise ValueError("material is required")

        self.material = material

        self.relax_workdir = Path(relax_workdir)
        self.scf_workdir = Path(scf_workdir)

        self.qe_command = qe_command

        # Résultat du workflow complet RELAX -> SCF.
        self.result: Any | None = None

        # Résultat d'un RELAX déjà exécuté et chargé.
        self.relax_result: Any | None = None

        # ========================================================
        # CALCULATEUR RELAX
        # ========================================================

        self.relax_calculator = QuantumEspressoCalculator(
            runner=DFTRunner(
                [
                    self.qe_command,
                    "-in",
                    "relax.in",
                ]
            ),
            workdir=self.relax_workdir,
            calculation="relax",
        )

        # ========================================================
        # CALCULATEUR SCF
        # ========================================================

        self.scf_calculator = QuantumEspressoCalculator(
            runner=DFTRunner(
                [
                    self.qe_command,
                    "-in",
                    "scf.in",
                ]
            ),
            workdir=self.scf_workdir,
            calculation="scf",
        )

        # ========================================================
        # WORKFLOW RELAX -> SCF
        # ========================================================

        self.workflow = RelaxSCFWorkflow(
            relax_calculator=self.relax_calculator,
            scf_calculator=self.scf_calculator,
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    def validate(self) -> Any:
        """Validate that the material can be used by the DFT workflow."""

        formula = getattr(
            self.material,
            "formula",
            None,
        )

        if not formula:
            raise ValueError(
                "Material must have a formula."
            )

        structure = getattr(
            self.material,
            "structure",
            None,
        )

        if structure is None:
            raise ValueError(
                "Material must have a structure."
            )

        atoms = getattr(
            structure,
            "atoms",
            None,
        )

        if not atoms:
            raise ValueError(
                "Material structure must contain atoms."
            )

        return type(
            "ValidationResult",
            (),
            {
                "success": True,
                "material": self.material,
            },
        )()

    # ============================================================
    # CHARGEMENT D'UN RELAX EXISTANT
    # ============================================================

    def load_relax_result(
        self,
        output_path: str | Path | None = None,
    ) -> Any:
        """Load and parse an existing QE RELAX output.

        The parsed DFTResult is stored in ``self.relax_result``.

        The relaxed structure is also transferred to
        ``self.material.structure`` so that the material is ready
        for a subsequent SCF calculation.
        """

        if output_path is None:
            output_path = (
                self.relax_workdir / "relax.out"
            )

        output_path = Path(output_path)

        if not output_path.exists():
            raise FileNotFoundError(
                f"RELAX output not found: {output_path}"
            )

        raw_output = output_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if not raw_output.strip():
            raise ValueError(
                f"RELAX output is empty: {output_path}"
            )

        # Utilise directement le QEParser du calculateur.
        result = self.relax_calculator.parser.parse(
            raw_output
        )

        self.relax_result = result

        # Transfert de la structure relaxée vers le Material.
        relaxed_structure = getattr(
            result,
            "relaxed_structure",
            None,
        )

        if relaxed_structure is not None:
            self.material.structure = (
                relaxed_structure
            )

        return result

    # ============================================================
    # RUN
    # ============================================================

    def run(self) -> Any:
        """Execute the real RELAX -> SCF workflow."""

        self.validate()

        self.relax_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.scf_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.result = self.workflow.run(
            self.material,
            candidate_id=getattr(
                self.material,
                "name",
                None,
            ),
        )

        return self.result

    # ============================================================
    # PREPARE
    # ============================================================

    def prepare(self) -> Any:
        """Prepare the RELAX input without executing QE."""

        self.validate()

        self.relax_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self.relax_calculator.prepare_input(
            self.material,
        )

    # ============================================================
    # SUMMARY
    # ============================================================

    def summary(self) -> dict[str, Any]:
        """Return a compact execution summary."""

        result = self.result

        # ========================================================
        # WORKFLOW COMPLET RELAX -> SCF
        # ========================================================

        if result is not None:
            return {
                "name": self.name,
                "status": getattr(
                    result,
                    "status",
                    None,
                ),
                "success": getattr(
                    result,
                    "success",
                    False,
                ),
                "relax_success": getattr(
                    result,
                    "relax_success",
                    False,
                ),
                "relax_converged": getattr(
                    result,
                    "relax_converged",
                    False,
                ),
                "scf_success": getattr(
                    result,
                    "scf_success",
                    False,
                ),
                "scf_converged": getattr(
                    result,
                    "scf_converged",
                    False,
                ),
                "relax_energy": getattr(
                    result,
                    "relax_energy",
                    None,
                ),
                "scf_energy": getattr(
                    result,
                    "scf_energy",
                    None,
                ),
            }

        # ========================================================
        # RELAX EXISTANT CHARGÉ
        # ========================================================

        relax_result = self.relax_result

        if relax_result is not None:

            forces = getattr(
                relax_result,
                "forces",
                None,
            )

            relaxed_structure = getattr(
                relax_result,
                "relaxed_structure",
                None,
            )

            return {
                "name": self.name,
                "status": "RELAX_LOADED",
                "success": getattr(
                    relax_result,
                    "success",
                    False,
                ),
                "relax_success": getattr(
                    relax_result,
                    "success",
                    False,
                ),
                "relax_converged": getattr(
                    relax_result,
                    "success",
                    False,
                ),
                "relax_energy": getattr(
                    relax_result,
                    "total_energy",
                    None,
                ),
                "forces": len(
                    forces or []
                ),
                "relaxed_structure": (
                    relaxed_structure is not None
                ),
                "scf_success": False,
                "scf_converged": False,
                "scf_energy": None,
            }

        # ========================================================
        # RIEN EXÉCUTÉ
        # ========================================================

        return {
            "name": self.name,
            "status": "NOT_RUN",
            "success": False,
        }
