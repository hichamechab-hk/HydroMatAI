from __future__ import annotations
"""MOFX-DB metadata integration utilities."""


import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class MOFRecord:

    name: str

    cif_path: str | None = None

    surface_area: float | None = None
    void_fraction: float | None = None
    pld: float | None = None
    lcd: float | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cif_path": self.cif_path,
            "surface_area": self.surface_area,
            "void_fraction": self.void_fraction,
            "pld": self.pld,
            "lcd": self.lcd,
        }


def _float_or_none(value: str | None) -> float | None:

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _first_value(row: dict, names: list[str]):

    lowered = {
        str(k).strip().lower(): v
        for k, v in row.items()
    }

    for name in names:

        value = lowered.get(name.lower())

        if value not in (None, ""):
            return value

    return None


def read_metadata_csv(
    path: str | Path,
) -> Iterator[MOFRecord]:
    """Stream MOF metadata from CSV without loading the file entirely."""

    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:

            name = _first_value(
                row,
                [
                    "name",
                    "mof_name",
                    "mofid",
                    "id",
                    "structure_id",
                ],
            )

            if not name:
                continue

            cif_path = _first_value(
                row,
                [
                    "cif_path",
                    "cif",
                    "path",
                    "filename",
                ],
            )

            surface_area = _float_or_none(
                _first_value(
                    row,
                    [
                        "surface_area",
                        "surface_area_m2_g",
                        "asa",
                        "sa",
                    ],
                )
            )

            void_fraction = _float_or_none(
                _first_value(
                    row,
                    [
                        "void_fraction",
                        "void_fraction_percent",
                        "vf",
                    ],
                )
            )

            pld = _float_or_none(
                _first_value(
                    row,
                    [
                        "pld",
                        "pore_limiting_diameter",
                    ],
                )
            )

            lcd = _float_or_none(
                _first_value(
                    row,
                    [
                        "lcd",
                        "largest_cavity_diameter",
                    ],
                )
            )

            yield MOFRecord(
                name=str(name),
                cif_path=str(cif_path) if cif_path else None,
                surface_area=surface_area,
                void_fraction=void_fraction,
                pld=pld,
                lcd=lcd,
            )


def count_records(path: str | Path) -> int:

    return sum(1 for _ in read_metadata_csv(path))
