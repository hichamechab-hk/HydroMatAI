from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class QEConvergenceResult:
    converged: bool
    job_done: bool
    scf_iterations: int
    total_energy: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class QEConvergenceAnalyzer:
    """
    Analyse la convergence et les erreurs d'une sortie
    Quantum ESPRESSO pw.x.
    """

    ENERGY_PATTERN = re.compile(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry"
    )

    ITERATION_PATTERN = re.compile(
        r"iteration\s+#\s*(\d+)",
        re.IGNORECASE,
    )

    def analyze(self, raw_output: str) -> QEConvergenceResult:

        if not raw_output:
            return QEConvergenceResult(
                converged=False,
                job_done=False,
                scf_iterations=0,
                error_type="EMPTY_OUTPUT",
                error_message="QE output is empty.",
            )

        # Énergie finale
        energy_matches = self.ENERGY_PATTERN.findall(raw_output)

        total_energy = (
            float(energy_matches[-1])
            if energy_matches
            else None
        )

        # Nombre maximal d'itérations
        iteration_matches = self.ITERATION_PATTERN.findall(
            raw_output
        )

        scf_iterations = (
            max(int(value) for value in iteration_matches)
            if iteration_matches
            else 0
        )

        lower_output = raw_output.lower()

        # JOB DONE
        job_done = "job done." in lower_output

        # Convergence
        converged = (
            "convergence has been achieved" in lower_output
            or "convergence achieved" in lower_output
        )

        # Erreurs
        error_type = None
        error_message = None

        if (
            "out of memory" in lower_output
            or "cannot allocate memory" in lower_output
            or "memory exhausted" in lower_output
            or "bad_alloc" in lower_output
        ):
            error_type = "MEMORY"
            error_message = (
                "Quantum ESPRESSO reported a memory problem."
            )

        elif "error in routine" in lower_output:
            error_type = "QE"
            error_message = (
                "Quantum ESPRESSO reported an error in a routine."
            )

        elif "convergence not achieved" in lower_output:
            error_type = "CONVERGENCE"
            error_message = (
                "SCF convergence was not achieved."
            )

        elif not converged:
            error_type = "CONVERGENCE"
            error_message = (
                "SCF convergence was not detected."
            )

        return QEConvergenceResult(
            converged=converged,
            job_done=job_done,
            scf_iterations=scf_iterations,
            total_energy=total_energy,
            error_type=error_type,
            error_message=error_message,
        )
