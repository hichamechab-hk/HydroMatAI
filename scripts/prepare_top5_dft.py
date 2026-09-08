from __future__ import annotations
import os
os.system("clear")

import csv
import shutil
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path.home() / "HydroMatAI"
STRUCTURE_DIR = ROOT / "structures" / "top5"
REPORT = ROOT / "reports" / "top5_structures.csv"
OUT = ROOT / "calculations" / "top5_dft"

PSEUDO_DIRS = [
    Path("/usr/share/espresso/pseudo"),
    Path.home() / "software" / "qe-7.5" / "pseudo",
]


def find_pseudo(element: str) -> Path | None:
    candidates = []

    for directory in PSEUDO_DIRS:
        if not directory.exists():
            continue

        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in {
                ".upf",
                ".UPF".lower(),
            }:
                candidates.append(path)

    # Prefer filenames beginning with the element symbol.
    symbol = element.lower()

    for path in candidates:
        if path.name.lower().startswith(symbol):
            return path

    return None


def read_ready_structures():
    if not REPORT.exists():
        raise FileNotFoundError(REPORT)

    rows = []

    with REPORT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            if row["status"] != "READY":
                continue

            path = Path(row["structure"])

            if path.exists():
                rows.append(row)

    return rows


def main():
    print("=" * 70)
    print(" HydroMatAI — DFT PREPARATION TOP 5")
    print("=" * 70)
    print()

    OUT.mkdir(parents=True, exist_ok=True)

    rows = read_ready_structures()

    if not rows:
        print("Aucune structure READY.")
        return

    for row in rows:
        material = row["material"]
        cif = Path(row["structure"])

        print(f"{material:20s}", end="")

        try:
            structure = Structure.from_file(cif)
        except Exception as exc:
            print(f" INVALID CIF : {exc}")
            continue

        elements = sorted(
            {str(site.specie) for site in structure}
        )

        material_dir = OUT / material.replace("/", "_")
        material_dir.mkdir(parents=True, exist_ok=True)

        destination = material_dir / f"{material}.cif"
        shutil.copy2(cif, destination)

        print(f" VALID  atoms={len(structure)}  elements={','.join(elements)}")

        print("  Pseudopotentiels :")

        all_found = True

        for element in elements:
            pseudo = find_pseudo(element)

            if pseudo:
                print(f"    {element:4s} OK  {pseudo.name}")
            else:
                print(f"    {element:4s} MISSING")
                all_found = False

        if all_found:
            print("  STATUS : READY_FOR_QE")
        else:
            print("  STATUS : WAITING_PSEUDOPOTENTIALS")

        print()

    print("=" * 70)
    print("FIN DE LA PREPARATION")
    print("=" * 70)
    print()
    print("AUCUN CALCUL QE N'A ÉTÉ LANCÉ.")
    print(f"Répertoire : {OUT}")


if __name__ == "__main__":
    main()
