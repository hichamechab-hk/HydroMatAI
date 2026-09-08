#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from mp_api.client import MPRester
from pymatgen.core import Structure


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT = Path("MOF_Library")

HYDRIDE_ROOT = ROOT / "METAL_HYDRIDES"
COMPLEX_ROOT = ROOT / "COMPLEXES"

HYDRIDE_CIF = HYDRIDE_ROOT / "cif"
COMPLEX_CIF = COMPLEX_ROOT / "cif"

HYDRIDE_METADATA = HYDRIDE_ROOT / "metadata.csv"
COMPLEX_METADATA = COMPLEX_ROOT / "metadata.csv"

SUMMARY_FILE = ROOT / "materials_project_full_import_summary.json"

CHUNK_SIZE = 1000

# Aucun calcul QE dans ce script.
QE_ENABLED = False


# ============================================================================
# OUTILS
# ============================================================================

def safe_filename(text: str) -> str:
    text = str(text)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return text[:180]


def structure_fingerprint(structure: Structure) -> str:
    """
    Empreinte déterministe de la structure.

    Elle tient compte :
      - du réseau
      - des espèces
      - des coordonnées fractionnelles

    Les valeurs sont arrondies afin d'éviter les différences numériques
    insignifiantes entre structures MP.
    """
    s = structure.copy()

    try:
        s = s.get_primitive_structure()
    except Exception:
        pass

    try:
        s = s.get_sorted_structure()
    except Exception:
        pass

    lattice = s.lattice.matrix

    parts = []

    for row in lattice:
        parts.append(
            ",".join(f"{float(x):.5f}" for x in row)
        )

    for site in s:
        frac = site.frac_coords
        species = str(site.species_string)

        parts.append(
            f"{species}:"
            f"{float(frac[0]) % 1:.5f},"
            f"{float(frac[1]) % 1:.5f},"
            f"{float(frac[2]) % 1:.5f}"
        )

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def contains_metal(elements: set[str]) -> bool:
    """
    Classification simple et robuste pour le screening.

    Métaux courants rencontrés dans les hydrures :
    alcalins, alcalino-terreux, métaux de transition,
    lanthanides, actinides et quelques métaux post-transition.
    """
    metals = {
        "Li", "Be", "Na", "Mg", "Al", "K", "Ca", "Sc", "Ti",
        "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga",
        "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh",
        "Pd", "Ag", "Cd", "In", "Sn", "Cs", "Ba", "La", "Ce",
        "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
        "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os",
        "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Fr", "Ra",
        "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk",
        "Cf", "Es", "Fm", "Md", "No", "Lr"
    }

    return bool(elements & metals)


def classify_structure(structure: Structure) -> str:
    """
    Catégories HydroMatAI :

      METAL_HYDRIDES :
          H + au moins un élément métallique

      COMPLEXES :
          toutes les autres structures contenant H
    """
    elements = {str(el) for el in structure.composition.elements}

    if "H" not in elements:
        return "IGNORE"

    if contains_metal(elements):
        return "METAL_HYDRIDES"

    return "COMPLEXES"


def metadata_row(doc, structure: Structure, category: str, fingerprint: str):
    material_id = str(doc.material_id)

    formula = getattr(doc, "formula_pretty", None)

    if not formula:
        formula = structure.composition.reduced_formula

    elements = ",".join(
        sorted(str(el) for el in structure.composition.elements)
    )

    symmetry = getattr(doc, "symmetry", None)

    spacegroup = None
    if symmetry is not None:
        spacegroup = getattr(symmetry, "symbol", None)

    return {
        "material_id": material_id,
        "formula": formula,
        "category": category,
        "elements": elements,
        "nsites": len(structure),
        "volume_A3": getattr(doc, "volume", None),
        "density_g_cm3": getattr(doc, "density", None),
        "spacegroup": spacegroup,
        "structure_fingerprint": fingerprint,
    }


def load_existing_index():
    """
    Indexe les CIF déjà présents.

    L'objectif est de permettre la reprise :
    un CIF déjà présent n'est jamais réécrit inutilement.
    """

    fingerprints = {}
    material_ids = set()

    for directory in (HYDRIDE_CIF, COMPLEX_CIF):
        if not directory.exists():
            continue

        for cif_path in directory.glob("*.cif"):

            match = re.match(r"^mp-(\d+)_", cif_path.name)

            if match:
                material_ids.add(f"mp-{match.group(1)}")

            try:
                structure = Structure.from_file(cif_path)
                fp = structure_fingerprint(structure)
                fingerprints[fp] = str(cif_path)

            except Exception:
                # Le contrôle complet des CIF est effectué séparément.
                continue

    return fingerprints, material_ids


def write_metadata(path: Path, rows: list[dict]):
    if not rows:
        return

    fieldnames = [
        "material_id",
        "formula",
        "category",
        "elements",
        "nsites",
        "volume_A3",
        "density_g_cm3",
        "spacegroup",
        "structure_fingerprint",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print(" HydroMatAI — IMPORT COMPLET MATERIALS PROJECT")
    print("=" * 80)

    # ----------------------------------------------------------------------
    # Vérification API
    # ----------------------------------------------------------------------

    api_key = os.environ.get("MP_API_KEY")

    if not api_key:
        print()
        print("ERREUR : MP_API_KEY absente.")
        print()
        print("Configure la clé dans cette session avec :")
        print("export MP_API_KEY='TA_CLE_MATERIALS_PROJECT'")
        print()
        sys.exit(1)

    print()
    print("===== CONFIGURATION =====")
    print(f"Hydrures CIF : {HYDRIDE_CIF}")
    print(f"Complexes CIF: {COMPLEX_CIF}")
    print(f"Chunk        : {CHUNK_SIZE}")
    print("QE           : NON LANCÉ")
    print()

    HYDRIDE_CIF.mkdir(parents=True, exist_ok=True)
    COMPLEX_CIF.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------------
    # Index existant
    # ----------------------------------------------------------------------

    print("===== INDEXATION EXISTANT =====")

    existing_fingerprints, existing_ids = load_existing_index()

    print(
        f"Empreintes existantes : "
        f"{len(existing_fingerprints):,}"
    )

    print(
        f"Material IDs existants : "
        f"{len(existing_ids):,}"
    )

    # ----------------------------------------------------------------------
    # Compteurs
    # ----------------------------------------------------------------------

    counters = Counter()

    hydride_rows = []
    complex_rows = []

    global_fingerprints = dict(existing_fingerprints)

    # ----------------------------------------------------------------------
    # Materials Project
    # ----------------------------------------------------------------------

    print()
    print("===== CONNEXION MATERIALS PROJECT =====")

    with MPRester(api_key) as mpr:

        print("Connexion : OK")
        print()
        print("===== RECHERCHE DE TOUTES LES STRUCTURES CONTENANT H =====")
        print("La récupération complète peut prendre du temps.")
        print("")

        fields = [
            "material_id",
            "formula_pretty",
            "structure",
            "elements",
            "volume",
            "density",
            "symmetry",
        ]

        # ------------------------------------------------------------------
        # IMPORT COMPLET
        # ------------------------------------------------------------------

        documents = mpr.materials.summary.search(
            elements=["H"],
            fields=fields,
            chunk_size=CHUNK_SIZE,
        )

        total = len(documents)

        print(f"Structures MP récupérées : {total:,}")
        print()

        for index, doc in enumerate(documents, start=1):

            counters["vus"] += 1

            material_id = str(doc.material_id)

            if material_id in existing_ids:
                counters["existants"] += 1
                continue

            structure = getattr(doc, "structure", None)

            if structure is None:
                counters["invalides"] += 1
                continue

            try:
                category = classify_structure(structure)

            except Exception:
                counters["invalides"] += 1
                continue

            if category == "IGNORE":
                counters["ignores"] += 1
                continue

            try:
                fingerprint = structure_fingerprint(structure)

            except Exception:
                counters["invalides"] += 1
                continue

            # --------------------------------------------------------------
            # Déduplication globale
            # --------------------------------------------------------------

            if fingerprint in global_fingerprints:
                counters["doublons"] += 1
                continue

            # --------------------------------------------------------------
            # Nom CIF
            # --------------------------------------------------------------

            formula = getattr(doc, "formula_pretty", None)

            if not formula:
                formula = structure.composition.reduced_formula

            filename = (
                f"{material_id}_"
                f"{safe_filename(formula)}.cif"
            )

            if category == "METAL_HYDRIDES":
                destination = HYDRIDE_CIF / filename
            else:
                destination = COMPLEX_CIF / filename

            # Collision de nom improbable mais gérée.
            if destination.exists():
                destination = (
                    destination.parent
                    / f"{material_id}_{safe_filename(formula)}_mp.cif"
                )

            try:
                structure.to(filename=destination)
            except Exception:
                counters["erreurs"] += 1
                continue

            # --------------------------------------------------------------
            # Index
            # --------------------------------------------------------------

            global_fingerprints[fingerprint] = str(destination)

            existing_ids.add(material_id)

            row = metadata_row(
                doc,
                structure,
                category,
                fingerprint,
            )

            if category == "METAL_HYDRIDES":
                hydride_rows.append(row)
                counters["hydrures_nouveaux"] += 1

            else:
                complex_rows.append(row)
                counters["complexes_nouveaux"] += 1

            counters["nouveaux"] += 1

            # --------------------------------------------------------------
            # Progression
            # --------------------------------------------------------------

            if counters["vus"] % 1000 == 0:
                print(
                    f"vus={counters['vus']:,} "
                    f"nouveaux={counters['nouveaux']:,} "
                    f"existants={counters['existants']:,} "
                    f"doublons={counters['doublons']:,} "
                    f"erreurs={counters['erreurs']:,}"
                )

    # ----------------------------------------------------------------------
    # Sauvegarde metadata
    # ----------------------------------------------------------------------

    print()
    print("===== SAUVEGARDE METADONNEES =====")

    # Pour ne pas perdre les métadonnées précédentes, on reconstruit
    # les fichiers à partir des CIF réellement présents si nécessaire.
    #
    # Ici on ajoute les nouvelles lignes au fichier existant.

    def append_rows(path: Path, rows: list[dict]):

        if not rows:
            return

        fieldnames = [
            "material_id",
            "formula",
            "category",
            "elements",
            "nsites",
            "volume_A3",
            "density_g_cm3",
            "spacegroup",
            "structure_fingerprint",
        ]

        path.parent.mkdir(parents=True, exist_ok=True)

        exists = path.exists()

        with path.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )

            if not exists:
                writer.writeheader()

            writer.writerows(rows)

    append_rows(HYDRIDE_METADATA, hydride_rows)
    append_rows(COMPLEX_METADATA, complex_rows)

    # ----------------------------------------------------------------------
    # Comptage final CIF
    # ----------------------------------------------------------------------

    hydride_count = len(list(HYDRIDE_CIF.glob("*.cif")))
    complex_count = len(list(COMPLEX_CIF.glob("*.cif")))

    total_cif = hydride_count + complex_count

    # ----------------------------------------------------------------------
    # Résumé
    # ----------------------------------------------------------------------

    summary = {
        "source": "Materials Project",
        "query": "all structures containing H",
        "qe_launched": False,
        "statistics": {
            "structures_vues": counters["vus"],
            "nouveaux": counters["nouveaux"],
            "existants": counters["existants"],
            "doublons": counters["doublons"],
            "invalides": counters["invalides"],
            "ignores": counters["ignores"],
            "erreurs": counters["erreurs"],
            "hydrures_nouveaux": counters["hydrures_nouveaux"],
            "complexes_nouveaux": counters["complexes_nouveaux"],
            "hydrures_cif_total": hydride_count,
            "complexes_cif_total": complex_count,
            "cif_total": total_cif,
        },
        "paths": {
            "hydrides_cif": str(HYDRIDE_CIF),
            "complexes_cif": str(COMPLEX_CIF),
            "hydrides_metadata": str(HYDRIDE_METADATA),
            "complexes_metadata": str(COMPLEX_METADATA),
        },
    }

    SUMMARY_FILE.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ----------------------------------------------------------------------
    # Résultat
    # ----------------------------------------------------------------------

    print()
    print("=" * 80)
    print(" IMPORT MATERIALS PROJECT TERMINÉ")
    print("=" * 80)

    print(
        f" Structures vues       : "
        f"{counters['vus']:,}"
    )

    print(
        f" Nouveaux              : "
        f"{counters['nouveaux']:,}"
    )

    print(
        f" Existants             : "
        f"{counters['existants']:,}"
    )

    print(
        f" Doublons structuraux  : "
        f"{counters['doublons']:,}"
    )

    print(
        f" Hydrures nouveaux     : "
        f"{counters['hydrures_nouveaux']:,}"
    )

    print(
        f" Complexes nouveaux    : "
        f"{counters['complexes_nouveaux']:,}"
    )

    print(
        f" Invalides             : "
        f"{counters['invalides']:,}"
    )

    print(
        f" Erreurs               : "
        f"{counters['erreurs']:,}"
    )

    print()
    print("===== CIF SUR DISQUE =====")

    print(
        f" Hydrures              : "
        f"{hydride_count:,}"
    )

    print(
        f" Complexes             : "
        f"{complex_count:,}"
    )

    print(
        f" TOTAL                 : "
        f"{total_cif:,}"
    )

    print()
    print(f"Hydrures CIF : {HYDRIDE_CIF}")
    print(f"Complexes CIF: {COMPLEX_CIF}")
    print(f"Hydrures CSV : {HYDRIDE_METADATA}")
    print(f"Complexes CSV: {COMPLEX_METADATA}")
    print(f"Résumé       : {SUMMARY_FILE}")

    print()
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()

