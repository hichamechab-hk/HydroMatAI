#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — DFT GLOBAL COMPLETE

Workflow unique
---------------

TOP200_GLOBAL_H2_RANKED.csv
        |
        v
Validation CIF
        |
        v
Maille primitive
        |
        v
Contrôle taille DFT
        |
        v
Contrôle pseudopotentiels
        |
        v
TOP20 DFT GLOBAL
        |
        v
Génération QE
        |
        +--> pw.relax.in
        |
        +--> pw.scf.in
        |
        v
Audit / Manifest
        |
        v
--execute
        |
        +--> RELAX
        |
        +--> SCF


Par défaut :
    Aucun calcul QE n'est lancé.

Préparation :
    python scripts/dft_global_complete.py

Test limité :
    python scripts/dft_global_complete.py --limit 5

Calcul QE :
    python scripts/dft_global_complete.py --execute

Calcul limité :
    python scripts/dft_global_complete.py --execute --limit 5
"""



import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from pymatgen.core import Structure


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT = Path("/home/hk/HydroMatAI")

REPORT_DIR = PROJECT / "reports" / "global_screening"

INPUT_TOP200 = REPORT_DIR / "TOP200_GLOBAL_H2_RANKED.csv"

OUTPUT_TOP20 = REPORT_DIR / "TOP20_DFT_GLOBAL.csv"

QE_DIR = PROJECT / "calculations" / "global_screening" / "qe"

TOP20_DIR = QE_DIR / "TOP20"

PSEUDO_DIR = TOP20_DIR / "pseudo"

MANIFEST_FILE = TOP20_DIR / "dft_global_manifest.json"

AUDIT_FILE = TOP20_DIR / "dft_global_audit.csv"

JOBS_FILE = TOP20_DIR / "dft_global_jobs.json"


# ----------------------------------------------------------------------------
# Quantum ESPRESSO
# ----------------------------------------------------------------------------

QE_INSTALL_DIR = Path("/home/hk/software/qe-7.5")

PW_X = QE_INSTALL_DIR / "bin" / "pw.x"


# ----------------------------------------------------------------------------
# Limites
# ----------------------------------------------------------------------------

MAX_PRIMITIVE_ATOMS = 300

MIN_PRIMITIVE_ATOMS = 2

TOP_N = 20

DEFAULT_LIMIT = 20

DEFAULT_TIMEOUT = 3600


# ============================================================================
# PSEUDOPOTENTIELS
# ============================================================================

"""
Mapping STRICT utilisé pour la génération QE.

Les noms correspondent aux fichiers actuellement présents dans :

calculations/global_screening/qe/TOP20/pseudo/
"""

PSEUDO_MAP = {
    "C": "C.pbe-n-kjpaw_psl.0.1.UPF",
    "Cu": "Cu.pbe-kjpaw.UPF",
    "H": "H.pbe-kjpaw.UPF",
    "N": "N.UPF",
    "O": "O.pbe-kjpaw.UPF",
}


# ============================================================================
# PARAMÈTRES QE
# ============================================================================

CONTROL_RELAX = {
    "calculation": "'relax'",
    "restart_mode": "'from_scratch'",
    "prefix": "'hydromatai'",
    "pseudo_dir": f"'{PSEUDO_DIR}'",
    "outdir": "'./tmp'",
    "verbosity": "'high'",
    "tprnfor": ".true.",
    "tstress": ".true.",
}

CONTROL_SCF = {
    "calculation": "'scf'",
    "restart_mode": "'restart'",
    "prefix": "'hydromatai'",
    "pseudo_dir": f"'{PSEUDO_DIR}'",
    "outdir": "'./tmp'",
    "verbosity": "'high'",
    "tprnfor": ".true.",
    "tstress": ".true.",
}

SYSTEM_DEFAULT = {
    "ibrav": 0,
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

IONS = {
    "ion_dynamics": "'bfgs'",
}


# ============================================================================
# OUTILS GÉNÉRAUX
# ============================================================================

def now_iso() -> str:
    return time.strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:

        while True:

            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def safe_float(value: Any) -> Optional[float]:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)

    except (TypeError, ValueError):
        return None


def safe_int(value: Any, default: int = 0) -> int:

    try:
        return int(float(value))

    except (TypeError, ValueError):
        return default


def normalize_element(value: str) -> str:

    value = str(value).strip()

    value = re.sub(
        r"[^A-Za-z]",
        "",
        value,
    )

    if not value:
        return ""

    return (
        value[0].upper()
        + value[1:].lower()
    )


def sanitize_name(name: str) -> str:

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_."
    )

    cleaned = "".join(
        char if char in allowed else "_"
        for char in name
    )

    return cleaned[:120] or "material"


def command_exists(command: str) -> bool:

    return shutil.which(command) is not None


# ============================================================================
# DIRECTOIRES
# ============================================================================

def ensure_directories() -> None:

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOP20_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PSEUDO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================================
# PSEUDOPOTENTIELS
# ============================================================================

def validate_pseudopotentials() -> dict:

    result = {
        "available": {},
        "missing": [],
        "valid": True,
    }

    for element, filename in PSEUDO_MAP.items():

        path = PSEUDO_DIR / filename

        if path.is_file() and path.stat().st_size > 0:

            result["available"][element] = str(path)

        else:

            result["missing"].append(
                {
                    "element": element,
                    "file": filename,
                    "path": str(path),
                }
            )

    if result["missing"]:
        result["valid"] = False

    return result


def detect_pseudopotential_elements() -> set[str]:

    elements = set()

    if not PSEUDO_DIR.exists():
        return elements

    for path in PSEUDO_DIR.iterdir():

        if not path.is_file():
            continue

        if path.suffix.lower() != ".upf":
            continue

        # On utilise le mapping strict lorsqu'il est disponible.
        for element, filename in PSEUDO_MAP.items():

            if path.name == filename:

                elements.add(element)

    return elements


# ============================================================================
# LECTURE TOP200
# ============================================================================

def load_top200() -> list[dict]:

    if not INPUT_TOP200.exists():

        raise FileNotFoundError(
            f"""
Fichier TOP200 introuvable :

{INPUT_TOP200}

Vérifie que le pré-screening global a été exécuté.
"""
        )

    with INPUT_TOP200.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        return list(reader)


# ============================================================================
# CHEMIN CIF
# ============================================================================

def resolve_cif_path(value: str) -> Optional[Path]:

    if not value:
        return None

    raw = Path(str(value).strip())

    # Chemin absolu
    if raw.is_absolute():

        if raw.exists():
            return raw

        return None

    # Relatif au projet
    candidate = PROJECT / raw

    if candidate.exists():
        return candidate

    # Relatif au répertoire courant
    candidate = Path.cwd() / raw

    if candidate.exists():
        return candidate

    # Recherche par nom dans MOFXDB_FULL
    cif_dir = (
        PROJECT
        / "MOF_Library"
        / "MOFXDB_FULL"
        / "cif"
    )

    candidate = cif_dir / raw.name

    if candidate.exists():
        return candidate

    return None


# ============================================================================
# CHARGEMENT STRUCTURE
# ============================================================================

def load_structure(
    cif_path: Path,
) -> Optional[Structure]:

    try:

        return Structure.from_file(
            cif_path
        )

    except Exception:

        return None


# ============================================================================
# ÉVALUATION STRUCTURE
# ============================================================================

def evaluate_structure(
    row: dict,
) -> dict:

    result = {
        "dft_eligible": 0,
        "dft_reason": "",

        "rank_source": row.get("rank", ""),
        "source": row.get("source", ""),
        "name": row.get("name", ""),
        "material_id": row.get(
            "material_id",
            row.get("id", ""),
        ),
        "formula": row.get(
            "formula",
            row.get("composition", ""),
        ),

        "cif": row.get("cif", ""),

        "n_atoms_cif": "",
        "n_atoms_primitive": "",
        "primitive_reduction": "",

        "elements": "",
        "missing_pseudopotentials": "",

        "dft_priority_score": row.get(
            "dft_priority_score",
            row.get("score", ""),
        ),

        "h2_score": row.get(
            "h2_score",
            "",
        ),
    }

    # ------------------------------------------------------------------------
    # CIF
    # ------------------------------------------------------------------------

    cif_path = resolve_cif_path(
        row.get("cif", "")
    )

    if cif_path is None:

        result["dft_reason"] = "CIF_ABSENT"

        return result

    result["cif"] = str(
        cif_path.resolve()
    )

    structure = load_structure(
        cif_path
    )

    if structure is None:

        result["dft_reason"] = (
            "CIF_PARSE_ERROR"
        )

        return result

    # ------------------------------------------------------------------------
    # Taille CIF
    # ------------------------------------------------------------------------

    n_atoms_cif = len(structure)

    result["n_atoms_cif"] = n_atoms_cif

    # ------------------------------------------------------------------------
    # Primitive
    # ------------------------------------------------------------------------

    try:

        primitive = (
            structure
            .get_primitive_structure()
        )

    except Exception:

        result["dft_reason"] = (
            "PRIMITIVE_CONVERSION_ERROR"
        )

        return result

    if primitive is None:

        result["dft_reason"] = (
            "PRIMITIVE_CONVERSION_ERROR"
        )

        return result

    n_atoms_primitive = len(
        primitive
    )

    result["n_atoms_primitive"] = (
        n_atoms_primitive
    )

    # ------------------------------------------------------------------------
    # Réduction
    # ------------------------------------------------------------------------

    if n_atoms_cif > 0:

        reduction = (
            1.0
            - (
                n_atoms_primitive
                / n_atoms_cif
            )
        ) * 100.0

        result["primitive_reduction"] = (
            round(reduction, 2)
        )

    # ------------------------------------------------------------------------
    # Éléments
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Taille minimale
    # ------------------------------------------------------------------------

    if (
        n_atoms_primitive
        < MIN_PRIMITIVE_ATOMS
    ):

        result["dft_reason"] = (
            "TOO_FEW_PRIMITIVE_ATOMS"
        )

        return result

    # ------------------------------------------------------------------------
    # Taille maximale
    # ------------------------------------------------------------------------

    if (
        n_atoms_primitive
        > MAX_PRIMITIVE_ATOMS
    ):

        result["dft_reason"] = (
            "TOO_MANY_PRIMITIVE_ATOMS"
        )

        return result

    # ------------------------------------------------------------------------
    # Pseudopotentiels
    # ------------------------------------------------------------------------

    missing = sorted(
        element
        for element in elements
        if element not in PSEUDO_MAP
        or not (
            PSEUDO_DIR
            / PSEUDO_MAP[element]
        ).is_file()
    )

    result["missing_pseudopotentials"] = (
        ",".join(missing)
    )

    if missing:

        result["dft_reason"] = (
            "MISSING_PSEUDOPOTENTIAL"
        )

        return result

    # ------------------------------------------------------------------------
    # Éligible
    # ------------------------------------------------------------------------

    result["dft_eligible"] = 1

    result["dft_reason"] = "OK"

    return result


# ============================================================================
# SÉLECTION TOP20
# ============================================================================

def select_top20(
    evaluations: list[dict],
) -> list[dict]:

    eligible = [
        row
        for row in evaluations
        if row["dft_eligible"] == 1
    ]

    def priority_key(row):

        score = (
            safe_float(
                row.get(
                    "dft_priority_score"
                )
            )
            or 0.0
        )

        h2_score = (
            safe_float(
                row.get(
                    "h2_score"
                )
            )
            or 0.0
        )

        source_rank = safe_int(
            row.get(
                "rank_source"
            ),
            999999,
        )

        return (
            -score,
            -h2_score,
            source_rank,
        )

    eligible.sort(
        key=priority_key
    )

    selected = eligible[:TOP_N]

    for index, row in enumerate(
        selected,
        start=1,
    ):

        row["dft_rank"] = index

        row["selection_class"] = (
            "TOP20"
        )

    return selected


# ============================================================================
# CSV
# ============================================================================

def write_top20_csv(
    rows: list[dict],
) -> None:

    OUTPUT_TOP20.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fields = [
        "dft_rank",
        "selection_class",
        "rank_source",
        "source",
        "name",
        "material_id",
        "formula",
        "cif",
        "n_atoms_cif",
        "n_atoms_primitive",
        "primitive_reduction",
        "elements",
        "missing_pseudopotentials",
        "dft_priority_score",
        "h2_score",
        "dft_eligible",
        "dft_reason",
    ]

    with OUTPUT_TOP20.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(rows)


# ============================================================================
# FORMAT QE
# ============================================================================

def format_qe_value(
    value: Any,
) -> str:

    if isinstance(value, bool):

        return (
            ".true."
            if value
            else ".false."
        )

    if isinstance(value, float):

        return f"{value:.12g}"

    return str(value)


def write_namelist(
    name: str,
    values: dict,
) -> str:

    lines = [
        f"&{name}"
    ]

    for key, value in values.items():

        if value is None:
            continue

        lines.append(
            f"  {key} = "
            f"{format_qe_value(value)}"
        )

    lines.append("/")

    return "\n".join(lines)


# ============================================================================
# ATOMIC SPECIES
# ============================================================================

ATOMIC_MASSES = {
    "H": 1.00794,
    "C": 12.0107,
    "N": 14.0067,
    "O": 15.9994,
    "Cu": 63.546,
}


def build_atomic_species(
    structure: Structure,
) -> tuple[list[str], dict[str, int]]:

    elements = sorted(
        {
            normalize_element(
                site.specie.symbol
            )
            for site in structure.sites
        }
    )

    element_index = {
        element: index
        for index, element in enumerate(
            elements,
            start=1,
        )
    }

    lines = []

    for element in elements:

        mass = ATOMIC_MASSES.get(
            element,
            1.0,
        )

        pseudo = PSEUDO_MAP[element]

        lines.append(
            f"{element:<4} "
            f"{mass:.6f} "
            f"{pseudo}"
        )

    return lines, element_index


# ============================================================================
# GÉNÉRATION QE
# ============================================================================

def structure_to_qe(
    structure: Structure,
) -> tuple[
    list[str],
    list[str],
    list[str],
    list[str],
]:

    atomic_species, element_index = (
        build_atomic_species(
            structure
        )
    )

    atomic_positions = []

    for site in structure.sites:

        element = normalize_element(
            site.specie.symbol
        )

        x, y, z = site.frac_coords

        atomic_positions.append(
            f"{element:<3} "
            f"{x:.12f} "
            f"{y:.12f} "
            f"{z:.12f}"
        )

    cell_parameters = []

    for vector in structure.lattice.matrix:

        cell_parameters.append(
            f"{vector[0]:.12f} "
            f"{vector[1]:.12f} "
            f"{vector[2]:.12f}"
        )

    return (
        atomic_species,
        atomic_positions,
        cell_parameters,
        list(element_index.keys()),
    )


def generate_relax_input(
    structure: Structure,
) -> str:

    atomic_species, atomic_positions, cell_parameters, elements = (
        structure_to_qe(
            structure
        )
    )

    control = dict(
        CONTROL_RELAX
    )

    system = dict(
        SYSTEM_DEFAULT
    )

    system["nat"] = len(
        structure
    )

    system["ntyp"] = len(
        elements
    )

    lines = []

    lines.append(
        write_namelist(
            "CONTROL",
            control,
        )
    )

    lines.append("")

    lines.append(
        write_namelist(
            "SYSTEM",
            system,
        )
    )

    lines.append("")

    lines.append(
        write_namelist(
            "ELECTRONS",
            ELECTRONS,
        )
    )

    lines.append("")

    lines.append(
        write_namelist(
            "IONS",
            IONS,
        )
    )

    lines.append("")

    lines.append(
        "ATOMIC_SPECIES"
    )

    lines.extend(
        atomic_species
    )

    lines.append("")

    lines.append(
        "ATOMIC_POSITIONS crystal"
    )

    lines.extend(
        atomic_positions
    )

    lines.append("")

    lines.append(
        "K_POINTS gamma"
    )

    lines.append("")

    lines.append(
        "CELL_PARAMETERS angstrom"
    )

    lines.extend(
        cell_parameters
    )

    lines.append("")

    return "\n".join(lines)


def generate_scf_input(
    structure: Structure,
) -> str:

    atomic_species, atomic_positions, cell_parameters, elements = (
        structure_to_qe(
            structure
        )
    )

    control = dict(
        CONTROL_SCF
    )

    system = dict(
        SYSTEM_DEFAULT
    )

    system["nat"] = len(
        structure
    )

    system["ntyp"] = len(
        elements
    )

    lines = []

    lines.append(
        write_namelist(
            "CONTROL",
            control,
        )
    )

    lines.append("")

    lines.append(
        write_namelist(
            "SYSTEM",
            system,
        )
    )

    lines.append("")

    lines.append(
        write_namelist(
            "ELECTRONS",
            ELECTRONS,
        )
    )

    lines.append("")

    lines.append(
        "ATOMIC_SPECIES"
    )

    lines.extend(
        atomic_species
    )

    lines.append("")

    lines.append(
        "ATOMIC_POSITIONS crystal"
    )

    lines.extend(
        atomic_positions
    )

    lines.append("")

    lines.append(
        "K_POINTS gamma"
    )

    lines.append("")

    lines.append(
        "CELL_PARAMETERS angstrom"
    )

    lines.extend(
        cell_parameters
    )

    lines.append("")

    return "\n".join(lines)


# ============================================================================
# PRÉPARATION D'UN CANDIDAT
# ============================================================================

def prepare_candidate(
    row: dict,
) -> dict:

    dft_rank = safe_int(
        row.get(
            "dft_rank"
        ),
        0,
    )

    name = str(
        row.get(
            "name"
        )
        or row.get(
            "material_id"
        )
        or f"candidate_{dft_rank}"
    )

    directory_name = (
        f"{dft_rank:04d}_"
        f"{sanitize_name(name)}"
    )

    job_dir = TOP20_DIR / directory_name

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    cif_path = Path(
        row["cif"]
    )

    structure = load_structure(
        cif_path
    )

    if structure is None:

        raise RuntimeError(
            f"Impossible de relire le CIF : "
            f"{cif_path}"
        )

    # ------------------------------------------------------------------------
    # Copie CIF
    # ------------------------------------------------------------------------

    destination_cif = (
        job_dir / "structure.cif"
    )

    shutil.copy2(
        cif_path,
        destination_cif,
    )

    # ------------------------------------------------------------------------
    # Inputs QE
    # ------------------------------------------------------------------------

    relax_input = (
        job_dir / "pw.relax.in"
    )

    scf_input = (
        job_dir / "pw.scf.in"
    )

    relax_input.write_text(
        generate_relax_input(
            structure
        ),
        encoding="utf-8",
    )

    scf_input.write_text(
        generate_scf_input(
            structure
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------------

    readme = (
        "HydroMatAI — DFT GLOBAL COMPLETE\n"
        "\n"
        f"Nom : {name}\n"
        f"Rang DFT : {dft_rank}\n"
        f"CIF source : {cif_path}\n"
        f"CIF local : {destination_cif}\n"
        f"Atomes : {len(structure)}\n"
        f"Éléments : "
        f"{','.join(sorted({site.specie.symbol for site in structure.sites}))}\n"
        "\n"
        "Fichiers QE :\n"
        "  pw.relax.in\n"
        "  pw.scf.in\n"
        "\n"
        "Aucun calcul n'est lancé par la génération.\n"
    )

    (
        job_dir / "README.txt"
    ).write_text(
        readme,
        encoding="utf-8",
    )

    return {
        "dft_rank": dft_rank,
        "name": name,
        "material_id": row.get(
            "material_id",
            "",
        ),
        "formula": row.get(
            "formula",
            "",
        ),
        "source_cif": str(
            cif_path.resolve()
        ),
        "local_cif": str(
            destination_cif.resolve()
        ),
        "job_dir": str(
            job_dir.resolve()
        ),
        "relax_input": str(
            relax_input.resolve()
        ),
        "scf_input": str(
            scf_input.resolve()
        ),
        "relax_output": str(
            (job_dir / "pw.relax.out").resolve()
        ),
        "scf_output": str(
            (job_dir / "pw.scf.out").resolve()
        ),
        "elements": sorted(
            {
                site.specie.symbol
                for site in structure.sites
            }
        ),
        "n_atoms": len(structure),
        "status": "INPUTS_GENERATED",
        "error": "",
    }


# ============================================================================
# EXÉCUTION QE
# ============================================================================

def run_qe(
    input_file: Path,
    output_file: Path,
    workdir: Path,
    timeout: int,
) -> dict:

    result = {
        "return_code": None,
        "status": "NOT_RUN",
        "error": "",
    }

    if not PW_X.exists():

        result["status"] = (
            "PW_X_NOT_FOUND"
        )

        result["error"] = (
            f"Executable absent : {PW_X}"
        )

        return result

    command = [
        str(PW_X),
    ]

    start = time.time()

    try:

        with input_file.open(
            "r",
            encoding="utf-8",
        ) as stdin_handle:

            with output_file.open(
                "w",
                encoding="utf-8",
            ) as stdout_handle:

                process = subprocess.run(
                    command,
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=subprocess.STDOUT,
                    cwd=workdir,
                    timeout=timeout,
                    check=False,
                    text=True,
                )

        elapsed = (
            time.time()
            - start
        )

        result["return_code"] = (
            process.returncode
        )

        result["elapsed_seconds"] = round(
            elapsed,
            2,
        )

        if process.returncode == 0:

            result["status"] = "SUCCESS"

        else:

            result["status"] = (
                "FAILED"
            )

            result["error"] = (
                f"pw.x return code "
                f"{process.returncode}"
            )

    except subprocess.TimeoutExpired:

        result["status"] = (
            "TIMEOUT"
        )

        result["error"] = (
            f"Calcul dépassant "
            f"{timeout} secondes"
        )

    except Exception as exc:

        result["status"] = (
            "EXECUTION_ERROR"
        )

        result["error"] = str(exc)

    return result


# ============================================================================
# LECTURE ÉNERGIE
# ============================================================================

def extract_total_energy(
    output_file: Path,
) -> Optional[float]:

    if not output_file.exists():
        return None

    pattern = re.compile(
        r"!\s+total energy\s*=\s*"
        r"([-+0-9.EeDd]+)\s+Ry"
    )

    last_energy = None

    try:

        text = output_file.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except OSError:

        return None

    for match in pattern.finditer(
        text
    ):

        value = match.group(1)

        value = value.replace(
            "D",
            "E",
        ).replace(
            "d",
            "e",
        )

        try:

            last_energy = float(
                value
            )

        except ValueError:

            continue

    return last_energy


# ============================================================================
# EXÉCUTION D'UN JOB
# ============================================================================

def execute_job(
    job: dict,
    timeout: int,
) -> dict:

    job_dir = Path(
        job["job_dir"]
    )

    relax_input = Path(
        job["relax_input"]
    )

    scf_input = Path(
        job["scf_input"]
    )

    relax_output = Path(
        job["relax_output"]
    )

    scf_output = Path(
        job["scf_output"]
    )

    # ------------------------------------------------------------------------
    # RELAX
    # ------------------------------------------------------------------------

    print(
        f"\n[RELAX] "
        f"{job['dft_rank']:04d} "
        f"{job['name']}"
    )

    relax_result = run_qe(
        relax_input,
        relax_output,
        job_dir,
        timeout,
    )

    job["relax_status"] = (
        relax_result["status"]
    )

    job["relax_return_code"] = (
        relax_result.get(
            "return_code"
        )
    )

    job["relax_error"] = (
        relax_result.get(
            "error",
            "",
        )
    )

    if relax_result["status"] != "SUCCESS":

        job["status"] = (
            "RELAX_FAILED"
        )

        return job

    # ------------------------------------------------------------------------
    # SCF
    # ------------------------------------------------------------------------

    print(
        f"[SCF]   "
        f"{job['dft_rank']:04d} "
        f"{job['name']}"
    )

    scf_result = run_qe(
        scf_input,
        scf_output,
        job_dir,
        timeout,
    )

    job["scf_status"] = (
        scf_result["status"]
    )

    job["scf_return_code"] = (
        scf_result.get(
            "return_code"
        )
    )

    job["scf_error"] = (
        scf_result.get(
            "error",
            "",
        )
    )

    job["total_energy_ry"] = (
        extract_total_energy(
            scf_output
        )
    )

    if scf_result["status"] != "SUCCESS":

        job["status"] = (
            "SCF_FAILED"
        )

        return job

    job["status"] = (
        "RELAX_SCF_SUCCESS"
    )

    return job


# ============================================================================
# AUDIT CSV
# ============================================================================

def write_audit(
    jobs: list[dict],
) -> None:

    fields = [
        "dft_rank",
        "name",
        "material_id",
        "formula",
        "source_cif",
        "local_cif",
        "job_dir",
        "relax_input",
        "relax_output",
        "scf_input",
        "scf_output",
        "elements",
        "n_atoms",
        "status",
        "relax_status",
        "relax_return_code",
        "relax_error",
        "scf_status",
        "scf_return_code",
        "scf_error",
        "total_energy_ry",
    ]

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()

        for job in jobs:

            row = dict(job)

            if isinstance(
                row.get("elements"),
                list,
            ):

                row["elements"] = ",".join(
                    row["elements"]
                )

            writer.writerow(row)


# ============================================================================
# MANIFEST
# ============================================================================

def write_json(
    path: Path,
    data: Any,
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            data,
            handle,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================================
# AFFICHAGE
# ============================================================================

def print_header() -> None:

    print(
        "=" * 80
    )

    print(
        " HydroMatAI — DFT GLOBAL COMPLETE"
    )

    print(
        "=" * 80
    )


def print_summary(
    evaluations: list[dict],
    selected: list[dict],
) -> None:

    total = len(
        evaluations
    )

    eligible = sum(
        row["dft_eligible"]
        for row in evaluations
    )

    excluded = total - eligible

    print()
    print(
        "=" * 80
    )

    print(
        " RÉSULTATS DU PRÉ-SCREENING DFT"
    )

    print(
        "=" * 80
    )

    print(
        f"Structures analysées : {total}"
    )

    print(
        f"Éligibles DFT        : {eligible}"
    )

    print(
        f"Exclues               : {excluded}"
    )

    print(
        f"TOP 20 retenues       : {len(selected)}"
    )

    print()
    print(
        "EXCLUSIONS"
    )

    print(
        "-" * 80
    )

    reasons = {}

    for row in evaluations:

        if row["dft_eligible"]:

            continue

        reason = row[
            "dft_reason"
        ]

        reasons[reason] = (
            reasons.get(
                reason,
                0,
            )
            + 1
        )

    for reason, count in sorted(
        reasons.items()
    ):

        print(
            f"{reason:<35} : {count:4d}"
        )

    print()
    print(
        "=" * 80
    )

    print(
        " TOP 20 DFT GLOBAL"
    )

    print(
        "=" * 80
    )

    if not selected:

        print(
            "Aucune structure éligible."
        )

        return

    print(
        f"{'Rang':<6}"
        f"{'Nom':<32}"
        f"{'Prim':>8}"
        f"{'Éléments':<20}"
    )

    print(
        "-" * 80
    )

    for row in selected:

        name = str(
            row["name"]
        )[:30]

        elements = str(
            row["elements"]
        )[:18]

        print(
            f"{row['dft_rank']:<6}"
            f"{name:<32}"
            f"{row['n_atoms_primitive']:>8}"
            f"{elements:<20}"
        )


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI — workflow DFT global complet"
        )
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Lance réellement pw.x RELAX puis SCF."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            "Nombre maximum de candidats à préparer/exécuter."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=(
            "Timeout en secondes par calcul QE."
        ),
    )

    args = parser.parse_args()

    print_header()

    # ------------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------------

    ensure_directories()

    print(
        f"\nLecture : {INPUT_TOP200}"
    )

    # ------------------------------------------------------------------------
    # Pseudopotentiels
    # ------------------------------------------------------------------------

    pseudo_status = (
        validate_pseudopotentials()
    )

    print()
    print(
        "Pseudopotentiels"
    )

    print(
        "-" * 80
    )

    for element, filename in (
        PSEUDO_MAP.items()
    ):

        path = PSEUDO_DIR / filename

        if path.is_file():

            print(
                f"OK      {element:<3} "
                f"{filename}"
            )

        else:

            print(
                f"MANQUE  {element:<3} "
                f"{filename}"
            )

    if not pseudo_status["valid"]:

        print()
        print(
            "ERREUR : pseudopotentiels manquants."
        )

        print(
            f"Répertoire : {PSEUDO_DIR}"
        )

        return 1

    # ------------------------------------------------------------------------
    # QE
    # ------------------------------------------------------------------------

    print()
    print(
        f"QE : {PW_X}"
    )

    if PW_X.exists():

        print(
            "pw.x détecté : OUI"
        )

    else:

        print(
            "pw.x détecté : NON"
        )

        if args.execute:

            print(
                "Impossible d'utiliser --execute."
            )

            return 1

    # ------------------------------------------------------------------------
    # TOP200
    # ------------------------------------------------------------------------

    rows = load_top200()

    print(
        f"Candidats reçus : {len(rows)}"
    )

    # ------------------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------------------

    evaluations = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        result = evaluate_structure(
            row
        )

        evaluations.append(
            result
        )

        if (
            index % 25 == 0
            or index == len(rows)
        ):

            print(
                f"   {index:3d}/"
                f"{len(rows)} "
                f"structures analysées"
            )

    # ------------------------------------------------------------------------
    # Sélection
    # ------------------------------------------------------------------------

    selected = select_top20(
        evaluations
    )

    print_summary(
        evaluations,
        selected,
    )

    # ------------------------------------------------------------------------
    # Sauvegarde TOP20
    # ------------------------------------------------------------------------

    write_top20_csv(
        selected
    )

    print()
    print(
        f"TOP20 DFT : {OUTPUT_TOP20}"
    )

    # ------------------------------------------------------------------------
    # Si aucune structure
    # ------------------------------------------------------------------------

    if not selected:

        print()
        print(
            "Aucun input QE généré."
        )

        print(
            "QE : NON LANCÉ"
        )

        return 0

    # ------------------------------------------------------------------------
    # Génération inputs
    # ------------------------------------------------------------------------

    print()
    print(
        "=" * 80
    )

    print(
        " GÉNÉRATION DES INPUTS QE"
    )

    print(
        "=" * 80
    )

    jobs = []

    generation_errors = 0

    for row in selected:

        try:

            job = prepare_candidate(
                row
            )

            jobs.append(
                job
            )

            print(
                f"[OK] "
                f"{row['dft_rank']:04d} "
                f"{row['name']}"
            )

        except Exception as exc:

            generation_errors += 1

            print(
                f"[ERREUR] "
                f"{row.get('name', '')} : "
                f"{exc}"
            )

            jobs.append(
                {
                    "dft_rank": row.get(
                        "dft_rank",
                        "",
                    ),
                    "name": row.get(
                        "name",
                        "",
                    ),
                    "material_id": row.get(
                        "material_id",
                        "",
                    ),
                    "formula": row.get(
                        "formula",
                        "",
                    ),
                    "source_cif": row.get(
                        "cif",
                        "",
                    ),
                    "status": "INPUT_GENERATION_FAILED",
                    "error": str(exc),
                }
            )

    # ------------------------------------------------------------------------
    # Limite
    # ------------------------------------------------------------------------

    if args.limit < 1:

        print(
            "\nErreur : --limit doit être >= 1."
        )

        return 1

    jobs = jobs[
        :args.limit
    ]

    # ------------------------------------------------------------------------
    # Sauvegarde manifest initial
    # ------------------------------------------------------------------------

    manifest = {
        "project": str(
            PROJECT
        ),
        "generated_at": now_iso(),
        "input_top200": str(
            INPUT_TOP200
        ),
        "output_top20": str(
            OUTPUT_TOP20
        ),
        "pseudo_dir": str(
            PSEUDO_DIR
        ),
        "pw_x": str(
            PW_X
        ),
        "max_primitive_atoms": (
            MAX_PRIMITIVE_ATOMS
        ),
        "min_primitive_atoms": (
            MIN_PRIMITIVE_ATOMS
        ),
        "top_n": TOP_N,
        "limit": args.limit,
        "execute": args.execute,
        "timeout": args.timeout,
        "pseudopotentials": PSEUDO_MAP,
        "pseudopotentials_valid": (
            pseudo_status["valid"]
        ),
        "generation_errors": (
            generation_errors
        ),
        "jobs": jobs,
    }

    # ------------------------------------------------------------------------
    # Exécution
    # ------------------------------------------------------------------------

    if args.execute:

        print()
        print(
            "=" * 80
        )

        print(
            " EXÉCUTION QUANTUM ESPRESSO"
        )

        print(
            "=" * 80
        )

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            print()
            print(
                f"JOB {index}/{len(jobs)}"
            )

            if (
                job.get("status")
                != "INPUTS_GENERATED"
            ):

                print(
                    "Job ignoré : inputs non disponibles."
                )

                continue

            execute_job(
                job,
                args.timeout,
            )

            # Sauvegarde intermédiaire
            manifest[
                "jobs"
            ] = jobs

            write_json(
                MANIFEST_FILE,
                manifest,
            )

            write_audit(
                jobs
            )

    else:

        print()
        print(
            "=" * 80
        )

        print(
            " MODE PRÉPARATION"
        )

        print(
            "=" * 80
        )

        print(
            "Aucun calcul QE n'a été lancé."
        )

        print(
            "Utiliser --execute pour lancer pw.x."
        )

    # ------------------------------------------------------------------------
    # Manifest final
    # ------------------------------------------------------------------------

    manifest["finished_at"] = (
        now_iso()
    )

    manifest["jobs"] = jobs

    write_json(
        MANIFEST_FILE,
        manifest,
    )

    write_json(
        JOBS_FILE,
        jobs,
    )

    write_audit(
        jobs
    )

    # ------------------------------------------------------------------------
    # Résumé final
    # ------------------------------------------------------------------------

    print()
    print(
        "=" * 80
    )

    print(
        " RÉSUMÉ FINAL"
    )

    print(
        "=" * 80
    )

    print(
        f"TOP20 CSV   : {OUTPUT_TOP20}"
    )

    print(
        f"QE directory: {TOP20_DIR}"
    )

    print(
        f"Audit       : {AUDIT_FILE}"
    )

    print(
        f"Manifest    : {MANIFEST_FILE}"
    )

    if args.execute:

        success = sum(
            1
            for job in jobs
            if job.get(
                "status"
            )
            == "RELAX_SCF_SUCCESS"
        )

        print()
        print(
            f"RELAX + SCF réussis : "
            f"{success}/{len(jobs)}"
        )

    else:

        print()
        print(
            "QE : NON LANCÉ"
        )

    print(
        "=" * 80
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
