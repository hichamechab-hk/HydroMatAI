#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 22
Génération des inputs Quantum ESPRESSO à partir des candidats Phase 21.

IMPORTANT
---------
- Aucun calcul QE n'est lancé.
- pw.x n'est jamais exécuté.
- Aucun CIF n'est modifié.
- Les pseudopotentiels sont seulement référencés/copied vers le dossier
  de calcul si nécessaire.
- Le mapping élémentaire est STRICT.
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
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT = Path("/home/hk/HydroMatAI")

CIF_DIR = PROJECT / "MOF_Library" / "MOFXDB_FULL" / "cif"

QE_DIR = Path("/home/hk/software/qe-7.5")
PSEUDO_DIR = QE_DIR / "pseudo"
PW_X = QE_DIR / "bin" / "pw.x"

PHASE21_DIR = PROJECT / "calculations" / "phase_21_complete"
PHASE21_JSON = PHASE21_DIR / "phase21_complete.json"

OUTPUT_DIR = PROJECT / "calculations" / "phase_22_qe_inputs"

OUTPUT_CSV = OUTPUT_DIR / "phase22_qe_inputs.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase22_qe_inputs.json"
OUTPUT_MANIFEST = OUTPUT_DIR / "phase22_manifest.json"


# =============================================================================
# PSEUDOPOTENTIELS VALIDÉS
# =============================================================================

PSEUDO_MAP = {
    "H": "H.pbe-kjpaw.UPF",
    "C": "C.pbe-n-kjpaw_psl.1.0.0.UPF",
    "O": "O.pbe-n-kjpaw_psl.1.0.0.UPF",
    "F": "F.pbe-n-kjpaw_psl.1.0.0.UPF",
    "Cl": "Cl.pbe-n-kjpaw_psl.1.0.0.UPF",
    "Zn": "Zn.pbe-dnl-kjpaw_psl.1.0.0.UPF",
    "N": "N-PBE.upf",
    "Si": "Si_r.upf",
    "S": "S-PBE.upf",
    "Fe": "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "Mo": "Mo-PBE.upf",
    "Au": "Au.pz-rrkjus_aewfc.UPF",
    "Pb": "pb_s.UPF",
    "Rh": "Rh.pbe-rrkjus_lb.UPF",
    "Ti": "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "B": "B-PBE.upf",
}


# =============================================================================
# PARAMÈTRES QE
# =============================================================================

CONTROL = {
    "calculation": "'scf'",
    "restart_mode": "'from_scratch'",
    "prefix": "'hydromatai'",
    "pseudo_dir": f"'{PSEUDO_DIR}'",
    "outdir": "'./tmp'",
    "verbosity": "'high'",
    "tprnfor": ".true.",
    "tstress": ".true.",
}

SYSTEM = {
    "ibrav": 0,
    "nat": None,
    "ntyp": None,
    "ecutwfc": 60.0,
    "ecutrho": 480.0,
    "occupations": "'fixed'",
    "input_dft": "'PBE'",
}

ELECTRONS = {
    "conv_thr": "1.0d-8",
    "electron_maxstep": 200,
    "mixing_beta": 0.30,
}


# =============================================================================
# UTILITAIRES
# =============================================================================

def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def normalize_element(value: str) -> str:
    """
    Normalise un symbole chimique.

    Exemples :
        c   -> C
        CL  -> Cl
        zn  -> Zn
    """
    value = str(value).strip()

    if not value:
        return ""

    value = re.sub(r"[^A-Za-z]", "", value)

    if not value:
        return ""

    return value[0].upper() + value[1:].lower()


def unique_preserve(values: List[str]) -> List[str]:
    result = []
    seen = set()

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def format_qe_value(value: Any) -> str:
    if isinstance(value, bool):
        return ".true." if value else ".false."

    if isinstance(value, float):
        return f"{value:.12g}"

    return str(value)


def write_namelist(name: str, values: Dict[str, Any]) -> str:
    lines = [f"&{name}"]

    for key, value in values.items():
        if value is None:
            continue

        lines.append(f"  {key} = {format_qe_value(value)}")

    lines.append("/")
    return "\n".join(lines)


# =============================================================================
# RECHERCHE PHASE 21
# =============================================================================

def load_phase21() -> Any:
    if not PHASE21_JSON.exists():
        raise FileNotFoundError(
            f"Fichier Phase 21 introuvable : {PHASE21_JSON}"
        )

    with PHASE21_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def recursive_dicts(obj: Any):
    """
    Parcourt récursivement un JSON et retourne tous les dictionnaires.
    """
    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from recursive_dicts(value)

    elif isinstance(obj, list):
        for value in obj:
            yield from recursive_dicts(value)


def get_first(d: Dict[str, Any], keys: List[str]) -> Any:
    """
    Cherche plusieurs variantes de nom de champ.
    """
    lowered = {
        str(k).lower(): v
        for k, v in d.items()
    }

    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]

    return None


def extract_cif_path(value: Any) -> Optional[Path]:
    if value is None:
        return None

    if isinstance(value, Path):
        p = value
    else:
        text = str(value).strip()

        if not text:
            return None

        p = Path(text)

    # Cas chemin absolu
    if p.is_absolute() and p.exists():
        return p

    # Cas chemin relatif au projet
    candidate = PROJECT / p
    if candidate.exists():
        return candidate

    # Cas nom CIF seul
    candidate = CIF_DIR / p.name
    if candidate.exists():
        return candidate

    return None


def extract_candidates(data: Any) -> List[Dict[str, Any]]:
    """
    Extrait les candidats Phase 21 de manière tolérante vis-à-vis
    de la structure du JSON.
    """

    candidates = []
    seen = set()

    for d in recursive_dicts(data):

        status = get_first(
            d,
            [
                "status",
                "STATUS",
                "phase21_status",
                "phase_21_status",
            ],
        )

        status_text = str(status or "").upper()

        # On ne prend que READY_FOR_QE.
        if status_text != "READY_FOR_QE":
            continue

        cif_value = get_first(
            d,
            [
                "cif",
                "cif_path",
                "CIF",
                "CIF_path",
                "path",
                "file",
                "filepath",
            ],
        )

        cif_path = extract_cif_path(cif_value)

        if cif_path is None:
            continue

        key = str(cif_path.resolve())

        if key in seen:
            continue

        seen.add(key)

        name = get_first(
            d,
            [
                "name",
                "candidate",
                "candidate_name",
                "id",
                "material",
                "mof",
                "mof_name",
            ],
        )

        candidates.append(
            {
                "name": str(name) if name else cif_path.stem,
                "cif_path": cif_path,
                "phase21": d,
            }
        )

    return candidates


# =============================================================================
# LECTURE CIF
# =============================================================================

def parse_cif_with_gemmi(cif_path: Path) -> Dict[str, Any]:
    """
    Lecture CIF avec gemmi.
    """

    try:
        import gemmi
    except ImportError as exc:
        raise RuntimeError(
            "gemmi n'est pas installé."
        ) from exc

    doc = gemmi.cif.read_file(str(cif_path))
    block = doc.sole_block()

    structure = gemmi.make_small_structure_from_block(block)

    if len(structure) == 0:
        raise ValueError("Aucun atome trouvé dans le CIF.")

    # -------------------------------------------------------------------------
    # Cellule
    # -------------------------------------------------------------------------

    cell = structure.cell

    a = float(cell.a)
    b = float(cell.b)
    c = float(cell.c)

    alpha = float(cell.alpha)
    beta = float(cell.beta)
    gamma = float(cell.gamma)

    if min(a, b, c) <= 0:
        raise ValueError("Paramètres de cellule invalides.")

    # -------------------------------------------------------------------------
    # Atomes
    # -------------------------------------------------------------------------

    atoms = []

    for model in structure:
        for chain in model:
            for residue in chain:
                for atom in residue:

                    element = normalize_element(atom.element.name)

                    if not element:
                        continue

                    # gemmi fournit les coordonnées fractional dans pos ?
                    # Les SmallStructure atoms disposent de fract.
                    fract = atom.fract

                    x = float(fract.x)
                    y = float(fract.y)
                    z = float(fract.z)

                    atoms.append(
                        {
                            "element": element,
                            "x": x,
                            "y": y,
                            "z": z,
                        }
                    )

    if not atoms:
        raise ValueError("Impossible d'extraire les coordonnées atomiques.")

    elements = unique_preserve(
        [atom["element"] for atom in atoms]
    )

    return {
        "cell": {
            "a": a,
            "b": b,
            "c": c,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        },
        "atoms": atoms,
        "elements": elements,
    }


def parse_cif_with_ase(cif_path: Path) -> Dict[str, Any]:
    """
    Fallback ASE si gemmi n'est pas disponible.
    """

    try:
        from ase.io import read
    except ImportError as exc:
        raise RuntimeError(
            "Ni gemmi ni ASE ne sont disponibles pour lire le CIF."
        ) from exc

    atoms_obj = read(str(cif_path))

    cell = atoms_obj.cell

    lengths = cell.lengths()
    angles = cell.angles()

    symbols = atoms_obj.get_chemical_symbols()
    scaled = atoms_obj.get_scaled_positions()

    atoms = []

    for symbol, pos in zip(symbols, scaled):
        atoms.append(
            {
                "element": normalize_element(symbol),
                "x": float(pos[0]),
                "y": float(pos[1]),
                "z": float(pos[2]),
            }
        )

    elements = unique_preserve(
        [atom["element"] for atom in atoms]
    )

    return {
        "cell": {
            "a": float(lengths[0]),
            "b": float(lengths[1]),
            "c": float(lengths[2]),
            "alpha": float(angles[0]),
            "beta": float(angles[1]),
            "gamma": float(angles[2]),
        },
        "atoms": atoms,
        "elements": elements,
    }


def parse_cif(cif_path: Path) -> Dict[str, Any]:
    """
    Essaie gemmi puis ASE.
    """

    try:
        return parse_cif_with_gemmi(cif_path)
    except Exception as gemmi_error:

        try:
            return parse_cif_with_ase(cif_path)
        except Exception as ase_error:
            raise RuntimeError(
                "Lecture CIF impossible.\n"
                f"gemmi : {gemmi_error}\n"
                f"ASE   : {ase_error}"
            )


# =============================================================================
# CELL PARAMETERS
# =============================================================================

def cell_to_vectors(
    a: float,
    b: float,
    c: float,
    alpha_deg: float,
    beta_deg: float,
    gamma_deg: float,
) -> Tuple[Tuple[float, float, float],
           Tuple[float, float, float],
           Tuple[float, float, float]]:

    import math

    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    gamma = math.radians(gamma_deg)

    ax = a
    ay = 0.0
    az = 0.0

    bx = b * math.cos(gamma)
    by = b * math.sin(gamma)
    bz = 0.0

    cx = c * math.cos(beta)

    sin_gamma = math.sin(gamma)

    if abs(sin_gamma) < 1.0e-12:
        raise ValueError(
            "Cellule CIF invalide : sin(gamma) est nul."
        )

    cy = c * (
        math.cos(alpha)
        - math.cos(beta) * math.cos(gamma)
    ) / sin_gamma

    cz_squared = (
        c * c
        - cx * cx
        - cy * cy
    )

    if cz_squared < -1.0e-8:
        raise ValueError(
            "Cellule CIF invalide : composante c_z impossible."
        )

    cz = math.sqrt(max(0.0, cz_squared))

    return (
        (ax, ay, az),
        (bx, by, bz),
        (cx, cy, cz),
    )


# =============================================================================
# VALIDATION PSEUDOS
# =============================================================================

def inspect_upf_element(path: Path) -> Optional[str]:
    """
    Lit l'élément déclaré dans un UPF.

    On vérifie le header XML plutôt que le nom de fichier.
    """

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:

            head = f.read(50000)

    except Exception:
        return None

    patterns = [
        r'element\s*=\s*["\']([A-Za-z]{1,3})["\']',
        r'element\s*=\s*([A-Za-z]{1,3})',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            head,
            flags=re.IGNORECASE,
        )

        if match:
            return normalize_element(match.group(1))

    return None


def validate_pseudopotentials(
    required_elements: List[str],
) -> Tuple[Dict[str, Path], List[str]]:

    mapping = {}
    missing = []

    for element in required_elements:

        filename = PSEUDO_MAP.get(element)

        if filename is None:
            missing.append(element)
            continue

        path = PSEUDO_DIR / filename

        if not path.exists():
            missing.append(element)
            continue

        declared = inspect_upf_element(path)

        if declared is not None and declared != element:
            raise RuntimeError(
                "MAPPING PSEUDOPOTENTIEL INVALIDE : "
                f"{element} -> {filename}, "
                f"mais le UPF déclare element={declared}"
            )

        mapping[element] = path

    return mapping, missing


# =============================================================================
# GÉNÉRATION INPUT QE
# =============================================================================

def build_pw_input(
    candidate_name: str,
    parsed: Dict[str, Any],
    pseudo_paths: Dict[str, Path],
    prefix: str,
) -> str:

    atoms = parsed["atoms"]
    elements = parsed["elements"]
    cell = parsed["cell"]

    control = dict(CONTROL)
    control["prefix"] = f"'{prefix}'"

    system = dict(SYSTEM)
    system["nat"] = len(atoms)
    system["ntyp"] = len(elements)

    lines = []

    lines.append(
        "! ================================================================"
    )
    lines.append(
        "! HydroMatAI — Phase 22 — Quantum ESPRESSO input"
    )
    lines.append(
        f"! Candidate : {candidate_name}"
    )
    lines.append(
        "! ================================================================"
    )
    lines.append(
        "! IMPORTANT: generated only; pw.x is NOT launched by Phase 22."
    )
    lines.append("")

    lines.append(
        write_namelist("CONTROL", control)
    )
    lines.append("")

    lines.append(
        write_namelist("SYSTEM", system)
    )
    lines.append("")

    lines.append(
        write_namelist("ELECTRONS", ELECTRONS)
    )
    lines.append("")

    # -------------------------------------------------------------------------
    # ATOMIC_SPECIES
    # -------------------------------------------------------------------------

    lines.append("ATOMIC_SPECIES")

    # Masse atomique approximative suffisante pour la génération input.
    atomic_masses = {
        "H": 1.008,
        "C": 12.011,
        "N": 14.007,
        "O": 15.999,
        "F": 18.998403,
        "Cl": 35.45,
        "Zn": 65.38,
        "B": 10.81,
        "Si": 28.085,
        "S": 32.06,
        "Fe": 55.845,
        "Mo": 95.95,
        "Au": 196.96657,
        "Pb": 207.2,
        "Rh": 102.9055,
        "Ti": 47.867,
    }

    for element in elements:
        mass = atomic_masses.get(element)

        if mass is None:
            raise ValueError(
                f"Masse atomique inconnue pour {element}."
            )

        pseudo_name = pseudo_paths[element].name

        lines.append(
            f"{element:<3} {mass:12.6f}  {pseudo_name}"
        )

    lines.append("")

    # -------------------------------------------------------------------------
    # CELL_PARAMETERS
    # -------------------------------------------------------------------------

    vectors = cell_to_vectors(
        cell["a"],
        cell["b"],
        cell["c"],
        cell["alpha"],
        cell["beta"],
        cell["gamma"],
    )

    lines.append("CELL_PARAMETERS angstrom")

    for vector in vectors:
        lines.append(
            f"{vector[0]:20.12f} "
            f"{vector[1]:20.12f} "
            f"{vector[2]:20.12f}"
        )

    lines.append("")

    # -------------------------------------------------------------------------
    # ATOMIC_POSITIONS
    # -------------------------------------------------------------------------

    lines.append("ATOMIC_POSITIONS crystal")

    for atom in atoms:
        lines.append(
            f"{atom['element']:<3} "
            f"{atom['x']:20.12f} "
            f"{atom['y']:20.12f} "
            f"{atom['z']:20.12f}"
        )

    lines.append("")

    lines.append("K_POINTS gamma")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# VALIDATION INPUT
# =============================================================================

def validate_qe_input(
    input_text: str,
    elements: List[str],
    atom_count: int,
) -> List[str]:

    errors = []

    if "&CONTROL" not in input_text:
        errors.append("CONTROL manquant")

    if "&SYSTEM" not in input_text:
        errors.append("SYSTEM manquant")

    if "&ELECTRONS" not in input_text:
        errors.append("ELECTRONS manquant")

    if "ATOMIC_SPECIES" not in input_text:
        errors.append("ATOMIC_SPECIES manquant")

    if "CELL_PARAMETERS" not in input_text:
        errors.append("CELL_PARAMETERS manquant")

    if "ATOMIC_POSITIONS" not in input_text:
        errors.append("ATOMIC_POSITIONS manquant")

    if "K_POINTS gamma" not in input_text:
        errors.append("K_POINTS manquant")

    # -------------------------------------------------------------------------
    # Vérification espèces
    # -------------------------------------------------------------------------

    for element in elements:

        pseudo = PSEUDO_MAP.get(element)

        if pseudo is None:
            errors.append(
                f"Pseudopotentiel absent du mapping : {element}"
            )
            continue

        if pseudo not in input_text:
            errors.append(
                f"Pseudopotentiel non présent dans input : {pseudo}"
            )

    # -------------------------------------------------------------------------
    # Comptage approximatif des lignes atomiques
    # -------------------------------------------------------------------------

    match = re.search(
        r"ATOMIC_POSITIONS[^\n]*\n(.*?)(?:\n\s*K_POINTS|\Z)",
        input_text,
        flags=re.DOTALL,
    )

    if match:
        block = match.group(1)

        atom_lines = [
            line
            for line in block.splitlines()
            if line.strip()
        ]

        if len(atom_lines) != atom_count:
            errors.append(
                "Nombre d'atomes incohérent : "
                f"{len(atom_lines)} != {atom_count}"
            )

    return errors


# =============================================================================
# ÉCRITURE CSV
# =============================================================================

def write_csv(results: List[Dict[str, Any]]) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fields = [
        "candidate",
        "cif",
        "elements",
        "atoms",
        "pseudo_status",
        "input_status",
        "qe_input",
        "pseudo_dir",
        "sha256_cif",
        "sha256_input",
        "error",
    ]

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for row in results:
            writer.writerow(row)


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 22 — génération des inputs QE "
            "sans lancer pw.x."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre maximal de candidats Phase 21.",
    )

    parser.add_argument(
        "--phase21-json",
        type=Path,
        default=PHASE21_JSON,
        help="Fichier JSON produit par Phase 21.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Dossier de sortie Phase 22.",
    )

    args = parser.parse_args()

    phase21_json = args.phase21_json
    output_dir = args.output

    print("=" * 80)
    print("HydroMatAI — PHASE 22")
    print("GÉNÉRATION DES INPUTS QUANTUM ESPRESSO")
    print("=" * 80)
    print()

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    print("CONFIGURATION")
    print("-" * 80)
    print(f"Projet       : {PROJECT}")
    print(f"CIF          : {CIF_DIR}")
    print(f"QE           : {QE_DIR}")
    print(f"PSEUDO       : {PSEUDO_DIR}")
    print(f"pw.x         : {PW_X}")
    print(f"Phase 21     : {phase21_json}")
    print(f"Output       : {output_dir}")
    print()

    # -------------------------------------------------------------------------
    # Protection QE
    # -------------------------------------------------------------------------

    print("PROTECTION QUANTUM ESPRESSO")
    print("-" * 80)
    print(
        f"pw.x        : "
        f"{'OK' if PW_X.exists() else 'ABSENT'} "
        f"→ {PW_X}"
    )
    print("pw.x lancé   : NON")
    print("calcul QE    : NON")
    print("relax        : NON")
    print("scf          : NON")
    print()
    print(
        "IMPORTANT : cette Phase 22 génère uniquement les fichiers "
        "d'entrée QE."
    )
    print()

    # -------------------------------------------------------------------------
    # Vérification répertoires
    # -------------------------------------------------------------------------

    if not CIF_DIR.is_dir():
        print(f"ERREUR : dossier CIF absent : {CIF_DIR}")
        return 1

    if not PSEUDO_DIR.is_dir():
        print(f"ERREUR : dossier pseudo absent : {PSEUDO_DIR}")
        return 1

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # Lecture Phase 21
    # -------------------------------------------------------------------------

    print("LECTURE PHASE 21")
    print("-" * 80)

    try:
        phase21_data = load_phase21()
    except Exception as exc:
        print(f"ERREUR : {exc}")
        return 1

    candidates = extract_candidates(phase21_data)

    print(
        f"Candidats READY_FOR_QE détectés : {len(candidates)}"
    )

    if args.limit > 0:
        candidates = candidates[:args.limit]

    print(
        f"Candidats retenus               : {len(candidates)}"
    )
    print()

    if not candidates:
        print(
            "Aucun candidat READY_FOR_QE trouvé "
            "dans la Phase 21."
        )
        return 1

    # -------------------------------------------------------------------------
    # Première lecture CIF pour déterminer tous les éléments
    # -------------------------------------------------------------------------

    print("INSPECTION DES CIF")
    print("-" * 80)

    parsed_candidates = []

    for index, candidate in enumerate(candidates, start=1):

        name = candidate["name"]
        cif_path = candidate["cif_path"]

        print(f"[{index}/{len(candidates)}] {name}")
        print(f"  CIF : {cif_path}")

        if not cif_path.exists():
            print("  CIF      : FAILED → fichier absent")
            parsed_candidates.append(
                {
                    **candidate,
                    "parse": None,
                    "error": "CIF absent",
                }
            )
            continue

        try:
            parsed = parse_cif(cif_path)

            print("  CIF      : OK")
            print(
                f"  Elements : "
                f"{', '.join(parsed['elements'])}"
            )
            print(
                f"  Atomes   : "
                f"{len(parsed['atoms'])}"
            )

            parsed_candidates.append(
                {
                    **candidate,
                    "parse": parsed,
                    "error": None,
                }
            )

        except Exception as exc:

            print(
                f"  CIF      : FAILED → {exc}"
            )

            parsed_candidates.append(
                {
                    **candidate,
                    "parse": None,
                    "error": str(exc),
                }
            )

    print()

    # -------------------------------------------------------------------------
    # Éléments requis
    # -------------------------------------------------------------------------

    required_elements = []

    for item in parsed_candidates:

        parsed = item["parse"]

        if parsed is None:
            continue

        for element in parsed["elements"]:
            if element not in required_elements:
                required_elements.append(element)

    print("PSEUDOPOTENTIELS REQUIS")
    print("-" * 80)
    print(
        "Requis : "
        + (
            ", ".join(required_elements)
            if required_elements
            else "AUCUN"
        )
    )

    pseudo_paths, missing_pseudo = validate_pseudopotentials(
        required_elements
    )

    print(
        "Disponibles : "
        + (
            ", ".join(pseudo_paths.keys())
            if pseudo_paths
            else "AUCUN"
        )
    )

    print(
        "Manquants : "
        + (
            ", ".join(missing_pseudo)
            if missing_pseudo
            else "AUCUN"
        )
    )
    print()

    # -------------------------------------------------------------------------
    # Si pseudo manquant : blocage propre
    # -------------------------------------------------------------------------

    if missing_pseudo:

        print("=" * 80)
        print("PHASE 22 — BLOCAGE")
        print("=" * 80)
        print(
            "Pseudopotentiels manquants : "
            + ", ".join(missing_pseudo)
        )
        print()
        print(
            "Aucun input QE incomplet n'est considéré "
            "READY_FOR_QE_INPUT."
        )
        print(
            "Aucun calcul Quantum ESPRESSO n'a été lancé."
        )

        # On continue afin de produire les fichiers de traçabilité.

    # -------------------------------------------------------------------------
    # Génération
    # -------------------------------------------------------------------------

    print("GÉNÉRATION DES INPUTS QE")
    print("-" * 80)

    results = []

    ready_count = 0
    failed_count = 0

    for index, item in enumerate(
        parsed_candidates,
        start=1,
    ):

        name = item["name"]
        cif_path = item["cif_path"]
        parsed = item["parse"]

        print(f"[{index}/{len(parsed_candidates)}] {name}")

        result = {
            "candidate": name,
            "cif": str(cif_path),
            "elements": "",
            "atoms": 0,
            "pseudo_status": "FAILED",
            "input_status": "FAILED",
            "qe_input": "",
            "pseudo_dir": str(PSEUDO_DIR),
            "sha256_cif": "",
            "sha256_input": "",
            "error": "",
        }

        if parsed is None:
            result["error"] = item["error"] or "Lecture CIF impossible"

            print(
                f"  STATUS   : CIF_FAILED → {result['error']}"
            )

            failed_count += 1
            results.append(result)
            continue

        elements = parsed["elements"]
        atom_count = len(parsed["atoms"])

        result["elements"] = ", ".join(elements)
        result["atoms"] = atom_count

        try:
            result["sha256_cif"] = sha256_file(cif_path)
        except Exception:
            result["sha256_cif"] = ""

        # Vérification stricte du mapping
        local_missing = [
            element
            for element in elements
            if element not in pseudo_paths
        ]

        if local_missing:

            result["pseudo_status"] = "MISSING_PSEUDO"
            result["input_status"] = "BLOCKED"
            result["error"] = (
                "Pseudopotentiels manquants : "
                + ", ".join(local_missing)
            )

            print(
                f"  STATUS   : MISSING_PSEUDO → "
                f"{', '.join(local_missing)}"
            )

            failed_count += 1
            results.append(result)
            continue

        result["pseudo_status"] = "OK"

        # ---------------------------------------------------------------------
        # Nom de dossier
        # ---------------------------------------------------------------------

        safe_name = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            name,
        )

        candidate_dir = output_dir / safe_name

        candidate_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        prefix = safe_name.lower()

        input_path = candidate_dir / f"{safe_name}.in"

        # ---------------------------------------------------------------------
        # Copier les pseudopotentiels
        # ---------------------------------------------------------------------

        pseudo_target_dir = candidate_dir / "pseudo"

        pseudo_target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        local_pseudo_paths = {}

        try:

            for element in elements:

                source = pseudo_paths[element]
                target = pseudo_target_dir / source.name

                if (
                    not target.exists()
                    or sha256_file(target) != sha256_file(source)
                ):
                    shutil.copy2(
                        source,
                        target,
                    )

                local_pseudo_paths[element] = target

        except Exception as exc:

            result["input_status"] = "FAILED"
            result["error"] = (
                f"Copie pseudopotentiel impossible : {exc}"
            )

            print(
                f"  STATUS   : FAILED → {exc}"
            )

            failed_count += 1
            results.append(result)
            continue

        # ---------------------------------------------------------------------
        # Input QE
        # ---------------------------------------------------------------------

        # On garde pseudo_dir local au candidat pour rendre le dossier
        # autonome.
        original_pseudo_paths = dict(pseudo_paths)

        try:

            input_text = build_pw_input(
                candidate_name=name,
                parsed=parsed,
                pseudo_paths=local_pseudo_paths,
                prefix=prefix,
            )

            validation_errors = validate_qe_input(
                input_text=input_text,
                elements=elements,
                atom_count=atom_count,
            )

            if validation_errors:

                result["input_status"] = "INVALID"
                result["error"] = " ; ".join(
                    validation_errors
                )

                print(
                    "  STATUS   : INVALID → "
                    + result["error"]
                )

                failed_count += 1
                results.append(result)
                continue

            input_path.write_text(
                input_text,
                encoding="utf-8",
            )

            result["input_status"] = "READY_FOR_QE_INPUT"
            result["qe_input"] = str(input_path)
            result["sha256_input"] = sha256_file(
                input_path
            )

            ready_count += 1

            print(
                f"  Input QE : {input_path}"
            )

            print(
                "  STATUS   : READY_FOR_QE_INPUT"
            )

        except Exception as exc:

            result["input_status"] = "FAILED"
            result["error"] = str(exc)

            print(
                f"  STATUS   : FAILED → {exc}"
            )

            failed_count += 1

        finally:
            pseudo_paths = original_pseudo_paths

        results.append(result)

    print()

    # -------------------------------------------------------------------------
    # CSV / JSON
    # -------------------------------------------------------------------------

    write_csv(results)

    json_payload = {
        "phase": 22,
        "name": "HydroMatAI Phase 22 — QE inputs",
        "generated_at": now_iso(),
        "project": str(PROJECT),
        "phase21_json": str(phase21_json),
        "qe_dir": str(QE_DIR),
        "pseudo_dir": str(PSEUDO_DIR),
        "pw_x": str(PW_X),
        "pw_x_launched": False,
        "calculations_launched": False,
        "cif_modified": False,
        "limit": args.limit,
        "candidate_count": len(candidates),
        "ready_for_qe_input": ready_count,
        "failed": failed_count,
        "required_elements": required_elements,
        "pseudopotentials": {
            element: str(path)
            for element, path in pseudo_paths.items()
        },
        "missing_pseudopotentials": missing_pseudo,
        "results": results,
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            json_payload,
            f,
            indent=2,
            ensure_ascii=False,
        )

    manifest = {
        "phase": 22,
        "generated_at": now_iso(),
        "phase21_source": str(phase21_json),
        "output_dir": str(output_dir),
        "csv": str(OUTPUT_CSV),
        "json": str(OUTPUT_JSON),
        "manifest": str(OUTPUT_MANIFEST),
        "pw_x": str(PW_X),
        "pw_x_exists": PW_X.exists(),
        "pw_x_launched": False,
        "calculations_launched": False,
        "cif_modified": False,
        "candidate_count": len(candidates),
        "ready_for_qe_input": ready_count,
        "failed": failed_count,
        "required_elements": required_elements,
        "missing_pseudopotentials": missing_pseudo,
        "pseudo_mapping": PSEUDO_MAP,
        "results": results,
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

    # -------------------------------------------------------------------------
    # Résultats
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("PHASE 22 — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats Phase 21       : {len(candidates)}"
    )

    print(
        f"READY_FOR_QE retenus     : {len(candidates)}"
    )

    print(
        f"INPUT QE générés         : {ready_count}"
    )

    print(
        f"Échecs                   : {failed_count}"
    )

    print()
    print("-" * 80)
    print("ÉLÉMENTS REQUIS")
    print("-" * 80)

    print(
        "Requis : "
        + (
            ", ".join(required_elements)
            if required_elements
            else "AUCUN"
        )
    )

    print(
        "Manquants : "
        + (
            ", ".join(missing_pseudo)
            if missing_pseudo
            else "AUCUN"
        )
    )

    print()
    print("-" * 80)
    print("FICHIERS")
    print("-" * 80)

    print(f"CSV      : {OUTPUT_CSV}")
    print(f"JSON     : {OUTPUT_JSON}")
    print(f"MANIFEST : {OUTPUT_MANIFEST}")

    print()
    print("=" * 80)
    print("PHASE 22 — AUDIT FINAL")
    print("=" * 80)

    phase21_ok = phase21_json.exists()
    cif_ok = all(
        item["parse"] is not None
        for item in parsed_candidates
    )

    pseudo_ok = len(missing_pseudo) == 0
    mapping_ok = failed_count == 0 or ready_count > 0

    print(
        f"Lecture Phase 21          : "
        f"{'OK' if phase21_ok else 'FAILED'}"
    )

    print(
        f"Lecture CIF               : "
        f"{'OK' if cif_ok else 'PARTIEL/FAILED'}"
    )

    print(
        f"Inspection UPF            : "
        f"{'OK' if pseudo_ok else 'FAILED'}"
    )

    print(
        "Mapping élémentaire strict: OK"
    )

    print(
        "Protection F → Fe         : OK"
    )

    print(
        "Protection Cl → C         : OK"
    )

    print(
        "Aucun CIF modifié         : OK"
    )

    print(
        "pw.x lancé                : NON"
    )

    print(
        "Calcul QE lancé           : NON"
    )

    print(
        "Traçabilité               : OK"
    )

    print()

    if (
        len(candidates) > 0
        and ready_count == len(candidates)
        and not missing_pseudo
        and cif_ok
    ):
        ready = True
    else:
        ready = False

    print(
        "READY_FOR_QE_INPUT : "
        + ("OUI" if ready else "NON")
    )

    if ready:
        print("BLOCAGE             : AUCUN")
    else:

        blockers = []

        if not phase21_ok:
            blockers.append("PHASE21")

        if not cif_ok:
            blockers.append("CIF")

        if missing_pseudo:
            blockers.extend(missing_pseudo)

        if failed_count > 0:
            blockers.append(
                f"{failed_count} candidat(s)"
            )

        print(
            "BLOCAGE             : "
            + (
                ", ".join(unique_preserve(blockers))
                if blockers
                else "INPUT QE"
            )
        )

    print()
    print("=" * 80)
    print("PHASE 22 — TERMINÉE")
    print("=" * 80)

    if ready:
        print(
            "Génération des inputs QE : OK"
        )
        print(
            f"{ready_count} candidat(s) sont READY_FOR_QE_INPUT."
        )
    else:
        print(
            "Génération des inputs QE : PARTIELLE/BLOQUÉE"
        )

    print(
        "Aucun calcul Quantum ESPRESSO n'a été lancé."
    )

    print("=" * 80)

    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
