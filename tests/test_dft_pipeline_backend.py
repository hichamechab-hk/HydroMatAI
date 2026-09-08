"""Tests for DFTPipeline backend integration."""

from pathlib import Path

from hydromatai.dft.pipeline import DFTPipeline
from hydromatai.dft.quantum_espresso import (
    QuantumEspressoBackend,
)


class DummyRunner:
    pass


def test_pipeline_accepts_backend(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    pipeline = DFTPipeline(
        backend=backend,
    )

    assert pipeline.backend is backend
    assert pipeline.calculator is backend.calculator
    assert pipeline.runner is backend.calculator.runner
    assert pipeline.parser is backend.calculator.parser


def test_pipeline_backend_validation(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    pipeline = DFTPipeline(
        backend=backend,
    )

    result = pipeline.validate()

    assert result.success is True
    assert result.stage == "validation"


def test_pipeline_backend_description(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    pipeline = DFTPipeline(
        backend=backend,
    )

    description = pipeline.describe()

    assert description["backend"] == (
        "QuantumEspressoBackend"
    )
    assert description["calculator"] == (
        "QuantumEspressoCalculator"
    )
    assert description["runner"] == "DummyRunner"
    assert description["parser"] == "QEParser"


def test_pipeline_legacy_mode_still_works(tmp_path):
    backend = QuantumEspressoBackend(
        runner=DummyRunner(),
        workdir=tmp_path,
    )

    pipeline = DFTPipeline(
        calculator=backend.calculator,
        runner=backend.calculator.runner,
        parser=backend.calculator.parser,
    )

    result = pipeline.validate()

    assert result.success is True
