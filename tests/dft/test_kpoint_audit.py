from pathlib import Path

import pytest

from hydromatai.dft.validation.kpoint_audit import (
    KPointResult,
    energy_spread,
    parse_kpoint_output,
    successive_energy_differences,
)


def test_parse_complete_kpoint_output(tmp_path: Path):
    output = tmp_path / "complete.out"

    output.write_text(
        """
        number of k points=    10
        convergence has been achieved
        !    total energy              =   -880.73456845 Ry
        the Fermi energy is    13.0295 ev
        JOB DONE.
        """
    )

    result = parse_kpoint_output("3x3x3", output)

    assert result.grid == "3x3x3"
    assert result.energy_ry == -880.73456845
    assert result.fermi_ev == 13.0295
    assert result.irreducible_kpoints == 10
    assert result.scf_converged is True
    assert result.job_done is True


def test_parse_incomplete_kpoint_output(tmp_path: Path):
    output = tmp_path / "incomplete.out"

    output.write_text(
        """
        number of k points=    30
        !    total energy              =   -880.71737007 Ry
        estimated scf accuracy < 0.00000080 Ry
        """
    )

    result = parse_kpoint_output("4x4x4", output)

    assert result.grid == "4x4x4"
    assert result.energy_ry == -880.71737007
    assert result.fermi_ev is None
    assert result.irreducible_kpoints == 30
    assert result.scf_converged is False
    assert result.job_done is False


def test_energy_spread():
    results = [
        KPointResult(
            grid="3x3x3",
            path=Path("3.out"),
            energy_ry=-880.73456845,
            fermi_ev=13.0295,
            irreducible_kpoints=10,
            scf_converged=True,
            job_done=True,
        ),
        KPointResult(
            grid="4x4x4",
            path=Path("4.out"),
            energy_ry=-880.73000000,
            fermi_ev=13.0,
            irreducible_kpoints=30,
            scf_converged=True,
            job_done=True,
        ),
        KPointResult(
            grid="5x5x5",
            path=Path("5.out"),
            energy_ry=-880.72800000,
            fermi_ev=12.9,
            irreducible_kpoints=39,
            scf_converged=True,
            job_done=True,
        ),
    ]

    assert energy_spread(results) == pytest.approx(0.00656845)


def test_energy_spread_requires_two_energies():
    result = KPointResult(
        grid="3x3x3",
        path=Path("3.out"),
        energy_ry=-880.73456845,
        fermi_ev=None,
        irreducible_kpoints=10,
        scf_converged=False,
        job_done=False,
    )

    assert energy_spread([result]) is None


def test_successive_energy_differences():
    results = [
        KPointResult(
            grid="3x3x3",
            path=Path("3.out"),
            energy_ry=-880.73456845,
            fermi_ev=None,
            irreducible_kpoints=10,
            scf_converged=True,
            job_done=True,
        ),
        KPointResult(
            grid="4x4x4",
            path=Path("4.out"),
            energy_ry=-880.73000000,
            fermi_ev=None,
            irreducible_kpoints=30,
            scf_converged=True,
            job_done=True,
        ),
        KPointResult(
            grid="5x5x5",
            path=Path("5.out"),
            energy_ry=None,
            fermi_ev=None,
            irreducible_kpoints=39,
            scf_converged=False,
            job_done=False,
        ),
    ]

    differences = successive_energy_differences(results)

    assert len(differences) == 1
    assert differences[0][0] == "3x3x3"
    assert differences[0][1] == "4x4x4"
    assert differences[0][2] == pytest.approx(0.00456845)
