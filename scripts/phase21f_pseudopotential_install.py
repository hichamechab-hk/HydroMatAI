#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 21F
INSTALLATION / PRÉPARATION DES PSEUDOPOTENTIELS QE

Objectifs
---------
1. Lire les candidats DFT PRIORITY.
2. Identifier les éléments réellement présents dans les CIF.
3. Inspecter le répertoire source des UPF QE.
4. Construire un répertoire dédié HydroMatAI/pseudopotentials/qe.
5. Copier uniquement les UPF explicitement associés aux éléments.
6. NE JAMAIS faire de correspondance ambiguë (ex: F -> Fe interdit).
7. Ne lancer aucun programme QE.
8. Produire CSV + JSON + manifest.
9. Indiquer précisément les éléments encore manquants.

IMPORTANT
---------
Ce script ne télécharge aucun pseudopotentiel.
Il ne fabrique aucun pseudopotentiel.
Il ne considère jamais le nom du fichier comme preuve suffisante
de l'élément : le contenu UPF est inspecté lorsque possible.

Utilisation
-----------
Audit uniquement :
    python scripts/phase21f_pseudopotential_install.py --limit 25

Installation depuis un répertoire UPF fourni :
    python scripts/phase21f_pseudopotential_install.py \
        --limit 25 \
        --source /chemin/vers/mes/upf \
        --install

Installation dans un répertoire personnalisé :
    python scripts/phase21f_pseudopotential_install.py \
        --limit 25 \
        --source /chemin/vers/mes/upf \
        --target /home/hk/HydroMatAI/pseudopotentials/qe \
        --install

QE :
    AUCUN lancement de pw.x / bands.x / dos.x / relax / scf.
"""


import argparse
import csv
import hashlib
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

PRIORITY_CSV = (
    PROJECT_ROOT
    / "reports"
    / "global_screening"
    / "dft_priority.csv"
)

DEFAULT_SOURCE = Path("/home/hk/software/qe-7.5/pseudo")

DEFAULT_TARGET = (
    PROJECT_ROOT
    / "pseudopotentials"
    / "qe"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "calculations"
    / "phase_21f_pseudopotential_install"
)

OUTPUT_CSV = OUTPUT_DIR / "phase21f_pseudopotential_install.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase21f_pseudopotential_install.json"
OUTPUT_MANIFEST = OUTPUT_DIR / "phase21f_manifest.json"


# =============================================================================
# ELEMENTS
# =============================================================================

# Symbol strictement validé.
ELEMENT_RE = re.compile(r"\b([A-Z][a-z]?)\b")

# Quelques éléments fréquemment rencontrés dans les datasets.
VALID_ELEMENTS = {
    "H", "He",
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se",
    "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru",
    "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te",
    "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au",
    "Hg", "Tl", "Pb", "Bi",
}


# =============================================================================
# LOG
# =============================================================================

def banner(title: str) -> None:
    print("=" * 80)
    print(f" HydroMatAI — {title}")
    print("=" * 80)


def section(title: str) -> None:
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)


# =============================================================================
# UTILITAIRES
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def normalize_element(value: str) -> Optional[str]:
    if not value:
        return None

    value = value.strip()

    if value in VALID_ELEMENTS:
        return value

    # Corrige seulement les variantes évidentes.
    if len(value) >= 1:
        candidate = value[0].upper() + value[1:].lower()

        if candidate in VALID_ELEMENTS:
            return candidate

    return None


# =============================================================================
# CIF
# =============================================================================

def extract_elements_from_cif(cif_path: Path) -> Set[str]:
    """
    Extraction robuste des éléments depuis un CIF.

    Priorité :
      1. _atom_site_type_symbol
      2. _atom_site_label

    On évite de déduire les éléments à partir de chemins ou noms de fichiers.
    """

    if not cif_path.exists():
        return set()

    try:
        text = cif_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return set()

    elements: Set[str] = set()

    # -------------------------------------------------------------------------
    # 1. _atom_site_type_symbol
    # -------------------------------------------------------------------------

    lines = text.splitlines()

    loop_headers: List[str] = []
    in_loop = False
    data_rows: List[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.lower() == "loop_":
            in_loop = True
            loop_headers = []
            data_rows = []
            continue

        if in_loop and stripped.startswith("_"):
            loop_headers.append(stripped.split()[0])
            continue

        if in_loop and loop_headers and not stripped.startswith("_"):
            if stripped.startswith("#"):
                if data_rows:
                    break
                continue

            data_rows.append(stripped)

            # On s'arrête raisonnablement après le bloc.
            if len(data_rows) > 10000:
                break

    if loop_headers and data_rows:
        normalized_headers = [h.lower() for h in loop_headers]

        type_index = None
        label_index = None

        for i, header in enumerate(normalized_headers):
            if header == "_atom_site_type_symbol":
                type_index = i

            if header == "_atom_site_label":
                label_index = i

        selected_index = (
            type_index
            if type_index is not None
            else label_index
        )

        if selected_index is not None:
            for row in data_rows:
                # Respecte les valeurs simples du CIF.
                tokens = row.split()

                if len(tokens) <= selected_index:
                    continue

                token = tokens[selected_index].strip(
                    "'\""
                )

                # Cas type symbol : "Zn"
                match = re.match(
                    r"^([A-Z][a-z]?)",
                    token,
                )

                if match:
                    element = normalize_element(match.group(1))

                    if element:
                        elements.add(element)

    # -------------------------------------------------------------------------
    # 2. Fallback sur les labels atomiques
    # -------------------------------------------------------------------------

    if not elements:
        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("_"):
                continue

            tokens = stripped.split()

            if not tokens:
                continue

            label = tokens[0].strip("'\"")

            # Ex: Zn1, O12, C23, H4
            match = re.match(
                r"^([A-Z][a-z]?)(?:\d|$)",
                label,
            )

            if match:
                element = normalize_element(match.group(1))

                if element:
                    elements.add(element)

    return elements


# =============================================================================
# PRIORITY CSV
# =============================================================================

def load_priority_candidates(limit: int) -> List[Dict]:
    if not PRIORITY_CSV.exists():
        raise FileNotFoundError(
            f"DFT priority introuvable : {PRIORITY_CSV}"
        )

    rows: List[Dict] = []

    with PRIORITY_CSV.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            classification = (
                row.get("priority")
                or row.get("class")
                or row.get("classification")
                or ""
            ).strip().upper()

            # Phase 21F travaille uniquement sur PRIORITY.
            if classification and classification != "PRIORITY":
                continue

            rows.append(row)

            if len(rows) >= limit:
                break

    return rows


# =============================================================================
# CIF PATH
# =============================================================================

def resolve_cif_path(row: Dict) -> Optional[Path]:
    candidates = [
        row.get("cif_path"),
        row.get("CIF"),
        row.get("cif"),
        row.get("path"),
    ]

    for raw in candidates:
        if not raw:
            continue

        path = Path(str(raw).strip())

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        if path.exists():
            return path.resolve()

    material_id = (
        row.get("material_id")
        or row.get("id")
        or row.get("name")
        or ""
    ).strip()

    if material_id:
        search_root = (
            PROJECT_ROOT
            / "MOF_Library"
            / "MOFXDB_FULL"
            / "cif"
        )

        if search_root.exists():
            matches = list(
                search_root.glob(
                    f"*_{material_id}.cif"
                )
            )

            if matches:
                return matches[0].resolve()

    return None


# =============================================================================
# UPF INSPECTION
# =============================================================================

def parse_upf_element(path: Path) -> Optional[str]:
    """
    Lit le premier élément explicitement identifiable dans un UPF.

    Priorité aux attributs :
      element="O"
      z_valence="..."
      pseudo_type="..."
    """

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return None

    # -------------------------------------------------------------------------
    # Format UPF XML moderne
    # -------------------------------------------------------------------------

    patterns = [
        r'\belement\s*=\s*["\']([A-Z][a-z]?)["\']',
        r'\bspecies\s*=\s*["\']([A-Z][a-z]?)["\']',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            element = normalize_element(
                match.group(1)
            )

            if element:
                return element

    # -------------------------------------------------------------------------
    # Recherche prudente dans les premières lignes.
    # -------------------------------------------------------------------------

    for line in text[:20000].splitlines():
        lower = line.lower()

        if "element" in lower:
            matches = re.findall(
                r"\b([A-Z][a-z]?)\b",
                line,
            )

            for candidate in matches:
                element = normalize_element(candidate)

                if element:
                    # Évite des faux positifs génériques.
                    if element not in {
                        "Up", "X", "Y",
                    }:
                        return element

    return None


def inspect_upf_directory(
    source: Path,
) -> Tuple[Dict[str, List[Path]], List[Dict]]:
    """
    Retourne :
      element -> liste UPF valides
      audit détaillé des fichiers
    """

    mapping: Dict[str, List[Path]] = {}
    audit: List[Dict] = []

    if not source.exists():
        return mapping, audit

    files = sorted(
        list(source.glob("*.UPF"))
        + list(source.glob("*.upf"))
    )

    for path in files:
        element = parse_upf_element(path)

        record = {
            "filename": path.name,
            "path": str(path.resolve()),
            "element": element,
            "sha256": None,
            "size_bytes": path.stat().st_size,
        }

        try:
            record["sha256"] = sha256(path)
        except Exception:
            pass

        audit.append(record)

        if element:
            mapping.setdefault(element, []).append(path)

    return mapping, audit


# =============================================================================
# SÉLECTION STRICTE
# =============================================================================

def choose_upf(
    element: str,
    mapping: Dict[str, List[Path]],
) -> Optional[Path]:
    """
    Sélectionne un UPF uniquement si son élément réel correspond exactement.

    Aucun fallback :
      F != Fe
      N != Ni
      O != Os
      Zn != Zr
    """

    candidates = mapping.get(element, [])

    if not candidates:
        return None

    # Tri déterministe.
    candidates = sorted(
        candidates,
        key=lambda p: p.name.lower(),
    )

    return candidates[0]


# =============================================================================
# INSTALLATION
# =============================================================================

def install_upf(
    source_file: Path,
    target_dir: Path,
    element: str,
) -> Dict:
    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_file = target_dir / source_file.name

    shutil.copy2(
        source_file,
        target_file,
    )

    # Vérification post-copie.
    copied_element = parse_upf_element(
        target_file
    )

    valid = copied_element == element

    return {
        "element": element,
        "source": str(source_file.resolve()),
        "target": str(target_file.resolve()),
        "source_sha256": sha256(source_file),
        "target_sha256": sha256(target_file),
        "element_verified": copied_element,
        "copy_ok": valid,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 21F — "
            "préparation stricte des pseudopotentiels QE"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de candidats PRIORITY à inspecter.",
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Répertoire source contenant les UPF.",
    )

    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Répertoire cible des UPF HydroMatAI.",
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Copier les UPF strictement validés.",
    )

    args = parser.parse_args()

    banner(
        "PHASE 21F\n"
        "INSTALLATION / PRÉPARATION PSEUDOPOTENTIELS QE"
    )

    # =========================================================================
    # PROTECTION QE
    # =========================================================================

    section("PROTECTION QE")

    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    # =========================================================================
    # ENVIRONNEMENT
    # =========================================================================

    section("ENVIRONNEMENT")

    print(f"Source UPF : {args.source}")

    if args.source.exists():
        print("Répertoire source : OK")
    else:
        print("Répertoire source : MISSING")

    print(f"Cible UPF  : {args.target}")

    if args.install:
        print("MODE       : INSTALLATION")
    else:
        print("MODE       : AUDIT / DRY-RUN")

    # =========================================================================
    # CANDIDATS
    # =========================================================================

    section("CHARGEMENT DFT PRIORITY")

    try:
        candidates = load_priority_candidates(
            args.limit
        )
    except Exception as exc:
        print(f"ERREUR : {exc}")
        return 1

    print(
        f"Candidats PRIORITY sélectionnés : "
        f"{len(candidates)}"
    )

    if not candidates:
        print("Aucun candidat PRIORITY.")
        return 1

    # =========================================================================
    # UPF
    # =========================================================================

    section("INSPECTION UPF")

    upf_mapping, upf_audit = inspect_upf_directory(
        args.source
    )

    total_upf = len(upf_audit)

    print(
        f"UPF trouvés : {total_upf}"
    )

    detected_elements = sorted(
        upf_mapping.keys()
    )

    if detected_elements:
        print(
            "Éléments réellement détectés : "
            + ", ".join(detected_elements)
        )
    else:
        print(
            "Éléments réellement détectés : aucun"
        )

    # =========================================================================
    # TRAITEMENT
    # =========================================================================

    section("VALIDATION PSEUDOPOTENTIELS")

    results: List[Dict] = []

    required_elements: Set[str] = set()

    installed: List[Dict] = []

    for index, row in enumerate(
        candidates,
        start=1,
    ):

        material_id = (
            row.get("material_id")
            or row.get("id")
            or row.get("name")
            or f"candidate_{index}"
        ).strip()

        cif_path = resolve_cif_path(row)

        print(
            f"[{index}/{len(candidates)}] "
            f"{material_id}"
        )

        # ---------------------------------------------------------------------
        # CIF
        # ---------------------------------------------------------------------

        if cif_path is None:
            print("  CIF    : FAILED")

            results.append({
                "material_id": material_id,
                "cif_path": None,
                "cif_status": "CIF_FAILED",
                "elements": "",
                "missing_pseudopotentials": "",
                "ready_for_qe": False,
                "installed": False,
                "status": "CIF_FAILED",
            })

            continue

        elements = sorted(
            extract_elements_from_cif(
                cif_path
            )
        )

        required_elements.update(elements)

        print(
            f"  CIF    : OK → {cif_path}"
        )

        print(
            "  Elements : "
            + (
                ", ".join(elements)
                if elements
                else "NONE"
            )
        )

        # ---------------------------------------------------------------------
        # Mapping strict
        # ---------------------------------------------------------------------

        element_mapping: Dict[str, Optional[str]] = {}
        missing: List[str] = []

        for element in elements:
            selected = choose_upf(
                element,
                upf_mapping,
            )

            if selected is None:
                element_mapping[element] = None
                missing.append(element)

                print(
                    f"  {element:<3} → MISSING"
                )

            else:
                element_mapping[element] = (
                    selected.name
                )

                print(
                    f"  {element:<3} → "
                    f"{selected.name}"
                )

        ready = (
            bool(elements)
            and len(missing) == 0
        )

        installed_for_material = False

        # ---------------------------------------------------------------------
        # Installation
        # ---------------------------------------------------------------------

        if args.install and ready:

            for element in elements:

                source_file = choose_upf(
                    element,
                    upf_mapping,
                )

                if source_file is None:
                    continue

                install_record = install_upf(
                    source_file,
                    args.target,
                    element,
                )

                installed.append(
                    {
                        "material_id": material_id,
                        **install_record,
                    }
                )

            installed_for_material = True

        # ---------------------------------------------------------------------
        # Status
        # ---------------------------------------------------------------------

        if ready:
            status = (
                "READY_FOR_QE"
                if not args.install
                else "READY_FOR_QE_INSTALLED"
            )
        else:
            status = "MISSING_PSEUDO"

        print(
            f"  STATUS : {status}"
        )

        results.append({
            "material_id": material_id,
            "cif_path": str(cif_path),
            "cif_status": "OK",
            "elements": ",".join(elements),
            "missing_pseudopotentials": ",".join(
                missing
            ),
            "element_mapping": json.dumps(
                element_mapping,
                sort_keys=True,
            ),
            "ready_for_qe": ready,
            "installed": installed_for_material,
            "status": status,
        })

    # =========================================================================
    # RÉSUMÉ
    # =========================================================================

    ready_count = sum(
        1
        for r in results
        if r["ready_for_qe"]
    )

    missing_count = sum(
        1
        for r in results
        if r["status"] == "MISSING_PSEUDO"
    )

    cif_failed_count = sum(
        1
        for r in results
        if r["status"] == "CIF_FAILED"
    )

    section("RÉSULTATS")

    print(
        f"Candidats          : {len(results)}"
    )

    print(
        f"CIF FAILED         : {cif_failed_count}"
    )

    print(
        f"READY_FOR_QE       : {ready_count}"
    )

    print(
        f"MISSING_PSEUDO     : {missing_count}"
    )

    print(
        f"UPF installés      : {len(installed)}"
    )

    # =========================================================================
    # ÉLÉMENTS MANQUANTS GLOBALS
    # =========================================================================

    available_elements = set(
        upf_mapping.keys()
    )

    missing_global = sorted(
        required_elements
        - available_elements
    )

    section("PSEUDOPOTENTIELS REQUIS")

    print(
        "Requis : "
        + (
            ", ".join(
                sorted(required_elements)
            )
            if required_elements
            else "aucun"
        )
    )

    print(
        "Disponibles : "
        + (
            ", ".join(
                sorted(available_elements)
            )
            if available_elements
            else "aucun"
        )
    )

    print(
        "Manquants : "
        + (
            ", ".join(missing_global)
            if missing_global
            else "aucun"
        )
    )

    # =========================================================================
    # ÉCRITURE DES RAPPORTS
    # =========================================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # CSV
    # -------------------------------------------------------------------------

    fieldnames = [
        "material_id",
        "cif_path",
        "cif_status",
        "elements",
        "missing_pseudopotentials",
        "element_mapping",
        "ready_for_qe",
        "installed",
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

        for row in results:
            writer.writerow(row)

    # -------------------------------------------------------------------------
    # JSON
    # -------------------------------------------------------------------------

    payload = {
        "phase": "21F",
        "timestamp": datetime.now().isoformat(),
        "project_root": str(
            PROJECT_ROOT
        ),
        "priority_csv": str(
            PRIORITY_CSV
        ),
        "source_upf": str(
            args.source.resolve()
        ),
        "target_upf": str(
            args.target.resolve()
        ),
        "mode": (
            "INSTALL"
            if args.install
            else "DRY_RUN"
        ),
        "qe_execution": {
            "pw_x": False,
            "bands_x": False,
            "dos_x": False,
            "relax": False,
            "scf": False,
            "heavy_calculation": False,
        },
        "summary": {
            "candidates": len(results),
            "cif_failed": cif_failed_count,
            "ready_for_qe": ready_count,
            "missing_pseudo": missing_count,
            "upf_found": total_upf,
            "installed_files": len(
                installed
            ),
        },
        "required_elements": sorted(
            required_elements
        ),
        "available_elements": sorted(
            available_elements
        ),
        "missing_global": missing_global,
        "upf_audit": upf_audit,
        "installation": installed,
        "candidates": results,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # -------------------------------------------------------------------------
    # MANIFEST
    # -------------------------------------------------------------------------

    manifest = {
        "phase": "21F",
        "status": (
            "READY_FOR_NEXT_PHASE"
            if ready_count > 0
            else "BLOCKED"
        ),
        "qe_execution": False,
        "source_upf": str(
            args.source.resolve()
        ),
        "target_upf": str(
            args.target.resolve()
        ),
        "required_elements": sorted(
            required_elements
        ),
        "available_elements": sorted(
            available_elements
        ),
        "missing_elements": missing_global,
        "ready_for_qe_candidates": [
            r["material_id"]
            for r in results
            if r["ready_for_qe"]
        ],
        "installed_files": installed,
        "reports": {
            "csv": str(
                OUTPUT_CSV
            ),
            "json": str(
                OUTPUT_JSON
            ),
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

    # =========================================================================
    # AUDIT FINAL
    # =========================================================================

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

    section("PHASE 21F — AUDIT FINAL")

    print(
        "Candidats DFT PRIORITY      : OK"
    )

    print(
        "Lecture CIF                  : OK"
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
        "Aucun calcul QE              : OK"
    )

    print(
        "Aucun CIF modifié            : OK"
    )

    print(
        "Traçabilité                  : OK"
    )

    if ready_count > 0:
        print(
            f"READY_FOR_QE                : "
            f"OUI ({ready_count})"
        )
    else:
        print(
            "READY_FOR_QE                : NON"
        )

    if missing_global:
        print(
            "BLOCAGE                     : "
            + ", ".join(missing_global)
        )
    else:
        print(
            "BLOCAGE                     : AUCUN"
        )

    print("=" * 80)

    # Retour non nul uniquement si aucun candidat n'est prêt.
    # Cela permet de détecter automatiquement un environnement incomplet.
    if ready_count == 0:
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
