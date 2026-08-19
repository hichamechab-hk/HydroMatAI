from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator
from hydromatai.dft.runner import DFTRunner


def test_quantum_espresso_calculator(tmp_path: Path):

    # ============================================================
    # 1. Structure TiO2
    # ============================================================

    structure = CrystalStructure(
        name="TiO2",
    )

    structure.add_atom(
        Atom("Ti", 0.0, 0.0, 0.0)
    )

    structure.add_atom(
        Atom("O", 0.5, 0.5, 0.5)
    )

    structure.add_atom(
        Atom("O", 0.5, 0.0, 0.0)
    )

    # ============================================================
    # 2. Matériau
    # ============================================================

    material = Material(
        name="Titanium dioxide",
        formula="TiO2",
        structure=structure,
    )

    # ============================================================
    # 3. Faux runner pour tester Calculator + Parser
    # ============================================================
    #
    # On simule une ligne réelle de sortie Quantum ESPRESSO.
    #

    runner = DFTRunner(
        [
            "python",
            "-c",
            "print('!    total energy              =   -10.12345678 Ry')",
        ]
    )

    # ============================================================
    # 4. Calculateur QE
    # ============================================================

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    # ============================================================
    # 5. Génération du fichier QE
    # ============================================================

    input_file = calculator.prepare_input(material)

    assert input_file.exists()

    # ============================================================
    # 6. Exécution
    # ============================================================

    calculator.run()

    # ============================================================
    # 7. Analyse de la sortie
    # ============================================================

    result = calculator.parse_output()

    assert result.success is True
    assert result.total_energy == -10.12345678
