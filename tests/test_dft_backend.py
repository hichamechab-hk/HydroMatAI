"""Tests for the common DFT backend interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from hydromatai.dft.backend import DFTBackend


class DummyBackend(DFTBackend):
    name = "dummy"

    def prepare(self, structure, workdir, **kwargs):
        return Path(workdir)

    def run(self, structure, workdir, **kwargs):
        return {"success": True}

    def parse(self, output, **kwargs):
        return {"parsed": True}


def test_backend_interface():
    backend = DummyBackend()

    assert backend.name == "dummy"
    assert repr(backend) == "DummyBackend(name='dummy')"


def test_backend_prepare():
    backend = DummyBackend()

    result = backend.prepare(
        structure=None,
        workdir="/tmp/test_dft_backend",
    )

    assert result == Path("/tmp/test_dft_backend")


def test_backend_run():
    backend = DummyBackend()

    result = backend.run(
        structure=None,
        workdir="/tmp/test_dft_backend",
    )

    assert result["success"] is True


def test_backend_parse():
    backend = DummyBackend()

    result = backend.parse("dummy.out")

    assert result["parsed"] is True


def test_cannot_instantiate_base_backend():
    with pytest.raises(TypeError):
        DFTBackend()
