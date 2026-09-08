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

    def __init__(
        self,
        runner,
        workdir: Path,
        calculation: str = "scf",
    ):
        self.runner = runner
        self.workdir = Path(workdir)
        self.output = None
        self.calculation = calculation

        self.input_generator = QEInputGenerator(
            calculation=calculation,
        )
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

        # Nom utilisé dans l'en-tête du fichier QE.
        # Exemple :
        # ! Material: TiO2
        material_name = getattr(
            material,
            "formula",
            None,
        )

        if not material_name:
            material_name = getattr(
                material,
                "name",
                "Unknown",
            )

        try:
            return self.input_generator.write(
                structure,
                self.workdir,
                material_name=material_name,
            )

        except Exception as exc:
            raise DFTInputError(
                f"Impossible de générer l'entrée QE : {exc}"
            ) from exc

    def run(self):
        """
        Exécute Quantum ESPRESSO.
        """

        if self.runner is None:
            raise DFTInputError(
                "Aucun runner Quantum ESPRESSO n'a été configuré."
            )

        self.output = self.runner.run(
            self.workdir
        )

        return self.output

    def parse_output(self):
        """
        Analyse la sortie Quantum ESPRESSO.

        ``self.output`` peut être :

            - une chaîne contenant directement la sortie QE ;
            - un Path vers le fichier de sortie QE.

        Retourne
        --------
        DFTResult
            Résultat parsé par QEParser.
        """

        if self.output is None:
            raise DFTParseError(
                "Aucune sortie DFT à analyser."
            )

        raw_output = self.output

        # --------------------------------------------------------
        # SORTIE SOUS FORME DE FICHIER
        # --------------------------------------------------------

        if isinstance(raw_output, Path):

            if not raw_output.exists():
                raise DFTParseError(
                    f"Fichier de sortie DFT introuvable : "
                    f"{raw_output}"
                )

            try:
                raw_output = raw_output.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

            except OSError as exc:
                raise DFTParseError(
                    f"Impossible de lire la sortie DFT : "
                    f"{raw_output}"
                ) from exc

        # --------------------------------------------------------
        # SORTIE SOUS FORME DE TEXTE
        # --------------------------------------------------------

        elif not isinstance(raw_output, str):

            raise DFTParseError(
                "La sortie DFT doit être une chaîne "
                "ou un chemin de fichier."
            )

        # --------------------------------------------------------
        # PARSING QE
        # --------------------------------------------------------

        return self.parser.parse(
            raw_output
        )

    def load_output(self, output_path):
        """
        Charge une sortie QE existante sans relancer QE.

        Paramètre
        ---------
        output_path :
            Chemin vers le fichier de sortie QE.

        Retourne
        --------
        DFTResult
            Résultat parsé de la sortie QE.
        """

        path = Path(output_path)

        if not path.exists():
            raise DFTParseError(
                f"Fichier de sortie DFT introuvable : {path}"
            )

        if not path.is_file():
            raise DFTParseError(
                f"La sortie DFT n'est pas un fichier : {path}"
            )

        self.output = path

        return self.parse_output()
