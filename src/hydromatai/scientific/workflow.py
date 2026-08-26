"""Scientific workflow."""

from __future__ import annotations

from .analysis import analyze_material


class ScientificWorkflow:


    def run(
        self,
        material,
        **kwargs
    ):

        return analyze_material(
            material,
            **kwargs
        )
