import os
os.system("clear")
from pathlib import Path
from collections import defaultdict
import csv
import hashlib

from pymatgen.core import Structure

ROOT = Path("MOF_Library")

COLLECTIONS = {
    "METAL_HYDRIDES": ROOT / "METAL_HYDRIDES" / "cif",
    "COMPLEXES": ROOT / "COMPLEXES" / "cif",
}

REPORT_DIR = Path("reports/hydrides_complexes")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = REPORT_DIR / "structural_duplicates.csv"


def fingerprint(structure: Structure) -> str:
    """
    Empreinte structurale normalisée.
    On utilise :
      - formule réduite
      - nombre de sites
      - paramètres de maille
      - espèces
      - coordonnées fractionnelles arrondies
    """
    lattice = structure.lattice

    species = [str(site.specie) for site in structure]
    coords = [
        tuple(round(float(x) % 1.0, 5) for x in site.frac_coords)
        for site in structure
    ]

    atoms = sorted(zip(species, coords))

    payload = (
        structure.composition.reduced_formula,
        len(structure),
        tuple(round(x, 5) for x in lattice.abc),
        tuple(round(x, 5) for x in lattice.angles),
        tuple(atoms),
    )

    return hashlib.sha256(repr(payload).encode()).hexdigest()


print("=" * 80)
print(" HydroMatAI — DÉDUPLICATION STRUCTURALE")
print("=" * 80)

groups = defaultdict(list)

total = 0
valid = 0
invalid = 0

for collection, directory in COLLECTIONS.items():

    print()
    print(f"===== {collection} =====")

    files = sorted(directory.glob("*.cif"))

    print(f"CIF trouvés : {len(files):,}")

    for path in files:
        total += 1

        try:
            structure = Structure.from_file(path)
            fp = fingerprint(structure)

            groups[fp].append(
                {
                    "collection": collection,
                    "path": str(path),
                    "formula": structure.composition.reduced_formula,
                    "sites": len(structure),
                }
            )

            valid += 1

        except Exception:
            invalid += 1

duplicates = {
    fp: entries
    for fp, entries in groups.items()
    if len(entries) > 1
}

duplicate_files = sum(len(v) - 1 for v in duplicates.values())

print()
print("=" * 80)
print(" RÉSULTATS")
print("=" * 80)

print(f"CIF total              : {total:,}")
print(f"CIF valides            : {valid:,}")
print(f"CIF invalides          : {invalid:,}")
print(f"Structures uniques     : {len(groups):,}")
print(f"Groupes de doublons    : {len(duplicates):,}")
print(f"CIF supplémentaires    : {duplicate_files:,}")

with REPORT.open("w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)

    writer.writerow(
        [
            "duplicate_group",
            "collection",
            "formula",
            "sites",
            "cif_path",
        ]
    )

    group_number = 0

    for fp, entries in sorted(duplicates.items()):

        group_number += 1

        for entry in entries:
            writer.writerow(
                [
                    group_number,
                    entry["collection"],
                    entry["formula"],
                    entry["sites"],
                    entry["path"],
                ]
            )

print()
print(f"Rapport : {REPORT}")

print()
print("IMPORTANT : aucun fichier supprimé.")
print("QE : NON LANCÉ")

print("=" * 80)
