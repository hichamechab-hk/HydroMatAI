from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.dft import QuantumEspressoCalculator


def test_quantum_espresso_prepare_input(tmp_path: Path):

    structure = CrystalStructure(
        name="TiO2",
    )

    structure.add_atom(
        Atom(
            symbol="Ti",
            x=0.0,
            y=0.0,
            z=0.0,
        )
    )

    structure.add_atom(
        Atom(
            symbol="O",
            x=0.5,
            y=0.5,
            z=0.5,
        )
    )

    structure.add_atom(
        Atom(
            symbol="O",
            x=0.5,
            y=0.0,
            z=0.0,
        )
    )

    material = Material(
        formula="TiO2",
        name="Titanium dioxide",
        structure=structure,
    )

    calculator = QuantumEspressoCalculator(
        runner=None,
        workdir=tmp_path,
    )

    input_file = calculator.prepare_input(material)

    assert input_file.exists()
    assert input_file.name == "scf.in"

    content = input_file.read_text()

    assert "HydroMatAI Quantum ESPRESSO input" in content
    assert "Material: TiO2" in content

    assert "&CONTROL" in content
    assert "&SYSTEM" in content
    assert "&ELECTRONS" in content

    assert "nat = 3" in content
    assert "ntyp = 2" in content

    assert "ATOMIC_SPECIES" in content
    assert "Ti" in content
    assert "O" in content

    assert "ATOMIC_POSITIONS" in content
    assert "Ti 0.0 0.0 0.0" in content
    assert "O 0.5 0.5 0.5" in content
    assert "O 0.5 0.0 0.0" in content

    assert "K_POINTS automatic" in content
