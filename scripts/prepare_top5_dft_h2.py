from __future__ import annotations
import os
os.system("clear")
"""HydroMatAI — Prepare TOP 5 DFT-H2 candidates."""


import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "reports/dft_h2_priority.csv"
OUTPUT = ROOT / "reports/top5_dft_h2.csv"


def main() -> None:
    print("=" * 70)
    print(" HydroMatAI — TOP 5 DFT / H2 PREPARATION")
    print("=" * 70)

    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    rows = rows[:5]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "priority",
            "material",
            "h2_uptake_wt_percent",
            "temperature_k",
            "pressure_mpa",
            "ambient_score",
            "scientific_score",
            "confidence",
            "literature_count",
        ]

        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for priority, row in enumerate(rows, 1):
            writer.writerow(
                {
                    "priority": priority,
                    **{
                        key: row[key]
                        for key in fields
                        if key != "priority"
                    },
                }
            )

            print(
                f"{priority}. {row['material']:<20} "
                f"ambient={row['ambient_score']} "
                f"scientific={row['scientific_score']} "
                f"H2={row['h2_uptake_wt_percent']} wt% "
                f"confidence={row['confidence']}"
            )

    print()
    print(f"TOP 5 DFT-H2 : {OUTPUT}")
    print()
    print("OK — TOP 5 PREPARES")


if __name__ == "__main__":
    main()
