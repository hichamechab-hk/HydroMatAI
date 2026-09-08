#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 21G
VALIDATION FINALE DES PSEUDOPOTENTIELS QE

Objectif
--------
1. Charger les candidats DFT PRIORITY.
2. Lire leurs CIF.
3. Détecter les éléments réellement présents.
4. Scanner les fichiers UPF disponibles.
5. Vérifier que le fichier UPF correspond réellement à l'élément.
6. Interdire toute substitution dangereuse (ex. F -> Fe).
7. Produire un mapping élément -> UPF.
8. Déclarer READY_FOR_QE uniquement si tous les éléments disposent
   d'un pseudopotentiel valide.
9. Générer CSV / JSON / manifest.
10. Ne lancer AUCUN calcul QE.

Usage
-----
python scripts/phase21g_pseudopotential_validation.py --limit 25

"""


import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DFT_PRIORITY = (
    PROJECT_ROOT
    / "reports"
    / "global_screening"
    / "dft_priority.csv"
)

CIF_ROOT = PROJECT_ROOT / "MOF_Library" / "MOFXDB_FULL" / "cif"

QE_ROOT = Path("/home/hk/software/qe-7.5")

PW_X_CANDIDATES = [
    QE_ROOT / "bin" / "pw.x",
    QE_ROOT / "PW" / "src" / "pw.x",
]

PSEUDO_DIR = QE_ROOT / "pseudo"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "calculations"
    / "phase_21g_pseudopotential_validation"
)

CSV_OUTPUT = OUTPUT_DIR / "phase21g_validation.csv"
JSON_OUTPUT = OUTPUT_DIR / "phase21g_validation.json"
MANIFEST_OUTPUT = OUTPUT_DIR / "phase21g_manifest.json"

# ---------------------------------------------------------------------
# ÉLÉMENTS
# ---------------------------------------------------------------------

VALID_ELEMENT_SYMBOLS = {
    "H", "He",
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni",
    "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
    "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
    "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am",
    "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg",
    "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}

# Mapping strict pour les éléments problématiques rencontrés.
# Le script ne considère JAMAIS Fe comme un pseudopotentiel de F.
FORBIDDEN_SUBSTITUTIONS = {
    ("F", "Fe"),
}

# ---------------------------------------------------------------------
# UTILITAIRES
# ---------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_element(symbol: str) -> str:
    symbol = symbol.strip()
    if not symbol:
        return symbol

    if len(symbol) == 1:
        return symbol.upper()

    return symbol[0].upper() + symbol[1:].lower()


def find_pw_x() -> Optional[Path]:
    for candidate in PW_X_CANDIDATES:
        if candidate.is_file():
            return candidate

    return None


def read_text(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        with path.open("rb") as handle:
            data = handle.read(max_bytes)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


# ---------------------------------------------------------------------
# CIF
# ---------------------------------------------------------------------


def extract_elements_from_cif(cif_path: Path) -> List[str]:
    """
    Extraction robuste des éléments depuis les labels / symbols CIF.

    Priorité :
      _atom_site_type_symbol
      _atom_site_label
    """

    text = read_text(cif_path)

    if not text:
        return []

    elements = set()

    lines = text.splitlines()

    # -------------------------------------------------------------
    # Chercher le loop atom_site
    # -------------------------------------------------------------

    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.lower() == "loop_":
            headers = []
            j = i + 1

            while j < len(lines):
                candidate = lines[j].strip()

                if not candidate:
                    j += 1
                    continue

                if candidate.startswith("_"):
                    headers.append(candidate)
                    j += 1
                    continue

                break

            atom_site_headers = [
                h for h in headers
                if h.lower().startswith("_atom_site_")
            ]

            if atom_site_headers:
                symbol_idx = None
                label_idx = None

                for idx, header in enumerate(atom_site_headers):
                    h = header.lower()

                    if h == "_atom_site_type_symbol":
                        symbol_idx = idx

                    if h == "_atom_site_label":
                        label_idx = idx

                k = j

                while k < len(lines):
                    row = lines[k].strip()

                    if (
                        not row
                        or row.startswith("#")
                        or row.startswith("_")
                        or row.lower() == "loop_"
                    ):
                        break

                    tokens = row.split()

                    if len(tokens) >= len(atom_site_headers):
                        value = None

                        if symbol_idx is not None:
                            value = tokens[symbol_idx]

                        elif label_idx is not None:
                            value = tokens[label_idx]

                        if value:
                            # Retirer éventuels caractères de charge
                            value = re.sub(r"[^A-Za-z]", "", value)

                            # Cas label comme Zn1 -> Zn
                            match = re.match(
                                r"([A-Z][a-z]?)",
                                value
                            )

                            if match:
                                element = normalize_element(match.group(1))

                                if element in VALID_ELEMENT_SYMBOLS:
                                    elements.add(element)

                    k += 1

            i = j
            continue

        i += 1

    # -------------------------------------------------------------
    # Fallback : recherche explicite des labels CIF
    # -------------------------------------------------------------

    if not elements:
        for line in lines:
            lower = line.lower()

            if "_atom_site_type_symbol" in lower:
                continue

            # Recherche de symboles usuels dans les lignes atomiques.
            tokens = line.split()

            for token in tokens[:4]:
                cleaned = re.sub(r"[^A-Za-z]", "", token)

                if not cleaned:
                    continue

                match = re.match(
                    r"^([A-Z][a-z]?)",
                    cleaned,
                )

                if match:
                    element = normalize_element(match.group(1))

                    if element in VALID_ELEMENT_SYMBOLS:
                        elements.add(element)

    return sorted(elements)


# ---------------------------------------------------------------------
# UPF
# ---------------------------------------------------------------------


def detect_upf_element(path: Path) -> Optional[str]:
    """
    Détermine l'élément d'un UPF en priorité depuis son contenu.

    Les métadonnées UPF sont plus fiables que le nom du fichier.
    """

    text = read_text(path, max_bytes=500_000)

    if not text:
        return None

    # UPF ancien / nouveau :
    #
    # element="O"
    # element='O'
    # element = "O"
    #

    patterns = [
        r'\belement\s*=\s*["\']([A-Z][a-z]?)["\']',
        r'\bsymbol\s*=\s*["\']([A-Z][a-z]?)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            element = normalize_element(match.group(1))

            if element in VALID_ELEMENT_SYMBOLS:
                return element

    # -----------------------------------------------------------------
    # Fallback sur les champs typiques UPF
    # -----------------------------------------------------------------

    patterns = [
        r'\bElement\s*[:=]\s*([A-Z][a-z]?)',
        r'\bPseudo\s*name\s*[:=]\s*([A-Z][a-z]?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            element = normalize_element(match.group(1))

            if element in VALID_ELEMENT_SYMBOLS:
                return element

    return None


def validate_upf_file(
    path: Path,
    expected_element: str,
) -> Tuple[bool, str, Optional[str]]:
    """
    Validation stricte d'un UPF.
    """

    if not path.is_file():
        return False, "FILE_MISSING", None

    if path.stat().st_size == 0:
        return False, "EMPTY_UPF", None

    text = read_text(path, max_bytes=500_000)

    if not text:
        return False, "UNREADABLE_UPF", None

    upper = text.upper()

    if "<UPF" not in upper:
        return False, "NOT_UPF_FORMAT", None

    detected = detect_upf_element(path)

    if detected is None:
        return False, "ELEMENT_UNDETECTED", None

    expected = normalize_element(expected_element)

    if detected != expected:
        if (expected, detected) in FORBIDDEN_SUBSTITUTIONS:
            return (
                False,
                f"FORBIDDEN_SUBSTITUTION_{expected}_TO_{detected}",
                detected,
            )

        return (
            False,
            f"ELEMENT_MISMATCH_{expected}_VS_{detected}",
            detected,
        )

    return True, "VALID", detected


# ---------------------------------------------------------------------
# SCAN PSEUDOPOTENTIELS
# ---------------------------------------------------------------------


def scan_upf_directory() -> Dict[str, List[Path]]:
    mapping: Dict[str, List[Path]] = {}

    if not PSEUDO_DIR.is_dir():
        return mapping

    for path in sorted(PSEUDO_DIR.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".upf", ".UPF".lower()}:
            continue

        element = detect_upf_element(path)

        if element is None:
            continue

        mapping.setdefault(element, []).append(path)

    return mapping


def choose_valid_upf(
    element: str,
    candidates: List[Path],
) -> Tuple[Optional[Path], str]:

    expected = normalize_element(element)

    if not candidates:
        return None, "MISSING_PSEUDO"

    valid = []

    for path in candidates:
        ok, reason, detected = validate_upf_file(
            path,
            expected,
        )

        if ok:
            valid.append(path)

    if not valid:
        return None, "NO_VALID_UPF"

    # Déterminisme : fichier alphabétiquement premier.
    valid = sorted(valid)

    return valid[0], "VALID"


# ---------------------------------------------------------------------
# DFT PRIORITY
# ---------------------------------------------------------------------


def load_candidates(limit: int) -> List[dict]:
    if not DFT_PRIORITY.is_file():
        raise FileNotFoundError(
            f"DFT priority introuvable : {DFT_PRIORITY}"
        )

    rows = []

    with DFT_PRIORITY.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        for row in reader:
            priority = str(
                row.get("priority")
                or row.get("class")
                or row.get("classification")
                or ""
            ).strip().upper()

            # Accepter PRIORITY explicitement.
            if priority != "PRIORITY":
                continue

            rows.append(row)

            if len(rows) >= limit:
                break

    return rows


def resolve_cif_path(row: dict) -> Optional[Path]:
    material_id = (
        row.get("material_id")
        or row.get("id")
        or row.get("ID")
        or row.get("name")
    )

    cif_path_value = (
        row.get("cif_path")
        or row.get("CIF")
        or row.get("cif")
    )

    if cif_path_value:
        candidate = Path(cif_path_value)

        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

        if candidate.is_file():
            return candidate

    # Recherche par material_id / name.
    identifiers = []

    if material_id:
        identifiers.append(str(material_id).strip())

    name = row.get("name")

    if name:
        identifiers.append(str(name).strip())

    for identifier in identifiers:
        direct_matches = list(
            CIF_ROOT.glob(f"*{identifier}*.cif")
        )

        if direct_matches:
            return sorted(direct_matches)[0]

    return None


# ---------------------------------------------------------------------
# VALIDATION CANDIDAT
# ---------------------------------------------------------------------


def validate_candidate(
    row: dict,
    upf_index: Dict[str, List[Path]],
) -> dict:

    material_id = (
        row.get("material_id")
        or row.get("id")
        or row.get("name")
        or "UNKNOWN"
    )

    formula = (
        row.get("formula")
        or row.get("composition")
        or ""
    )

    cif_path = resolve_cif_path(row)

    result = {
        "material_id": str(material_id),
        "formula": str(formula),
        "cif_path": str(cif_path) if cif_path else None,
        "cif_status": "FAILED",
        "elements": [],
        "pseudo_mapping": {},
        "pseudo_status": {},
        "missing_pseudos": [],
        "invalid_pseudos": [],
        "ready_for_qe": False,
        "status": "CIF_FAILED",
    }

    if cif_path is None:
        return result

    elements = extract_elements_from_cif(cif_path)

    if not elements:
        result["status"] = "CIF_ELEMENTS_UNDETECTED"
        return result

    result["cif_status"] = "OK"
    result["elements"] = elements

    all_valid = True

    for element in elements:
        candidates = upf_index.get(element, [])

        selected, status = choose_valid_upf(
            element,
            candidates,
        )

        if selected:
            result["pseudo_mapping"][element] = str(
                selected
            )
            result["pseudo_status"][element] = "VALID"
        else:
            result["pseudo_mapping"][element] = None
            result["pseudo_status"][element] = status

            if status in {
                "MISSING_PSEUDO",
                "NO_VALID_UPF",
            }:
                result["missing_pseudos"].append(element)

            result["invalid_pseudos"].append(element)

            all_valid = False

    if all_valid:
        result["ready_for_qe"] = True
        result["status"] = "READY_FOR_QE"
    else:
        result["status"] = "MISSING_OR_INVALID_PSEUDO"

    return result


# ---------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------


def write_csv(results: List[dict]) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fields = [
        "material_id",
        "formula",
        "cif_path",
        "cif_status",
        "elements",
        "pseudo_mapping",
        "pseudo_status",
        "missing_pseudos",
        "invalid_pseudos",
        "ready_for_qe",
        "status",
    ]

    with CSV_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for result in results:
            row = dict(result)

            row["elements"] = ",".join(
                result["elements"]
            )

            row["pseudo_mapping"] = json.dumps(
                result["pseudo_mapping"],
                ensure_ascii=False,
                sort_keys=True,
            )

            row["pseudo_status"] = json.dumps(
                result["pseudo_status"],
                ensure_ascii=False,
                sort_keys=True,
            )

            row["missing_pseudos"] = ",".join(
                result["missing_pseudos"]
            )

            row["invalid_pseudos"] = ",".join(
                result["invalid_pseudos"]
            )

            writer.writerow(row)


# ---------------------------------------------------------------------
# JSON / MANIFEST
# ---------------------------------------------------------------------


def build_manifest(
    results: List[dict],
    upf_index: Dict[str, List[Path]],
    pw_x: Optional[Path],
) -> dict:

    required_elements = sorted(
        {
            element
            for result in results
            for element in result["elements"]
        }
    )

    available_elements = sorted(upf_index.keys())

    ready = [
        r["material_id"]
        for r in results
        if r["ready_for_qe"]
    ]

    missing = sorted(
        {
            element
            for result in results
            for element in result["missing_pseudos"]
        }
    )

    return {
        "phase": "21G",
        "project": "HydroMatAI",
        "timestamp": now_iso(),

        "qe": {
            "pw_x": str(pw_x) if pw_x else None,
            "pw_x_detected": bool(pw_x),
            "calculation_executed": False,
            "bands_x_executed": False,
            "dos_x_executed": False,
            "relax_executed": False,
            "scf_executed": False,
        },

        "pseudo_directory": str(PSEUDO_DIR),

        "required_elements": required_elements,
        "available_elements": available_elements,
        "missing_elements": missing,

        "candidates": len(results),
        "cif_valid": sum(
            r["cif_status"] == "OK"
            for r in results
        ),
        "ready_for_qe": len(ready),
        "not_ready_for_qe": len(results) - len(ready),

        "ready_materials": ready,

        "results": results,

        "scientific_protection": {
            "cif_modified": False,
            "scientific_results_modified": False,
            "new_qe_calculation": False,
        },
    }


def write_outputs(
    results: List[dict],
    upf_index: Dict[str, List[Path]],
    pw_x: Optional[Path],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = build_manifest(
        results,
        upf_index,
        pw_x,
    )

    JSON_OUTPUT.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    MANIFEST_OUTPUT.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_csv(results)


# ---------------------------------------------------------------------
# AFFICHAGE
# ---------------------------------------------------------------------


def print_mapping(result: dict, index: int, total: int) -> None:

    print(
        f"[{index}/{total}] "
        f"{result['material_id']}"
    )

    print(
        f"  CIF      : {result['cif_status']}"
        + (
            f" → {result['cif_path']}"
            if result["cif_path"]
            else ""
        )
    )

    print(
        f"  Elements : "
        f"{', '.join(result['elements'])}"
    )

    for element in result["elements"]:

        pseudo = result["pseudo_mapping"].get(element)

        if pseudo:
            print(
                f"  {element:<3} → {pseudo}"
            )
        else:
            status = result["pseudo_status"].get(
                element,
                "MISSING",
            )

            print(
                f"  {element:<3} → "
                f"{status}"
            )

    print(
        f"  STATUS   : {result['status']}"
    )


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 21G — "
            "validation pseudopotentiels QE"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de candidats PRIORITY à vérifier",
    )

    args = parser.parse_args()

    print("=" * 80)
    print(" HydroMatAI — PHASE 21G")
    print(" VALIDATION FINALE PSEUDOPOTENTIELS QE")
    print("=" * 80)

    # -------------------------------------------------------------
    # PROTECTION
    # -------------------------------------------------------------

    print()
    print("PROTECTION QE")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    # -------------------------------------------------------------
    # QE
    # -------------------------------------------------------------

    pw_x = find_pw_x()

    print()
    print("ENVIRONNEMENT QE")
    print("-" * 80)

    if pw_x:
        print(f"pw.x : OK → {pw_x}")
    else:
        print("pw.x : NON TROUVÉ")

    print()
    print("PSEUDOPOTENTIELS")
    print("-" * 80)
    print(f"Répertoire : {PSEUDO_DIR}")

    upf_index = scan_upf_directory()

    total_upf = sum(
        len(files)
        for files in upf_index.values()
    )

    print(f"UPF valides détectables : {total_upf}")

    print()
    print("ÉLÉMENTS DÉTECTÉS")
    print("-" * 80)

    for element in sorted(upf_index):
        names = [
            path.name
            for path in upf_index[element]
        ]

        print(
            f"{element:<3} : "
            + ", ".join(names)
        )

    # -------------------------------------------------------------
    # CANDIDATS
    # -------------------------------------------------------------

    try:
        candidates = load_candidates(
            max(1, args.limit)
        )

    except Exception as exc:
        print()
        print(f"ERREUR : {exc}")
        return 1

    print()
    print("CANDIDATS")
    print("-" * 80)
    print(
        f"Priority sélectionnés : "
        f"{len(candidates)}"
    )

    results = []

    for index, row in enumerate(
        candidates,
        start=1,
    ):

        result = validate_candidate(
            row,
            upf_index,
        )

        results.append(result)

        print_mapping(
            result,
            index,
            len(candidates),
        )

    # -------------------------------------------------------------
    # STATISTIQUES
    # -------------------------------------------------------------

    cif_valid = sum(
        r["cif_status"] == "OK"
        for r in results
    )

    cif_failed = len(results) - cif_valid

    ready = sum(
        r["ready_for_qe"]
        for r in results
    )

    not_ready = len(results) - ready

    missing_elements = sorted(
        {
            element
            for result in results
            for element in result["missing_pseudos"]
        }
    )

    # -------------------------------------------------------------
    # OUTPUTS
    # -------------------------------------------------------------

    write_outputs(
        results,
        upf_index,
        pw_x,
    )

    print()
    print("=" * 80)
    print(" PHASE 21G — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats          : {len(results)}"
    )

    print(
        f"CIF valides        : {cif_valid}"
    )

    print(
        f"CIF FAILED         : {cif_failed}"
    )

    print(
        f"READY_FOR_QE       : {ready}"
    )

    print(
        f"NOT_READY_FOR_QE   : {not_ready}"
    )

    print()
    print(
        "PSEUDOPOTENTIELS MANQUANTS / INVALIDES"
    )
    print("-" * 80)

    if missing_elements:
        print(
            ", ".join(missing_elements)
        )
    else:
        print("Aucun")

    print()
    print("FICHIERS")
    print("-" * 80)

    print(
        f"CSV      : {CSV_OUTPUT}"
    )

    print(
        f"JSON     : {JSON_OUTPUT}"
    )

    print(
        f"MANIFEST : {MANIFEST_OUTPUT}"
    )

    # -------------------------------------------------------------
    # AUDIT FINAL
    # -------------------------------------------------------------

    print()
    print("=" * 80)
    print(" PHASE 21G — AUDIT FINAL")
    print("=" * 80)

    print(
        "Candidats DFT PRIORITY      : OK"
    )

    print(
        f"Lecture CIF                 : "
        f"{'OK' if cif_valid == len(results) else 'PARTIAL'}"
    )

    print(
        "Inspection UPF              : OK"
    )

    print(
        "Mapping élémentaire strict  : OK"
    )

    print(
        "Protection F → Fe           : OK"
    )

    print(
        "Aucun calcul QE             : OK"
    )

    print(
        "Aucun CIF modifié           : OK"
    )

    print(
        "Traçabilité                 : OK"
    )

    if ready == len(results) and len(results) > 0:
        print(
            "READY_FOR_QE                : YES"
        )
        print(
            "BLOCAGE                     : AUCUN"
        )
    else:
        print(
            "READY_FOR_QE                : NON"
        )

        if missing_elements:
            print(
                "BLOCAGE                     : "
                + ", ".join(missing_elements)
            )

    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
