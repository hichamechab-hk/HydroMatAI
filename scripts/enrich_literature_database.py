#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")
"""Bulk enrichment of HydroMatAI published hydrogen-storage data."""


import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "literature" / "sources"
SOURCE_FILE = SOURCE_DIR / "bulk_hydrogen_materials.csv"

FIELDNAMES = [
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


RSC_TITLE = (
    "Metal–Organic Frameworks for Hydrogen and Methane Storage"
)
RSC_DOI = "10.1039/9781837677566-00001"
RSC_YEAR = "2026"

HYDRIDE_TITLE = (
    "Recent challenges and development of technical and "
    "technoeconomic aspects for hydrogen storage"
)
HYDRIDE_DOI = "10.1016/J.IJHYDENE.2024.05.182"
HYDRIDE_YEAR = "2024"


ROWS: list[dict[str, str]] = []


def add(
    material: str,
    property_name: str,
    value: str,
    unit: str,
    *,
    title: str,
    doi: str,
    year: str,
    method: str,
    temperature: str = "",
    pressure: str = "",
    loading: str = "",
    notes: str = "",
) -> None:
    ROWS.append(
        {
            "material": material,
            "property": property_name,
            "value": value,
            "unit": unit,
            "title": title,
            "authors": "",
            "year": year,
            "doi": doi,
            "method": method,
            "temperature": temperature,
            "pressure": pressure,
            "loading": loading,
            "notes": notes,
        }
    )


# ============================================================
# MOFs — hydrogen adsorption data
# Source: RSC 2026 chapter, Table 1.2
# ============================================================

MOF = dict(
    title=RSC_TITLE,
    doi=RSC_DOI,
    year=RSC_YEAR,
    method="secondary_literature",
)

add(
    "DMOF-1-NH2",
    "bet_surface_area",
    "1369",
    "m2/g",
    **MOF,
    notes="BET area reported in the RSC 2026 hydrogen-storage summary.",
)

add(
    "DMOF-1-NH2",
    "h2_uptake",
    "2.08",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
    notes="H2 uptake at 77 K and 1 bar.",
)

add(
    "DUT-6",
    "h2_uptake",
    "2.02",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "DUT-6",
    "h2_uptake",
    "5.64",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="50 bar",
    loading="high_pressure",
)

add(
    "DUT-9",
    "h2_uptake",
    "2.18",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "DUT-9",
    "h2_uptake",
    "5.85",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="40 bar",
    loading="high_pressure",
)

add(
    "Fe3[(Fe4Cl)3(btt)8]",
    "bet_surface_area",
    "2010",
    "m2/g",
    **MOF,
)

add(
    "Fe3[(Fe4Cl)3(btt)8]",
    "h2_uptake",
    "2.3",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "Fe4O2(BTB)8/3",
    "bet_surface_area",
    "1121",
    "m2/g",
    **MOF,
)

add(
    "Fe4O2(BTB)8/3",
    "h2_uptake",
    "2.1",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "FJI-1",
    "bet_surface_area",
    "4043",
    "m2/g",
    **MOF,
)

add(
    "FJI-1",
    "h2_uptake",
    "1.02",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "FJI-1",
    "h2_uptake",
    "6.52",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="37 bar",
    loading="high_pressure",
)

add(
    "FJI-1",
    "h2_uptake",
    "9.08",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="62 bar",
    loading="high_pressure",
)

add(
    "FJI-1",
    "h2_uptake",
    "0.43",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="65 bar",
)

add(
    "HKUST-1",
    "bet_surface_area",
    "1482",
    "m2/g",
    **MOF,
)

add(
    "HKUST-1",
    "h2_uptake",
    "2.9",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "IRMOF-6",
    "bet_surface_area",
    "2630",
    "m2/g",
    **MOF,
)

add(
    "IRMOF-6",
    "h2_uptake",
    "1.0",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="10 bar",
)

add(
    "IRMOF-8",
    "bet_surface_area",
    "1430",
    "m2/g",
    **MOF,
)

add(
    "IRMOF-8",
    "h2_uptake",
    "0.44",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="100 bar",
)

add(
    "IRMOF-20",
    "bet_surface_area",
    "4024",
    "m2/g",
    **MOF,
)

add(
    "IRMOF-20",
    "h2_uptake",
    "6.7",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="80 bar",
)

add(
    "JUC-48",
    "bet_surface_area",
    "880",
    "m2/g",
    **MOF,
)

add(
    "JUC-48",
    "h2_uptake",
    "1.1",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="100 bar",
)

add(
    "MIL-101",
    "bet_surface_area",
    "5500",
    "m2/g",
    **MOF,
)

add(
    "MIL-101",
    "h2_uptake",
    "6.1",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="80 bar",
)

add(
    "MIL-101",
    "h2_uptake",
    "0.43",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="80 bar",
)

add(
    "Mn-BTT",
    "bet_surface_area",
    "2100",
    "m2/g",
    **MOF,
)

add(
    "Mn-BTT",
    "h2_uptake",
    "5.1",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="90 bar",
)

add(
    "Mn-BTT",
    "h2_uptake",
    "0.94",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="90 bar",
)

add(
    "MOC-2",
    "bet_surface_area",
    "1420",
    "m2/g",
    **MOF,
)

add(
    "MOC-2",
    "h2_uptake",
    "2.17",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "MOF-5",
    "bet_surface_area",
    "3800",
    "m2/g",
    **MOF,
)

add(
    "MOF-5",
    "h2_uptake",
    "7.1",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="40 bar",
)

add(
    "MOF-5",
    "h2_uptake",
    "10.0",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="100 bar",
)

add(
    "MOF-5",
    "h2_uptake",
    "1.65",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="48 bar",
)

add(
    "MOF-74(Mg)",
    "bet_surface_area",
    "1510",
    "m2/g",
    **MOF,
)

add(
    "MOF-74(Mg)",
    "h2_uptake",
    "2.2",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "MOF-74",
    "bet_surface_area",
    "783",
    "m2/g",
    **MOF,
)

add(
    "MOF-74",
    "h2_uptake",
    "1.8",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="1 bar",
)

add(
    "MOF-177",
    "bet_surface_area",
    "4746",
    "m2/g",
    **MOF,
)

add(
    "MOF-177",
    "h2_uptake",
    "7.5",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="70 bar",
)

add(
    "MOF-177",
    "h2_uptake",
    "0.62",
    "wt%",
    **MOF,
    temperature="room_temperature",
    pressure="100 bar",
)

add(
    "MOF-200",
    "bet_surface_area",
    "4530",
    "m2/g",
    **MOF,
)

add(
    "MOF-200",
    "h2_uptake",
    "6.9",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="80 bar",
)

add(
    "MOF-205",
    "bet_surface_area",
    "4460",
    "m2/g",
    **MOF,
)

add(
    "MOF-205",
    "h2_uptake",
    "6.5",
    "wt%",
    **MOF,
    temperature="77 K",
    pressure="80 bar",
)

# ============================================================
# METAL / COMPLEX HYDRIDES
# Source: 2024 IJHE review, Table 1
# ============================================================

HYD = dict(
    title=HYDRIDE_TITLE,
    doi=HYDRIDE_DOI,
    year=HYDRIDE_YEAR,
    method="secondary_literature",
)


def hydride(
    material: str,
    gravimetric: str,
    volumetric: str,
    desorption: str,
) -> None:
    add(
        material,
        "h2_storage_capacity",
        gravimetric,
        "wt%",
        **HYD,
        notes="Published gravimetric capacity from the 2024 review table.",
    )

    add(
        material,
        "h2_volumetric_capacity",
        volumetric,
        "g/L",
        **HYD,
        notes="Published volumetric capacity from the 2024 review table.",
    )

    if "-" in desorption:
        minimum, maximum = desorption.split("-", 1)

        add(
            material,
            "desorption_temperature_min",
            minimum,
            "degC",
            **HYD,
            notes=f"Lower bound of reported desorption-temperature range: {desorption} degC.",
        )

        add(
            material,
            "desorption_temperature_max",
            maximum,
            "degC",
            **HYD,
            notes=f"Upper bound of reported desorption-temperature range: {desorption} degC.",
        )
    else:
        add(
            material,
            "desorption_temperature",
            desorption,
            "degC",
            **HYD,
            notes="Published desorption temperature from the review table.",
        )


hydride("LiH", "7.7", "150", "910")
hydride("AlH3", "10.1", "84", "99")
hydride("FeTiH2", "1.9", "88", "40")
hydride("LaNi5H6", "1.40", "120", "106")
hydride("NaAlH4", "3.99", "53", "150-200")
hydride("Mg2FeH6", "5.5", "120", "350")
hydride("Mg2NiH4", "3.60", "95", "290")
hydride("LiAlH4", "7.9", "46", "180")
hydride("LiBH4", "13.5", "59", "400")
hydride("LiNH2-LiH", "5.5", "105", "200")
hydride("Mg(NH2)2-LiH", "5.6", "120", "160")
hydride("MgH2-LiAlH4", "9.5", "105", "265")
hydride("MgH2-LiNH2 (1:2)", "5.5", "52", "150-300")
hydride("MgH2-NaAlH4", "7.6", "100", "185")
hydride("MgH2-LiBH4", "11.5", "68", "378")


def write_source() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    with SOURCE_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(ROWS)


def main() -> int:
    print("=" * 70)
    print("HydroMatAI — MASSIVE LITERATURE ENRICHMENT")
    print("=" * 70)

    print(f"New source records : {len(ROWS)}")
    print(f"Source file        : {SOURCE_FILE}")

    write_source()

    print()
    print("=" * 70)
    print("MERGING INTO MASTER DATABASE")
    print("=" * 70)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_literature.py"),
        ],
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        return result.returncode

    print()
    print("=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
