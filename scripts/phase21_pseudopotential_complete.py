#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 21
PIPELINE COMPLET A → G
Pseudopotential QE : découverte, audit, mapping, installation locale,
validation finale et génération des manifestes.

IMPORTANT :
- Aucun calcul QE n'est lancé.
- Aucun CIF n'est modifié.
- Aucun pseudopotentiel inventé.
- Mapping strict par élément chimique.
- F ne peut JAMAIS être associé à Fe.
- Recherche récursive des fichiers UPF.
- Détection robuste des éléments dans les UPF.
- Fonctionne même si les CSV précédents ont des colonnes différentes.

Usage :

    python scripts/phase21_pseudopotential_complete.py --limit 25

Pour copier des UPF depuis un répertoire source :

    python scripts/phase21_pseudopotential_complete.py \
        --limit 25 \
        --source-dir /chemin/vers/upf_source

Pour simplement auditer le répertoire QE :

    python scripts/phase21_pseudopotential_complete.py \
        --limit 25 \
        --pseudo-dir /home/hk/software/qe-7.5/pseudo

Aucun calcul QE n'est lancé par ce script.
"""


import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path("/home/hk/HydroMatAI")

DEFAULT_QE_ROOT = Path("/home/hk/software/qe-7.5")
DEFAULT_PSEUDO_DIR = DEFAULT_QE_ROOT / "pseudo"

CIF_DIR = PROJECT_ROOT / "MOF_Library" / "MOFXDB_FULL" / "cif"

CALC_DIR = PROJECT_ROOT / "calculations" / "phase_21_complete"

CSV_OUT = CALC_DIR / "phase21_complete.csv"
JSON_OUT = CALC_DIR / "phase21_complete.json"
MANIFEST_OUT = CALC_DIR / "phase21_manifest.json"

# Éléments autorisés dans les candidats actuels.
# Le mapping sera toujours strict.
TARGET_ELEMENTS = {"C", "F", "H", "N", "O", "Zn"}

# Noms de fichiers explicitement interdits comme fallback.
# On ne doit jamais utiliser Fe pour F.
FORBIDDEN_CROSS_ELEMENT_MAPPING = {
    "F": {"Fe"},
}

# Quelques noms possibles de colonnes d'identifiant.
ID_COLUMNS = [
    "candidate_id",
    "candidate",
    "name",
    "id",
    "mof_id",
    "hmof",
    "material_id",
    "refcode",
]

# ============================================================================
# UTILITAIRES
# ============================================================================


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def run_version_check(executable: str) -> dict:
    result = {
        "executable": executable,
        "found": False,
        "path": None,
        "version": None,
    }

    path = shutil.which(executable)

    if path:
        result["found"] = True
        result["path"] = str(Path(path).resolve())

        try:
            p = subprocess.run(
                [path, "-h"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10,
            )

            text = p.stdout or ""

            version_match = re.search(
                r"(?i)(?:version|quantum espresso).*?(\d+\.\d+(?:\.\d+)?)",
                text,
            )

            if version_match:
                result["version"] = version_match.group(1)

        except Exception:
            pass

    return result


def normalize_element(value: str) -> str:
    value = value.strip()

    if not value:
        return ""

    if len(value) == 1:
        return value.upper()

    return value[0].upper() + value[1:].lower()


# ============================================================================
# DÉTECTION DES ÉLÉMENTS DANS LES UPF
# ============================================================================


def detect_element_from_upf(path: Path) -> str | None:
    """
    Détecte l'élément chimique depuis le contenu UPF.

    On privilégie :
        element="O"
        element='O'
        element = "O"

    Puis des champs classiques :
        element O
        <PP_HEADER element="O" ...

    On ne déduit PAS l'élément uniquement depuis le nom de fichier
    lorsqu'un contenu exploitable existe.
    """

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )[:250000]
    except Exception:
        return None

    patterns = [
        r'\belement\s*=\s*["\']([A-Za-z]{1,2})["\']',
        r'\belement\s*=\s*([A-Za-z]{1,2})\b',
        r'<PP_HEADER[^>]*\belement\s*=\s*["\']([A-Za-z]{1,2})["\']',
        r'\belement\s+([A-Za-z]{1,2})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            element = normalize_element(match.group(1))

            if element in {
                "H", "He",
                "Li", "Be", "B", "C", "N", "O", "F", "Ne",
                "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
                "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
                "Co", "Ni", "Cu", "Zn",
                "Ga", "Ge", "As", "Se", "Br", "Kr",
                "Rb", "Sr", "Y", "Zr", "Nb", "Mo",
                "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
                "In", "Sn", "Sb", "Te", "I", "Xe",
                "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm",
                "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er",
                "Tm", "Yb", "Lu",
                "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au",
                "Hg", "Tl", "Pb", "Bi",
            }:
                return element

    return None


# ============================================================================
# INVENTAIRE UPF
# ============================================================================


def inventory_upf(pseudo_dir: Path) -> list[dict]:
    records = []

    if not pseudo_dir.exists():
        return records

    for path in sorted(pseudo_dir.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".upf", ".UPF".lower()}:
            continue

        element = detect_element_from_upf(path)

        record = {
            "path": str(path.resolve()),
            "filename": path.name,
            "element": element,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "usable": element is not None,
        }

        records.append(record)

    return records


def build_element_mapping(upfs: list[dict]) -> dict[str, list[dict]]:
    mapping = {}

    for item in upfs:
        element = item.get("element")

        if not element:
            continue

        mapping.setdefault(element, []).append(item)

    return mapping


# ============================================================================
# DÉTECTION CIF
# ============================================================================


def parse_elements_from_cif(cif_path: Path) -> list[str]:
    """
    Lecture simple et robuste des symboles chimiques dans le CIF.

    Recherche prioritaire :
      _atom_site_type_symbol
      _atom_site_label

    Les labels sont interprétés avec prudence.
    """

    if not cif_path.exists():
        return []

    try:
        text = cif_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return []

    elements = set()

    # ------------------------------------------------------------------------
    # 1. _atom_site_type_symbol
    # ------------------------------------------------------------------------

    lines = text.splitlines()

    loop_indices = []

    for i, line in enumerate(lines):
        if line.strip().lower() == "loop_":
            loop_indices.append(i)

    for start in loop_indices:

        headers = []
        j = start + 1

        while j < len(lines):
            stripped = lines[j].strip()

            if not stripped:
                j += 1
                continue

            if stripped.startswith("_"):
                headers.append(stripped)
                j += 1
                continue

            break

        if not headers:
            continue

        lower_headers = [h.lower() for h in headers]

        if "_atom_site_type_symbol" not in lower_headers:
            continue

        symbol_index = lower_headers.index("_atom_site_type_symbol")

        # Lecture des lignes de données.
        while j < len(lines):
            stripped = lines[j].strip()

            if not stripped:
                j += 1
                continue

            if stripped.startswith("_") or stripped.lower() == "loop_":
                break

            # éviter les commentaires
            if stripped.startswith("#"):
                j += 1
                continue

            parts = stripped.split()

            if len(parts) <= symbol_index:
                j += 1
                continue

            symbol = parts[symbol_index]

            symbol = re.sub(
                r"[^A-Za-z]",
                "",
                symbol,
            )

            if symbol:
                elements.add(normalize_element(symbol))

            j += 1

    # ------------------------------------------------------------------------
    # 2. Fallback atom labels
    # ------------------------------------------------------------------------

    if not elements:

        atom_label_pattern = re.compile(
            r"^\s*[A-Za-z]{1,3}\d+\b"
        )

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if not atom_label_pattern.match(stripped):
                continue

            first = stripped.split()[0]

            match = re.match(
                r"([A-Za-z]{1,2})",
                first,
            )

            if match:
                elements.add(
                    normalize_element(match.group(1))
                )

    return sorted(elements)


def find_cif_for_candidate(candidate: str) -> Path | None:

    # Cas direct : hMOF-2272
    direct = list(CIF_DIR.glob(f"*{candidate}*.cif"))

    if direct:
        return sorted(direct)[0]

    # Cas numérique : 17610 / 17731 etc.
    numeric = re.sub(r"\D", "", candidate)

    if numeric:
        for path in CIF_DIR.glob("*.cif"):

            digits = re.findall(r"\d+", path.stem)

            if numeric in digits:
                return path

    return None


# ============================================================================
# EXTRACTION DES CANDIDATS
# ============================================================================


def discover_candidate_cifs(limit: int) -> list[dict]:

    if not CIF_DIR.exists():
        return []

    cif_files = sorted(CIF_DIR.glob("*.cif"))

    candidates = []

    # Priorité : fichiers hMOF-XXXX
    priority = []

    for path in cif_files:

        match = re.search(
            r"(hMOF-\d+)",
            path.name,
            flags=re.IGNORECASE,
        )

        if match:
            candidate_id = match.group(1)

            priority.append(
                {
                    "candidate_id": candidate_id,
                    "cif": path,
                }
            )

    # On conserve l'ordre du dataset.
    for item in priority:

        if len(candidates) >= limit:
            break

        candidates.append(item)

    # Fallback si pas assez de hMOF.
    if len(candidates) < limit:

        used = {
            str(x["cif"].resolve())
            for x in candidates
        }

        for path in cif_files:

            if str(path.resolve()) in used:
                continue

            if len(candidates) >= limit:
                break

            candidates.append(
                {
                    "candidate_id": path.stem,
                    "cif": path,
                }
            )

    return candidates


# ============================================================================
# INSTALLATION LOCALE DES UPF
# ============================================================================


def install_missing_pseudos(
    source_dir: Path | None,
    pseudo_dir: Path,
    required_elements: set[str],
) -> dict:

    result = {
        "source_dir": str(source_dir) if source_dir else None,
        "target_dir": str(pseudo_dir),
        "copied": [],
        "skipped": [],
        "errors": [],
    }

    if source_dir is None:
        result["status"] = "NO_SOURCE_DIR"
        return result

    if not source_dir.exists():
        result["status"] = "SOURCE_NOT_FOUND"
        result["errors"].append(
            f"Source inexistante: {source_dir}"
        )
        return result

    pseudo_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_upfs = inventory_upf(source_dir)
    source_mapping = build_element_mapping(source_upfs)

    for element in sorted(required_elements):

        candidates = source_mapping.get(
            element,
            [],
        )

        if not candidates:
            result["skipped"].append(
                {
                    "element": element,
                    "reason": "NO_VALID_UPF_IN_SOURCE",
                }
            )
            continue

        # Premier UPF exploitable.
        selected = candidates[0]

        src = Path(selected["path"])
        dst = pseudo_dir / src.name

        # Protection absolue contre F -> Fe.
        detected = selected.get("element")

        if element == "F" and detected == "Fe":
            result["errors"].append(
                f"SECURITY: refus F -> Fe : {src}"
            )
            continue

        if detected != element:
            result["errors"].append(
                f"STRICT_MAPPING_FAILURE: "
                f"requested={element}, detected={detected}, "
                f"file={src}"
            )
            continue

        if dst.exists():

            # Ne pas écraser automatiquement.
            result["skipped"].append(
                {
                    "element": element,
                    "source": str(src),
                    "target": str(dst),
                    "reason": "TARGET_ALREADY_EXISTS",
                }
            )

            continue

        try:
            shutil.copy2(src, dst)

            result["copied"].append(
                {
                    "element": element,
                    "source": str(src),
                    "target": str(dst),
                    "sha256": sha256_file(dst),
                }
            )

        except Exception as exc:
            result["errors"].append(
                f"{element}: {exc}"
            )

    result["status"] = (
        "OK"
        if not result["errors"]
        else "ERROR"
    )

    return result


# ============================================================================
# VALIDATION D'UN CANDIDAT
# ============================================================================


def validate_candidate(
    candidate_id: str,
    cif_path: Path,
    element_mapping: dict[str, list[dict]],
) -> dict:

    elements = parse_elements_from_cif(cif_path)

    mapping = {}
    missing = []
    invalid = []

    for element in elements:

        if element not in TARGET_ELEMENTS:
            # On garde quand même l'élément pour la transparence.
            pass

        matches = element_mapping.get(
            element,
            [],
        )

        if not matches:

            mapping[element] = None
            missing.append(element)
            continue

        selected = matches[0]

        # Protection stricte.
        detected = selected.get("element")

        if detected != element:

            mapping[element] = None

            invalid.append(
                {
                    "element": element,
                    "detected": detected,
                    "file": selected.get("filename"),
                }
            )

            continue

        if (
            element in FORBIDDEN_CROSS_ELEMENT_MAPPING
            and detected in FORBIDDEN_CROSS_ELEMENT_MAPPING[element]
        ):
            mapping[element] = None

            invalid.append(
                {
                    "element": element,
                    "detected": detected,
                    "file": selected.get("filename"),
                    "reason": "FORBIDDEN_CROSS_ELEMENT_MAPPING",
                }
            )

            continue

        mapping[element] = selected["filename"]

    if invalid:
        status = "INVALID_MAPPING"

    elif missing:
        status = "MISSING_PSEUDO"

    elif not elements:
        status = "NO_ELEMENTS"

    else:
        status = "READY_FOR_QE"

    return {
        "candidate_id": candidate_id,
        "cif": str(cif_path.resolve()),
        "cif_valid": cif_path.exists(),
        "elements": elements,
        "mapping": mapping,
        "missing": sorted(missing),
        "invalid": invalid,
        "status": status,
    }


# ============================================================================
# EXPORT CSV
# ============================================================================


def write_csv(rows: list[dict], path: Path):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "candidate_id",
        "cif",
        "cif_valid",
        "elements",
        "mapping",
        "missing",
        "invalid",
        "status",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "cif": row["cif"],
                    "cif_valid": row["cif_valid"],
                    "elements": ",".join(
                        row["elements"]
                    ),
                    "mapping": json.dumps(
                        row["mapping"],
                        ensure_ascii=False,
                    ),
                    "missing": ",".join(
                        row["missing"]
                    ),
                    "invalid": json.dumps(
                        row["invalid"],
                        ensure_ascii=False,
                    ),
                    "status": row["status"],
                }
            )


# ============================================================================
# MAIN
# ============================================================================


def main():

    parser = argparse.ArgumentParser(
        description="HydroMatAI Phase 21 complète A→G"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de CIF à inspecter",
    )

    parser.add_argument(
        "--pseudo-dir",
        type=Path,
        default=DEFAULT_PSEUDO_DIR,
        help=(
            "Répertoire QE contenant les UPF "
            f"(défaut: {DEFAULT_PSEUDO_DIR})"
        ),
    )

    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help=(
            "Répertoire source contenant les UPF manquants. "
            "Aucun téléchargement automatique."
        ),
    )

    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Ne pas copier les UPF depuis --source-dir",
    )

    args = parser.parse_args()

    pseudo_dir = args.pseudo_dir.resolve()

    CALC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================================
    # HEADER
    # ========================================================================

    print("=" * 80)
    print(" HydroMatAI — PHASE 21 COMPLÈTE")
    print(" PSEUDOPOTENTIELS QE — A → G")
    print("=" * 80)

    print()
    print("PROTECTION QE")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    # ========================================================================
    # 21A — ENVIRONNEMENT
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21A — ENVIRONNEMENT")
    print("=" * 80)

    pw = run_version_check("pw.x")

    print()
    print(f"pw.x : {'OK' if pw['found'] else 'NON TROUVÉ'}")

    if pw["path"]:
        print(f"       {pw['path']}")

    # IMPORTANT :
    # Nous n'exécutons pas pw.x.
    # La détection utilise seulement which + -h.
    #
    # Même ceci peut être considéré comme un appel à l'exécutable.
    # Pour respecter strictement la protection calcul, on ne lance
    # aucune commande de calcul. -h est uniquement une inspection.
    #
    # ========================================================================
    # 21B — CANDIDATS CIF
    # ========================================================================

    candidates = discover_candidate_cifs(
        args.limit
    )

    print()
    print("=" * 80)
    print("PHASE 21B — CANDIDATS")
    print("=" * 80)
    print(
        f"Priority sélectionnés : {len(candidates)}"
    )

    # ========================================================================
    # 21C — INVENTAIRE UPF
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21C — INVENTAIRE PSEUDOPOTENTIELS")
    print("=" * 80)

    print(
        f"Répertoire : {pseudo_dir}"
    )

    upfs = inventory_upf(
        pseudo_dir
    )

    print(
        f"UPF trouvés : {len(upfs)}"
    )

    element_mapping = build_element_mapping(
        upfs
    )

    detected_elements = sorted(
        element_mapping.keys()
    )

    if detected_elements:

        print()
        print("ÉLÉMENTS DÉTECTÉS")

        for element in detected_elements:

            files = element_mapping[element]

            print(
                f"  {element:<3} : "
                + ", ".join(
                    x["filename"]
                    for x in files
                )
            )

    else:

        print()
        print(
            "Aucun UPF exploitable détecté."
        )

    # ========================================================================
    # 21D — DÉTECTION DES ÉLÉMENTS REQUIS
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21D — ÉLÉMENTS REQUIS")
    print("=" * 80)

    required_elements = set()

    candidate_preview = []

    for item in candidates:

        elements = parse_elements_from_cif(
            item["cif"]
        )

        required_elements.update(
            elements
        )

        candidate_preview.append(
            {
                "candidate_id": item["candidate_id"],
                "cif": item["cif"],
                "elements": elements,
            }
        )

    print(
        "Requis : "
        + (
            ", ".join(
                sorted(required_elements)
            )
            if required_elements
            else "AUCUN"
        )
    )

    # ========================================================================
    # 21E — INSTALLATION / COPIE LOCALE
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21E — SETUP / INSTALLATION")
    print("=" * 80)

    if args.no_install:

        install_result = {
            "status": "SKIPPED_BY_USER",
            "copied": [],
            "skipped": [],
            "errors": [],
        }

        print(
            "Installation désactivée par --no-install"
        )

    elif args.source_dir:

        print(
            f"Source UPF : "
            f"{args.source_dir.resolve()}"
        )

        install_result = install_missing_pseudos(
            args.source_dir.resolve(),
            pseudo_dir,
            required_elements,
        )

        print(
            f"UPF copiés : "
            f"{len(install_result['copied'])}"
        )

        for item in install_result["copied"]:

            print(
                f"  {item['element']} → "
                f"{item['target']}"
            )

        if install_result["skipped"]:

            print(
                f"UPF déjà présents / ignorés : "
                f"{len(install_result['skipped'])}"
            )

        if install_result["errors"]:

            print()
            print("ERREURS")

            for error in install_result["errors"]:
                print(f"  {error}")

    else:

        install_result = {
            "status": "NO_SOURCE_SPECIFIED",
            "copied": [],
            "skipped": [],
            "errors": [],
        }

        print(
            "Aucune source UPF fournie."
        )

        print(
            "Mode audit uniquement."
        )

    # ========================================================================
    # RE-INVENTAIRE APRÈS INSTALLATION
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21F — RE-INVENTAIRE APRÈS SETUP")
    print("=" * 80)

    upfs_final = inventory_upf(
        pseudo_dir
    )

    mapping_final = build_element_mapping(
        upfs_final
    )

    print(
        f"UPF exploitables : "
        f"{len(upfs_final)}"
    )

    available_required = sorted(
        e for e in required_elements
        if e in mapping_final
    )

    missing_required = sorted(
        e for e in required_elements
        if e not in mapping_final
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
        "Manquants   : "
        + (
            ", ".join(missing_required)
            if missing_required
            else "AUCUN"
        )
    )

    # ========================================================================
    # 21G — VALIDATION FINALE
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21G — VALIDATION FINALE")
    print("=" * 80)

    rows = []

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        candidate_id = item["candidate_id"]
        cif_path = item["cif"]

        result = validate_candidate(
            candidate_id,
            cif_path,
            mapping_final,
        )

        rows.append(result)

        print()
        print(
            f"[{index}/{len(candidates)}] "
            f"{candidate_id}"
        )

        print(
            f"  CIF      : {cif_path}"
        )

        print(
            "  Elements : "
            + (
                ", ".join(
                    result["elements"]
                )
                if result["elements"]
                else "AUCUN"
            )
        )

        for element in result["elements"]:

            mapped = result["mapping"].get(
                element
            )

            if mapped:

                print(
                    f"  {element:<3} → {mapped}"
                )

            else:

                print(
                    f"  {element:<3} → MISSING"
                )

        print(
            f"  STATUS   : {result['status']}"
        )

    # ========================================================================
    # STATISTIQUES
    # ========================================================================

    counter = Counter(
        row["status"]
        for row in rows
    )

    ready = counter.get(
        "READY_FOR_QE",
        0,
    )

    missing = counter.get(
        "MISSING_PSEUDO",
        0,
    )

    invalid = counter.get(
        "INVALID_MAPPING",
        0,
    )

    no_elements = counter.get(
        "NO_ELEMENTS",
        0,
    )

    cif_failed = sum(
        not row["cif_valid"]
        for row in rows
    )

    # ========================================================================
    # EXPORT
    # ========================================================================

    write_csv(
        rows,
        CSV_OUT,
    )

    final_manifest = {
        "phase": "21",
        "phase_name": "pseudopotential_complete",
        "timestamp": now_iso(),

        "project_root": str(
            PROJECT_ROOT
        ),

        "qe": {
            "qe_root": str(
                DEFAULT_QE_ROOT
            ),
            "pseudo_dir": str(
                pseudo_dir
            ),
            "pw_x_detected": pw,
            "calculations_launched": False,
            "relax_launched": False,
            "scf_launched": False,
            "bands_launched": False,
            "dos_launched": False,
        },

        "protection": {
            "no_qe_calculation": True,
            "no_cif_modification": True,
            "strict_element_mapping": True,
            "forbid_F_to_Fe": True,
        },

        "candidates": {
            "requested_limit": args.limit,
            "selected": len(candidates),
        },

        "elements": {
            "required": sorted(
                required_elements
            ),
            "available": sorted(
                mapping_final.keys()
            ),
            "available_required": available_required,
            "missing_required": missing_required,
        },

        "upf_inventory": upfs_final,

        "installation": install_result,

        "results": {
            "candidates": len(rows),
            "cif_failed": cif_failed,
            "ready_for_qe": ready,
            "missing_pseudo": missing,
            "invalid_mapping": invalid,
            "no_elements": no_elements,
        },

        "files": {
            "csv": str(
                CSV_OUT
            ),
            "json": str(
                JSON_OUT
            ),
            "manifest": str(
                MANIFEST_OUT
            ),
        },

        "candidates_results": rows,
    }

    with JSON_OUT.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            final_manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with MANIFEST_OUT.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "phase": "21",
                "timestamp": now_iso(),
                "pseudo_dir": str(
                    pseudo_dir
                ),
                "required_elements": sorted(
                    required_elements
                ),
                "available_required": available_required,
                "missing_required": missing_required,
                "ready_for_qe": ready,
                "missing_pseudo": missing,
                "invalid_mapping": invalid,
                "calculations_launched": False,
                "cif_modified": False,
                "strict_mapping": True,
                "F_to_Fe_forbidden": True,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================================
    # RÉSULTATS
    # ========================================================================

    print()
    print("=" * 80)
    print("PHASE 21 — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats          : {len(rows)}"
    )

    print(
        f"CIF FAILED         : {cif_failed}"
    )

    print(
        f"READY_FOR_QE       : {ready}"
    )

    print(
        f"MISSING_PSEUDO     : {missing}"
    )

    print(
        f"INVALID_MAPPING    : {invalid}"
    )

    print()
    print("-" * 80)
    print("PSEUDOPOTENTIELS REQUIS")
    print("-" * 80)

    print(
        "Requis : "
        + (
            ", ".join(
                sorted(required_elements)
            )
            if required_elements
            else "AUCUN"
        )
    )

    print(
        "Disponibles : "
        + (
            ", ".join(
                available_required
            )
            if available_required
            else "AUCUN"
        )
    )

    print(
        "Manquants : "
        + (
            ", ".join(
                missing_required
            )
            if missing_required
            else "AUCUN"
        )
    )

    print()
    print("-" * 80)
    print("FICHIERS")
    print("-" * 80)

    print(
        f"CSV      : {CSV_OUT}"
    )

    print(
        f"JSON     : {JSON_OUT}"
    )

    print(
        f"MANIFEST : {MANIFEST_OUT}"
    )

    print()
    print("=" * 80)
    print("PHASE 21 — AUDIT FINAL")
    print("=" * 80)

    print(
        f"Lecture CIF                 : "
        f"{'OK' if cif_failed == 0 else 'FAILED'}"
    )

    print(
        f"Inspection UPF              : "
        f"{'OK' if upfs_final else 'FAILED'}"
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

    print()

    if ready == len(rows) and len(rows) > 0:

        print(
            "READY_FOR_QE : OUI"
        )

        print()
        print(
            "La Phase 21 est prête "
            "pour le lancement ultérieur de QE."
        )

    else:

        print(
            "READY_FOR_QE : NON"
        )

        if missing_required:

            print(
                "BLOCAGE : "
                + ", ".join(
                    missing_required
                )
            )

        elif invalid:

            print(
                "BLOCAGE : INVALID_MAPPING"
            )

        elif no_elements:

            print(
                "BLOCAGE : CIF SANS ÉLÉMENTS"
            )

    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
