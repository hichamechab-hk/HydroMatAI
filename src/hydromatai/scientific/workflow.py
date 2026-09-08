from __future__ import annotations
"""Scientific workflow."""


from pathlib import Path

from hydromatai.literature import (
    LiteratureRepository,
    import_literature_csv,
)

from .analysis import analyze_material


class ScientificWorkflow:
    """Run scientific analysis with optional literature data."""

    def __init__(
        self,
        literature_path: str | Path = "data/literature/published_results.csv",
    ) -> None:
        self.literature_path = Path(literature_path)
        self.literature_repository = LiteratureRepository()

        if self.literature_path.exists():
            self.literature_repository.add_many(
                import_literature_csv(self.literature_path)
            )

    def run(
        self,
        material: str,
        **kwargs,
    ):
        """Analyze a material and attach matching literature results."""

        literature_results = self.literature_repository.for_material(material)

        return analyze_material(
            material,
            literature_results=literature_results,
            **kwargs,
        )
