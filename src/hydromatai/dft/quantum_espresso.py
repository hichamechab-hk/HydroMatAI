from pathlib import Path

from hydromatai.dft.calculator import DFTCalculator
from hydromatai.dft.output import DFTResult
from hydromatai.dft.exceptions import DFTInputError, DFTParseError


class QuantumEspressoCalculator(DFTCalculator):
    """Calculateur DFT utilisant Quantum ESPRESSO."""

    def __init__(self, runner, workdir: Path):
        self.runner = runner
        self.workdir = Path(workdir)
        self.output = None

    def prepare_input(self, material):
        """Prépare le fichier d'entrée Quantum ESPRESSO."""

        self.workdir.mkdir(parents=True, exist_ok=True)

        formula = getattr(material, "formula", None)

        if not formula:
            raise DFTInputError("Le matériau doit avoir une formule.")

        input_file = self.workdir / "scf.in"

        input_file.write_text(
            f"! HydroMatAI Quantum ESPRESSO input\n"
            f"! Material: {formula}\n"
        )

        return input_file

    def run(self):
        """Exécute Quantum ESPRESSO."""

        self.output = self.runner.run(self.workdir)
        return self.output

    def parse_output(self):
        """Convertit la sortie Quantum ESPRESSO en DFTResult."""

        if self.output is None:
            raise DFTParseError("Aucune sortie DFT à analyser.")

        return DFTResult(
            success=True,
            raw_output=self.output,
        )
