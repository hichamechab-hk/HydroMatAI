from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .convergence import QEConvergenceAnalyzer


@dataclass
class CandidateValidationResult:
    """
    Résultat standardisé de validation DFT d'un candidat MOF.
    """

    candidate_id: str
    status: str

    structure_valid: bool = False
    input_valid: bool = False
    run_success: bool = False
    parse_success: bool = False

    converged: bool = False
    job_done: bool = False
    scf_iterations: int = 0

    total_energy: Optional[float] = None

    nat: Optional[int] = None
    ntyp: Optional[int] = None

    error_type: Optional[str] = None
    error_message: Optional[str] = None

    output_file: Optional[Path] = None

    @property
    def success(self) -> bool:
        return self.status == "PASS"


class CandidateValidator:
    """
    Validation automatique d'un candidat avec Quantum ESPRESSO.

    Le validator utilise :
        - QuantumEspressoCalculator
        - QEParser
        - QEConvergenceAnalyzer
    """

    PASS = "PASS"

    FAIL_STRUCTURE = "FAIL_STRUCTURE"
    FAIL_INPUT = "FAIL_INPUT"
    FAIL_CONVERGENCE = "FAIL_CONVERGENCE"
    FAIL_MEMORY = "FAIL_MEMORY"
    FAIL_QE = "FAIL_QE"
    FAIL_PARSE = "FAIL_PARSE"

    def __init__(self, calculator):
        self.calculator = calculator
        self.convergence_analyzer = QEConvergenceAnalyzer()

    def validate_structure(self, material):
        """
        Vérifie qu'un matériau possède une structure exploitable.
        """

        if material is None:
            return False, "Material is None."

        structure = getattr(material, "structure", None)

        if structure is None:
            return False, "Material has no structure."

        atoms = getattr(structure, "atoms", None)

        if not atoms:
            return False, "Structure contains no atoms."

        formula = getattr(material, "formula", None)

        if not formula:
            return False, "Material has no formula."

        return True, None

    def _get_structure_info(self, material):

        structure = material.structure
        atoms = structure.atoms

        symbols = []

        for atom in atoms:
            if atom.symbol not in symbols:
                symbols.append(atom.symbol)

        return len(atoms), len(symbols)

    def validate(self, material, candidate_id: Optional[str] = None):

        if candidate_id is None:
            candidate_id = (
                getattr(material, "name", None)
                or getattr(material, "formula", None)
                or "unknown"
            )

        result = CandidateValidationResult(
            candidate_id=str(candidate_id),
            status=self.FAIL_STRUCTURE,
        )

        # ======================================================
        # 1. STRUCTURE
        # ======================================================

        valid, error = self.validate_structure(material)

        if not valid:
            result.error_message = error
            return result

        result.structure_valid = True
        result.nat, result.ntyp = self._get_structure_info(material)

        # ======================================================
        # 2. QE INPUT
        # ======================================================

        try:
            self.calculator.prepare_input(material)
            result.input_valid = True

        except Exception as exc:
            result.status = self.FAIL_INPUT
            result.error_type = "INPUT"
            result.error_message = str(exc)
            return result

        # ======================================================
        # 3. RUN QE
        # ======================================================

        try:
            raw_output = self.calculator.run()
            result.run_success = True

        except Exception as exc:

            message = str(exc)
            lower_message = message.lower()

            if (
                "memory" in lower_message
                or "bad_alloc" in lower_message
                or "cannot allocate" in lower_message
            ):
                result.status = self.FAIL_MEMORY
                result.error_type = "MEMORY"

            else:
                result.status = self.FAIL_QE
                result.error_type = "QE"

            result.error_message = message

            return result

        # ======================================================
        # 4. CONVERGENCE ANALYSIS
        # ======================================================

        convergence = self.convergence_analyzer.analyze(
            raw_output
        )

        result.converged = convergence.converged
        result.job_done = convergence.job_done
        result.scf_iterations = convergence.scf_iterations

        if convergence.total_energy is not None:
            result.total_energy = convergence.total_energy

        # Déterminer le fichier de sortie
        workdir = getattr(
            self.calculator,
            "workdir",
            None,
        )

        if workdir is not None:
            workdir = Path(workdir)

            possible_outputs = [
                workdir / "scf.out",
                workdir / "pw.out",
                workdir / "output.out",
            ]

            for output_file in possible_outputs:
                if output_file.exists():
                    result.output_file = output_file
                    break

        # ======================================================
        # 5. ERREURS QE
        # ======================================================

        if convergence.error_type == "MEMORY":
            result.status = self.FAIL_MEMORY
            result.error_type = "MEMORY"
            result.error_message = convergence.error_message
            return result

        if convergence.error_type == "QE":
            result.status = self.FAIL_QE
            result.error_type = "QE"
            result.error_message = convergence.error_message
            return result

        # ======================================================
        # 6. CONVERGENCE
        # ======================================================

        if not convergence.converged:
            result.status = self.FAIL_CONVERGENCE
            result.error_type = "CONVERGENCE"
            result.error_message = convergence.error_message
            return result

        # ======================================================
        # 7. JOB DONE
        # ======================================================

        if not convergence.job_done:
            result.status = self.FAIL_QE
            result.error_type = "INCOMPLETE"
            result.error_message = (
                "SCF convergence detected but JOB DONE was not found."
            )
            return result

        # ======================================================
        # 8. PARSING ÉNERGIE
        # ======================================================

        try:
            parsed = self.calculator.parse_output()

        except Exception as exc:
            result.status = self.FAIL_PARSE
            result.error_type = "PARSE"
            result.error_message = str(exc)
            return result

        result.parse_success = bool(
            getattr(parsed, "success", False)
        )

        if result.total_energy is None:
            result.total_energy = getattr(
                parsed,
                "total_energy",
                None,
            )

        if not result.parse_success:
            result.status = self.FAIL_PARSE
            result.error_type = "PARSE"
            result.error_message = (
                "DFT parser returned success=False."
            )
            return result

        # ======================================================
        # 9. VALIDATION FINALE
        # ======================================================

        result.status = self.PASS
        result.error_type = None
        result.error_message = None

        return result
