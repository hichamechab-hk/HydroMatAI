from __future__ import annotations
import os
os.system("clear")

import csv
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.core.composition import Composition


ROOT = Path.home() / "HydroMatAI"
TOP5_FILE = ROOT / "reports" / "top5_dft_h2.csv"
STRUCTURE_DIR = ROOT / "structures" / "top5"
REPORT = ROOT / "reports" / "top5_structures.csv"

STRUCTURE_DIR.mkdir(parents=True, exist_ok=True)


def normalize(name: str) -> str:
    return (
        name.replace("-", "")
        .replace("_", "")
        .replace(" ", "")
        .lower()
    )


def load_top5() -> list[str]:
    materials = []

    with TOP5_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            material = row.get("material", "").strip()

            if material:
                materials.append(material)

    return materials[:5]


def find_material_project(material: str):
    try:
        from mp_api.client import MPRester
    except ImportError:
        print("ERREUR: mp-api n'est pas installé.")
        return []

    api_key = os.environ.get("MP_API_KEY")

    if not api_key:
        print("ERREUR: MP_API_KEY n'est pas défini.")
        print()
        print("Définir votre clé Materials Project avec :")
        print("export MP_API_KEY='VOTRE_CLE'")
        return []

    try:
        composition = Composition(material)

        formula = composition.reduced_formula

    except Exception:
        formula = material

    print(f"  recherche MP : {formula}")

    try:
        with MPRester(api_key) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=[
                    "material_id",
                    "formula_pretty",
                    "composition_reduced",
                    "structure",
                ],
            )

        return docs

    except Exception as exc:
        print(f"  erreur Materials Project : {exc}")
        return []


def choose_structure(material: str, docs):
    if not docs:
        return None

    target = normalize(material)

    exact = []

    for doc in docs:
        formula = getattr(
            doc,
            "formula_pretty",
            None,
        )

        if formula and normalize(formula) == target:
            exact.append(doc)

    if exact:
        return exact[0]

    return docs[0]


def validate_cif(path: Path) -> tuple[bool, str]:
    try:
        structure = Structure.from_file(path)

        if len(structure) == 0:
            return False, "EMPTY_STRUCTURE"

        elements = sorted(
            {
                str(site.specie)
                for site in structure
            }
        )

        return True, ",".join(elements)

    except Exception as exc:
        return False, str(exc)


def main() -> None:
    print("=" * 70)
    print(" HydroMatAI — TOP 5 STRUCTURE RECOVERY")
    print("=" * 70)
    print()

    materials = load_top5()

    if not materials:
        print("ERREUR : top5_dft_h2.csv introuvable ou vide.")
        return

    print(f"TOP 5 : {len(materials)}")
    print()

    rows = []

    for number, material in enumerate(materials, 1):

        print(
            f"{number}. {material:20s}",
            end="",
            flush=True,
        )

        docs = find_material_project(material)

        doc = choose_structure(material, docs)

        if doc is None:
            print(" MISSING")

            rows.append(
                {
                    "material": material,
                    "status": "STRUCTURE_MISSING",
                    "material_id": "",
                    "formula": "",
                    "structure": "",
                    "elements": "",
                }
            )

            continue

        structure = getattr(doc, "structure", None)

        if structure is None:
            print(" NO_STRUCTURE")

            rows.append(
                {
                    "material": material,
                    "status": "NO_STRUCTURE",
                    "material_id": str(
                        getattr(doc, "material_id", "")
                    ),
                    "formula": str(
                        getattr(doc, "formula_pretty", "")
                    ),
                    "structure": "",
                    "elements": "",
                }
            )

            continue

        safe_name = (
            material
            .replace("/", "_")
            .replace(" ", "_")
        )

        cif_path = STRUCTURE_DIR / f"{safe_name}.cif"

        structure.to(
            filename=str(cif_path),
            fmt="cif",
        )

        valid, details = validate_cif(cif_path)

        if valid:
            print(
                f" READY  "
                f"MP={getattr(doc, 'material_id', '')}  "
                f"elements={details}"
            )

            status = "READY"

        else:
            print(f" INVALID  {details}")
            status = "INVALID"

        rows.append(
            {
                "material": material,
                "status": status,
                "material_id": str(
                    getattr(doc, "material_id", "")
                ),
                "formula": str(
                    getattr(doc, "formula_pretty", "")
                ),
                "structure": str(cif_path),
                "elements": details if valid else "",
            }
        )

    with REPORT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "material",
                "status",
                "material_id",
                "formula",
                "structure",
                "elements",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    ready = sum(
        row["status"] == "READY"
        for row in rows
    )

    print()
    print("=" * 70)
    print(" RESULTAT")
    print("=" * 70)
    print(f"Structures recherchées : {len(rows)}")
    print(f"Structures valides     : {ready}")
    print(f"Structures non prêtes  : {len(rows) - ready}")
    print()
    print(f"Rapport : {REPORT}")

    if ready == len(rows):
        print()
        print("OK — TOP 5 STRUCTURES VALIDÉES")
        print("PROCHAINE ÉTAPE : PRÉPARATION QE")
    else:
        print()
        print("QE NON LANCÉ")
        print("Des structures doivent encore être récupérées.")


if __name__ == "__main__":
    main()
