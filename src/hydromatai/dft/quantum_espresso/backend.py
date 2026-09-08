from __future__ import annotations
"""Quantum ESPRESSO implementation of the common DFT backend."""


from pathlib import Path
from typing import Any
from collections import Counter

from hydromatai.core import Material

from hydromatai.dft.backend import DFTBackend
from hydromatai.dft.quantum_espresso.calculator import (
    QuantumEspressoCalculator,
)


class QuantumEspressoBackend(DFTBackend):
    """DFT backend using Quantum ESPRESSO."""

    name = "quantum_espresso"

    def __init__(
        self,
        runner: Any | None = None,
        workdir: str | Path | None = None,
        calculator: QuantumEspressoCalculator | None = None,
        calculation: str = "scf",
    ) -> None:
        """Create a QE backend.

        A calculator may be injected directly. Otherwise both ``runner``
        and ``workdir`` are required to construct one.
        """

        if calculator is not None:
            self.calculator = calculator
            return

        if runner is None:
            raise ValueError(
                "runner is required when calculator is not provided"
            )

        if workdir is None:
            raise ValueError(
                "workdir is required when calculator is not provided"
            )

        self.calculator = QuantumEspressoCalculator(
            runner=runner,
            workdir=Path(workdir),
            calculation=calculation,
        )

    def prepare(
        self,
        structure: Any,
        workdir: str | Path | None = None,
        **kwargs: Any,
    ) -> Any:
        """Prepare a QE calculation without executing it."""

        target_workdir = (
            Path(workdir)
            if workdir is not None
            else self.calculator.workdir
        )

        target_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Adapter l'API publique du backend vers le Calculator
        # historique de HydroMatAI.
        self.calculator.workdir = target_workdir

        # Le backend public travaille avec une structure, tandis que
        # QuantumEspressoCalculator travaille avec un Material.
        if isinstance(structure, Material):
            material = structure
        else:
            atoms = getattr(structure, "atoms", None)

            if atoms is None:
                raise TypeError(
                    "QE backend requires a Material or a structure "
                    "containing atoms."
                )

            counts = Counter(atom.symbol for atom in atoms)

            formula = kwargs.get("formula")
            if not formula:
                formula = "".join(
                    symbol
                    + (str(count) if count > 1 else "")
                    for symbol, count in counts.items()
                )

            name = kwargs.get(
                "material_name",
                kwargs.get("name", formula),
            )

            material = Material(
                name=name,
                formula=formula,
                structure=structure,
            )

        if hasattr(self.calculator, "prepare_input"):
            return self.calculator.prepare_input(
                material,
            )

        if hasattr(self.calculator, "prepare"):
            return self.calculator.prepare(
                structure=structure,
                workdir=target_workdir,
                **kwargs,
            )

        if hasattr(self.calculator, "generate_input"):
            return self.calculator.generate_input(
                structure=structure,
                workdir=target_workdir,
                **kwargs,
            )

        raise AttributeError(
            "QuantumEspressoCalculator does not expose "
            "a supported preparation method."
        )

    def run(
        self,
        structure: Any,
        workdir: str | Path | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run QE through the existing calculator."""

        if not hasattr(self.calculator, "run"):
            raise AttributeError(
                "QuantumEspressoCalculator does not expose run()."
            )

        target_workdir = (
            Path(workdir)
            if workdir is not None
            else self.calculator.workdir
        )

        self.calculator.workdir = target_workdir

        # Le Calculator actuel possède run() sans argument.
        return self.calculator.run()

    def run_relax(
        self,
        structure: Any,
        workdir: str | Path | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run a dedicated QE RELAX calculation."""

        target_workdir = (
            Path(workdir)
            if workdir is not None
            else self.calculator.workdir
        )

        target_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        calculator = QuantumEspressoCalculator(
            runner=self.calculator.runner,
            workdir=target_workdir,
            calculation="relax",
        )

        if isinstance(structure, Material):
            material = structure
        else:
            atoms = getattr(structure, "atoms", None)

            if atoms is None:
                raise TypeError(
                    "QE RELAX requires a Material or a structure "
                    "containing atoms."
                )

            counts = Counter(atom.symbol for atom in atoms)

            formula = kwargs.get("formula")

            if not formula:
                formula = "".join(
                    symbol
                    + (str(count) if count > 1 else "")
                    for symbol, count in counts.items()
                )

            name = kwargs.get(
                "material_name",
                kwargs.get("name", formula),
            )

            material = Material(
                name=name,
                formula=formula,
                structure=structure,
            )

        calculator.prepare_input(material)

        return calculator.run()

    def run_scf(
        self,
        structure: Any,
        workdir: str | Path | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run a dedicated QE SCF calculation."""

        target_workdir = (
            Path(workdir)
            if workdir is not None
            else self.calculator.workdir
        )

        target_workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        calculator = QuantumEspressoCalculator(
            runner=self.calculator.runner,
            workdir=target_workdir,
            calculation="scf",
        )

        if isinstance(structure, Material):
            material = structure
        else:
            atoms = getattr(structure, "atoms", None)

            if atoms is None:
                raise TypeError(
                    "QE SCF requires a Material or a structure "
                    "containing atoms."
                )

            counts = Counter(atom.symbol for atom in atoms)

            formula = kwargs.get("formula")

            if not formula:
                formula = "".join(
                    symbol
                    + (str(count) if count > 1 else "")
                    for symbol, count in counts.items()
                )

            name = kwargs.get(
                "material_name",
                kwargs.get("name", formula),
            )

            material = Material(
                name=name,
                formula=formula,
                structure=structure,
            )

        calculator.prepare_input(material)

        return calculator.run()


    def parse(
        self,
        output: str | Path,
        **kwargs: Any,
    ) -> Any:
        """Parse QE output using the existing parser."""

        if hasattr(self.calculator, "parse"):
            return self.calculator.parse(
                output,
                **kwargs,
            )

        if hasattr(self.calculator, "parse_output"):
            return self.calculator.parse_output()

        parser = getattr(
            self.calculator,
            "parser",
            None,
        )

        if parser is not None and hasattr(parser, "parse"):
            return parser.parse(
                output,
                **kwargs,
            )

        raise AttributeError(
            "No supported QE parsing interface was found."
        )
