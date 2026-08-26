"""
HydroMatAI DFT orchestration layer.

This module coordinates existing calculator, runner and parser
components without forcing a real DFT calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DFTPipelineResult:
    """Standard result object for the DFT pipeline."""

    success: bool
    stage: str
    message: str = ""
    total_energy: Optional[float] = None
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class DFTPipeline:
    """
    High-level orchestration layer for HydroMatAI DFT calculations.

    The pipeline does not launch anything by itself during
    construction or validation.
    """

    STAGES = (
        "validation",
        "input",
        "run",
        "parse",
    )

    def __init__(
        self,
        calculator: Any = None,
        runner: Any = None,
        parser: Any = None,
    ):
        self.calculator = calculator
        self.runner = runner
        self.parser = parser

    def validate(self) -> DFTPipelineResult:
        """Validate the pipeline configuration without running DFT."""

        if self.calculator is None:
            return DFTPipelineResult(
                success=False,
                stage="validation",
                message="No calculator configured.",
            )

        return DFTPipelineResult(
            success=True,
            stage="validation",
            message="DFT pipeline configuration is valid.",
        )

    @staticmethod
    def _find_method(obj: Any, names: tuple[str, ...]):
        if obj is None:
            return None

        for name in names:
            method = getattr(obj, name, None)
            if callable(method):
                return method

        return None

    def generate_input(self, *args, **kwargs):
        """Delegate input generation to the existing calculator."""

        method = self._find_method(
            self.calculator,
            (
                "generate_input",
                "create_input",
                "write_input",
                "generate",
            ),
        )

        if method is None:
            raise AttributeError(
                "Calculator has no input-generation method."
            )

        return method(*args, **kwargs)

    def run(self, *args, **kwargs):
        """Delegate execution to runner, or calculator if no runner exists."""

        executor = self.runner or self.calculator

        method = self._find_method(
            executor,
            (
                "run",
                "execute",
                "calculate",
            ),
        )

        if method is None:
            raise AttributeError(
                "No run/execute/calculate method available."
            )

        return method(*args, **kwargs)

    def parse(self, output=None, *args, **kwargs):
        """Delegate output parsing to the existing parser."""

        method = self._find_method(
            self.parser,
            (
                "parse",
                "parse_output",
                "read",
            ),
        )

        if method is None:
            raise AttributeError(
                "Parser has no parse method."
            )

        if output is None:
            return method(*args, **kwargs)

        return method(output, *args, **kwargs)

    def run_stage(self, stage: str, *args, **kwargs):
        """Run one explicitly requested pipeline stage."""

        stage = stage.strip().lower()

        if stage == "validation":
            return self.validate()

        if stage == "input":
            return self.generate_input(*args, **kwargs)

        if stage == "run":
            return self.run(*args, **kwargs)

        if stage == "parse":
            return self.parse(*args, **kwargs)

        raise ValueError(
            f"Unsupported stage '{stage}'. "
            f"Available stages: {', '.join(self.STAGES)}"
        )

    def describe(self) -> Dict[str, Any]:
        """Return the pipeline configuration."""

        return {
            "calculator": (
                type(self.calculator).__name__
                if self.calculator is not None
                else None
            ),
            "runner": (
                type(self.runner).__name__
                if self.runner is not None
                else None
            ),
            "parser": (
                type(self.parser).__name__
                if self.parser is not None
                else None
            ),
            "stages": list(self.STAGES),
        }
