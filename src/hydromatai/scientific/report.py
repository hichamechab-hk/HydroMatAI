"""Scientific report generation."""

from __future__ import annotations

from pathlib import Path


def write_scientific_report(
    result,
    path: str | Path,
):

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    text = f"""
HydroMatAI Scientific Report
============================

Material:
{result.material}

Energy:
{result.total_energy}

Band gap:
{result.band_gap}

Electronic:
{result.electronic_classification}

Optical:
{result.optical_classification}

Stability score:
{result.stability_score}

Hydrogen score:
{result.hydrogen_score}

Final score:
{result.final_score}


Summary:
{result.summary}
"""


    path.write_text(
        text,
        encoding="utf-8"
    )

    return path
