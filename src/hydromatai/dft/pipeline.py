from __future__ import annotations
"""
HydroMatAI DFT orchestration layer.

This module coordinates existing calculator, runner and parser
components without forcing a real DFT calculation.
"""


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
        "relax_scf",
    )

    def __init__(
        self,
        calculator: Any = None,
        runner: Any = None,
        parser: Any = None,
        backend: Any = None,
        relax_scf_workflow: Any = None,
    ):
        """Create a DFT pipeline.

        ``backend`` is the preferred modern interface.

        ``calculator``, ``runner`` and ``parser`` remain supported
        for backward compatibility with the existing HydroMatAI code.
        """
        self.backend = backend
        self.calculator = calculator
        self.runner = runner
        self.parser = parser
        self.relax_scf_workflow = relax_scf_workflow

        if self.backend is not None:
            self.calculator = getattr(
                self.backend,
                "calculator",
                self.calculator,
            )

            if self.runner is None and self.calculator is not None:
                self.runner = getattr(
                    self.calculator,
                    "runner",
                    None,
                )

            if self.parser is None and self.calculator is not None:
                self.parser = getattr(
                    self.calculator,
                    "parser",
                    None,
                )

    def validate(self) -> DFTPipelineResult:
        """Validate the pipeline configuration without running DFT."""

        if (
            self.backend is None
            and self.calculator is None
            and self.relax_scf_workflow is None
        ):
            return DFTPipelineResult(
                success=False,
                stage="validation",
                message="No DFT backend or calculator configured.",
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

        if self.backend is not None:
            method = self._find_method(
                self.backend,
                (
                    "prepare",
                    "generate_input",
                    "create_input",
                    "write_input",
                    "generate",
                ),
            )

            if method is not None:
                return method(*args, **kwargs)

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

        if self.backend is not None:
            method = self._find_method(
                self.backend,
                (
                    "run",
                    "execute",
                    "calculate",
                ),
            )

            if method is not None:
                return method(*args, **kwargs)

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

        if self.backend is not None:
            method = self._find_method(
                self.backend,
                (
                    "parse",
                    "parse_output",
                    "read",
                ),
            )

            if method is not None:
                if output is None:
                    return method(*args, **kwargs)

                return method(output, *args, **kwargs)

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

    def run_relax_scf(self, material, candidate_id=None):
        """Run the RELAX -> SCF workflow.

        This method is deliberately separate from ``run()`` so the
        existing DFT backend API remains backward compatible.
        """

        workflow = self.relax_scf_workflow

        if workflow is None:
            raise RuntimeError(
                "No RELAX -> SCF workflow configured."
            )

        run_method = getattr(
            workflow,
            "run",
            None,
        )

        if not callable(run_method):
            raise AttributeError(
                "Configured RELAX -> SCF workflow has no run() method."
            )

        return run_method(
            material,
            candidate_id=candidate_id,
        )

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

        if stage == "relax_scf":
            return self.run_relax_scf(*args, **kwargs)

        raise ValueError(
            f"Unsupported stage '{stage}'. "
            f"Available stages: {', '.join(self.STAGES)}"
        )

    def describe(self) -> Dict[str, Any]:
        """Return the pipeline configuration."""

        return {
            "backend": (
                type(self.backend).__name__
                if self.backend is not None
                else None
            ),
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
            "relax_scf_workflow": (
                type(self.relax_scf_workflow).__name__
                if self.relax_scf_workflow is not None
                else None
            ),
            "stages": list(self.STAGES),
        }
