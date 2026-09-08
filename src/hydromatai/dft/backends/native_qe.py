from __future__ import annotations
"""Native Quantum ESPRESSO backend for HydroMatAI."""


from pathlib import Path
from typing import Any

from hydromatai.dft.backend import DFTBackend
from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator


class NativeQEBackend(DFTBackend):
    """DFT backend using HydroMatAI's native QE calculator.

    The backend adapts the generic DFTBackend interface to the
    existing QuantumEspressoCalculator API.
    """

    def __init__(
        self,
        runner: Any,
        workdir: Path,
    ) -> None:
        self.runner = runner
        self.workdir = Path(workdir)

    @property
    def name(self) -> str:
        """Return the backend name."""
        return "native_quantum_espresso"

    def _calculator(
        self,
        calculation: str,
    ) -> QuantumEspressoCalculator:
        """Create a QE calculator for a specific calculation."""
        return QuantumEspressoCalculator(
            runner=self.runner,
            workdir=self.workdir,
            calculation=calculation,
        )

    def _run(
        self,
        calculation: str,
        material: Any,
    ) -> Any:
        """Prepare, execute and parse one QE calculation."""
        calculator = self._calculator(calculation)

        calculator.prepare_input(material)
        calculator.run()

        return calculator.parse_output()

    def run_relax(
        self,
        material: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a QE structural relaxation."""
        return self._run(
            calculation="relax",
            material=material,
        )

    def run_scf(
        self,
        material: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a QE SCF calculation."""
        return self._run(
            calculation="scf",
            material=material,
        )

    def run_bands(
        self,
        material: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a QE band-structure calculation."""
        return self._run(
            calculation="bands",
            material=material,
        )

    def run_dos(
        self,
        material: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a QE DOS calculation."""
        return self._run(
            calculation="nscf",
            material=material,
        )
