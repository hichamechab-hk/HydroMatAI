from pathlib import Path

from hydromatai.core.material import Material
from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator
from hydromatai.dft.runner import DFTRunner


def test_quantum_espresso_calculator(tmp_path: Path):

    material = Material(
        name="Titanium dioxide",
        formula="TiO2",
    )

    runner = DFTRunner(
        ["python", "-c", "print('QE TEST OK')"]
    )

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    input_file = calculator.prepare_input(material)

    assert input_file.exists()
    assert "TiO2" in input_file.read_text()

    calculator.run()

    result = calculator.parse_output()

    assert result.success is True
    assert "QE TEST OK" in result.raw_output
