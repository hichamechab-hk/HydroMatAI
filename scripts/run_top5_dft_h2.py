from __future__ import annotations
import os
os.system("clear")
"""HydroMatAI — Complete TOP 5 DFT/H2 orchestration."""


import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOP5 = ROOT / "reports/top5_dft_h2.csv"
REPORT_DIR = ROOT / "reports"
RESULTS = REPORT_DIR / "top5_dft_h2_final.csv"


def find_structure(material: str) -> Path | None:
    """Find an existing structure without inventing one."""
    candidates = []

    for root in (
        ROOT / "data",
        ROOT / "structures",
        ROOT / "calculations",
    ):
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".cif", ".xyz", ".vasp", ".json"}:
                continue

            name = path.stem.lower()
            target = material.lower().replace(" ", "")

            if target in name.replace(" ", ""):
                candidates.append(path)

    return candidates[0] if candidates else None


def main() -> None:
    print("=" * 70)
    print(" HydroMatAI — COMPLETE TOP 5 DFT / H2 WORKFLOW")
    print("=" * 70)

    if not TOP5.exists():
        raise FileNotFoundError(TOP5)

    with TOP5.open("r", encoding="utf-8", newline="") as handle:
        top5 = list(csv.DictReader(handle))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    print()
    print("===== STRUCTURE VALIDATION =====")

    for row in top5:
        material = row["material"]
        structure = find_structure(material)

        if structure is None:
            status = "STRUCTURE_MISSING"
            structure_text = "N/A"
        else:
            status = "READY_FOR_DFT"
            structure_text = str(structure)

        print(
            f"{material:<20} "
            f"{status:<18} "
            f"{structure_text}"
        )

        rows.append(
            {
                **row,
                "structure": structure_text,
                "status": status,
                "dft_status": (
                    "NOT_STARTED"
                    if structure is None
                    else "READY"
                ),
                "adsorption_energy_ev": "",
            }
        )

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
        "structure",
        "status",
        "dft_status",
        "adsorption_energy_ev",
    ]

    with RESULTS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ready = sum(
        row["status"] == "READY_FOR_DFT"
        for row in rows
    )

    print()
    print("===== WORKFLOW STATUS =====")
    print(f"TOP 5 candidats : {len(rows)}")
    print(f"Structures disponibles : {ready}")
    print(f"Structures manquantes : {len(rows) - ready}")

    if ready == 0:
        print()
        print("Aucun calcul QE lancé.")
        print("Les structures réelles doivent être ajoutées avant DFT.")
    else:
        print()
        print("Structures disponibles détectées.")
        print("Étape QE prête à être exécutée.")

    print()
    print(f"Résultat : {RESULTS}")
    print()
    print("OK — ORCHESTRATION TOP 5 TERMINÉE")


if __name__ == "__main__":
    main()
