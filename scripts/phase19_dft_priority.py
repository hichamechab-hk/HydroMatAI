#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")
"""
HydroMatAI — PHASE 19
DFT PRIORITY + SELECTION DES CANDIDATS

Objectifs
---------
1. Charger TOP100_GLOBAL_H2.csv
2. Valider les candidats
3. Exclure les structures invalides
4. Exclure les doublons
5. Calculer un score DFT Priority traçable
6. Classer les candidats :
      PRIORITY
      SECONDARY
      RESERVE
7. Générer :
      reports/global_screening/dft_priority.csv
      reports/global_screening/dft_priority_summary.json
      reports/global_screening/dft_priority_rejected.csv

Protection QE
-------------
Aucun programme Quantum ESPRESSO n'est lancé.
Aucun calcul RELAX / SCF / DOS / BANDS n'est lancé.

PHASE 19 = sélection uniquement.
"""


import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT = Path(".")

REPORT_DIR = ROOT / "reports" / "global_screening"

INPUT_TOP100 = REPORT_DIR / "TOP100_GLOBAL_H2.csv"

OUTPUT_PRIORITY = REPORT_DIR / "dft_priority.csv"
OUTPUT_REJECTED = REPORT_DIR / "dft_priority_rejected.csv"
OUTPUT_SUMMARY = REPORT_DIR / "dft_priority_summary.json"


# Nombre maximal de candidats retenus
MAX_PRIORITY = 25
MAX_SECONDARY = 50
MAX_RESERVE = 25


# ============================================================================
# POIDS DU SCORE
# ============================================================================

# Le score H2 reste dominant.
WEIGHT_H2 = 0.40

# Qualité structurelle / informations disponibles.
WEIGHT_STRUCTURE = 0.20

# Stabilité : utilisée uniquement si une donnée explicite existe.
WEIGHT_STABILITY = 0.20

# Préparation électronique : présence d'informations électroniques.
WEIGHT_ELECTRONIC = 0.10

# Diversité : bonus appliqué après classement.
WEIGHT_DIVERSITY = 0.10


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class Candidate:
    rank_h2: int
    source: str
    name: str
    material_id: str
    formula: str
    cif: str

    valid: bool
    duplicate: bool
    passes_screening: bool

    h2_score: float

    structure_score: float
    stability_score: float
    electronic_score: float
    diversity_score: float

    dft_priority_score: float

    selection_class: str
    selection_reason: str


# ============================================================================
# UTILITAIRES
# ============================================================================


def safe_float(value) -> Optional[float]:
    """Convertit proprement une valeur en float."""
    if value is None:
        return None

    text = str(value).strip()

    if text == "":
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def safe_int(value, default=0) -> int:
    """Convertit proprement une valeur en entier."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_bool(value) -> bool:
    """Interprète 0/1/true/false."""
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {
        "1",
        "true",
        "yes",
        "y",
        "oui",
    }


def clamp(value: float, low=0.0, high=1.0) -> float:
    """Limite une valeur à [low, high]."""
    return max(low, min(value, high))


# ============================================================================
# VALIDATION DU CIF
# ============================================================================


def validate_cif_path(cif_path: str) -> bool:
    """
    Vérifie uniquement la présence du CIF.

    Important :
    aucune lecture lourde de structure ici.
    Aucun calcul QE.
    """
    if not cif_path:
        return False

    return Path(cif_path).exists()


# ============================================================================
# SCORE STRUCTUREL
# ============================================================================


def calculate_structure_score(row: dict) -> float:
    """
    Score structurel.

    Le score utilise uniquement les informations déjà présentes
    dans TOP100_GLOBAL_H2.csv.

    Il ne fabrique aucune donnée scientifique.
    """

    score_components = []

    # Nombre d'atomes
    n_atoms = safe_float(row.get("n_atoms"))

    if n_atoms is not None and n_atoms > 0:
        # Une taille raisonnable est préférable pour les calculs DFT.
        if n_atoms <= 50:
            atom_score = 1.0
        elif n_atoms <= 100:
            atom_score = 0.85
        elif n_atoms <= 150:
            atom_score = 0.70
        elif n_atoms <= 250:
            atom_score = 0.50
        else:
            atom_score = 0.25

        score_components.append(atom_score)

    # Fraction de vide
    vf = safe_float(row.get("void_fraction"))

    if vf is not None:
        score_components.append(
            clamp(vf / 0.90)
        )

    # Surface spécifique
    sa = safe_float(row.get("surface_area_m2g"))

    if sa is not None:
        score_components.append(
            clamp(sa / 5000.0)
        )

    # PLD
    pld = safe_float(row.get("pld"))

    if pld is not None:
        score_components.append(
            clamp(pld / 10.0)
        )

    # LCD
    lcd = safe_float(row.get("lcd"))

    if lcd is not None:
        score_components.append(
            clamp(lcd / 20.0)
        )

    if not score_components:
        # Pour hydrures/complexes sans données poreuses :
        # score neutre, pas de données inventées.
        return 0.50

    return sum(score_components) / len(score_components)


# ============================================================================
# STABILITÉ
# ============================================================================


def calculate_stability_score(row: dict) -> float:
    """
    Score de stabilité.

    Si aucune donnée de stabilité n'est disponible,
    retourne une valeur neutre.

    Aucun proxy arbitraire n'est introduit.
    """

    possible_fields = [
        "stability_score",
        "energy_above_hull",
        "formation_energy",
    ]

    for field in possible_fields:

        value = safe_float(row.get(field))

        if value is None:
            continue

        if field == "stability_score":
            return clamp(value)

        if field == "energy_above_hull":
            # 0 eV/atom = très favorable.
            # >= 0.5 eV/atom = faible priorité.
            return clamp(1.0 - value / 0.5)

        if field == "formation_energy":
            # Très simplifié : uniquement si la donnée existe.
            # Une énergie de formation négative est favorable.
            if value <= 0:
                return 1.0

            return clamp(1.0 - value / 2.0)

    return 0.50


# ============================================================================
# ELECTRONIC READINESS
# ============================================================================


def calculate_electronic_score(row: dict) -> float:
    """
    Mesure la disponibilité d'informations électroniques.

    Ce score ne prétend PAS être un band-gap.
    Il indique uniquement la maturité des données disponibles.
    """

    score = 0.0
    count = 0

    band_gap = safe_float(row.get("band_gap"))

    if band_gap is not None:
        score += 1.0
        count += 1

    electronic_score = safe_float(row.get("electronic_score"))

    if electronic_score is not None:
        score += clamp(electronic_score)
        count += 1

    electronic_status = str(
        row.get("electronic_status", "")
    ).strip().lower()

    if electronic_status in {
        "ready",
        "validated",
        "complete",
    }:
        score += 1.0
        count += 1

    if count == 0:
        return 0.50

    return score / count


# ============================================================================
# DIVERSITÉ
# ============================================================================


def diversity_key(row: dict) -> str:
    """
    Clé de diversité.

    Priorité à la source puis à la formule.
    """

    source = str(row.get("source", "")).strip()
    formula = str(row.get("formula", "")).strip()

    return f"{source}|{formula}"


def calculate_diversity_scores(rows: list[dict]) -> dict[int, float]:
    """
    Attribue un bonus de diversité.

    Les candidats appartenant à des familles déjà très représentées
    reçoivent un score légèrement inférieur.
    """

    counts: dict[str, int] = {}

    for row in rows:
        key = diversity_key(row)
        counts[key] = counts.get(key, 0) + 1

    scores = {}

    for index, row in enumerate(rows):

        key = diversity_key(row)
        count = counts.get(key, 1)

        if count == 1:
            score = 1.0
        elif count == 2:
            score = 0.85
        elif count <= 4:
            score = 0.70
        elif count <= 8:
            score = 0.50
        else:
            score = 0.30

        scores[index] = score

    return scores


# ============================================================================
# SCORE GLOBAL
# ============================================================================


def calculate_priority_score(
    h2_score: float,
    structure_score: float,
    stability_score: float,
    electronic_score: float,
    diversity_score: float,
) -> float:

    score = (
        WEIGHT_H2 * h2_score
        + WEIGHT_STRUCTURE * structure_score
        + WEIGHT_STABILITY * stability_score
        + WEIGHT_ELECTRONIC * electronic_score
        + WEIGHT_DIVERSITY * diversity_score
    )

    return round(clamp(score), 6)


# ============================================================================
# LECTURE TOP100
# ============================================================================


def load_top100(path: Path) -> list[dict]:

    if not path.exists():
        raise FileNotFoundError(
            f"TOP100 introuvable : {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        return list(reader)


# ============================================================================
# VALIDATION
# ============================================================================


def validate_candidate(row: dict) -> tuple[bool, str]:

    valid = safe_bool(row.get("valid"))
    duplicate = safe_bool(row.get("duplicate"))
    passes = safe_bool(row.get("passes_screening"))

    if not valid:
        return False, "structure_invalid"

    if duplicate:
        return False, "duplicate_structure"

    if not passes:
        return False, "failed_h2_screening"

    cif = str(row.get("cif", "")).strip()

    if not validate_cif_path(cif):
        return False, "cif_missing"

    return True, "validated"


# ============================================================================
# SÉLECTION
# ============================================================================


def classify_candidates(
    candidates: list[Candidate],
) -> None:

    for index, candidate in enumerate(candidates):

        if index < MAX_PRIORITY:
            candidate.selection_class = "PRIORITY"
            candidate.selection_reason = (
                "Top DFT priority after H2, "
                "structure, stability, electronic "
                "and diversity scoring."
            )

        elif index < MAX_PRIORITY + MAX_SECONDARY:
            candidate.selection_class = "SECONDARY"
            candidate.selection_reason = (
                "Strong candidate retained after "
                "priority selection."
            )

        elif index < (
            MAX_PRIORITY
            + MAX_SECONDARY
            + MAX_RESERVE
        ):
            candidate.selection_class = "RESERVE"
            candidate.selection_reason = (
                "Reserve candidate for later DFT runs."
            )

        else:
            candidate.selection_class = "REJECTED"
            candidate.selection_reason = (
                "Outside configured DFT selection window."
            )


# ============================================================================
# CSV OUTPUT
# ============================================================================


def write_priority_csv(
    path: Path,
    candidates: list[Candidate],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "dft_rank",
        "rank_h2",
        "source",
        "name",
        "material_id",
        "formula",
        "cif",
        "valid",
        "duplicate",
        "passes_screening",
        "h2_score",
        "structure_score",
        "stability_score",
        "electronic_score",
        "diversity_score",
        "dft_priority_score",
        "selection_class",
        "selection_reason",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for rank, candidate in enumerate(
            candidates,
            start=1,
        ):

            row = asdict(candidate)

            row["dft_rank"] = rank

            writer.writerow(
                {
                    "dft_rank": rank,
                    **row,
                }
            )


# ============================================================================
# REJECTED CSV
# ============================================================================


def write_rejected_csv(
    path: Path,
    rejected: list[dict],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "rank_h2",
        "source",
        "name",
        "material_id",
        "formula",
        "cif",
        "reason",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(rejected)


# ============================================================================
# SUMMARY
# ============================================================================


def write_summary(
    path: Path,
    total_input: int,
    validated: int,
    rejected: int,
    selected: list[Candidate],
) -> None:

    counts = {
        "PRIORITY": 0,
        "SECONDARY": 0,
        "RESERVE": 0,
        "REJECTED": 0,
    }

    for candidate in selected:
        counts[candidate.selection_class] = (
            counts.get(candidate.selection_class, 0) + 1
        )

    source_counts: dict[str, int] = {}

    for candidate in selected:

        source = candidate.source

        source_counts[source] = (
            source_counts.get(source, 0) + 1
        )

    summary = {
        "phase": 19,
        "phase_name": "DFT PRIORITY + CANDIDATE SELECTION",
        "qe_launched": False,
        "quantum_espresso": {
            "pw_x": False,
            "bands_x": False,
            "dos_x": False,
            "relax": False,
            "scf": False,
        },
        "input": str(INPUT_TOP100),
        "output": str(OUTPUT_PRIORITY),
        "total_input": total_input,
        "validated": validated,
        "rejected": rejected,
        "selected": len(selected),
        "classes": counts,
        "sources": source_counts,
        "weights": {
            "h2": WEIGHT_H2,
            "structure": WEIGHT_STRUCTURE,
            "stability": WEIGHT_STABILITY,
            "electronic": WEIGHT_ELECTRONIC,
            "diversity": WEIGHT_DIVERSITY,
        },
        "limits": {
            "priority": MAX_PRIORITY,
            "secondary": MAX_SECONDARY,
            "reserve": MAX_RESERVE,
        },
        "protection": "QE NOT LAUNCHED",
    }

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:

    print("=" * 80)
    print(" HydroMatAI — PHASE 19")
    print(" DFT PRIORITY + SELECTION DES CANDIDATS")
    print("=" * 80)

    print()
    print("QE PROTECTION")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")

    # ----------------------------------------------------------------------
    # LOAD
    # ----------------------------------------------------------------------

    print()
    print("1. CHARGEMENT TOP100")
    print("-" * 80)
    print(f"Input : {INPUT_TOP100}")

    rows = load_top100(INPUT_TOP100)

    print(f"Candidats chargés : {len(rows):,}")

    # ----------------------------------------------------------------------
    # VALIDATION
    # ----------------------------------------------------------------------

    valid_rows = []
    rejected_rows = []

    for row in rows:

        ok, reason = validate_candidate(row)

        rank_h2 = safe_int(
            row.get("rank"),
            default=0,
        )

        if ok:
            valid_rows.append(row)

        else:
            rejected_rows.append(
                {
                    "rank_h2": rank_h2,
                    "source": row.get("source", ""),
                    "name": row.get("name", ""),
                    "material_id": row.get(
                        "material_id",
                        "",
                    ),
                    "formula": row.get(
                        "formula",
                        "",
                    ),
                    "cif": row.get(
                        "cif",
                        "",
                    ),
                    "reason": reason,
                }
            )

    print()
    print("2. VALIDATION")
    print("-" * 80)
    print(f"Validés    : {len(valid_rows):,}")
    print(f"Rejetés    : {len(rejected_rows):,}")

    # ----------------------------------------------------------------------
    # DIVERSITY
    # ----------------------------------------------------------------------

    diversity_scores = calculate_diversity_scores(
        valid_rows
    )

    # ----------------------------------------------------------------------
    # BUILD CANDIDATES
    # ----------------------------------------------------------------------

    candidates: list[Candidate] = []

    for index, row in enumerate(valid_rows):

        h2_score = safe_float(
            row.get("score")
        )

        if h2_score is None:
            h2_score = 0.0

        h2_score = clamp(h2_score)

        structure_score = calculate_structure_score(
            row
        )

        stability_score = calculate_stability_score(
            row
        )

        electronic_score = calculate_electronic_score(
            row
        )

        diversity_score = diversity_scores[index]

        dft_score = calculate_priority_score(
            h2_score=h2_score,
            structure_score=structure_score,
            stability_score=stability_score,
            electronic_score=electronic_score,
            diversity_score=diversity_score,
        )

        candidate = Candidate(
            rank_h2=safe_int(
                row.get("rank"),
                default=0,
            ),
            source=str(
                row.get("source", "")
            ),
            name=str(
                row.get("name", "")
            ),
            material_id=str(
                row.get("material_id", "")
            ),
            formula=str(
                row.get("formula", "")
            ),
            cif=str(
                row.get("cif", "")
            ),
            valid=True,
            duplicate=False,
            passes_screening=True,
            h2_score=round(h2_score, 6),
            structure_score=round(
                structure_score,
                6,
            ),
            stability_score=round(
                stability_score,
                6,
            ),
            electronic_score=round(
                electronic_score,
                6,
            ),
            diversity_score=round(
                diversity_score,
                6,
            ),
            dft_priority_score=dft_score,
            selection_class="",
            selection_reason="",
        )

        candidates.append(candidate)

    # ----------------------------------------------------------------------
    # SORT
    # ----------------------------------------------------------------------

    candidates.sort(
        key=lambda candidate: (
            candidate.dft_priority_score,
            candidate.h2_score,
            candidate.rank_h2,
        ),
        reverse=True,
    )

    # ----------------------------------------------------------------------
    # CLASSIFICATION
    # ----------------------------------------------------------------------

    classify_candidates(candidates)

    # ----------------------------------------------------------------------
    # LIMIT TO OUTPUT WINDOW
    # ----------------------------------------------------------------------

    max_selected = (
        MAX_PRIORITY
        + MAX_SECONDARY
        + MAX_RESERVE
    )

    selected = candidates[:max_selected]

    # ----------------------------------------------------------------------
    # OUTPUTS
    # ----------------------------------------------------------------------

    write_priority_csv(
        OUTPUT_PRIORITY,
        selected,
    )

    write_rejected_csv(
        OUTPUT_REJECTED,
        rejected_rows,
    )

    write_summary(
        OUTPUT_SUMMARY,
        total_input=len(rows),
        validated=len(valid_rows),
        rejected=len(rejected_rows),
        selected=selected,
    )

    # ----------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("3. DFT PRIORITY")
    print("=" * 80)

    print(
        f"PRIORITY   : "
        f"{sum(c.selection_class == 'PRIORITY' for c in selected):,}"
    )

    print(
        f"SECONDARY  : "
        f"{sum(c.selection_class == 'SECONDARY' for c in selected):,}"
    )

    print(
        f"RESERVE    : "
        f"{sum(c.selection_class == 'RESERVE' for c in selected):,}"
    )

    print()
    print("=" * 80)
    print("TOP 20 DFT")
    print("=" * 80)

    print(
        f"{'RANK':<6}"
        f"{'CLASS':<12}"
        f"{'SOURCE':<18}"
        f"{'MATERIAL':<30}"
        f"{'H2':>8}"
        f"{'DFT':>10}"
    )

    print("-" * 80)

    for rank, candidate in enumerate(
        selected[:20],
        start=1,
    ):

        print(
            f"{rank:<6}"
            f"{candidate.selection_class:<12}"
            f"{candidate.source:<18}"
            f"{candidate.name[:29]:<30}"
            f"{candidate.h2_score:>8.4f}"
            f"{candidate.dft_priority_score:>10.4f}"
        )

    # ----------------------------------------------------------------------
    # FILES
    # ----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("4. FICHIERS")
    print("=" * 80)

    print(
        f"DFT PRIORITY : {OUTPUT_PRIORITY}"
    )

    print(
        f"REJECTED     : {OUTPUT_REJECTED}"
    )

    print(
        f"SUMMARY      : {OUTPUT_SUMMARY}"
    )

    # ----------------------------------------------------------------------
    # FINAL AUDIT
    # ----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("PHASE 19 — AUDIT FINAL")
    print("=" * 80)

    print("TOP100 chargé                 : OK")
    print("Validation candidats          : OK")
    print("Déduplication                 : OK")
    print("Scoring DFT                   : OK")
    print("Classification                : OK")
    print("dft_priority.csv              : OK")
    print("Résumé JSON                   : OK")
    print("Protection QE                 : OK")
    print("Nouveau calcul QE             : NON")
    print("Calcul lourd                  : NON")

    print()
    print("=" * 80)
    print("PHASE 19 — TERMINÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
