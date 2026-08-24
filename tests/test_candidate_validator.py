from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure

from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator
from hydromatai.dft.runner import DFTRunner

from hydromatai.dft.validation import CandidateValidator


def create_tio2():

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

    return Material(
        name="Titanium dioxide",
        formula="TiO2",
        structure=structure,
    )


def test_candidate_validator_pass(tmp_path: Path):

    material = create_tio2()

    qe_output = """
iteration # 1
iteration # 2
iteration # 3

convergence has been achieved in 3 iterations

!    total energy              =   -10.12345678 Ry

JOB DONE.
"""

    runner = DFTRunner(
        [
            "python",
            "-c",
            f"print({qe_output!r})",
        ]
    )

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    validator = CandidateValidator(
        calculator=calculator,
    )

    result = validator.validate(
        material,
        candidate_id="TiO2_test",
    )

    assert result.success is True
    assert result.status == "PASS"

    assert result.structure_valid is True
    assert result.input_valid is True
    assert result.run_success is True
    assert result.parse_success is True

    assert result.converged is True
    assert result.job_done is True
    assert result.scf_iterations == 3

    assert result.total_energy == -10.12345678

    assert result.nat == 3
    assert result.ntyp == 2


def test_candidate_validator_convergence_failure(tmp_path: Path):

    material = create_tio2()

    qe_output = """
iteration # 1
iteration # 2

convergence NOT achieved
"""

    runner = DFTRunner(
        [
            "python",
            "-c",
            f"print({qe_output!r})",
        ]
    )

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    validator = CandidateValidator(
        calculator=calculator,
    )

    result = validator.validate(
        material,
        candidate_id="TiO2_no_convergence",
    )

    assert result.success is False
    assert result.status == "FAIL_CONVERGENCE"
    assert result.converged is False
    assert result.scf_iterations == 2


def test_candidate_validator_memory_failure(tmp_path: Path):

    material = create_tio2()

    qe_output = """
iteration # 1
Error in routine c_bands
cannot allocate memory
"""

    runner = DFTRunner(
        [
            "python",
            "-c",
            f"print({qe_output!r})",
        ]
    )

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    validator = CandidateValidator(
        calculator=calculator,
    )

    result = validator.validate(
        material,
        candidate_id="TiO2_memory",
    )

    assert result.success is False
    assert result.status == "FAIL_MEMORY"
    assert result.error_type == "MEMORY"


def test_candidate_validator_invalid_structure(tmp_path: Path):

    calculator = QuantumEspressoCalculator(
        runner=None,
        workdir=tmp_path,
    )

    validator = CandidateValidator(
        calculator=calculator,
    )

    result = validator.validate(
        None,
        candidate_id="invalid",
    )

    assert result.success is False
    assert result.status == "FAIL_STRUCTURE"


def test_candidate_validator_missing_structure(tmp_path: Path):

    material = Material(
        name="Invalid material",
        formula="X",
        structure=None,
    )

    calculator = QuantumEspressoCalculator(
        runner=None,
        workdir=tmp_path,
    )

    validator = CandidateValidator(
        calculator=calculator,
    )

    result = validator.validate(
        material,
        candidate_id="missing_structure",
    )

    assert result.status == "FAIL_STRUCTURE"
    assert result.success is False
