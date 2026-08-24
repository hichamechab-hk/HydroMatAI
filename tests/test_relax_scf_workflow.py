from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure

from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator
from hydromatai.dft.runner import DFTRunner

from hydromatai.dft.workflow import RelaxSCFWorkflow


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


def make_relax_runner(energy):

    output = f"""
Program PWSCF

ATOMIC_POSITIONS angstrom
Ti  0.10000000  0.10000000  0.10000000
O   0.60000000  0.60000000  0.60000000
O   0.60000000  0.10000000  0.10000000

CELL_PARAMETERS angstrom
10.00000000  0.00000000  0.00000000
0.00000000  10.00000000  0.00000000
0.00000000  0.00000000  10.00000000

iteration # 1
iteration # 2

convergence has been achieved in 2 iterations

!    total energy              =   {energy} Ry

JOB DONE.
"""

    return DFTRunner(
        [
            "python",
            "-c",
            f"print({output!r})",
        ]
    )


def make_scf_runner(energy):

    output = f"""
Program PWSCF

iteration # 1
iteration # 2

convergence has been achieved in 2 iterations

!    total energy              =   {energy} Ry

JOB DONE.
"""

    return DFTRunner(
        [
            "python",
            "-c",
            f"print({output!r})",
        ]
    )


def test_relax_scf_success(tmp_path: Path):

    material = create_tio2()

    relax = QuantumEspressoCalculator(
        runner=make_relax_runner("-20.00000000"),
        workdir=tmp_path / "relax",
    )

    scf = QuantumEspressoCalculator(
        runner=make_scf_runner("-21.00000000"),
        workdir=tmp_path / "scf",
    )

    workflow = RelaxSCFWorkflow(
        relax_calculator=relax,
        scf_calculator=scf,
    )

    result = workflow.run(
        material,
        candidate_id="TiO2_test",
    )

    assert result.success is True
    assert result.status == "PASS"

    assert result.relax_success is True
    assert result.relax_converged is True
    assert result.relax_iterations == 2
    assert result.relax_energy == -20.0

    assert result.relaxed_structure_transferred is True

    assert result.scf_success is True
    assert result.scf_converged is True
    assert result.scf_iterations == 2
    assert result.scf_energy == -21.0

    # Vérification de la géométrie relaxée
    assert material.structure is not None
    assert len(material.structure.atoms) == 3

    assert material.structure.atoms[0].symbol == "Ti"

    assert material.structure.atoms[0].x == 0.1
    assert material.structure.atoms[0].y == 0.1
    assert material.structure.atoms[0].z == 0.1


def test_relax_scf_transfers_relaxed_coordinates(
    tmp_path: Path,
):

    material = create_tio2()

    # Coordonnée initiale du Ti
    assert material.structure.atoms[0].x == 0.0

    relax = QuantumEspressoCalculator(
        runner=make_relax_runner("-20.00000000"),
        workdir=tmp_path / "relax",
    )

    scf = QuantumEspressoCalculator(
        runner=make_scf_runner("-21.00000000"),
        workdir=tmp_path / "scf",
    )

    workflow = RelaxSCFWorkflow(
        relax_calculator=relax,
        scf_calculator=scf,
    )

    result = workflow.run(
        material,
        candidate_id="TiO2_geometry",
    )

    assert result.success is True

    # Le Ti doit maintenant être à la position relaxée
    assert material.structure.atoms[0].x == 0.1
    assert material.structure.atoms[0].y == 0.1
    assert material.structure.atoms[0].z == 0.1

    # Vérification de la cellule finale
    assert material.structure.cell[0] == [
        10.0,
        0.0,
        0.0,
    ]


def test_relax_failure_stops_workflow(
    tmp_path: Path,
):

    material = create_tio2()

    output = """
iteration # 1
iteration # 2
convergence NOT achieved
"""

    relax = QuantumEspressoCalculator(
        runner=DFTRunner(
            [
                "python",
                "-c",
                f"print({output!r})",
            ]
        ),
        workdir=tmp_path / "relax",
    )

    scf = QuantumEspressoCalculator(
        runner=make_scf_runner("-21.00000000"),
        workdir=tmp_path / "scf",
    )

    workflow = RelaxSCFWorkflow(
        relax_calculator=relax,
        scf_calculator=scf,
    )

    result = workflow.run(
        material,
        candidate_id="TiO2_relax_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_RELAX"
    assert result.relax_success is False
    assert result.scf_success is False


def test_scf_failure_after_relax(
    tmp_path: Path,
):

    material = create_tio2()

    relax = QuantumEspressoCalculator(
        runner=make_relax_runner("-20.00000000"),
        workdir=tmp_path / "relax",
    )

    output = """
iteration # 1
iteration # 2
convergence NOT achieved
"""

    scf = QuantumEspressoCalculator(
        runner=DFTRunner(
            [
                "python",
                "-c",
                f"print({output!r})",
            ]
        ),
        workdir=tmp_path / "scf",
    )

    workflow = RelaxSCFWorkflow(
        relax_calculator=relax,
        scf_calculator=scf,
    )

    result = workflow.run(
        material,
        candidate_id="TiO2_scf_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_SCF"

    assert result.relax_success is True
    assert result.relaxed_structure_transferred is True

    assert result.scf_success is False
