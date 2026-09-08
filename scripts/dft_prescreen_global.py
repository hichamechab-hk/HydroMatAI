#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — DFT GLOBAL SCREENING
=================================

Pipeline unique :

    TOP200_GLOBAL_H2_RANKED.csv
                |
                v
        lecture des CIF
                |
                v
      structure primitive
                |
                v
    contrôle taille / éléments
                |
                v
    contrôle pseudopotentiels
                |
                v
          TOP20 DFT
                |
                v
        génération QE
                |
                v
          pw.scf.in

IMPORTANT
---------
- Aucun calcul QE n'est lancé.
- Aucun CIF original n'est modifié.
- Les pseudopotentiels sont copiés dans le dossier TOP20.
"""



import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

from pymatgen.core import Structure


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT = Path("/home/hk/HydroMatAI")

REPORT_DIR = PROJECT / "reports" / "global_screening"

INPUT = REPORT_DIR / "TOP200_GLOBAL_H2_RANKED.csv"
OUTPUT = REPORT_DIR / "TOP20_DFT_GLOBAL.csv"

QE_DIR = PROJECT / "calculations" / "global_screening" / "qe" / "TOP20"

PSEUDO_DIR = QE_DIR / "pseudo"

# ---------------------------------------------------------------------------
# LIMITES
# ---------------------------------------------------------------------------

MIN_PRIMITIVE_ATOMS = 2

# Ancienne limite : 300
# Nouvelle limite : 500
MAX_PRIMITIVE_ATOMS = 500

TOP_N = 20


# ============================================================================
# PSEUDOPOTENTIELS
# ============================================================================

# Les fichiers réellement présents dans ton projet.
PSEUDO_MAP = {
    "C": "C.pbe-n-kjpaw_psl.0.1.UPF",
    "H": "H.pbe-kjpaw.UPF",
    "N": "N.UPF",
    "O": "O.pbe-kjpaw.UPF",
    "Cu": "Cu.pbe-kjpaw.UPF",
}


# ============================================================================
# OUTILS
# ============================================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def normalize_element(symbol: str) -> str:
    symbol = str(symbol).strip()

    if not symbol:
        return ""

    return symbol[0].upper() + symbol[1:].lower()


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=999999):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# ============================================================================
# PSEUDOPOTENTIELS
# ============================================================================

def verify_pseudopotentials():
    """
    Vérifie les pseudopotentiels explicitement utilisés par le protocole.
    """

    print()
    print("=" * 80)
    print(" PSEUDOPOTENTIELS QE")
    print("=" * 80)

    PSEUDO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    missing = []
    available = []

    for element, filename in PSEUDO_MAP.items():

        source = PROJECT / "calculations" / "global_screening" / "qe" / "TOP20" / "pseudo" / filename

        # Cas normal : déjà dans TOP20/pseudo
        if not source.exists():

            # Recherche dans les emplacements connus
            candidates = [
                PROJECT / "results" / "scientific_runs" / "hMOF-22381" / "pseudo" / filename,
                Path("/home/hk/software/qe-7.5/pseudo") / filename,
            ]

            for candidate in candidates:
                if candidate.exists():
                    source = candidate
                    break

        if not source.exists():
            print(f"MANQUE : {element:3s} -> {filename}")
            missing.append(element)
            continue

        destination = PSEUDO_DIR / filename

        if source.resolve() != destination.resolve():

            shutil.copy2(
                source,
                destination,
            )

        available.append(element)

        print(
            f"OK     : {element:3s} -> "
            f"{destination}"
        )

    print()
    print(
        f"Pseudopotentiels disponibles : "
        f"{len(available)}/{len(PSEUDO_MAP)}"
    )

    if missing:

        print(
            "Pseudopotentiels manquants : "
            + ", ".join(missing)
        )

    return set(available), missing


# ============================================================================
# LECTURE TOP200
# ============================================================================

def load_top200():

    if not INPUT.exists():

        raise FileNotFoundError(
            f"TOP200 introuvable : {INPUT}"
        )

    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


# ============================================================================
# CIF
# ============================================================================

def load_structure(path: Path):

    try:
        return Structure.from_file(path)

    except Exception as exc:

        print(
            f"ATTENTION CIF illisible : "
            f"{path}"
        )

        print(
            f"  {exc}"
        )

        return None


# ============================================================================
# ÉVALUATION
# ============================================================================

def evaluate_structure(
    row,
    pseudo_elements,
):

    cif_value = str(
        row.get("cif", "")
    ).strip()

    cif = Path(cif_value)

    # ------------------------------------------------------------
    # Résolution chemin
    # ------------------------------------------------------------

    if not cif.is_absolute():

        candidates = [
            PROJECT / cif,
            PROJECT / "MOF_Library" / "MOFXDB_FULL" / "cif" / cif.name,
        ]

        for candidate in candidates:

            if candidate.exists():

                cif = candidate
                break

    result = {
        "source": row.get("source", ""),
        "name": row.get("name", ""),
        "material_id": row.get("material_id", ""),
        "formula": row.get("formula", ""),
        "cif": str(cif),

        "h2_score": row.get("h2_score", ""),
        "global_rank": row.get("global_rank", ""),

        "dft_eligible": 0,
        "dft_reason": "",

        "n_atoms_cif": "",
        "n_atoms_primitive": "",

        "primitive_reduction_percent": "",

        "elements": "",
        "missing_pseudopotentials": "",

        "cif_sha256": "",
    }

    # ------------------------------------------------------------
    # CIF absent
    # ------------------------------------------------------------

    if not cif.exists():

        result["dft_reason"] = "CIF_ABSENT"

        return result

    # ------------------------------------------------------------
    # SHA256
    # ------------------------------------------------------------

    try:

        result["cif_sha256"] = sha256_file(cif)

    except Exception:

        result["dft_reason"] = "CIF_READ_ERROR"

        return result

    # ------------------------------------------------------------
    # Lecture CIF
    # ------------------------------------------------------------

    structure = load_structure(cif)

    if structure is None:

        result["dft_reason"] = "CIF_PARSE_ERROR"

        return result

    # ------------------------------------------------------------
    # Nombre d'atomes CIF
    # ------------------------------------------------------------

    n_atoms_cif = len(structure)

    result["n_atoms_cif"] = n_atoms_cif

    # ------------------------------------------------------------
    # Primitive
    # ------------------------------------------------------------

    try:

        primitive = structure.get_primitive_structure()

    except Exception:

        result["dft_reason"] = (
            "PRIMITIVE_CONVERSION_ERROR"
        )

        return result

    if primitive is None:

        result["dft_reason"] = (
            "PRIMITIVE_CONVERSION_FAILED"
        )

        return result

    n_atoms_primitive = len(primitive)

    result["n_atoms_primitive"] = (
        n_atoms_primitive
    )

    # ------------------------------------------------------------
    # Réduction
    # ------------------------------------------------------------

    if n_atoms_cif > 0:

        reduction = (
            1.0
            - (
                n_atoms_primitive
                / n_atoms_cif
            )
        ) * 100.0

        result[
            "primitive_reduction_percent"
        ] = round(
            reduction,
            2,
        )

    # ------------------------------------------------------------
    # Éléments
    # ------------------------------------------------------------

    elements = sorted(
        {
            normalize_element(
                site.specie.symbol
            )
            for site in primitive.sites
        }
    )

    result["elements"] = ",".join(
        elements
    )

    # ------------------------------------------------------------
    # Taille minimale
    # ------------------------------------------------------------

    if (
        n_atoms_primitive
        < MIN_PRIMITIVE_ATOMS
    ):

        result["dft_reason"] = (
            "TOO_FEW_PRIMITIVE_ATOMS"
        )

        return result

    # ------------------------------------------------------------
    # Taille maximale
    # ------------------------------------------------------------

    if (
        n_atoms_primitive
        > MAX_PRIMITIVE_ATOMS
    ):

        result["dft_reason"] = (
            "TOO_MANY_PRIMITIVE_ATOMS"
        )

        return result

    # ------------------------------------------------------------
    # Pseudopotentiels
    # ------------------------------------------------------------

    missing = sorted(
        element
        for element in elements
        if element not in pseudo_elements
    )

    result[
        "missing_pseudopotentials"
    ] = ",".join(missing)

    if missing:

        result["dft_reason"] = (
            "MISSING_PSEUDOPOTENTIAL"
        )

        return result

    # ------------------------------------------------------------
    # Éligible
    # ------------------------------------------------------------

    result["dft_eligible"] = 1
    result["dft_reason"] = "OK"

    return result


# ============================================================================
# SCORE DFT
# ============================================================================

def dft_score(row):

    h2 = safe_float(
        row.get("h2_score"),
        0.0,
    )

    global_rank = safe_int(
        row.get("global_rank"),
        999999,
    )

    primitive = safe_int(
        row.get("n_atoms_primitive"),
        999999,
    )

    # Priorité :
    # 1. score H2 élevé
    # 2. structure plus petite
    # 3. meilleur rang global

    size_penalty = primitive / 1000.0

    rank_penalty = global_rank / 100000.0

    return (
        h2
        - size_penalty
        - rank_penalty
    )


# ============================================================================
# ÉCRITURE CSV
# ============================================================================

def write_csv(rows):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "dft_rank",
        "source",
        "name",
        "material_id",
        "formula",
        "cif",

        "global_rank",
        "h2_score",

        "dft_score",

        "n_atoms_cif",
        "n_atoms_primitive",
        "primitive_reduction_percent",

        "elements",
        "missing_pseudopotentials",

        "dft_eligible",
        "dft_reason",

        "cif_sha256",
    ]

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        for index, row in enumerate(
            rows,
            start=1,
        ):

            output_row = dict(row)

            output_row[
                "dft_rank"
            ] = index

            writer.writerow(
                output_row
            )


# ============================================================================
# GÉNÉRATION QE
# ============================================================================

def generate_qe_input(
    row,
    rank,
):

    name = (
        row.get("name")
        or f"candidate_{rank:04d}"
    )

    # Nettoyage nom dossier
    safe_name = "".join(
        c
        if c.isalnum()
        or c in "-_."
        else "_"
        for c in name
    )

    safe_name = safe_name[
        :100
    ]

    job_dir = (
        QE_DIR
        / f"{rank:04d}_{safe_name}"
    )

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    cif = Path(
        row["cif"]
    )

    structure = Structure.from_file(
        cif
    )

    primitive = (
        structure
        .get_primitive_structure()
    )

    elements = sorted(
        {
            normalize_element(
                site.specie.symbol
            )
            for site in primitive.sites
        }
    )

    # ------------------------------------------------------------
    # Cellule
    # ------------------------------------------------------------

    lattice = primitive.lattice

    a = lattice.matrix

    cell_parameters = [
        a[0],
        a[1],
        a[2],
    ]

    # ------------------------------------------------------------
    # Atomic positions
    # ------------------------------------------------------------

    atomic_positions = []

    for site in primitive.sites:

        element = normalize_element(
            site.specie.symbol
        )

        x, y, z = site.frac_coords

        atomic_positions.append(
            (
                element,
                x,
                y,
                z,
            )
        )

    # ------------------------------------------------------------
    # Input QE
    # ------------------------------------------------------------

    lines = []

    lines.append(
        "&CONTROL"
    )

    lines.append(
        "  calculation = 'scf',"
    )

    lines.append(
        "  restart_mode = 'from_scratch',"
    )

    lines.append(
        "  prefix = 'hydromatai',"
    )

    lines.append(
        f"  pseudo_dir = '{PSEUDO_DIR}',"
    )

    lines.append(
        "  outdir = './tmp',"
    )

    lines.append(
        "  verbosity = 'high',"
    )

    lines.append(
        "  tprnfor = .true.,"
    )

    lines.append(
        "  tstress = .true.,"
    )

    lines.append(
        "/"
    )

    lines.append("")

    lines.append(
        "&SYSTEM"
    )

    lines.append(
        "  ibrav = 0,"
    )

    lines.append(
        f"  nat = {len(primitive)},"
    )

    lines.append(
        f"  ntyp = {len(elements)},"
    )

    lines.append(
        "  ecutwfc = 60.0,"
    )

    lines.append(
        "  ecutrho = 480.0,"
    )

    lines.append(
        "  occupations = 'fixed',"
    )

    lines.append(
        "  input_dft = 'PBE',"
    )

    lines.append(
        "/"
    )

    lines.append("")

    lines.append(
        "&ELECTRONS"
    )

    lines.append(
        "  conv_thr = 1.0d-8,"
    )

    lines.append(
        "  electron_maxstep = 200,"
    )

    lines.append(
        "  mixing_beta = 0.30,"
    )

    lines.append(
        "/"
    )

    lines.append("")

    # ------------------------------------------------------------
    # ATOMIC SPECIES
    # ------------------------------------------------------------

    masses = {
        "H": 1.00794,
        "C": 12.0107,
        "N": 14.0067,
        "O": 15.9994,
        "Cu": 63.546,
    }

    lines.append(
        "ATOMIC_SPECIES"
    )

    for element in elements:

        mass = masses.get(
            element,
            1.0,
        )

        pseudo = PSEUDO_MAP[
            element
        ]

        lines.append(
            f"{element:<3s} "
            f"{mass:.6f} "
            f"{pseudo}"
        )

    lines.append("")

    # ------------------------------------------------------------
    # CELL_PARAMETERS
    # ------------------------------------------------------------

    lines.append(
        "CELL_PARAMETERS angstrom"
    )

    for vector in cell_parameters:

        lines.append(
            "  "
            + " ".join(
                f"{value:.12f}"
                for value in vector
            )
        )

    lines.append("")

    # ------------------------------------------------------------
    # ATOMIC POSITIONS
    # ------------------------------------------------------------

    lines.append(
        "ATOMIC_POSITIONS crystal"
    )

    for (
        element,
        x,
        y,
        z,
    ) in atomic_positions:

        lines.append(
            f"{element:<3s} "
            f"{x:.12f} "
            f"{y:.12f} "
            f"{z:.12f}"
        )

    lines.append("")

    # ------------------------------------------------------------
    # K_POINTS
    # ------------------------------------------------------------

    lines.append(
        "K_POINTS gamma"
    )

    lines.append("")

    input_file = (
        job_dir
        / "pw.scf.in"
    )

    input_file.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Copie CIF
    # ------------------------------------------------------------

    shutil.copy2(
        cif,
        job_dir / cif.name,
    )

    return input_file


# ============================================================================
# MANIFEST
# ============================================================================

def write_manifest(
    selected,
):

    manifest = {
        "protocol": {
            "max_primitive_atoms":
                MAX_PRIMITIVE_ATOMS,
            "min_primitive_atoms":
                MIN_PRIMITIVE_ATOMS,
            "top_n": TOP_N,
            "ecutwfc": 60.0,
            "ecutrho": 480.0,
            "functional": "PBE",
            "qe_executed": False,
        },

        "pseudo_dir": str(
            PSEUDO_DIR
        ),

        "candidates": [],
    }

    for index, row in enumerate(
        selected,
        start=1,
    ):

        manifest[
            "candidates"
        ].append(
            {
                "rank": index,
                "name": row.get(
                    "name",
                    "",
                ),
                "material_id": row.get(
                    "material_id",
                    "",
                ),
                "cif": row.get(
                    "cif",
                    "",
                ),
                "n_atoms_primitive":
                    row.get(
                        "n_atoms_primitive",
                        "",
                    ),
                "dft_score":
                    row.get(
                        "dft_score",
                        "",
                    ),
            }
        )

    manifest_path = (
        QE_DIR
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print(" HydroMatAI — DFT PRE-SCREENING GLOBAL")
    print("=" * 80)

    print()
    print(
        f"Lecture : {INPUT}"
    )

    # ------------------------------------------------------------
    # Pseudopotentiels
    # ------------------------------------------------------------

    pseudo_elements, missing_pseudo = (
        verify_pseudopotentials()
    )

    # ------------------------------------------------------------
    # TOP200
    # ------------------------------------------------------------

    rows = load_top200()

    print()
    print(
        f"Candidats reçus : {len(rows)}"
    )

    # ------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------

    results = []

    exclusion_count = {}

    print()
    print(
        "Analyse des structures..."
    )

    for index, row in enumerate(
        rows,
        start=1,
    ):

        result = evaluate_structure(
            row,
            pseudo_elements,
        )

        results.append(
            result
        )

        reason = result[
            "dft_reason"
        ]

        if reason != "OK":

            exclusion_count[
                reason
            ] = (
                exclusion_count.get(
                    reason,
                    0,
                )
                + 1
            )

        if (
            index % 25 == 0
            or index == len(rows)
        ):

            print(
                f"{index:5d}/{len(rows)} "
                "structures analysées"
            )

    # ------------------------------------------------------------
    # Éligibles
    # ------------------------------------------------------------

    eligible = [
        row
        for row in results
        if row[
            "dft_eligible"
        ] == 1
    ]

    # ------------------------------------------------------------
    # Score
    # ------------------------------------------------------------

    for row in eligible:

        row[
            "dft_score"
        ] = round(
            dft_score(row),
            8,
        )

    eligible.sort(
        key=lambda row: (
            -safe_float(
                row.get(
                    "dft_score"
                ),
                -999999,
            ),
            safe_int(
                row.get(
                    "n_atoms_primitive"
                ),
                999999,
            ),
        )
    )

    selected = eligible[
        :TOP_N
    ]

    # ------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------

    write_csv(
        selected
    )

    # ------------------------------------------------------------
    # QE
    # ------------------------------------------------------------

    generated_inputs = []

    for index, row in enumerate(
        selected,
        start=1,
    ):

        try:

            input_file = (
                generate_qe_input(
                    row,
                    index,
                )
            )

            generated_inputs.append(
                str(input_file)
            )

        except Exception as exc:

            print()
            print(
                "ERREUR génération QE :"
            )

            print(
                f"  {row.get('name', '')}"
            )

            print(
                f"  {exc}"
            )

    write_manifest(
        selected
    )

    # ------------------------------------------------------------
    # Résultats
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print(" RÉSULTATS DU PRÉ-SCREENING DFT")
    print("=" * 80)

    print(
        f"Structures analysées : "
        f"{len(rows)}"
    )

    print(
        f"Éligibles DFT        : "
        f"{len(eligible)}"
    )

    print(
        f"Exclues               : "
        f"{len(rows) - len(eligible)}"
    )

    print(
        f"TOP 20 retenues       : "
        f"{len(selected)}"
    )

    print()
    print("EXCLUSIONS")
    print("-" * 80)

    if exclusion_count:

        for reason, count in sorted(
            exclusion_count.items(),
            key=lambda item: -item[1],
        ):

            print(
                f"{reason:<35s} : "
                f"{count:4d}"
            )

    else:

        print(
            "Aucune exclusion."
        )

    # ------------------------------------------------------------
    # TOP20
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print(" TOP 20 DFT GLOBAL")
    print("=" * 80)

    if not selected:

        print(
            "Aucune structure éligible."
        )

    else:

        print(
            f"{'Rang':<6}"
            f"{'Nom':<28}"
            f"{'Prim':<8}"
            f"{'Éléments':<20}"
            f"{'Score':<12}"
        )

        print(
            "-" * 80
        )

        for index, row in enumerate(
            selected,
            start=1,
        ):

            print(
                f"{index:<6}"
                f"{row.get('name', '')[:27]:<28}"
                f"{str(row.get('n_atoms_primitive', '')):<8}"
                f"{row.get('elements', '')[:19]:<20}"
                f"{str(row.get('dft_score', '')):<12}"
            )

    # ------------------------------------------------------------
    # Fichiers
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print(" FICHIERS")
    print("=" * 80)

    print(
        f"TOP20 DFT : {OUTPUT}"
    )

    print(
        f"QE DIR    : {QE_DIR}"
    )

    print(
        f"PSEUDO    : {PSEUDO_DIR}"
    )

    print(
        f"Inputs QE générés : "
        f"{len(generated_inputs)}"
    )

    print()
    print(
        "QE : NON LANCÉ"
    )

    print(
        "Le script prépare uniquement "
        "les inputs pw.scf.in."
    )

    print("=" * 80)


if __name__ == "__main__":
    main()

