#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")
"""Add verified published hydrogen-storage results."""


import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "literature" / "sources"
OUTPUT = SOURCE_DIR / "verified_hydrogen_materials.csv"


ROWS = [
    {
        "material": "MgH2",
        "property": "h2_theoretical_capacity",
        "value": "7.6",
        "unit": "wt%",
        "title": "Magnesium-based hydrogen storage materials: Design and performance optimization of single-component and multi-component systems",
        "authors": "2026 International Journal of Hydrogen Energy review",
        "year": "2026",
        "doi": "10.1016/j.ijhydene.2026.153673",
        "method": "literature_review",
        "temperature": "",
        "pressure": "",
        "loading": "",
        "notes": "Theoretical gravimetric hydrogen capacity of MgH2",
    },
    {
        "material": "MgH2",
        "property": "h2_volumetric_capacity",
        "value": "110",
        "unit": "g/L",
        "title": "Magnesium-based hydrogen storage materials: Design and performance optimization of single-component and multi-component systems",
        "authors": "2026 International Journal of Hydrogen Energy review",
        "year": "2026",
        "doi": "10.1016/j.ijhydene.2026.153673",
        "method": "literature_review",
        "temperature": "",
        "pressure": "",
        "loading": "",
        "notes": "Approximate volumetric hydrogen storage density reported for MgH2",
    },
    {
        "material": "MgH2",
        "property": "dehydrogenation_enthalpy",
        "value": "76",
        "unit": "kJ/mol_H2",
        "title": "Magnesium-based hydrogen storage materials: Design and performance optimization of single-component and multi-component systems",
        "authors": "2026 International Journal of Hydrogen Energy review",
        "year": "2026",
        "doi": "10.1016/j.ijhydene.2026.153673",
        "method": "literature_review",
        "temperature": "",
        "pressure": "",
        "loading": "",
        "notes": "Approximate enthalpy associated with MgH2 dehydrogenation",
    },
    {
        "material": "MgH2",
        "property": "desorption_temperature",
        "value": "300",
        "unit": "degC",
        "title": "Magnesium-based hydrogen storage materials: Design and performance optimization of single-component and multi-component systems",
        "authors": "2026 International Journal of Hydrogen Energy review",
        "year": "2026",
        "doi": "10.1016/j.ijhydene.2026.153673",
        "method": "literature_review",
        "temperature": "",
        "pressure": "",
        "loading": "",
        "notes": "High-temperature limitation; reported dehydrogenation temperature is above approximately 300 degC",
    },
    {
        "material": "MOF-177",
        "property": "h2_saturation_uptake",
        "value": "7.5",
        "unit": "wt%",
        "title": "Exceptional H2 Saturation Uptake in Microporous Metal-Organic Frameworks",
        "authors": "Antek G Wong-Foy;Adam J Matzger;Omar M Yaghi",
        "year": "2006",
        "doi": "10.1021/ja058213h",
        "method": "experiment",
        "temperature": "77 K",
        "pressure": "",
        "loading": "saturation",
        "notes": "Highest gravimetric saturation uptake reported in the studied MOF series",
    },
    {
        "material": "IRMOF-20",
        "property": "h2_saturation_uptake",
        "value": "34",
        "unit": "g/L",
        "title": "Exceptional H2 Saturation Uptake in Microporous Metal-Organic Frameworks",
        "authors": "Antek G Wong-Foy;Adam J Matzger;Omar M Yaghi",
        "year": "2006",
        "doi": "10.1021/ja058213h",
        "method": "experiment",
        "temperature": "77 K",
        "pressure": "",
        "loading": "saturation",
        "notes": "Highest volumetric saturation uptake reported in the studied MOF series",
    },
]


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )

        writer.writeheader()
        writer.writerows(ROWS)

    print("=" * 70)
    print("HydroMatAI — VERIFIED HYDROGEN MATERIALS")
    print("=" * 70)
    print(f"Records added to source : {len(ROWS)}")
    print(f"Source                  : {OUTPUT}")
    print()
    for row in ROWS:
        print(
            f"{row['material']:12} | "
            f"{row['property']:28} | "
            f"{row['value']:8} {row['unit']}"
        )


if __name__ == "__main__":
    main()
