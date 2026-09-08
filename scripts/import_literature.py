#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")
"""HydroMatAI bulk literature importer.

Scans data/literature/sources/ recursively, merges CSV datasets,
normalizes DOI/material/property fields, removes duplicate scientific
records, validates required fields, and writes the master database.
"""


import csv
import hashlib
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "literature" / "sources"
OUTPUT = ROOT / "data" / "literature" / "published_results.csv"

REQUIRED_COLUMNS = {
    "material",
    "property",
    "value",
    "unit",
}

OUTPUT_COLUMNS = [
    "material",
    "property",
    "value",
    "unit",
    "title",
    "authors",
    "year",
    "doi",
    "method",
    "temperature",
    "pressure",
    "loading",
    "notes",
]


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


def normalize_doi(value: str | None) -> str:
    doi = normalize_text(value).lower()

    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
        "doi ",
    )

    for prefix in prefixes:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]

    return doi.strip()


def normalize_authors(value: str | None) -> str:
    if not value:
        return ""

    parts = []

    for item in value.replace("|", ";").split(";"):
        item = normalize_text(item)
        if item:
            parts.append(item)

    return ";".join(parts)


def normalize_value(value: str | None) -> str:
    value = normalize_text(value)

    if not value:
        return ""

    try:
        number = float(value)
        return str(number)
    except ValueError:
        return value


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {
        column: normalize_text(row.get(column))
        for column in OUTPUT_COLUMNS
    }

    normalized["authors"] = normalize_authors(
        row.get("authors")
    )

    normalized["doi"] = normalize_doi(
        row.get("doi")
    )

    normalized["value"] = normalize_value(
        row.get("value")
    )

    return normalized


def record_key(row: dict[str, str]) -> str:
    """Build a stable key for one scientific result."""

    material = normalize_text(row.get("material")).lower()
    prop = normalize_text(row.get("property")).lower()
    unit = normalize_text(row.get("unit")).lower()
    doi = normalize_doi(row.get("doi"))

    if doi:
        raw = "|".join([
            doi,
            material,
            prop,
            unit,
        ])
    else:
        raw = "|".join([
            material,
            prop,
            row.get("value", ""),
            unit,
            normalize_text(row.get("title")).lower(),
            row.get("year", ""),
        ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = set(reader.fieldnames or [])

        missing = REQUIRED_COLUMNS - fields

        if missing:
            print(
                f"[SKIP] {path.name}: "
                f"missing columns {sorted(missing)}"
            )
            return []

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            normalized = normalize_row(row)

            if not normalized["material"]:
                print(
                    f"[SKIP] {path.name}:{row_number}: "
                    "empty material"
                )
                continue

            if not normalized["property"]:
                print(
                    f"[SKIP] {path.name}:{row_number}: "
                    "empty property"
                )
                continue

            if not normalized["value"]:
                print(
                    f"[SKIP] {path.name}:{row_number}: "
                    "empty value"
                )
                continue

            if not normalized["unit"]:
                print(
                    f"[SKIP] {path.name}:{row_number}: "
                    "empty unit"
                )
                continue

            rows.append(normalized)

    return rows


def load_all_sources() -> list[dict[str, str]]:
    all_rows: list[dict[str, str]] = []

    for path in sorted(
        SOURCE_DIR.rglob("*.csv")
    ):
        print(f"[READ] {path.relative_to(ROOT)}")
        all_rows.extend(load_csv(path))

    return all_rows


def merge_with_existing(
    rows: Iterable[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge incoming data with the current master database."""

    merged: dict[str, dict[str, str]] = {}

    if OUTPUT.exists():
        with OUTPUT.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                normalized = normalize_row(row)
                key = record_key(normalized)

                if key not in merged:
                    merged[key] = normalized

    for row in rows:
        key = record_key(row)

        if key not in merged:
            merged[key] = row

    return list(merged.values())


def write_master(rows: list[dict[str, str]]) -> None:
    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = sorted(
        rows,
        key=lambda row: (
            row["material"].lower(),
            row["property"].lower(),
            row["unit"].lower(),
        ),
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_COLUMNS,
        )

        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    print("=" * 70)
    print("HydroMatAI — BULK LITERATURE IMPORT")
    print("=" * 70)

    SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sources = sorted(
        SOURCE_DIR.rglob("*.csv")
    )

    print(f"Source files : {len(sources)}")
    print(f"Master file  : {OUTPUT}")
    print()

    incoming = load_all_sources()

    print()
    print(f"Valid incoming records : {len(incoming)}")

    merged = merge_with_existing(
        incoming
    )

    print(f"Master records          : {len(merged)}")

    write_master(merged)

    print()
    print("=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Records : {len(merged)}")
    print(f"Output  : {OUTPUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
