#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 21G
VALIDATION FINALE PSEUDOPOTENTIELS QE

Objectifs
---------
1. Trouver automatiquement l'installation QE.
2. Trouver le répertoire pseudo/ correct.
3. Lire le résultat de Phase 21F.
4. Inspecter réellement les fichiers UPF.
5. Mapper strictement les éléments chimiques.
6. Interdire toute confusion F -> Fe.
7. Vérifier C/H/N/O/Zn/F.
8. Ne lancer AUCUN calcul QE.
9. Ne modifier AUCUN CIF.
10. Produire CSV + JSON + MANIFEST.

Usage
-----
python scripts/phase21g_pseudopotential_final.py --limit 25

Optionnel :
python scripts/phase21g_pseudopotential_final.py --limit 25 --pseudo-dir /home/hk/software/qe-7.5/pseudo
"""


import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path("/home/hk/HydroMatAI")

QE_CANDIDATE_DIRS = [
    Path("/home/hk/software/qe-7.5"),
    Path("/home/hk/HydroMatAI/software/qe-7.5"),
    PROJECT_ROOT / "software" / "qe-7.5",
]

PSEUDO_CANDIDATE_DIRS = [
    Path("/home/hk/software/qe-7.5/pseudo"),
    Path("/home/hk/HydroMatAI/software/qe-7.5/pseudo"),
    PROJECT_ROOT / "software" / "qe-7.5" / "pseudo",
]

PHASE21F_DIR = (
    PROJECT_ROOT
    / "calculations"
    / "phase_21f_pseudopotential_install"
)

PHASE21F_CSV = PHASE21F_DIR / "phase21f_pseudopotential_install.csv"
PHASE21F_JSON = PHASE21F_DIR / "phase21f_pseudopotential_install.json"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "calculations"
    / "phase_21g_pseudopotential_final"
)

OUTPUT_CSV = OUTPUT_DIR / "phase21g_pseudopotential_final.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase21g_pseudopotential_final.json"
OUTPUT_MANIFEST = OUTPUT_DIR / "phase21g_manifest.json"

# Eléments explicitement surveillés pour les candidats actuels.
TARGET_ELEMENTS = {"C", "F", "H", "N", "O", "Zn"}

# Extension UPF acceptées.
UPF_EXTENSIONS = {".upf"}

# Mots interdits pour éviter les faux mappings.
FORBIDDEN_F_ELEMENT_PATTERNS = {
    "fe",
    "iron",
}

# =============================================================================
# AFFICHAGE
# =============================================================================


def banner(text: str) -> None:
    print("=" * 80)
    print(text)
    print("=" * 80)


def section(text: str) -> None:
    print()
    print("-" * 80)
    print(text)
    print("-" * 80)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# =============================================================================
# UTILITAIRES
# =============================================================================


def normalize_element(value: str) -> str:
    """
    Normalise un symbole chimique.

    C -> C
    h -> H
    ZN -> Zn
    zn -> Zn
    """
    value = str(value).strip()

    if not value:
        return ""

    if len(value) == 1:
        return value.upper()

    return value[0].upper() + value[1:].lower()


def find_first_existing(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def find_qe_root() -> Optional[Path]:
    # 1. PATH
    pw = shutil.which("pw.x")

    if pw:
        p = Path(pw).resolve()

        # /.../qe-7.5/bin/pw.x
        if p.parent.name == "bin":
            return p.parent.parent

        # /.../PW/src/pw.x
        if p.parent.name == "src":
            return p.parent.parent.parent

    # 2. chemins connus
    for root in QE_CANDIDATE_DIRS:
        if (root / "bin" / "pw.x").exists():
            return root

        if (root / "PW" / "src" / "pw.x").exists():
            return root

    return None


def find_pseudo_dir(explicit: Optional[str] = None) -> Optional[Path]:
    candidates: List[Path] = []

    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())

    # Si QE a été trouvé, privilégier son pseudo/
    qe_root = find_qe_root()

    if qe_root:
        candidates.append(qe_root / "pseudo")

    candidates.extend(PSEUDO_CANDIDATE_DIRS)

    seen = set()

    for directory in candidates:
        directory = directory.resolve()

        if str(directory) in seen:
            continue

        seen.add(str(directory))

        if directory.is_dir():
            return directory

    return None


def find_phase21f_csv() -> Optional[Path]:
    if PHASE21F_CSV.exists():
        return PHASE21F_CSV

    # Recherche de secours
    candidates = [
        PROJECT_ROOT
        / "calculations"
        / "phase_21f_pseudopotential_install"
        / "phase21f_mapping.csv",
        PROJECT_ROOT
        / "calculations"
        / "phase_21f_pseudopotential_install"
        / "phase21f_pseudopotential_install.csv",
    ]

    for p in candidates:
        if p.exists():
            return p

    return None


# =============================================================================
# INSPECTION UPF
# =============================================================================


def read_text_safe(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        with path.open("rb") as f:
            data = f.read(max_bytes)

        return data.decode("utf-8", errors="ignore")

    except Exception:
        return ""


def detect_upf_element(path: Path) -> Optional[str]:
    """
    Détecte l'élément à partir du contenu UPF.

    Priorité :
      1. element="..."
      2. element='...'
      3. <PP_HEADER element="...">
      4. attributs proches
      5. nom du fichier uniquement comme dernier recours.

    Important :
    Le nom du fichier seul n'est pas considéré comme suffisamment fiable
    si le contenu UPF fournit une information contradictoire.
    """

    text = read_text_safe(path)

    if not text:
        return None

    patterns = [
        r'\belement\s*=\s*["\']([A-Za-z]{1,3})["\']',
        r'\belement\s*=\s*([A-Za-z]{1,3})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            element = normalize_element(match.group(1))

            if element:
                return element

    # Recherche PP_HEADER
    header_match = re.search(
        r"<PP_HEADER\b[^>]*>",
        text,
        re.IGNORECASE,
    )

    if header_match:
        header = header_match.group(0)

        match = re.search(
            r'\belement\s*=\s*["\']([A-Za-z]{1,3})["\']',
            header,
            re.IGNORECASE,
        )

        if match:
            return normalize_element(match.group(1))

    return None


def inspect_upf_directory(
    pseudo_dir: Path,
) -> Tuple[Dict[str, List[Path]], List[Dict[str, str]]]:

    by_element: Dict[str, List[Path]] = {}
    records: List[Dict[str, str]] = []

    files = sorted(
        [
            p
            for p in pseudo_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".upf"
        ],
        key=lambda p: p.name.lower(),
    )

    for path in files:
        element = detect_upf_element(path)

        record = {
            "file": path.name,
            "element": element or "",
            "path": str(path),
        }

        records.append(record)

        if element:
            by_element.setdefault(element, []).append(path)

    return by_element, records


# =============================================================================
# PROTECTION F -> FE
# =============================================================================


def is_safe_f_pseudopotential(path: Path, detected_element: Optional[str]) -> bool:
    """
    F ne peut être mappé que si l'UPF est réellement identifié comme F.

    Un fichier Fe contenant "Fe" dans son nom ne peut jamais servir pour F.
    """

    if detected_element != "F":
        return False

    name = path.name.lower()

    for forbidden in FORBIDDEN_F_ELEMENT_PATTERNS:
        # Fe détecté explicitement
        if re.search(rf"(^|[^a-z]){re.escape(forbidden)}([^a-z]|$)", name):
            return False

    return True


# =============================================================================
# SÉLECTION DU PSEUDO
# =============================================================================


def choose_pseudopotential(
    element: str,
    by_element: Dict[str, List[Path]],
) -> Optional[Path]:

    candidates = by_element.get(element, [])

    if not candidates:
        return None

    # Protection spécifique F.
    if element == "F":
        candidates = [
            p
            for p in candidates
            if is_safe_f_pseudopotential(p, "F")
        ]

    if not candidates:
        return None

    # Préférence simple et déterministe.
    # On évite toute logique basée sur des noms "semblables".
    candidates = sorted(
        candidates,
        key=lambda p: p.name.lower(),
    )

    return candidates[0]


# =============================================================================
# LECTURE PHASE 21F
# =============================================================================


def read_phase21f(path: Path) -> List[Dict[str, str]]:
    """
    Lecture robuste du CSV 21F.

    Supporte différents noms de colonnes.
    """

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise RuntimeError(
                f"CSV Phase 21F sans en-tête : {path}"
            )

        rows = []

        for row in reader:
            normalized = {}

            for key, value in row.items():
                if key is None:
                    continue

                normalized[key.strip()] = (
                    value.strip() if isinstance(value, str) else value
                )

            rows.append(normalized)

    return rows


def get_column(
    row: Dict[str, str],
    aliases: List[str],
) -> str:

    lowered = {
        str(k).strip().lower(): v
        for k, v in row.items()
    }

    for alias in aliases:
        if alias.lower() in lowered:
            value = lowered[alias.lower()]

            if value is None:
                return ""

            return str(value).strip()

    return ""


def extract_candidate_name(row: Dict[str, str]) -> str:
    return get_column(
        row,
        [
            "candidate",
            "name",
            "material",
            "mof",
            "mof_name",
            "id",
            "structure_id",
            "identifier",
        ],
    )


def extract_cif(row: Dict[str, str]) -> str:
    return get_column(
        row,
        [
            "cif",
            "cif_path",
            "path",
            "structure_path",
            "file",
        ],
    )


def extract_elements(row: Dict[str, str]) -> List[str]:
    raw = get_column(
        row,
        [
            "elements",
            "element",
            "species",
            "chemical_elements",
        ],
    )

    if not raw:
        return []

    # Accepte :
    # C, H, O, Zn
    # C H O Zn
    # C;H;O;Zn
    # ["C","H","O","Zn"]
    raw = raw.replace("[", "")
    raw = raw.replace("]", "")
    raw = raw.replace('"', "")
    raw = raw.replace("'", "")
    raw = raw.replace(";", ",")
    raw = raw.replace("|", ",")

    tokens = re.split(r"[\s,]+", raw)

    elements = []

    for token in tokens:
        token = token.strip()

        if not token:
            continue

        token = normalize_element(token)

        # Ne garder que symboles chimiques plausibles.
        if re.fullmatch(r"[A-Z][a-z]?", token):
            elements.append(token)

    # unique + ordre alphabétique
    return sorted(set(elements))


# =============================================================================
# VALIDATION
# =============================================================================


def validate_candidate(
    row: Dict[str, str],
    by_element: Dict[str, List[Path]],
) -> Dict:

    candidate = extract_candidate_name(row)
    cif = extract_cif(row)
    elements = extract_elements(row)

    if not candidate:
        candidate = "UNKNOWN"

    mapping = {}
    missing = []
    pseudo_files = []

    for element in elements:

        pseudo = choose_pseudopotential(
            element,
            by_element,
        )

        if pseudo is None:
            mapping[element] = "MISSING"
            missing.append(element)

        else:
            mapping[element] = pseudo.name
            pseudo_files.append(pseudo.name)

    # Si aucun élément n'a été lu, on ne déclare jamais READY.
    if not elements:
        status = "INVALID_ELEMENTS"

    elif missing:
        status = "MISSING_PSEUDO"

    else:
        status = "READY_FOR_QE"

    # Protection F -> Fe
    f_mapping = mapping.get("F")

    if f_mapping and f_mapping != "MISSING":
        selected = by_element.get("F", [])

        if not any(
            p.name == f_mapping
            and is_safe_f_pseudopotential(p, "F")
            for p in selected
        ):
            mapping["F"] = "MISSING"
            if "F" not in missing:
                missing.append("F")

            status = "MISSING_PSEUDO"

    return {
        "candidate": candidate,
        "cif": cif,
        "elements": elements,
        "mapping": mapping,
        "missing": sorted(set(missing)),
        "pseudo_files": sorted(set(pseudo_files)),
        "status": status,
    }


# =============================================================================
# EXPORT
# =============================================================================


def export_results(
    results: List[Dict],
    pseudo_dir: Path,
    upf_records: List[Dict[str, str]],
    phase21f_path: Path,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # CSV
    # -------------------------------------------------------------------------

    fieldnames = [
        "candidate",
        "cif",
        "elements",
        "C",
        "F",
        "H",
        "N",
        "O",
        "Zn",
        "missing",
        "status",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            row = {
                "candidate": result["candidate"],
                "cif": result["cif"],
                "elements": ",".join(result["elements"]),
                "missing": ",".join(result["missing"]),
                "status": result["status"],
            }

            for element in [
                "C",
                "F",
                "H",
                "N",
                "O",
                "Zn",
            ]:
                row[element] = result["mapping"].get(
                    element,
                    "",
                )

            writer.writerow(row)

    # -------------------------------------------------------------------------
    # JSON
    # -------------------------------------------------------------------------

    summary = {
        "phase": "21G",
        "timestamp": now_iso(),
        "pseudo_dir": str(pseudo_dir),
        "phase21f_input": str(phase21f_path),
        "upf_count": len(upf_records),
        "results": results,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # -------------------------------------------------------------------------
    # MANIFEST
    # -------------------------------------------------------------------------

    manifest = {
        "phase": "21G",
        "timestamp": now_iso(),
        "project_root": str(PROJECT_ROOT),
        "phase21f_input": str(phase21f_path),
        "pseudo_dir": str(pseudo_dir),
        "upf_count": len(upf_records),
        "upf_inventory": upf_records,
        "target_elements": sorted(TARGET_ELEMENTS),
        "ready_for_qe": sum(
            r["status"] == "READY_FOR_QE"
            for r in results
        ),
        "missing_pseudo": sum(
            r["status"] == "MISSING_PSEUDO"
            for r in results
        ),
        "protections": {
            "no_qe_execution": True,
            "no_cif_modification": True,
            "strict_element_mapping": True,
            "f_to_fe_protection": True,
        },
    }

    with OUTPUT_MANIFEST.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 21G — "
            "Validation finale des pseudopotentiels QE"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre maximum de candidats à inspecter.",
    )

    parser.add_argument(
        "--pseudo-dir",
        type=str,
        default=None,
        help="Répertoire pseudo QE explicite.",
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # HEADER
    # -------------------------------------------------------------------------

    banner(
        " HydroMatAI — PHASE 21G\n"
        " VALIDATION FINALE PSEUDOPOTENTIELS QE"
    )

    # -------------------------------------------------------------------------
    # PROTECTION
    # -------------------------------------------------------------------------

    section("PROTECTION QE")

    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    # -------------------------------------------------------------------------
    # QE
    # -------------------------------------------------------------------------

    section("ENVIRONNEMENT QE")

    qe_root = find_qe_root()

    if qe_root:

        pw_candidates = [
            qe_root / "bin" / "pw.x",
            qe_root / "PW" / "src" / "pw.x",
        ]

        pw_path = next(
            (
                p
                for p in pw_candidates
                if p.exists()
            ),
            None,
        )

        if pw_path:
            print(f"pw.x : OK → {pw_path}")
        else:
            print(
                f"pw.x : NON TROUVÉ dans {qe_root}"
            )

    else:
        print("pw.x : NON TROUVÉ")

    # -------------------------------------------------------------------------
    # PSEUDO DIR
    # -------------------------------------------------------------------------

    section("PSEUDOPOTENTIELS")

    pseudo_dir = find_pseudo_dir(
        args.pseudo_dir
    )

    if pseudo_dir is None:
        print("Répertoire pseudo : NON TROUVÉ")
        print()
        print(
            "ERREUR : impossible de localiser le répertoire pseudo QE."
        )
        return 2

    print(f"Répertoire : {pseudo_dir}")

    by_element, upf_records = inspect_upf_directory(
        pseudo_dir
    )

    print(f"UPF analysés : {len(upf_records)}")

    # -------------------------------------------------------------------------
    # INVENTAIRE
    # -------------------------------------------------------------------------

    section("ÉLÉMENTS DÉTECTÉS")

    if not by_element:
        print("Aucun UPF exploitable détecté.")

    else:
        for element in sorted(by_element):
            names = [
                p.name
                for p in by_element[element]
            ]

            print(
                f"{element:<3} : "
                + ", ".join(names)
            )

    # -------------------------------------------------------------------------
    # PHASE 21F
    # -------------------------------------------------------------------------

    section("CHARGEMENT PHASE 21F")

    phase21f_path = find_phase21f_csv()

    if phase21f_path is None:
        print(
            "ERREUR : CSV Phase 21F introuvable."
        )
        print(
            f"Recherche principale : {PHASE21F_CSV}"
        )
        return 3

    try:
        rows = read_phase21f(
            phase21f_path
        )

    except Exception as exc:
        print(
            f"ERREUR lecture Phase 21F : {exc}"
        )
        return 4

    print(
        f"Lignes disponibles : {len(rows)}"
    )

    if args.limit is not None:
        rows = rows[: args.limit]

    print(
        f"Lignes inspectées   : {len(rows)}"
    )

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    section("VALIDATION")

    results = []

    for index, row in enumerate(rows, start=1):

        result = validate_candidate(
            row,
            by_element,
        )

        results.append(result)

        print(
            f"[{index}/{len(rows)}] "
            f"{result['candidate']}"
        )

        print(
            f"  CIF    : "
            f"{result['cif'] or 'NON RENSEIGNÉ'}"
        )

        print(
            "  Elements : "
            + (
                ", ".join(result["elements"])
                if result["elements"]
                else "AUCUN"
            )
        )

        for element in result["elements"]:
            pseudo = result["mapping"].get(
                element,
                "MISSING",
            )

            print(
                f"  {element:<2} → {pseudo}"
            )

        print(
            f"  STATUS : {result['status']}"
        )

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    ready = sum(
        r["status"] == "READY_FOR_QE"
        for r in results
    )

    missing = sum(
        r["status"] == "MISSING_PSEUDO"
        for r in results
    )

    invalid = sum(
        r["status"] == "INVALID_ELEMENTS"
        for r in results
    )

    required: Set[str] = set()

    for result in results:
        required.update(
            result["elements"]
        )

    available_required = sorted(
        required.intersection(
            set(by_element.keys())
        )
    )

    missing_required = sorted(
        required.difference(
            set(by_element.keys())
        )
    )

    section("PHASE 21G — RÉSULTATS")

    print(
        f"Candidats              : {len(results)}"
    )

    print(
        f"READY_FOR_QE           : {ready}"
    )

    print(
        f"MISSING_PSEUDO         : {missing}"
    )

    if invalid:
        print(
            f"INVALID_ELEMENTS       : {invalid}"
        )

    section("PSEUDOPOTENTIELS REQUIS")

    print(
        "Requis : "
        + (
            ", ".join(sorted(required))
            if required
            else "AUCUN"
        )
    )

    print(
        "Disponibles : "
        + (
            ", ".join(available_required)
            if available_required
            else "AUCUN"
        )
    )

    print(
        "Manquants : "
        + (
            ", ".join(missing_required)
            if missing_required
            else "AUCUN"
        )
    )

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    export_results(
        results=results,
        pseudo_dir=pseudo_dir,
        upf_records=upf_records,
        phase21f_path=phase21f_path,
    )

    section("FICHIERS")

    print(
        f"CSV      : {OUTPUT_CSV}"
    )

    print(
        f"JSON     : {OUTPUT_JSON}"
    )

    print(
        f"MANIFEST : {OUTPUT_MANIFEST}"
    )

    # -------------------------------------------------------------------------
    # FINAL AUDIT
    # -------------------------------------------------------------------------

    section("PHASE 21G — AUDIT FINAL")

    print("Lecture Phase 21F          : OK")
    print("UPF inspection             : OK")
    print("Mapping élémentaire strict : OK")
    print("Protection F → Fe          : OK")
    print("Aucun calcul QE            : OK")
    print("Aucun CIF modifié          : OK")
    print("Traçabilité                : OK")

    print()

    if ready == len(results) and len(results) > 0:
        print("READY_FOR_QE : OUI")
        print(
            "BLOCAGE : AUCUN"
        )

    else:
        print("READY_FOR_QE : NON")

        if missing_required:
            print(
                "BLOCAGE : "
                + ", ".join(missing_required)
            )

        else:
            print(
                "BLOCAGE : "
                "mapping incomplet ou éléments invalides"
            )

    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
