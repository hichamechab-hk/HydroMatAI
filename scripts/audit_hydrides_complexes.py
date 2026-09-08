import os
os.system("clear")
from pathlib import Path
from collections import Counter
from pymatgen.core import Structure

ROOT = Path("MOF_Library")

collections = {
    "METAL_HYDRIDES": ROOT / "METAL_HYDRIDES" / "cif",
    "COMPLEXES": ROOT / "COMPLEXES" / "cif",
}

print("=" * 80)
print(" HydroMatAI — AUDIT HYDRURES & COMPLEXES")
print("=" * 80)

global_seen = set()

for name, directory in collections.items():
    files = sorted(directory.glob("*.cif"))

    valid = 0
    invalid = 0
    no_h = 0
    empty = 0
    duplicate = 0
    formulas = Counter()
    elements = Counter()

    for path in files:
        try:
            structure = Structure.from_file(path)

            if len(structure) == 0:
                empty += 1
                continue

            valid += 1

            formula = structure.composition.reduced_formula
            formulas[formula] += 1

            elems = tuple(sorted(str(e) for e in structure.composition.elements))
            elements.update(elems)

            if "H" not in elems:
                no_h += 1

            # Empreinte simple : formule + nombre de sites + éléments
            fingerprint = (
                formula,
                len(structure),
                elems,
            )

            if fingerprint in global_seen:
                duplicate += 1
            else:
                global_seen.add(fingerprint)

        except Exception:
            invalid += 1

    print()
    print(f"===== {name} =====")
    print(f"CIF trouvés          : {len(files):,}")
    print(f"CIF valides          : {valid:,}")
    print(f"CIF invalides        : {invalid:,}")
    print(f"CIF sans H           : {no_h:,}")
    print(f"CIF vides            : {empty:,}")
    print(f"Doublons structuraux : {duplicate:,}")

    print()
    print("Top formules :")
    for formula, count in formulas.most_common(10):
        print(f"  {formula:<25} {count:>6}")

    print()
    print("Éléments présents :")
    print("  " + ", ".join(sorted(elements)))

print()
print("=" * 80)
print(" AUDIT GLOBAL")
print("=" * 80)
print(f"Empreintes uniques : {len(global_seen):,}")
print()
print("QE : NON LANCÉ")
print("=" * 80)
