from __future__ import annotations
import os
os.system("clear")

import csv
import json
from pathlib import Path

from mp_api.client import MPRester
from pymatgen.core import Composition, Structure


ROOT = Path("MOF_Library")

HYDRIDES_DIR = ROOT / "METAL_HYDRIDES"
COMPLEXES_DIR = ROOT / "COMPLEXES"

HYDRIDES_CIF = HYDRIDES_DIR / "cif"
COMPLEXES_CIF = COMPLEXES_DIR / "cif"

HYDRIDES_META = HYDRIDES_DIR / "metadata.csv"
COMPLEXES_META = COMPLEXES_DIR / "metadata.csv"

SUMMARY = ROOT / "hydrid_complex_import_summary.json"

LIMIT = 1000


# Métaux couramment rencontrés dans les hydrures métalliques.
METALS = {
    "Li", "Na", "K", "Rb", "Cs",
    "Be", "Mg", "Ca", "Sr", "Ba",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Al", "Ga", "In", "Tl",
    "Si", "Ge", "Sn", "Pb",
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb",
    "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Th", "U", "Np", "Pu",
}


def classify(composition: Composition) -> str | None:
    """Classify a hydrogen-containing material."""

    elements = {str(el) for el in composition.elements}

    if "H" not in elements:
        return None

    non_h = elements - {"H"}

    if not non_h:
        return None

    # Hydrure métallique :
    # H + au moins un élément métallique, sans N/B/C/O/F/S/P/halogènes
    # servant de matrice complexe.
    if non_h & METALS:
        light_complex_elements = {
            "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"
        }

        if not (non_h & light_complex_elements):
            return "metal_hydride"

        # Composés métal + H + ligand léger :
        # classés comme complexes plutôt que hydrures simples.
        return "complex"

    # Complexes d'hydrures / composés hydrogénés sans métal.
    if non_h & {"B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"}:
        return "complex"

    return None


def ensure_dirs() -> None:
    HYDRIDES_CIF.mkdir(parents=True, exist_ok=True)
    COMPLEXES_CIF.mkdir(parents=True, exist_ok=True)


def existing_ids(directory: Path) -> set[str]:
    result = set()

    for path in directory.glob("*.cif"):
        stem = path.name.split("_", 1)[0]
        if stem.startswith("mp-"):
            result.add(stem)

    return result


def metadata_writer(path: Path, rows: list[dict]) -> None:
    fields = [
        "material_id",
        "formula",
        "classification",
        "n_sites",
        "elements",
        "cif_path",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_dirs()

    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        raise SystemExit("ERREUR : MP_API_KEY absente")

    print("=" * 80)
    print(" HydroMatAI — IMPORT PILOTE HYDRURES & COMPLEXES")
    print("=" * 80)
    print()
    print(f"LIMIT : {LIMIT}")
    print("QE    : NON LANCÉ")
    print()

    existing_h = existing_ids(HYDRIDES_CIF)
    existing_c = existing_ids(COMPLEXES_CIF)

    print("===== ÉTAT INITIAL =====")
    print(f"Hydrures existants : {len(existing_h):,}")
    print(f"Complexes existants : {len(existing_c):,}")
    print()

    rows_h = []
    rows_c = []

    seen = set()

    stats = {
        "retrieved": 0,
        "hydrides": 0,
        "complexes": 0,
        "ignored": 0,
        "duplicates": 0,
        "invalid": 0,
        "cif_written": 0,
    }

    with MPRester(api_key) as mpr:
        print("===== RÉCUPÉRATION MATERIALS PROJECT =====")

        docs = mpr.materials.summary.search(
            elements=["H"],
            num_chunks=1,
            chunk_size=LIMIT,
        )

        stats["retrieved"] = len(docs)

        print(f"Structures récupérées : {len(docs):,}")
        print()

        for i, doc in enumerate(docs, 1):
            material_id = str(doc.material_id)

            if material_id in seen:
                stats["duplicates"] += 1
                continue

            seen.add(material_id)

            formula = doc.formula_pretty or getattr(doc, "formula", None)

            if not formula:
                stats["invalid"] += 1
                continue

            try:
                composition = Composition(formula)
                classification = classify(composition)

                if classification is None:
                    stats["ignored"] += 1
                    continue

                structure = mpr.get_structure_by_material_id(material_id)

                if structure is None:
                    stats["invalid"] += 1
                    continue

                # Validation pymatgen.
                structure = Structure.from_dict(structure.as_dict())

            except Exception:
                stats["invalid"] += 1
                continue

            elements = sorted(
                {str(el) for el in structure.composition.elements}
            )

            if classification == "metal_hydride":
                target_dir = HYDRIDES_CIF
                existing = existing_h
                rows = rows_h
                stats["hydrides"] += 1
            else:
                target_dir = COMPLEXES_CIF
                existing = existing_c
                rows = rows_c
                stats["complexes"] += 1

            if material_id in existing:
                stats["duplicates"] += 1
                continue

            filename = f"{material_id}_{formula.replace('/', '-')}.cif"
            cif_path = target_dir / filename

            try:
                structure.to(filename=str(cif_path), fmt="cif")
            except Exception:
                stats["invalid"] += 1
                continue

            rows.append(
                {
                    "material_id": material_id,
                    "formula": formula,
                    "classification": classification,
                    "n_sites": len(structure),
                    "elements": ",".join(elements),
                    "cif_path": str(cif_path),
                }
            )

            stats["cif_written"] += 1

            if i % 100 == 0:
                print(
                    f"vus={i:,} | "
                    f"hydrures={stats['hydrides']:,} | "
                    f"complexes={stats['complexes']:,} | "
                    f"ignorés={stats['ignored']:,}"
                )

    metadata_writer(HYDRIDES_META, rows_h)
    metadata_writer(COMPLEXES_META, rows_c)

    summary = {
        "source": "Materials Project",
        "limit": LIMIT,
        "retrieved": stats["retrieved"],
        "hydrides": stats["hydrides"],
        "complexes": stats["complexes"],
        "ignored": stats["ignored"],
        "duplicates": stats["duplicates"],
        "invalid": stats["invalid"],
        "cif_written": stats["cif_written"],
        "qe_launched": False,
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(" IMPORT PILOTE TERMINÉ")
    print("=" * 80)
    print(f"Structures MP récupérées : {stats['retrieved']:,}")
    print(f"Hydrures métalliques     : {stats['hydrides']:,}")
    print(f"Complexes                : {stats['complexes']:,}")
    print(f"Ignorés                  : {stats['ignored']:,}")
    print(f"Doublons                 : {stats['duplicates']:,}")
    print(f"Invalides                : {stats['invalid']:,}")
    print(f"CIF écrits               : {stats['cif_written']:,}")
    print()
    print(f"Hydrures CIF : {HYDRIDES_CIF}")
    print(f"Complexes CIF: {COMPLEXES_CIF}")
    print(f"Hydrures CSV : {HYDRIDES_META}")
    print(f"Complexes CSV: {COMPLEXES_META}")
    print(f"Résumé       : {SUMMARY}")
    print()
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
