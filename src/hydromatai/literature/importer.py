from __future__ import annotations
"""Import published scientific results."""


import csv
from pathlib import Path
from typing import Any

from .models import LiteratureResult


def _parse_float(value: str, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numeric value for '{field_name}': {value!r}"
        ) from exc


def _parse_year(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid year: {value!r}") from exc


def import_literature_csv(path: str | Path) -> list[LiteratureResult]:
    """Import literature results from a CSV file."""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    results: list[LiteratureResult] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        required = {"material", "property", "value", "unit"}
        fields = set(reader.fieldnames or [])

        missing = required - fields
        if missing:
            raise ValueError(
                f"Missing required CSV columns: {sorted(missing)}"
            )

        for row in reader:
            authors = []
            raw_authors = row.get("authors", "")

            if raw_authors.strip():
                authors = [
                    author.strip()
                    for author in raw_authors.split(";")
                    if author.strip()
                ]

            conditions: dict[str, Any] = {}

            for key in ("temperature", "pressure", "loading"):
                value = row.get(key, "")
                if value and value.strip():
                    conditions[key] = value.strip()

            results.append(
                LiteratureResult(
                    material=row["material"],
                    property_name=row["property"],
                    value=_parse_float(row["value"], "value"),
                    unit=row["unit"],
                    title=row.get("title") or None,
                    authors=authors,
                    journal=row.get("journal") or None,
                    year=_parse_year(row.get("year")),
                    doi=row.get("doi") or None,
                    method=row.get("method") or None,
                    conditions=conditions,
                    notes=row.get("notes") or None,
                )
            )

    return results
