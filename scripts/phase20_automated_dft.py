#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")
"""
HydroMatAI — PHASE 20
AUTOMATED DFT WORKFLOW

Pipeline
--------
DFT priority
    ↓
CIF validation
    ↓
QE input generation
    ↓
RELAX
    ↓
SCF
    ↓
Electronic preparation
    ↓
Manifest / audit

IMPORTANT
---------
Par défaut, aucun calcul QE n'est lancé.

Pour réellement exécuter Quantum ESPRESSO :
    python scripts/phase20_automated_dft.py --execute

Pour limiter le nombre de candidats :
    python scripts/phase20_automated_dft.py --execute --limit 5

Pour exécuter uniquement certains candidats :
    python scripts/phase20_automated_dft.py --execute --names hMOF-2272 hMOF-2393

Le script ne lance jamais bands.x ou dos.x automatiquement dans cette
première version. Ils seront traités dans la phase Electronic dédiée.
"""


import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT = Path.cwd()

REPORT_DIR = ROOT / "reports" / "global_screening"
INPUT_PRIORITY = REPORT_DIR / "dft_priority.csv"

CALCULATIONS_DIR = ROOT / "calculations" / "phase_20_automated_dft"

MANIFEST_FILE = CALCULATIONS_DIR / "phase20_manifest.json"
AUDIT_FILE = CALCULATIONS_DIR / "phase20_audit.csv"

RELAX_DIR = CALCULATIONS_DIR / "relax"
SCF_DIR = CALCULATIONS_DIR / "scf"

# Quantum ESPRESSO
PW_X_DEFAULT = "pw.x"

# Nombre maximum par défaut.
DEFAULT_LIMIT = 25

# Timeout de sécurité par calcul.
DEFAULT_TIMEOUT = 3600

# Nombre de tentatives maximum.
MAX_ATTEMPTS = 1


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class DFTJob:
    rank: int
    source: str
    name: str
    material_id: str
    formula: str
    cif: str

    dft_priority_score: float
    selection_class: str

    cif_exists: bool
    cif_sha256: str

    relax_input: str
    relax_output: str

    scf_input: str
    scf_output: str

    relax_status: str
    scf_status: str

    relax_return_code: Optional[int]
    scf_return_code: Optional[int]

    total_energy_ry: Optional[float]

    electronic_status: str

    execution_mode: str
    error: str


# ============================================================================
# UTILITAIRES
# ============================================================================


def sha256_file(path: Path) -> str:
    """Calcule l'empreinte SHA256 du CIF."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def safe_float(value) -> Optional[float]:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def safe_int(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def sanitize_name(name: str) -> str:
    """
    Rend le nom compatible avec un répertoire de calcul.
    """
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


def ensure_directories() -> None:
    CALCULATIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RELAX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SCF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================================
# QE DETECTION
# ============================================================================


def detect_qe(command: str) -> tuple[bool, str]:
    """
    Détecte pw.x.

    Aucun lancement.
    """

    executable = shutil.which(command)

    if executable is None:
        return False, ""

    return True, executable


# ============================================================================
# CIF VALIDATION
# ============================================================================


def validate_cif(path_text: str) -> tuple[bool, str]:
    """
    Validation légère du fichier CIF.

    Cette étape ne lance aucun calcul.
    """

    if not path_text:
        return False, ""

    path = Path(path_text)

    if not path.exists():
        return False, ""

    if not path.is_file():
        return False, ""

    try:
        if path.stat().st_size == 0:
            return False, ""

        digest = sha256_file(path)

        return True, digest

    except OSError:
        return False, ""


# ============================================================================
# TOP PRIORITY LOADER
# ============================================================================


def load_priority(
    path: Path,
    names: Optional[list[str]] = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:

    if not path.exists():
        raise FileNotFoundError(
            f"Fichier DFT priority absent : {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        rows = list(csv.DictReader(handle))

    priority_rows = [
        row
        for row in rows
        if str(
            row.get("selection_class", "")
        ).strip().upper() == "PRIORITY"
    ]

    if names:
        wanted = {
            name.strip()
            for name in names
        }

        priority_rows = [
            row
            for row in priority_rows
            if str(
                row.get("name", "")
            ).strip() in wanted
        ]

    priority_rows.sort(
        key=lambda row: (
            safe_int(row.get("dft_rank"), 999999),
            -(
                safe_float(
                    row.get("dft_priority_score")
                )
                or 0.0
            ),
        )
    )

    return priority_rows[:limit]


# ============================================================================
# QE INPUT GENERATION
# ============================================================================


def generate_relax_input(
    row: dict,
    output_path: Path,
) -> None:
    """
    Génère un input QE RELAX.

    La structure initiale est chargée directement depuis le CIF via
    ibrav=0 et ATOMIC_POSITIONS crystal.

    Les paramètres de cellule et positions sont extraits avec pymatgen.
    """

    try:
        from pymatgen.core import Structure
    except ImportError as exc:
        raise RuntimeError(
            "pymatgen est nécessaire pour générer les inputs QE."
        ) from exc

    cif_path = Path(row["cif"])

    structure = Structure.from_file(cif_path)

    formula = structure.composition.reduced_formula

    prefix = sanitize_name(row["name"])

    # ----------------------------------------------------------------------
    # CELLULE
    # ----------------------------------------------------------------------

    lattice = structure.lattice

    cell_parameters = (
        f"{lattice.matrix[0][0]:.12f} "
        f"{lattice.matrix[0][1]:.12f} "
        f"{lattice.matrix[0][2]:.12f}\n"
        f"{lattice.matrix[1][0]:.12f} "
        f"{lattice.matrix[1][1]:.12f} "
        f"{lattice.matrix[1][2]:.12f}\n"
        f"{lattice.matrix[2][0]:.12f} "
        f"{lattice.matrix[2][1]:.12f} "
        f"{lattice.matrix[2][2]:.12f}"
    )

    # ----------------------------------------------------------------------
    # ATOMES
    # ----------------------------------------------------------------------

    atomic_positions = []

    for site in structure.sites:

        species = site.specie.symbol

        x, y, z = (
            float(site.frac_coords[0]),
            float(site.frac_coords[1]),
            float(site.frac_coords[2]),
        )

        atomic_positions.append(
            f"{species:<4} "
            f"{x:.12f} "
            f"{y:.12f} "
            f"{z:.12f}"
        )

    # ----------------------------------------------------------------------
    # ESPÈCES
    # ----------------------------------------------------------------------

    elements = sorted(
        {
            site.specie.symbol
            for site in structure.sites
        }
    )

    # ----------------------------------------------------------------------
    # MASSES
    # ----------------------------------------------------------------------

    species_lines = []

    for element in elements:

        try:
            from pymatgen.core import Element

            mass = float(
                Element(element).atomic_mass
            )

        except Exception:
            mass = 1.0

        # Pseudopotentiel par défaut.
        #
        # IMPORTANT :
        # ces noms doivent être adaptés à la bibliothèque PP réellement
        # installée sur la machine avant un calcul de production.
        pseudo = f"{element}.UPF"

        species_lines.append(
            f"{element:<4} "
            f"{mass:.6f} "
            f"{pseudo}"
        )

    nat = len(structure)
    ntyp = len(elements)

    input_text = f"""&CONTROL
    calculation = 'relax',
    prefix = '{prefix}',
    pseudo_dir = './pseudo',
    outdir = './tmp',
    tstress = .true.,
    tprnfor = .true.,
    verbosity = 'high',
/

&SYSTEM
    ibrav = 0,
    nat = {nat},
    ntyp = {ntyp},
    ecutwfc = 60.0,
    ecutrho = 480.0,
    occupations = 'fixed',
/

&ELECTRONS
    conv_thr = 1.0d-8,
    electron_maxstep = 200,
    mixing_beta = 0.3,
/

&IONS
    ion_dynamics = 'bfgs',
/

ATOMIC_SPECIES
{chr(10).join(species_lines)}

CELL_PARAMETERS angstrom
{cell_parameters}

ATOMIC_POSITIONS crystal
{chr(10).join(atomic_positions)}

K_POINTS automatic
1 1 1 0 0 0
"""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        input_text,
        encoding="utf-8",
    )


# ============================================================================
# SCF INPUT
# ============================================================================


def generate_scf_input(
    row: dict,
    relax_output_dir: Path,
    output_path: Path,
) -> None:
    """
    Génère l'input SCF.

    La structure finale issue de RELAX est récupérée depuis QE.
    """

    try:
        from pymatgen.core import Structure
    except ImportError as exc:
        raise RuntimeError(
            "pymatgen est nécessaire pour générer les inputs QE."
        ) from exc

    # QE produit normalement prefix.save dans outdir.
    prefix = sanitize_name(row["name"])

    relaxed_structure = None

    # ----------------------------------------------------------------------
    # Recherche du CIF final éventuel.
    # ----------------------------------------------------------------------

    candidates = [
        relax_output_dir / f"{prefix}.cif",
        relax_output_dir / "relaxed.cif",
    ]

    for candidate in candidates:

        if candidate.exists():

            try:
                relaxed_structure = Structure.from_file(
                    candidate
                )

                break

            except Exception:
                pass

    # ----------------------------------------------------------------------
    # Si aucun CIF relaxé n'existe, on utilise la structure initiale.
    #
    # Cela permet au script de préparer le SCF, mais l'exécution du SCF
    # après RELAX exige idéalement une conversion de la structure finale.
    # ----------------------------------------------------------------------

    if relaxed_structure is None:
        relaxed_structure = Structure.from_file(
            row["cif"]
        )

    lattice = relaxed_structure.lattice

    cell_parameters = (
        f"{lattice.matrix[0][0]:.12f} "
        f"{lattice.matrix[0][1]:.12f} "
        f"{lattice.matrix[0][2]:.12f}\n"
        f"{lattice.matrix[1][0]:.12f} "
        f"{lattice.matrix[1][1]:.12f} "
        f"{lattice.matrix[1][2]:.12f}\n"
        f"{lattice.matrix[2][0]:.12f} "
        f"{lattice.matrix[2][1]:.12f} "
        f"{lattice.matrix[2][2]:.12f}"
    )

    atomic_positions = []

    for site in relaxed_structure.sites:

        x, y, z = (
            float(site.frac_coords[0]),
            float(site.frac_coords[1]),
            float(site.frac_coords[2]),
        )

        atomic_positions.append(
            f"{site.specie.symbol:<4} "
            f"{x:.12f} "
            f"{y:.12f} "
            f"{z:.12f}"
        )

    elements = sorted(
        {
            site.specie.symbol
            for site in relaxed_structure.sites
        }
    )

    species_lines = []

    try:
        from pymatgen.core import Element
    except ImportError:
        Element = None

    for element in elements:

        if Element is not None:

            try:
                mass = float(
                    Element(element).atomic_mass
                )
            except Exception:
                mass = 1.0

        else:
            mass = 1.0

        pseudo = f"{element}.UPF"

        species_lines.append(
            f"{element:<4} "
            f"{mass:.6f} "
            f"{pseudo}"
        )

    nat = len(relaxed_structure)
    ntyp = len(elements)

    input_text = f"""&CONTROL
    calculation = 'scf',
    prefix = '{prefix}',
    pseudo_dir = './pseudo',
    outdir = './tmp',
    tstress = .true.,
    tprnfor = .true.,
    verbosity = 'high',
/

&SYSTEM
    ibrav = 0,
    nat = {nat},
    ntyp = {ntyp},
    ecutwfc = 60.0,
    ecutrho = 480.0,
    occupations = 'fixed',
/

&ELECTRONS
    conv_thr = 1.0d-10,
    electron_maxstep = 300,
    mixing_beta = 0.3,
/

ATOMIC_SPECIES
{chr(10).join(species_lines)}

CELL_PARAMETERS angstrom
{cell_parameters}

ATOMIC_POSITIONS crystal
{chr(10).join(atomic_positions)}

K_POINTS automatic
1 1 1 0 0 0
"""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        input_text,
        encoding="utf-8",
    )


# ============================================================================
# QE EXECUTION
# ============================================================================


def run_qe(
    executable: str,
    input_path: Path,
    output_path: Path,
    workdir: Path,
    timeout: int,
) -> tuple[str, int, str]:
    """
    Exécute pw.x.

    Cette fonction n'est appelée que lorsque --execute est actif.
    """

    workdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    start = time.time()

    try:

        with input_path.open(
            "r",
            encoding="utf-8",
        ) as stdin_handle, output_path.open(
            "w",
            encoding="utf-8",
        ) as stdout_handle:

            completed = subprocess.run(
                [
                    executable,
                    "-in",
                    str(input_path),
                ],
                stdin=stdin_handle,
                stdout=stdout_handle,
                stderr=subprocess.STDOUT,
                cwd=workdir,
                timeout=timeout,
                check=False,
            )

        elapsed = time.time() - start

        if completed.returncode == 0:
            return (
                "DONE",
                completed.returncode,
                f"{elapsed:.1f}s",
            )

        return (
            "FAILED",
            completed.returncode,
            f"{elapsed:.1f}s",
        )

    except subprocess.TimeoutExpired:

        return (
            "TIMEOUT",
            -1,
            f">{timeout}s",
        )

    except Exception as exc:

        return (
            "ERROR",
            -1,
            str(exc),
        )


# ============================================================================
# QE OUTPUT PARSER
# ============================================================================


def parse_total_energy(
    output_path: Path,
) -> Optional[float]:
    """
    Extrait la dernière énergie totale QE en Ry.
    """

    if not output_path.exists():
        return None

    last_energy = None

    try:

        for line in output_path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines():

            if "!    total energy" in line:

                parts = line.split()

                for index, token in enumerate(parts):

                    if token == "=" and index + 1 < len(parts):

                        value = safe_float(
                            parts[index + 1]
                        )

                        if value is not None:
                            last_energy = value

    except OSError:
        return None

    return last_energy


def qe_job_done(
    output_path: Path,
) -> bool:

    if not output_path.exists():
        return False

    try:

        text = output_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return "JOB DONE." in text

    except OSError:
        return False


# ============================================================================
# MANIFEST
# ============================================================================


def write_manifest(
    jobs: list[DFTJob],
    qe_executable: str,
    execute: bool,
) -> None:

    summary = {
        "phase": 20,
        "name": "AUTOMATED DFT",
        "project_root": str(ROOT),
        "input_priority": str(INPUT_PRIORITY),
        "qe_executable": qe_executable,
        "execute": execute,
        "qe_launched": execute and bool(jobs),
        "pw_x_launched": execute and bool(jobs),
        "bands_x_launched": False,
        "dos_x_launched": False,
        "total_jobs": len(jobs),
        "relax_done": sum(
            job.relax_status == "DONE"
            for job in jobs
        ),
        "relax_failed": sum(
            job.relax_status in {
                "FAILED",
                "ERROR",
                "TIMEOUT",
            }
            for job in jobs
        ),
        "scf_done": sum(
            job.scf_status == "DONE"
            for job in jobs
        ),
        "scf_failed": sum(
            job.scf_status in {
                "FAILED",
                "ERROR",
                "TIMEOUT",
            }
            for job in jobs
        ),
        "jobs": [
            asdict(job)
            for job in jobs
        ],
    }

    MANIFEST_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_audit(
    jobs: list[DFTJob],
) -> None:

    fields = [
        "rank",
        "source",
        "name",
        "material_id",
        "formula",
        "cif",
        "dft_priority_score",
        "selection_class",
        "cif_exists",
        "cif_sha256",
        "relax_input",
        "relax_output",
        "scf_input",
        "scf_output",
        "relax_status",
        "scf_status",
        "relax_return_code",
        "scf_return_code",
        "total_energy_ry",
        "electronic_status",
        "execution_mode",
        "error",
    ]

    with AUDIT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for job in jobs:
            writer.writerow(asdict(job))


# ============================================================================
# JOB PROCESSING
# ============================================================================


def process_job(
    row: dict,
    qe_executable: str,
    execute: bool,
    timeout: int,
) -> DFTJob:

    rank = safe_int(
        row.get("dft_rank"),
        default=0,
    )

    source = str(
        row.get("source", "")
    )

    name = str(
        row.get("name", "")
    )

    material_id = str(
        row.get("material_id", "")
    )

    formula = str(
        row.get("formula", "")
    )

    cif = str(
        row.get("cif", "")
    )

    priority_score = safe_float(
        row.get("dft_priority_score")
    ) or 0.0

    selection_class = str(
        row.get("selection_class", "")
    )

    safe = sanitize_name(name)

    relax_workdir = RELAX_DIR / f"{rank:03d}_{safe}"
    scf_workdir = SCF_DIR / f"{rank:03d}_{safe}"

    relax_input = relax_workdir / "relax.in"
    relax_output = relax_workdir / "relax.out"

    scf_input = scf_workdir / "scf.in"
    scf_output = scf_workdir / "scf.out"

    cif_exists, cif_hash = validate_cif(cif)

    job = DFTJob(
        rank=rank,
        source=source,
        name=name,
        material_id=material_id,
        formula=formula,
        cif=cif,
        dft_priority_score=round(
            priority_score,
            6,
        ),
        selection_class=selection_class,
        cif_exists=cif_exists,
        cif_sha256=cif_hash,
        relax_input=str(relax_input),
        relax_output=str(relax_output),
        scf_input=str(scf_input),
        scf_output=str(scf_output),
        relax_status="NOT_STARTED",
        scf_status="NOT_STARTED",
        relax_return_code=None,
        scf_return_code=None,
        total_energy_ry=None,
        electronic_status="NOT_STARTED",
        execution_mode=(
            "EXECUTE"
            if execute
            else "DRY_RUN"
        ),
        error="",
    )

    # ----------------------------------------------------------------------
    # CIF
    # ----------------------------------------------------------------------

    if not cif_exists:

        job.relax_status = "BLOCKED"
        job.scf_status = "BLOCKED"
        job.electronic_status = "BLOCKED"
        job.error = "CIF_NOT_FOUND"

        return job

    # ----------------------------------------------------------------------
    # GENERATE RELAX
    # ----------------------------------------------------------------------

    try:

        generate_relax_input(
            row,
            relax_input,
        )

        job.relax_status = "INPUT_READY"

    except Exception as exc:

        job.relax_status = "INPUT_ERROR"
        job.scf_status = "BLOCKED"
        job.electronic_status = "BLOCKED"
        job.error = (
            f"RELAX_INPUT_ERROR: {exc}"
        )

        return job

    # ----------------------------------------------------------------------
    # DRY RUN
    # ----------------------------------------------------------------------

    if not execute:

        job.scf_status = "WAITING_RELAX"
        job.electronic_status = "WAITING_SCF"

        return job

    # ----------------------------------------------------------------------
    # RELAX
    # ----------------------------------------------------------------------

    status, return_code, _ = run_qe(
        executable=qe_executable,
        input_path=relax_input,
        output_path=relax_output,
        workdir=relax_workdir,
        timeout=timeout,
    )

    job.relax_status = status
    job.relax_return_code = return_code

    if status != "DONE":

        job.scf_status = "BLOCKED"
        job.electronic_status = "BLOCKED"

        job.error = (
            f"RELAX_{status}"
        )

        return job

    # ----------------------------------------------------------------------
    # CHECK JOB DONE
    # ----------------------------------------------------------------------

    if not qe_job_done(relax_output):

        job.relax_status = "FAILED"
        job.scf_status = "BLOCKED"
        job.electronic_status = "BLOCKED"
        job.error = "RELAX_NO_JOB_DONE"

        return job

    # ----------------------------------------------------------------------
    # GENERATE SCF
    # ----------------------------------------------------------------------

    try:

        generate_scf_input(
            row,
            relax_workdir,
            scf_input,
        )

        job.scf_status = "INPUT_READY"

    except Exception as exc:

        job.scf_status = "INPUT_ERROR"
        job.electronic_status = "BLOCKED"
        job.error = (
            f"SCF_INPUT_ERROR: {exc}"
        )

        return job

    # ----------------------------------------------------------------------
    # SCF
    # ----------------------------------------------------------------------

    status, return_code, _ = run_qe(
        executable=qe_executable,
        input_path=scf_input,
        output_path=scf_output,
        workdir=scf_workdir,
        timeout=timeout,
    )

    job.scf_status = status
    job.scf_return_code = return_code

    if status != "DONE":

        job.electronic_status = "BLOCKED"
        job.error = (
            f"SCF_{status}"
        )

        return job

    # ----------------------------------------------------------------------
    # SCF VALIDATION
    # ----------------------------------------------------------------------

    if not qe_job_done(scf_output):

        job.scf_status = "FAILED"
        job.electronic_status = "BLOCKED"
        job.error = "SCF_NO_JOB_DONE"

        return job

    job.total_energy_ry = parse_total_energy(
        scf_output
    )

    job.electronic_status = "READY_FOR_PHASE_21"

    return job


# ============================================================================
# ARGUMENTS
# ============================================================================


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 20 — Automated DFT"
        )
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Autorise réellement l'exécution de pw.x."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            f"Nombre maximal de candidats "
            f"(défaut={DEFAULT_LIMIT})."
        ),
    )

    parser.add_argument(
        "--names",
        nargs="*",
        default=None,
        help=(
            "Noms de matériaux à traiter."
        ),
    )

    parser.add_argument(
        "--qe",
        default=PW_X_DEFAULT,
        help=(
            f"Executable pw.x "
            f"(défaut={PW_X_DEFAULT})."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=(
            f"Timeout par calcul en secondes "
            f"(défaut={DEFAULT_TIMEOUT})."
        ),
    )

    return parser.parse_args()


# ============================================================================
# MAIN
# ============================================================================


def main():

    args = parse_args()

    print("=" * 80)
    print(" HydroMatAI — PHASE 20")
    print(" AUTOMATED DFT")
    print("=" * 80)

    print()
    print("MODE")
    print("-" * 80)

    if args.execute:
        print("EXECUTION QE : AUTORISÉE")
    else:
        print("EXECUTION QE : NON")
        print("MODE          : DRY-RUN / PREPARATION")

    print()
    print("PROTECTION")
    print("-" * 80)
    print(
        "bands.x : NON LANCÉ"
    )
    print(
        "dos.x   : NON LANCÉ"
    )

    ensure_directories()

    # ----------------------------------------------------------------------
    # QE
    # ----------------------------------------------------------------------

    qe_available, qe_path = detect_qe(
        args.qe
    )

    print()
    print("ENVIRONNEMENT QE")
    print("-" * 80)

    if qe_available:
        print(
            f"pw.x : OK → {qe_path}"
        )
    else:
        print(
            f"pw.x : ABSENT → {args.qe}"
        )

        if args.execute:
            print()
            print(
                "ERREUR : --execute demandé mais pw.x "
                "est introuvable."
            )
            sys.exit(2)

    # ----------------------------------------------------------------------
    # INPUT
    # ----------------------------------------------------------------------

    print()
    print("CHARGEMENT DFT PRIORITY")
    print("-" * 80)

    try:

        rows = load_priority(
            INPUT_PRIORITY,
            names=args.names,
            limit=max(1, args.limit),
        )

    except Exception as exc:

        print(
            f"ERREUR : {exc}"
        )

        sys.exit(1)

    print(
        f"Candidats PRIORITY sélectionnés : "
        f"{len(rows)}"
    )

    if not rows:

        print(
            "Aucun candidat à traiter."
        )

        sys.exit(0)

    # ----------------------------------------------------------------------
    # PROCESS
    # ----------------------------------------------------------------------

    jobs: list[DFTJob] = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        name = row.get(
            "name",
            "",
        )

        print()
        print(
            f"[{index}/{len(rows)}] "
            f"{name}"
        )

        job = process_job(
            row=row,
            qe_executable=(
                qe_path
                if qe_available
                else args.qe
            ),
            execute=args.execute,
            timeout=args.timeout,
        )

        jobs.append(job)

        print(
            f"  CIF    : "
            f"{'OK' if job.cif_exists else 'FAIL'}"
        )

        print(
            f"  RELAX  : "
            f"{job.relax_status}"
        )

        print(
            f"  SCF    : "
            f"{job.scf_status}"
        )

        print(
            f"  Energy : "
            f"{job.total_energy_ry}"
        )

        if job.error:
            print(
                f"  ERROR  : "
                f"{job.error}"
            )

    # ----------------------------------------------------------------------
    # OUTPUTS
    # ----------------------------------------------------------------------

    write_manifest(
        jobs=jobs,
        qe_executable=(
            qe_path
            if qe_available
            else args.qe
        ),
        execute=args.execute,
    )

    write_audit(jobs)

    # ----------------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------------

    relax_done = sum(
        job.relax_status == "DONE"
        for job in jobs
    )

    scf_done = sum(
        job.scf_status == "DONE"
        for job in jobs
    )

    failed = sum(
        job.relax_status in {
            "FAILED",
            "ERROR",
            "TIMEOUT",
            "BLOCKED",
        }
        or job.scf_status in {
            "FAILED",
            "ERROR",
            "TIMEOUT",
        }
        for job in jobs
    )

    print()
    print("=" * 80)
    print(" PHASE 20 — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats                  : {len(jobs)}"
    )

    print(
        f"RELAX terminés             : {relax_done}"
    )

    print(
        f"SCF terminés               : {scf_done}"
    )

    print(
        f"Jobs avec problème         : {failed}"
    )

    print()
    print(
        f"MANIFEST : {MANIFEST_FILE}"
    )

    print(
        f"AUDIT    : {AUDIT_FILE}"
    )

    print()
    print("=" * 80)

    if args.execute:

        print(
            "QE : EXÉCUTÉ UNIQUEMENT POUR "
            "LES CANDIDATS PRIORITY"
        )

    else:

        print(
            "QE : NON LANCÉ — MODE DRY-RUN"
        )

    print(
        "bands.x : NON LANCÉ"
    )

    print(
        "dos.x   : NON LANCÉ"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()
