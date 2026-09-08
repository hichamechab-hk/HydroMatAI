from __future__ import annotations
import os
os.system("clear")

import csv
import math
import re
import warnings
from pathlib import Path

from pymatgen.core import Structure


# ============================================================================
# HydroMatAI — RANKING GLOBAL H₂ V2
# ============================================================================
#
# Objectif :
#   Classer les candidats H₂ en tenant compte :
#
#   1. du score scientifique existant
#   2. de la taille de la maille primitive
#   3. de la disponibilité des pseudopotentiels QE
#   4. de la faisabilité DFT
#
# Aucun calcul QE n'est lancé.
# ============================================================================


ROOT = Path("MOF_Library")
REPORT = Path("reports/global_screening")

INPUT = REPORT / "global_audit.csv"

OUTPUT_TOP200 = REPORT / "TOP200_GLOBAL_H2_RANKED_V2.csv"
OUTPUT_TOP20 = REPORT / "TOP20_GLOBAL_H2_RANKED_V2.csv"


# ---------------------------------------------------------------------------
# Limites DFT
# ---------------------------------------------------------------------------

MAX_PRIMITIVE_ATOMS = 400

# Au-delà de cette taille, la structure reste éventuellement intéressante
# scientifiquement, mais devient beaucoup plus difficile pour un DFT
# systématique.
SOFT_PRIMITIVE_ATOMS = 150


# ---------------------------------------------------------------------------
# Pseudopotentiels
# ---------------------------------------------------------------------------

PSEUDO_DIRECTORIES = [
    Path("/usr/share/espresso/pseudo"),
    Path("/home/hk/software/qe-7.5/pseudo"),
]


# ============================================================================
# UTILITAIRES
# ============================================================================


def find_pseudopotential_elements() -> set[str]:
    """
    Détecte les éléments disponibles dans les répertoires QE.
    """

    elements: set[str] = set()

    element_re = re.compile(
        r"^([A-Z][a-z]?)"
    )

    for directory in PSEUDO_DIRECTORIES:

        if not directory.exists():
            continue

        for path in directory.iterdir():

            if not path.is_file():
                continue

            match = element_re.match(path.name)

            if match:
                elements.add(match.group(1))

    return elements


def get_float(row: dict, key: str) -> float:
    try:
        value = row.get(key)

        if value in (None, "", "None"):
            return 0.0

        return float(value)

    except (TypeError, ValueError):
        return 0.0


def get_int(row: dict, key: str) -> int:
    try:
        return int(float(row.get(key, 0)))

    except (TypeError, ValueError):
        return 0


# ============================================================================
# SCORE H₂
# ============================================================================


def hydrogen_component(row: dict) -> float:
    """
    Score H₂ déjà calculé par l'audit.

    On utilise hydrogen_score lorsque disponible.
    """

    value = get_float(row, "hydrogen_score")

    if value > 0:
        return min(value, 1.0)

    # Compatibilité avec anciens fichiers.
    value = get_float(row, "score")

    return min(max(value, 0.0), 1.0)


# ============================================================================
# SCORE POROSITÉ
# ============================================================================


def porosity_component(row: dict) -> float:

    values = [
        get_float(row, "void_fraction"),
        get_float(row, "surface_area_m2g"),
        get_float(row, "pld"),
        get_float(row, "lcd"),
    ]

    vf, sa, pld, lcd = values

    if max(values) <= 0:
        return 0.0

    vf_score = min(vf / 0.90, 1.0)
    sa_score = min(sa / 5000.0, 1.0)
    pld_score = min(pld / 20.0, 1.0)
    lcd_score = min(lcd / 20.0, 1.0)

    return (
        0.30 * vf_score
        + 0.30 * sa_score
        + 0.20 * pld_score
        + 0.20 * lcd_score
    )


# ============================================================================
# SCORE TAILLE PRIMITIVE
# ============================================================================


def primitive_size_score(n_atoms: int) -> float:
    """
    Score compris entre 0 et 1.

    <= 50 atomes       : 1.00
    100 atomes         : ~0.85
    150 atomes         : ~0.70
    200 atomes         : ~0.55
    300 atomes         : ~0.25
    400 atomes         : 0
    >400               : 0
    """

    if n_atoms <= 0:
        return 0.0

    if n_atoms <= 50:
        return 1.0

    if n_atoms >= MAX_PRIMITIVE_ATOMS:
        return 0.0

    # décroissance progressive
    score = 1.0 - (
        (n_atoms - 50)
        / (MAX_PRIMITIVE_ATOMS - 50)
    )

    return max(0.0, min(score, 1.0))


# ============================================================================
# ANALYSE STRUCTURE
# ============================================================================


def analyze_structure(
    cif_path: str,
    pseudo_elements: set[str],
) -> dict:

    result = {
        "primitive_atoms": 0,
        "elements": "",
        "missing_pseudopotentials": "",
        "pseudo_ok": 0,
        "structure_ok": 0,
        "error": "",
    }

    try:

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            structure = Structure.from_file(cif_path)

        result["structure_ok"] = 1

        primitive = structure.get_primitive_structure()

        n_atoms = len(primitive)

        result["primitive_atoms"] = n_atoms

        elements = sorted(
            {
                site.specie.symbol
                for site in primitive.sites
            }
        )

        result["elements"] = ",".join(elements)

        missing = [
            element
            for element in elements
            if element not in pseudo_elements
        ]

        result["missing_pseudopotentials"] = ",".join(
            missing
        )

        if not missing:
            result["pseudo_ok"] = 1

    except Exception as exc:

        result["error"] = str(exc)

    return result


# ============================================================================
# SCORE DFT
# ============================================================================


def dft_feasibility_score(
    primitive_atoms: int,
    pseudo_ok: int,
) -> float:

    if not pseudo_ok:
        return 0.0

    size_score = primitive_size_score(
        primitive_atoms
    )

    if primitive_atoms <= 100:
        size_bonus = 1.0

    elif primitive_atoms <= 150:
        size_bonus = 0.90

    elif primitive_atoms <= 200:
        size_bonus = 0.75

    elif primitive_atoms <= 300:
        size_bonus = 0.50

    elif primitive_atoms <= 400:
        size_bonus = 0.20

    else:
        size_bonus = 0.0

    return (
        0.70 * size_score
        + 0.30 * size_bonus
    )


# ============================================================================
# SCORE GLOBAL V2
# ============================================================================


def global_score(
    row: dict,
    primitive_atoms: int,
    pseudo_ok: int,
) -> float:

    h2 = hydrogen_component(row)

    porosity = porosity_component(row)

    dft = dft_feasibility_score(
        primitive_atoms,
        pseudo_ok,
    )

    size = primitive_size_score(
        primitive_atoms
    )

    #
    # Pondération V2
    #
    # H₂          : 40 %
    # Porosité    : 20 %
    # DFT         : 30 %
    # Taille      : 10 %
    #

    score = (
        0.40 * h2
        + 0.20 * porosity
        + 0.30 * dft
        + 0.10 * size
    )

    return round(
        min(max(score, 0.0), 1.0),
        6,
    )


# ============================================================================
# MAIN
# ============================================================================


def main():

    REPORT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print(" HydroMatAI — RANKING GLOBAL H₂ V2")
    print("=" * 80)

    print()
    print(f"Lecture : {INPUT}")

    if not INPUT.exists():

        print()
        print("ERREUR : global_audit.csv absent.")
        return

    # ------------------------------------------------------------------------
    # Pseudopotentiels
    # ------------------------------------------------------------------------

    pseudo_elements = find_pseudopotential_elements()

    print()
    print(
        f"Pseudopotentiels détectés : "
        f"{len(pseudo_elements)} éléments"
    )

    # ------------------------------------------------------------------------
    # Lecture audit
    # ------------------------------------------------------------------------

    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        rows = list(reader)

    # ------------------------------------------------------------------------
    # Candidats
    # ------------------------------------------------------------------------

    candidates = []

    for row in rows:

        try:

            valid = int(
                float(
                    row.get(
                        "valid",
                        0,
                    )
                )
            )

        except (TypeError, ValueError):

            valid = 0

        try:

            screening = int(
                float(
                    row.get(
                        "passes_screening",
                        0,
                    )
                )
            )

        except (TypeError, ValueError):

            screening = 0

        try:

            duplicate = int(
                float(
                    row.get(
                        "duplicate",
                        0,
                    )
                )
            )

        except (TypeError, ValueError):

            duplicate = 0

        if not valid:
            continue

        if not screening:
            continue

        if duplicate:
            continue

        candidates.append(row)

    print()
    print(
        f"Candidats avant classement : "
        f"{len(candidates):,}"
    )

    # ------------------------------------------------------------------------
    # Analyse DFT
    # ------------------------------------------------------------------------

    ranked = []

    total = len(candidates)

    for index, row in enumerate(
        candidates,
        start=1,
    ):

        cif_path = row.get(
            "cif",
            "",
        )

        analysis = analyze_structure(
            cif_path,
            pseudo_elements,
        )

        primitive_atoms = analysis[
            "primitive_atoms"
        ]

        pseudo_ok = analysis[
            "pseudo_ok"
        ]

        score = global_score(
            row,
            primitive_atoms,
            pseudo_ok,
        )

        enriched = dict(row)

        enriched[
            "primitive_atoms"
        ] = primitive_atoms

        enriched[
            "elements"
        ] = analysis["elements"]

        enriched[
            "missing_pseudopotentials"
        ] = analysis[
            "missing_pseudopotentials"
        ]

        enriched[
            "pseudo_ok"
        ] = pseudo_ok

        enriched[
            "structure_ok"
        ] = analysis[
            "structure_ok"
        ]

        enriched[
            "dft_feasibility_score"
        ] = round(
            dft_feasibility_score(
                primitive_atoms,
                pseudo_ok,
            ),
            6,
        )

        enriched[
            "primitive_size_score"
        ] = round(
            primitive_size_score(
                primitive_atoms
            ),
            6,
        )

        enriched[
            "ranking_score_v2"
        ] = score

        enriched[
            "ranking_error"
        ] = analysis[
            "error"
        ]

        ranked.append(enriched)

        if (
            index % 5000 == 0
            or index == total
        ):

            print(
                f"  {index:,}/{total:,} "
                f"structures analysées"
            )

    # ------------------------------------------------------------------------
    # Filtrage DFT réel
    # ------------------------------------------------------------------------

    dft_candidates = [
        row
        for row in ranked
        if (
            row["structure_ok"] == 1
            and row["pseudo_ok"] == 1
            and row["primitive_atoms"] > 0
            and row["primitive_atoms"]
            <= MAX_PRIMITIVE_ATOMS
        )
    ]

    # ------------------------------------------------------------------------
    # Classement
    # ------------------------------------------------------------------------

    dft_candidates.sort(
        key=lambda row: (
            float(
                row[
                    "ranking_score_v2"
                ]
            ),
            float(
                row[
                    "hydrogen_score"
                ]
                if row.get(
                    "hydrogen_score"
                )
                else 0.0
            ),
            -int(
                row[
                    "primitive_atoms"
                ]
            ),
        ),
        reverse=True,
    )

    top200 = dft_candidates[:200]
    top20 = dft_candidates[:20]

    # ------------------------------------------------------------------------
    # Rang
    # ------------------------------------------------------------------------

    for rank, row in enumerate(
        top200,
        start=1,
    ):

        row["rank"] = rank

    # ------------------------------------------------------------------------
    # Colonnes
    # ------------------------------------------------------------------------

    fieldnames = [
        "rank",
        "source",
        "name",
        "material_id",
        "cif",
        "formula",
        "n_atoms",
        "primitive_atoms",
        "elements",
        "hydrogen_wt_percent",
        "hydrogen_score",
        "void_fraction",
        "surface_area_m2g",
        "pld",
        "lcd",
        "score",
        "ranking_score_v2",
        "dft_feasibility_score",
        "primitive_size_score",
        "pseudo_ok",
        "missing_pseudopotentials",
        "valid",
        "duplicate",
        "duplicate_of",
        "passes_screening",
        "error",
        "ranking_error",
    ]

    # ------------------------------------------------------------------------
    # Écriture
    # ------------------------------------------------------------------------

    def write_csv(
        path: Path,
        data,
    ):

        with path.open(
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

            writer.writerows(data)

    write_csv(
        OUTPUT_TOP200,
        top200,
    )

    write_csv(
        OUTPUT_TOP20,
        top20,
    )

    # ------------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------------

    print()
    print("=" * 80)
    print(" RÉSULTATS")
    print("=" * 80)

    print()
    print(
        f"Candidats analysés : "
        f"{len(ranked):,}"
    )

    print(
        f"Éligibles DFT      : "
        f"{len(dft_candidates):,}"
    )

    print(
        f"TOP 200            : "
        f"{len(top200):,}"
    )

    print(
        f"TOP 20             : "
        f"{len(top20):,}"
    )

    # ------------------------------------------------------------------------
    # Répartition source
    # ------------------------------------------------------------------------

    print()
    print("RÉPARTITION TOP 200")
    print("-" * 80)

    source_counts = {}

    for row in top200:

        source = row[
            "source"
        ]

        source_counts[
            source
        ] = (
            source_counts.get(
                source,
                0,
            )
            + 1
        )

    for source, count in sorted(
        source_counts.items()
    ):

        print(
            f"{source:<20} : "
            f"{count:4d}"
        )

    # ------------------------------------------------------------------------
    # TOP 20
    # ------------------------------------------------------------------------

    print()
    print("=" * 80)
    print(" TOP 20 DFT-AWARE GLOBAL H₂")
    print("=" * 80)

    print(
        f"{'Rang':>4} "
        f"{'Source':<18} "
        f"{'Nom':<30} "
        f"{'Prim':>6} "
        f"{'Score':>10}"
    )

    print("-" * 80)

    for row in top20:

        print(
            f"{int(row['rank']):4d} "
            f"{row['source']:<18} "
            f"{row['name']:<30} "
            f"{int(row['primitive_atoms']):6d} "
            f"{float(row['ranking_score_v2']):10.6f}"
        )

    # ------------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------------

    if top200:

        scores = [
            float(
                row[
                    "ranking_score_v2"
                ]
            )
            for row in top200
        ]

        atoms = [
            int(
                row[
                    "primitive_atoms"
                ]
            )
            for row in top200
        ]

        print()
        print("=" * 80)
        print(" STATISTIQUES TOP 200")
        print("=" * 80)

        print(
            f"Score min          : "
            f"{min(scores):.6f}"
        )

        print(
            f"Score max          : "
            f"{max(scores):.6f}"
        )

        print(
            f"Score moyen        : "
            f"{sum(scores) / len(scores):.6f}"
        )

        print(
            f"Atomes primitifs min: "
            f"{min(atoms)}"
        )

        print(
            f"Atomes primitifs max: "
            f"{max(atoms)}"
        )

        print(
            f"Atomes primitifs moy: "
            f"{sum(atoms) / len(atoms):.1f}"
        )

    # ------------------------------------------------------------------------
    # Fichiers
    # ------------------------------------------------------------------------

    print()
    print("=" * 80)
    print(" FICHIERS")
    print("=" * 80)

    print(
        f"TOP200 : {OUTPUT_TOP200}"
    )

    print(
        f"TOP20  : {OUTPUT_TOP20}"
    )

    print()
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
