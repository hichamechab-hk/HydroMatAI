from __future__ import annotations
import os
os.system("clear")
"""HydroMatAI — DFT/H2 priority selection."""


import csv
from pathlib import Path

from hydromatai.literature import (
    build_ambient_benchmark,
    import_literature_csv,
)
from hydromatai.scientific import ScientificWorkflow


ROOT = Path(__file__).resolve().parents[1]
LITERATURE = ROOT / "data/literature/published_results.csv"
REPORT_DIR = ROOT / "reports"
OUTPUT = REPORT_DIR / "dft_h2_priority.csv"


def main() -> None:
    print("=" * 70)
    print(" HydroMatAI — DFT / H2 PRIORITY SELECTION")
    print("=" * 70)

    results = import_literature_csv(LITERATURE)
    benchmark = build_ambient_benchmark(results)

    workflow = ScientificWorkflow(LITERATURE)

    rows = []

    for entry in benchmark:
        result = workflow.run(entry.material)

        rows.append(
            {
                "material": entry.material,
                "h2_uptake_wt_percent": entry.h2_uptake_wt_percent,
                "temperature_k": entry.temperature_k,
                "pressure_mpa": entry.pressure_mpa,
                "ambient_score": entry.screening_score,
                "scientific_score": result.final_score,
                "confidence": entry.confidence,
                "literature_count": result.literature_count,
            }
        )

    rows.sort(
        key=lambda row: (
            row["ambient_score"],
            row["scientific_score"],
        ),
        reverse=True,
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "priority",
                "material",
                "h2_uptake_wt_percent",
                "temperature_k",
                "pressure_mpa",
                "ambient_score",
                "scientific_score",
                "confidence",
                "literature_count",
            ],
        )

        writer.writeheader()

        for priority, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "priority": priority,
                    **row,
                }
            )

    print()
    print("===== TOP CANDIDATS DFT-H2 =====")

    for priority, row in enumerate(rows, start=1):
        pressure = (
            f"{row['pressure_mpa']:.2f} MPa"
            if row["pressure_mpa"] is not None
            else "N/A"
        )

        print(
            f"{priority:2d}. "
            f"{row['material']:<20} "
            f"H2={row['h2_uptake_wt_percent']:.2f} wt% "
            f"T={row['temperature_k']:.1f} K "
            f"P={pressure:<10} "
            f"ambient={row['ambient_score']:.4f} "
            f"scientific={row['scientific_score']:.4f} "
            f"{row['confidence']}"
        )

    print()
    print(f"===== DFT PRIORITY FILE =====")
    print(f"{OUTPUT}")
    print()
    print("OK — DFT/H2 PRIORITY SELECTION TERMINÉ")


if __name__ == "__main__":
    main()
