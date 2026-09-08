from __future__ import annotations
"""Scientific report generation."""


from pathlib import Path

from hydromatai.literature import build_ambient_benchmark


def write_scientific_report(
    result,
    path: str | Path,
):
    """Write a scientific report including literature and ambient H2 benchmark."""

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    literature_lines: list[str] = []

    if result.literature_results:
        for item in result.literature_results:
            literature_lines.append(
                f"Property: {item.property_name}\n"
                f"Value: {item.value} {item.unit}\n"
                f"Method: {item.method or 'unknown'}\n"
                f"Year: {item.year or 'unknown'}\n"
                f"DOI: {item.doi or 'unknown'}\n"
            )
    else:
        literature_lines.append("No published results available.")

    literature_text = "\n".join(literature_lines)

    # Build the published near-ambient H2 benchmark from attached literature.
    ambient_entries = build_ambient_benchmark(
        result.literature_results
    )

    if ambient_entries:
        ambient_lines: list[str] = []

        for rank, entry in enumerate(ambient_entries, start=1):
            pressure = (
                f"{entry.pressure_mpa:.4g} MPa"
                if entry.pressure_mpa is not None
                else "N/A"
            )

            ambient_lines.append(
                f"{rank}. {entry.material}\n"
                f"   H2 uptake: {entry.h2_uptake_wt_percent:.4g} wt%\n"
                f"   Temperature: {entry.temperature_k:.1f} K\n"
                f"   Pressure: {pressure}\n"
                f"   Screening score: {entry.screening_score:.4f}\n"
                f"   Confidence: {entry.confidence}\n"
            )

        ambient_text = "\n".join(ambient_lines)
    else:
        ambient_text = (
            "No published near-ambient gravimetric H2 results available."
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


Literature hydrogen-storage score:
----------------------------------
{
    result.hydrogen_literature_score.final_score
    if result.hydrogen_literature_score
    else "N/A"
}


AMBIENT H2 — Published Benchmark:
---------------------------------
{ambient_text}


Published literature:
---------------------
{literature_text}

Summary:
{result.summary}
"""

    path.write_text(
        text,
        encoding="utf-8",
    )

    return path
