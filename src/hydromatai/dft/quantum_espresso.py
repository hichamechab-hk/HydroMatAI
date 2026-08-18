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

        structure = getattr(material, "structure", None)

        if structure is None:
            atoms = []
        else:
            atoms = getattr(structure, "atoms", [])

        symbols = []

        for atom in atoms:
            if atom.symbol not in symbols:
                symbols.append(atom.symbol)

        atomic_species = "\n".join(
            f"{symbol} 1.0 {symbol}.UPF"
            for symbol in symbols
        )

        atomic_positions = "\n".join(
            f"{atom.symbol} {atom.x} {atom.y} {atom.z}"
            for atom in atoms
        )

        nat = len(atoms)
        ntyp = len(symbols)

        input_file = self.workdir / "scf.in"

        input_file.write_text(
            f"! HydroMatAI Quantum ESPRESSO input\n"
            f"! Material: {formula}\n\n"
            f"&CONTROL\n"
            f"    calculation = 'scf',\n"
            f"    prefix = 'hydromatai',\n"
            f"/\n\n"
            f"&SYSTEM\n"
            f"    ibrav = 0,\n"
            f"    nat = {nat},\n"
            f"    ntyp = {ntyp},\n"
            f"/\n\n"
            f"&ELECTRONS\n"
            f"    conv_thr = 1.0d-8,\n"
            f"/\n\n"
            f"ATOMIC_SPECIES\n"
            f"{atomic_species}\n\n"
            f"ATOMIC_POSITIONS\n"
            f"{atomic_positions}\n\n"
            f"K_POINTS automatic\n"
            f"    1 1 1 0 0 0\n"
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
