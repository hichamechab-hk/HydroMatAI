"""Streaming screening of MOF metadata."""

from __future__ import annotations

from pathlib import Path

from .database import read_metadata_csv
from .mof import record_to_candidate
from .screening import screen_candidate


def screen_metadata(
    path: str | Path,
):

    for record in read_metadata_csv(path):

        candidate = record_to_candidate(record)

        if screen_candidate(candidate):
            yield candidate


def write_screened_csv(
    input_path: str | Path,
    output_path: str | Path,
) -> int:

    import csv

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    count = 0

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "cif_path",
                "surface_area",
                "void_fraction",
                "pld",
                "lcd",
            ],
        )

        writer.writeheader()

        for candidate in screen_metadata(input_path):

            writer.writerow(
                candidate.__dict__
            )

            count += 1

    return count
