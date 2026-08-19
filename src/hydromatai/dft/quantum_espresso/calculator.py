from pathlib import Path

from hydromatai.dft.calculator import DFTCalculator
from hydromatai.dft.exceptions import DFTInputError, DFTParseError
from hydromatai.dft.quantum_espresso.input_generator import (
    QEInputGenerator,
)
from hydromatai.dft.quantum_espresso.parser import QEParser


class QuantumEspressoCalculator(DFTCalculator):
    """
    Calculateur DFT utilisant Quantum ESPRESSO.
    """

    def __init__(self, runner, workdir: Path):
        self.runner = runner
        self.workdir = Path(workdir)
        self.output = None

        self.input_generator = QEInputGenerator()
        self.parser = QEParser()

    def prepare_input(self, material):
        """
        Prépare le fichier d'entrée Quantum ESPRESSO.
        """

        if material is None:
            raise DFTInputError(
                "Le matériau ne peut pas être None."
            )

        formula = getattr(material, "formula", None)

        if not formula:
            raise DFTInputError(
                "Le matériau doit avoir une formule."
            )

        structure = getattr(material, "structure", None)

        if structure is None:
            raise DFTInputError(
                "Le matériau doit posséder une structure."
            )

        try:
            return self.input_generator.write(
                structure,
                self.workdir,
            )
        except Exception as exc:
            raise DFTInputError(
                f"Impossible de générer l'entrée QE : {exc}"
            ) from exc

    def run(self):
        """
        Exécute Quantum ESPRESSO.
        """

        self.output = self.runner.run(self.workdir)

        return self.output

    def parse_output(self):
        """
        Analyse la sortie Quantum ESPRESSO.
        """

        if self.output is None:
            raise DFTParseError(
                "Aucune sortie DFT à analyser."
            )

        return self.parser.parse(self.output)
