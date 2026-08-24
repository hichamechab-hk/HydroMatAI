from dataclasses import dataclass
from typing import Optional


@dataclass
class RelaxSCFResult:
    """
    Résultat complet du workflow RELAX -> SCF.
    """

    candidate_id: str
    status: str

    relax_success: bool = False
    relax_converged: bool = False
    relax_iterations: int = 0
    relax_energy: Optional[float] = None

    scf_success: bool = False
    scf_converged: bool = False
    scf_iterations: int = 0
    scf_energy: Optional[float] = None

    # Indique explicitement que la géométrie relaxée
    # a été transférée vers le SCF.
    relaxed_structure_transferred: bool = False

    error_type: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "PASS"


class RelaxSCFWorkflow:
    """
    Workflow DFT complet :

        structure initiale
                ↓
              RELAX
                ↓
        structure relaxée
                ↓
               SCF
                ↓
        énergie électronique finale
    """

    PASS = "PASS"
    FAIL_RELAX = "FAIL_RELAX"
    FAIL_SCF = "FAIL_SCF"

    def __init__(self, relax_calculator, scf_calculator):

        self.relax_calculator = relax_calculator
        self.scf_calculator = scf_calculator

    # ============================================================
    # ANALYSE QE
    # ============================================================

    def _analyze(self, calculator, raw_output):
        """
        Analyse la sortie QE avec QEConvergenceAnalyzer.
        """

        from hydromatai.dft.validation import (
            QEConvergenceAnalyzer,
        )

        analyzer = QEConvergenceAnalyzer()

        return analyzer.analyze(raw_output)

    # ============================================================
    # TRANSFERT STRUCTURE RELAXÉE
    # ============================================================

    def _transfer_relaxed_structure(
        self,
        material,
        relax_result,
    ):
        """
        Transfère la structure finale du RELAX vers le matériau
        utilisé par le calcul SCF.

        Retourne True si le transfert est effectué.
        """

        relaxed_structure = getattr(
            relax_result,
            "relaxed_structure",
            None,
        )

        if relaxed_structure is None:
            return False

        material.structure = relaxed_structure

        return True

    # ============================================================
    # WORKFLOW
    # ============================================================

    def run(self, material, candidate_id=None):

        if candidate_id is None:

            candidate_id = (
                getattr(material, "name", None)
                or getattr(material, "formula", None)
                or "unknown"
            )

        result = RelaxSCFResult(
            candidate_id=str(candidate_id),
            status=self.FAIL_RELAX,
        )

        # ========================================================
        # 1. RELAX
        # ========================================================

        try:

            self.relax_calculator.prepare_input(
                material
            )

            relax_output = (
                self.relax_calculator.run()
            )

        except Exception as exc:

            result.status = self.FAIL_RELAX
            result.error_type = "RELAX"
            result.error_message = str(exc)

            return result

        # ========================================================
        # 2. ANALYSE RELAX
        # ========================================================

        relax_convergence = self._analyze(
            self.relax_calculator,
            relax_output,
        )

        result.relax_converged = (
            relax_convergence.converged
        )

        result.relax_iterations = (
            relax_convergence.scf_iterations
        )

        result.relax_energy = (
            relax_convergence.total_energy
        )

        # ========================================================
        # 3. ERREUR RELAX
        # ========================================================

        if relax_convergence.error_type is not None:

            result.status = self.FAIL_RELAX

            result.error_type = (
                relax_convergence.error_type
            )

            result.error_message = (
                relax_convergence.error_message
            )

            return result

        # ========================================================
        # 4. VÉRIFICATION CONVERGENCE RELAX
        # ========================================================

        if (
            not relax_convergence.converged
            or not relax_convergence.job_done
        ):

            result.status = self.FAIL_RELAX
            result.error_type = "CONVERGENCE"

            result.error_message = (
                "RELAX did not finish successfully."
            )

            return result

        result.relax_success = True

        # ========================================================
        # 5. PARSER RELAX
        # ========================================================

        try:

            relax_parsed = (
                self.relax_calculator.parse_output()
            )

        except Exception as exc:

            result.status = self.FAIL_RELAX
            result.error_type = "PARSE"
            result.error_message = str(exc)

            return result

        # ========================================================
        # 6. TRANSFERT DE LA GÉOMÉTRIE RELAXÉE
        # ========================================================

        transferred = (
            self._transfer_relaxed_structure(
                material,
                relax_parsed,
            )
        )

        result.relaxed_structure_transferred = (
            transferred
        )

        if not transferred:

            result.status = self.FAIL_RELAX
            result.error_type = "GEOMETRY"
            result.error_message = (
                "RELAX converged, but no relaxed "
                "structure was returned by QEParser."
            )

            return result

        # ========================================================
        # 7. SCF SUR STRUCTURE RELAXÉE
        # ========================================================

        try:

            self.scf_calculator.prepare_input(
                material
            )

            scf_output = (
                self.scf_calculator.run()
            )

        except Exception as exc:

            result.status = self.FAIL_SCF
            result.error_type = "SCF"
            result.error_message = str(exc)

            return result

        # ========================================================
        # 8. ANALYSE SCF
        # ========================================================

        scf_convergence = self._analyze(
            self.scf_calculator,
            scf_output,
        )

        result.scf_converged = (
            scf_convergence.converged
        )

        result.scf_iterations = (
            scf_convergence.scf_iterations
        )

        result.scf_energy = (
            scf_convergence.total_energy
        )

        # ========================================================
        # 9. ERREUR SCF
        # ========================================================

        if scf_convergence.error_type is not None:

            result.status = self.FAIL_SCF

            result.error_type = (
                scf_convergence.error_type
            )

            result.error_message = (
                scf_convergence.error_message
            )

            return result

        # ========================================================
        # 10. VÉRIFICATION CONVERGENCE SCF
        # ========================================================

        if (
            not scf_convergence.converged
            or not scf_convergence.job_done
        ):

            result.status = self.FAIL_SCF
            result.error_type = "CONVERGENCE"

            result.error_message = (
                "SCF did not finish successfully."
            )

            return result

        result.scf_success = True

        # ========================================================
        # 11. SUCCÈS FINAL
        # ========================================================

        result.status = self.PASS

        return result
