from __future__ import annotations
"""Repository for published scientific results."""


from .models import LiteratureResult


class LiteratureRepository:
    """Store and query published scientific results."""

    def __init__(self) -> None:
        self._results: list[LiteratureResult] = []

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip().lower()

    @staticmethod
    def _normalize_doi(doi: str | None) -> str | None:
        if not doi:
            return None

        value = doi.strip().lower()

        for prefix in (
            "https://doi.org/",
            "http://doi.org/",
            "doi:",
            "doi ",
        ):
            if value.startswith(prefix):
                value = value[len(prefix):]

        return value.strip()

    def add(self, result: LiteratureResult) -> bool:
        """Add a result unless the same scientific record already exists."""

        result_doi = self._normalize_doi(result.doi)

        if result_doi:
            for existing in self._results:
                if (
                    self._normalize_doi(existing.doi) == result_doi
                    and self._normalize(existing.material)
                    == self._normalize(result.material)
                    and self._normalize(existing.property_name)
                    == self._normalize(result.property_name)
                    and self._normalize(existing.unit)
                    == self._normalize(result.unit)
                ):
                    return False

        self._results.append(result)
        return True

    def add_many(self, results: list[LiteratureResult]) -> int:
        added = 0

        for result in results:
            if self.add(result):
                added += 1

        return added

    def all(self) -> list[LiteratureResult]:
        return list(self._results)

    def for_material(self, material: str) -> list[LiteratureResult]:
        target = self._normalize(material)

        return [
            result
            for result in self._results
            if self._normalize(result.material) == target
        ]

    def for_property(self, property_name: str) -> list[LiteratureResult]:
        target = self._normalize(property_name)

        return [
            result
            for result in self._results
            if self._normalize(result.property_name) == target
        ]

    def search(
        self,
        material: str | None = None,
        property_name: str | None = None,
    ) -> list[LiteratureResult]:
        """Search by material, property, or both."""

        results = self._results

        if material is not None:
            material_key = self._normalize(material)
            results = [
                result
                for result in results
                if self._normalize(result.material) == material_key
            ]

        if property_name is not None:
            property_key = self._normalize(property_name)
            results = [
                result
                for result in results
                if self._normalize(result.property_name) == property_key
            ]

        return list(results)

    def for_doi(self, doi: str) -> list[LiteratureResult]:
        target = self._normalize_doi(doi)

        return [
            result
            for result in self._results
            if self._normalize_doi(result.doi) == target
        ]

    def clear(self) -> None:
        self._results.clear()

    def __len__(self) -> int:
        return len(self._results)


    def for_family(self, family: str):
        """Return published results belonging to a material family."""

        target = family.strip().upper()

        return [
            result
            for result in self._results
            if (result.family or "").upper() == target
        ]
