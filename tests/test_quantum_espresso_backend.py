"""Tests for the Quantum ESPRESSO DFT backend."""

from __future__ import annotations

from pathlib import Path

import pytest

from hydromatai.dft.backend import DFTBackend
from hydromatai.dft.quantum_espresso import (
    QuantumEspressoBackend,
)


class DummyRunner:
    """Runner used only for backend construction tests."""

    pass


def test_qe_backend_is_dft_backend(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    assert isinstance(backend, DFTBackend)
    assert backend.name == "quantum_espresso"


def test_qe_backend_has_calculator(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    assert backend.calculator is not None
    assert backend.calculator.runner is not None
    assert backend.calculator.workdir == Path(tmp_path)


def test_qe_backend_repr(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    assert repr(backend) == (
        "QuantumEspressoBackend(name='quantum_espresso')"
    )


def test_qe_backend_requires_runner(tmp_path):
    with pytest.raises(ValueError, match="runner"):
        QuantumEspressoBackend(
            workdir=tmp_path,
        )


def test_qe_backend_requires_workdir():
    with pytest.raises(ValueError, match="workdir"):
        QuantumEspressoBackend(
            runner=DummyRunner(),
        )


def test_qe_backend_accepts_injected_calculator(
    tmp_path,
):
    from hydromatai.dft.quantum_espresso.calculator import (
        QuantumEspressoCalculator,
    )

    runner = DummyRunner()

    calculator = QuantumEspressoCalculator(
        runner=runner,
        workdir=tmp_path,
    )

    backend = QuantumEspressoBackend(
        calculator=calculator,
    )

    assert backend.calculator is calculator


def test_prepare_creates_workdir(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path / "qe_test",
    )

    workdir = backend.calculator.workdir

    workdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    assert workdir.exists()
