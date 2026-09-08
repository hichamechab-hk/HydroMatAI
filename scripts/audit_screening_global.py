from __future__ import annotations
import os
os.system("clear")

import csv
import hashlib
import json
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path("MOF_Library")
REPORT = Path("reports/global_screening")

SOURCES = {
    "MOFXDB": ROOT / "MOFXDB_FULL" / "cif",
    "METAL_HYDRIDES": ROOT / "METAL_HYDRIDES" / "cif",
    "COMPLEXES": ROOT / "COMPLEXES" / "cif",
}

MIN_VOID_FRACTION = 0.50
MIN_SURFACE_AREA = 1000.0
MIN_PLD = 3.0
MIN_LCD = 6.0

# Screening compositionnel minimal pour les matériaux contenant H.
MIN_HYDROGEN_WT_PERCENT = 0.5


# ============================================================================
# FINGERPRINT
# ============================================================================

def fingerprint(structure: Structure) -> str:
    """
    Empreinte structurale reproductible.

    Les coordonnées sont arrondies pour éviter que de très petites
    différences numériques créent de faux doublons.
    """
    data = []

    for site in structure.sites:
        frac = site.frac_coords

        data.append(
            (
                site.specie.symbol,
                round(float(frac[0] % 1), 5),
                round(float(frac[1] % 1), 5),
                round(float(frac[2] % 1), 5),
            )
        )

    data.sort()

    lattice = structure.lattice

    payload = {
        "lattice": [
            round(float(lattice.a), 4),
            round(float(lattice.b), 4),
            round(float(lattice.c), 4),
            round(float(lattice.alpha), 4),
            round(float(lattice.beta), 4),
            round(float(lattice.gamma), 4),
        ],
        "sites": data,
    }

    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()


# ============================================================================
# METADATA
# ============================================================================

def read_metadata(source: str) -> dict[str, dict]:
    """
    Charge les metadata CSV si disponibles.

    Indexe par :
        - nom
        - identifiant matériau
        - nom de fichier CIF

    Pour MOFXDB, le CSV contient notamment :
        id
        name
        mofkey
        void_fraction
        surface_area_m2g
        surface_area_m2cm3
        pld
        lcd
        cif_path
    """
    result: dict[str, dict] = {}

    if source == "MOFXDB":
        path = ROOT / "MOFXDB_FULL" / "metadata.csv"

    elif source == "METAL_HYDRIDES":
        path = ROOT / "METAL_HYDRIDES" / "metadata.csv"

    else:
        path = ROOT / "COMPLEXES" / "metadata.csv"

    if not path.exists():
        print(
            f"  ATTENTION : metadata absente : {path}"
        )
        return result

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            name = (
                row.get("name")
                or ""
            ).strip()

            material_id = (
                row.get("id")
                or row.get("material_id")
                or ""
            ).strip()

            if name:
                result[name] = row

            if material_id:
                result[f"id:{material_id}"] = row

            cif_path = (
                row.get("cif_path")
                or ""
            ).strip()

            if cif_path:
                cif_name = Path(
                    cif_path
                ).name

                result[
                    f"cif:{cif_name}"
                ] = row

    return result


def metadata_for_cif(
    metadata: dict[str, dict],
    cif_path: Path,
) -> dict:
    """
    Retrouve les metadata correspondant à un CIF.

    Stratégie :

    1. nom exact du fichier sans extension ;
    2. nom exact du fichier CIF ;
    3. suppression du préfixe numérique MOFXDB ;
       ex. 0015338_hMOF-6.cif -> hMOF-6 ;
    4. identifiant numérique extrait du nom du CIF.

    Cette correction est essentielle pour MOFXDB.
    """

    stem = cif_path.stem

    # ------------------------------------------------------------------
    # 1. Nom exact
    # ------------------------------------------------------------------

    row = metadata.get(stem)

    if row is not None:
        return row.copy()

    # ------------------------------------------------------------------
    # 2. Nom exact du fichier CIF
    # ------------------------------------------------------------------

    row = metadata.get(
        f"cif:{cif_path.name}"
    )

    if row is not None:
        return row.copy()

    # ------------------------------------------------------------------
    # 3. Préfixe numérique MOFXDB
    #
    # Exemple :
    #
    # 0015338_hMOF-6.cif
    #
    # devient :
    #
    # hMOF-6
    # ------------------------------------------------------------------

    parts = stem.split(
        "_",
        1,
    )

    if (
        len(parts) == 2
        and parts[0].isdigit()
    ):

        material_name = parts[1]

        row = metadata.get(
            material_name
        )

        if row is not None:
            return row.copy()

        # --------------------------------------------------------------
        # 4. ID numérique
        # --------------------------------------------------------------

        row = metadata.get(
            f"id:{parts[0]}"
        )

        if row is not None:
            return row.copy()

    return {}


def get_material_id(row: dict) -> str:
    """
    Supporte les deux schémas de metadata :

    MOFXDB:
        id

    Hydrides/Complexes:
        material_id
    """
    return (
        row.get("id")
        or row.get("material_id")
        or ""
    ).strip()


def get_float(
    row: dict,
    key: str,
):
    """
    Conversion robuste d'une valeur numérique.
    """
    try:
        value = row.get(key)

        if value in (
            None,
            "",
            "None",
        ):
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================================
# HYDROGEN
# ============================================================================

def hydrogen_weight_percent(
    structure: Structure,
) -> float:
    """
    Calcule le pourcentage massique d'hydrogène.

    wt% H = masse H / masse totale * 100
    """

    composition = structure.composition

    total_mass = float(
        composition.weight
    )

    if total_mass <= 0:
        return 0.0

    hydrogen_amount = float(
        composition.get_atomic_fraction(
            "H"
        )
    )

    return round(
        hydrogen_amount * 100.0,
        6,
    )


def hydrogen_score(
    hydrogen_wt_percent: float,
) -> float:
    """
    Score compositionnel H₂ compris entre 0 et 1.

    10 wt% H correspond ici à la référence maximale
    du screening compositionnel.

    Ce score n'est PAS un score d'adsorption DFT.
    """

    if hydrogen_wt_percent <= 0:
        return 0.0

    return round(
        min(
            hydrogen_wt_percent / 10.0,
            1.0,
        ),
        6,
    )


# ============================================================================
# MOFXDB SCORE
# ============================================================================

def mofxdb_score(
    row: dict,
) -> float:
    """
    Score basé sur les propriétés poreuses MOFXDB.
    """

    vf = get_float(
        row,
        "void_fraction",
    )

    sa = get_float(
        row,
        "surface_area_m2g",
    )

    pld = get_float(
        row,
        "pld",
    )

    lcd = get_float(
        row,
        "lcd",
    )

    if None in (
        vf,
        sa,
        pld,
        lcd,
    ):
        return 0.0

    vf_score = min(
        vf / 0.90,
        1.0,
    )

    sa_score = min(
        sa / 5000.0,
        1.0,
    )

    pld_score = min(
        pld / 20.0,
        1.0,
    )

    lcd_score = min(
        lcd / 20.0,
        1.0,
    )

    return round(
        0.30 * vf_score
        + 0.30 * sa_score
        + 0.20 * pld_score
        + 0.20 * lcd_score,
        6,
    )


# ============================================================================
# MATERIAL SCORE
# ============================================================================

def material_score(
    source: str,
    row: dict,
    h_wt: float,
) -> float:
    """
    Score de priorité du screening global.

    MOFXDB :
        score poreux.

    METAL_HYDRIDES / COMPLEXES :
        score compositionnel H.

    Ce score est une priorité de screening,
    pas une prédiction d'adsorption.
    """

    if source == "MOFXDB":
        return mofxdb_score(
            row
        )

    return hydrogen_score(
        h_wt
    )


# ============================================================================
# SCREENING
# ============================================================================

def passes_screening(
    source: str,
    row: dict,
    h_wt: float,
) -> bool:
    """
    Screening adapté à la famille du matériau.
    """

    if source == "MOFXDB":

        vf = get_float(
            row,
            "void_fraction",
        )

        sa = get_float(
            row,
            "surface_area_m2g",
        )

        pld = get_float(
            row,
            "pld",
        )

        lcd = get_float(
            row,
            "lcd",
        )

        return (
            vf is not None
            and sa is not None
            and pld is not None
            and lcd is not None
            and vf >= MIN_VOID_FRACTION
            and sa >= MIN_SURFACE_AREA
            and pld >= MIN_PLD
            and lcd >= MIN_LCD
        )

    # ------------------------------------------------------------------
    # Hydrures et complexes
    # ------------------------------------------------------------------

    return (
        h_wt
        >= MIN_HYDROGEN_WT_PERCENT
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
    print(
        " HydroMatAI — AUDIT GLOBAL + SCREENING H2"
    )
    print("=" * 80)

    all_rows = []

    fingerprints = {}

    totals = {
        source: {
            "cif": 0,
            "valid": 0,
            "invalid": 0,
            "duplicates": 0,
            "screened": 0,
            "metadata_found": 0,
            "metadata_missing": 0,
        }
        for source in SOURCES
    }

    # ========================================================================
    # TRAITEMENT DES SOURCES
    # ========================================================================

    for source, directory in SOURCES.items():

        print()
        print(
            f"===== SOURCE : {source} ====="
        )

        print(
            f"Répertoire : {directory}"
        )

        if not directory.exists():

            print(
                "Répertoire absent — ignoré"
            )

            continue

        metadata = read_metadata(
            source
        )

        files = sorted(
            directory.glob("*.cif")
        )

        print(
            f"CIF trouvés : {len(files):,}"
        )

        if metadata:

            print(
                f"Metadata indexées : "
                f"{len(metadata):,}"
            )

        else:

            print(
                "Metadata : AUCUNE"
            )

        # --------------------------------------------------------------------
        # Boucle CIF
        # --------------------------------------------------------------------

        for index, cif_path in enumerate(
            files,
            start=1,
        ):

            totals[source]["cif"] += 1

            name = cif_path.stem

            row = metadata_for_cif(
                metadata,
                cif_path,
            )

            if row:

                totals[source][
                    "metadata_found"
                ] += 1

            else:

                totals[source][
                    "metadata_missing"
                ] += 1

            try:

                structure = Structure.from_file(
                    cif_path
                )

                totals[source][
                    "valid"
                ] += 1

                # ------------------------------------------------------------
                # Fingerprint
                # ------------------------------------------------------------

                fp = fingerprint(
                    structure
                )

                duplicate = (
                    fp in fingerprints
                )

                if duplicate:

                    totals[source][
                        "duplicates"
                    ] += 1

                    duplicate_of = (
                        fingerprints[fp]
                    )

                else:

                    fingerprints[fp] = (
                        f"{source}:"
                        f"{cif_path.name}"
                    )

                    duplicate_of = ""

                # ------------------------------------------------------------
                # Hydrogène
                # ------------------------------------------------------------

                h_wt = (
                    hydrogen_weight_percent(
                        structure
                    )
                )

                h_score = (
                    hydrogen_score(
                        h_wt
                    )
                )

                # ------------------------------------------------------------
                # Score
                # ------------------------------------------------------------

                score = material_score(
                    source,
                    row,
                    h_wt,
                )

                # ------------------------------------------------------------
                # Screening
                # ------------------------------------------------------------

                passes = passes_screening(
                    source,
                    row,
                    h_wt,
                )

                if passes:

                    totals[source][
                        "screened"
                    ] += 1

                # ------------------------------------------------------------
                # Propriétés MOFXDB
                # ------------------------------------------------------------

                if source == "MOFXDB":

                    vf = get_float(
                        row,
                        "void_fraction",
                    )

                    sa = get_float(
                        row,
                        "surface_area_m2g",
                    )

                    pld = get_float(
                        row,
                        "pld",
                    )

                    lcd = get_float(
                        row,
                        "lcd",
                    )

                else:

                    vf = None
                    sa = None
                    pld = None
                    lcd = None

                # ------------------------------------------------------------
                # Ligne complète
                # ------------------------------------------------------------

                all_rows.append(
                    {
                        "source": source,

                        "name": (
                            row.get("name")
                            or name
                        ),

                        "material_id": (
                            get_material_id(
                                row
                            )
                        ),

                        "cif": str(
                            cif_path
                        ),

                        "valid": 1,

                        "duplicate": int(
                            duplicate
                        ),

                        "duplicate_of": (
                            duplicate_of
                        ),

                        "formula": (
                            structure.composition.reduced_formula
                        ),

                        "n_atoms": (
                            len(structure)
                        ),

                        "hydrogen_wt_percent": (
                            h_wt
                        ),

                        "hydrogen_score": (
                            h_score
                        ),

                        "void_fraction": (
                            vf
                        ),

                        "surface_area_m2g": (
                            sa
                        ),

                        "pld": (
                            pld
                        ),

                        "lcd": (
                            lcd
                        ),

                        "score": (
                            score
                        ),

                        "passes_screening": int(
                            passes
                        ),

                        "error": "",
                    }
                )

            except Exception as exc:

                totals[source][
                    "invalid"
                ] += 1

                all_rows.append(
                    {
                        "source": source,

                        "name": name,

                        "material_id": (
                            get_material_id(
                                row
                            )
                        ),

                        "cif": str(
                            cif_path
                        ),

                        "valid": 0,

                        "duplicate": 0,

                        "duplicate_of": "",

                        "formula": "",

                        "n_atoms": "",

                        "hydrogen_wt_percent": "",

                        "hydrogen_score": "",

                        "void_fraction": "",

                        "surface_area_m2g": "",

                        "pld": "",

                        "lcd": "",

                        "score": 0.0,

                        "passes_screening": 0,

                        "error": str(
                            exc
                        ),
                    }
                )

            # ----------------------------------------------------------------
            # Progression
            # ----------------------------------------------------------------

            if index % 5000 == 0:

                print(
                    f"  {index:,} CIF traités"
                    f" | valides="
                    f"{totals[source]['valid']:,}"
                    f" | invalides="
                    f"{totals[source]['invalid']:,}"
                    f" | metadata="
                    f"{totals[source]['metadata_found']:,}"
                    f" | candidats="
                    f"{totals[source]['screened']:,}"
                )

        # --------------------------------------------------------------------
        # Résumé source
        # --------------------------------------------------------------------

        print()
        print(
            f"[{source}] FIN"
        )

        print(
            f"  CIF              : "
            f"{totals[source]['cif']:,}"
        )

        print(
            f"  valides          : "
            f"{totals[source]['valid']:,}"
        )

        print(
            f"  invalides        : "
            f"{totals[source]['invalid']:,}"
        )

        print(
            f"  metadata trouvées : "
            f"{totals[source]['metadata_found']:,}"
        )

        print(
            f"  metadata absentes : "
            f"{totals[source]['metadata_missing']:,}"
        )

        print(
            f"  doublons         : "
            f"{totals[source]['duplicates']:,}"
        )

        print(
            f"  candidats        : "
            f"{totals[source]['screened']:,}"
        )

    # ========================================================================
    # CSV GLOBAL
    # ========================================================================

    fieldnames = [
        "source",
        "name",
        "material_id",
        "cif",
        "valid",
        "duplicate",
        "duplicate_of",
        "formula",
        "n_atoms",
        "hydrogen_wt_percent",
        "hydrogen_score",
        "void_fraction",
        "surface_area_m2g",
        "pld",
        "lcd",
        "score",
        "passes_screening",
        "error",
    ]

    audit_path = (
        REPORT / "global_audit.csv"
    )

    with audit_path.open(
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

        writer.writerows(
            all_rows
        )

    # ========================================================================
    # RÉSULTATS PAR SOURCE
    # ========================================================================

    print()
    print("=" * 80)
    print(
        " RÉSULTATS PAR SOURCE"
    )
    print("=" * 80)

    for source, values in totals.items():

        print()
        print(source)

        print(
            f"  CIF              : "
            f"{values['cif']:,}"
        )

        print(
            f"  valides          : "
            f"{values['valid']:,}"
        )

        print(
            f"  invalides        : "
            f"{values['invalid']:,}"
        )

        print(
            f"  metadata trouvées : "
            f"{values['metadata_found']:,}"
        )

        print(
            f"  metadata absentes : "
            f"{values['metadata_missing']:,}"
        )

        print(
            f"  doublons         : "
            f"{values['duplicates']:,}"
        )

        print(
            f"  candidats        : "
            f"{values['screened']:,}"
        )

    # ========================================================================
    # TOP GLOBAL
    # ========================================================================

    valid_candidates = [
        row
        for row in all_rows
        if (
            row["valid"] == 1
            and row["passes_screening"] == 1
            and row["duplicate"] == 0
        )
    ]

    valid_candidates.sort(
        key=lambda x: (
            float(x["score"]),
            float(x["hydrogen_score"]),
        ),
        reverse=True,
    )

    top100 = valid_candidates[:100]

    top20 = valid_candidates[:20]

    dft_priority = valid_candidates[:200]

    # ========================================================================
    # ÉCRITURE CSV
    # ========================================================================

    def write_rows(
        path: Path,
        rows,
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

            writer.writerows(
                rows
            )

    write_rows(
        REPORT
        / "TOP100_GLOBAL_H2.csv",
        top100,
    )

    write_rows(
        REPORT
        / "TOP20_GLOBAL_H2.csv",
        top20,
    )

    write_rows(
        REPORT
        / "dft_priority.csv",
        dft_priority,
    )

    # ========================================================================
    # TOP PAR FAMILLE
    # ========================================================================

    for source in SOURCES:

        source_rows = [
            row
            for row in valid_candidates
            if row["source"] == source
        ]

        write_rows(
            REPORT
            / f"TOP100_{source}_H2.csv",
            source_rows[:100],
        )

    # ========================================================================
    # SUMMARY
    # ========================================================================

    summary = {

        "sources": totals,

        "total_cif": sum(
            v["cif"]
            for v in totals.values()
        ),

        "total_valid": sum(
            v["valid"]
            for v in totals.values()
        ),

        "total_invalid": sum(
            v["invalid"]
            for v in totals.values()
        ),

        "total_duplicates": sum(
            v["duplicates"]
            for v in totals.values()
        ),

        "total_candidates": len(
            valid_candidates
        ),

        "unique_fingerprints": len(
            fingerprints
        ),

        "screening": {

            "mofxdb": {

                "min_void_fraction":
                    MIN_VOID_FRACTION,

                "min_surface_area_m2g":
                    MIN_SURFACE_AREA,

                "min_pld":
                    MIN_PLD,

                "min_lcd":
                    MIN_LCD,
            },

            "hydrides_complexes": {

                "min_hydrogen_wt_percent":
                    MIN_HYDROGEN_WT_PERCENT,
            },
        },

        "score_definition": {

            "mofxdb":
                "porosity_score",

            "metal_hydrides":
                "hydrogen_weight_percent_score",

            "complexes":
                "hydrogen_weight_percent_score",
        },

        "qe_launched": False,

        "files": {

            "audit":
                str(audit_path),

            "top100":
                str(
                    REPORT
                    / "TOP100_GLOBAL_H2.csv"
                ),

            "top20":
                str(
                    REPORT
                    / "TOP20_GLOBAL_H2.csv"
                ),

            "dft_priority":
                str(
                    REPORT
                    / "dft_priority.csv"
                ),
        },
    }

    with (
        REPORT
        / "global_screening_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================================
    # TOP 20 AFFICHAGE
    # ========================================================================

    print()
    print("=" * 80)
    print(
        " TOP 20 GLOBAL H₂"
    )
    print("=" * 80)

    print(
        f"Candidats retenus : "
        f"{len(valid_candidates):,}"
    )

    print(
        "-" * 90
    )

    for rank, row in enumerate(
        top20,
        start=1,
    ):

        print(
            f"{rank:3d}. "
            f"{row['source']:18s} "
            f"{row['name'][:35]:35s} "
            f"score={float(row['score']):.4f}"
        )

    # ========================================================================
    # FICHIERS
    # ========================================================================

    print()
    print("=" * 80)
    print(
        " FICHIERS"
    )
    print("=" * 80)

    print(
        f"Audit       : "
        f"{audit_path}"
    )

    print(
        f"TOP100      : "
        f"{REPORT / 'TOP100_GLOBAL_H2.csv'}"
    )

    print(
        f"TOP20       : "
        f"{REPORT / 'TOP20_GLOBAL_H2.csv'}"
    )

    print(
        f"DFT priority : "
        f"{REPORT / 'dft_priority.csv'}"
    )

    print(
        f"Summary     : "
        f"{REPORT / 'global_screening_summary.json'}"
    )

    print()
    print("=" * 80)
    print(
        " TERMINÉ"
    )
    print("=" * 80)
    print(
        "Aucun CIF supprimé."
    )
    print(
        "QE : NON LANCÉ"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
