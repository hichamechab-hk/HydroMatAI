from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read_csv_row(path: Path, subject: str) -> dict[str, Any] | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        for row in rows:
            values = [str(value).strip() for value in row.values()]
            if subject.lower() in values or subject.lower() in str(row).lower():
                return dict(row)

    return None


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_priority_record(subject: str) -> dict[str, Any] | None:
    """Read-only access to the DFT/H2 priority report."""
    path = PROJECT_ROOT / "reports" / "dft_h2_priority.csv"
    return _read_csv_row(path, subject)


def load_phase55_record(subject: str) -> dict[str, Any] | None:
    """Read-only access to the Phase 55 final ranking."""
    path = (
        PROJECT_ROOT
        / "calculations"
        / "phase_55_final_scientific_consistency"
        / "phase55_final_ranking.csv"
    )
    return _read_csv_row(path, subject)


def discover_qe_files(subject: str) -> dict[str, list[str]]:
    """Discover QE files without reading or modifying their contents."""
    roots = {
        "historical_top5_dft": PROJECT_ROOT / "calculations" / "top5_dft" / subject,
        "new_campaign": PROJECT_ROOT / "calculations" / "new_campaign" / subject,
    }

    result: dict[str, list[str]] = {}

    for label, root in roots.items():
        if not root.exists():
            result[label] = []
            continue

        files = [
            str(path.relative_to(PROJECT_ROOT))
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".in", ".out", ".dos", ".cif", ".xml"}
        ]

        result[label] = sorted(files)

    return result


def load_phase55_manifest() -> Any:
    """Read-only access to the Phase 55 manifest."""
    path = (
        PROJECT_ROOT
        / "calculations"
        / "phase_55_final_scientific_consistency"
        / "phase55_manifest.json"
    )
    return _read_json(path)


def collect_subject_sources(subject: str) -> dict[str, Any]:
    """
    Collect provenance-oriented source information for one material.

    This function only reads existing HydroMatAI files.
    It does not calculate or modify scientific values.
    """
    return {
        "subject": subject,
        "priority_report": load_priority_record(subject),
        "phase55_ranking": load_phase55_record(subject),
        "phase55_manifest": load_phase55_manifest(),
        "qe_files": discover_qe_files(subject),
    }
