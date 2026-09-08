from __future__ import annotations
import os
os.system("clear")

import argparse
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "global_screening"
PRIORITY_FILE = REPORT_DIR / "dft_priority.csv"

PHASE20_DIR = ROOT / "calculations" / "phase_20_automated_dft"
PHASE21_DIR = ROOT / "calculations" / "phase_21_relax_diagnostic"
PHASE21B_DIR = ROOT / "calculations" / "phase_21b_relax_test"

QE_CANDIDATES = [
    ROOT / "software" / "qe-7.5" / "bin" / "pw.x",
    Path.home() / "software" / "qe-7.5" / "bin" / "pw.x",
    Path("/usr/bin/pw.x"),
]

PSEUDO_CANDIDATES = [
    ROOT / "pseudo",
    ROOT / "pseudopotentials",
    ROOT / "qe_pseudo",
    ROOT / "calculations" / "pseudo",
    Path.home() / "software" / "qe-7.5" / "pseudo",
]

ELEMENT_PSEUDO_MAP = {
    "H": "H.pbe-kjpaw_psl.1.0.0.UPF",
    "Mg": "Mg.pbe-n-kjpaw_psl.1.0.0.UPF",
}

QE_TIMEOUT = 1800


def find_pw() -> Path | None:
    for path in QE_CANDIDATES:
        if path.exists() and path.is_file():
            return path

    found = shutil.which("pw.x")
    if found:
        return Path(found)

    return None


def find_pseudo_dir(elements: list[str]) -> Path | None:
    for directory in PSEUDO_CANDIDATES:
        if not directory.exists():
            continue

        files = {
            p.name
            for p in directory.glob("*.UPF")
        }

        if all(
            any(
                name.lower().startswith(element.lower())
                for name in files
            )
            for element in elements
        ):
            return directory

    for directory in PSEUDO_CANDIDATES:
        if directory.exists() and any(directory.glob("*.UPF")):
            return directory

    return None


def read_priority(limit: int) -> list[dict[str, str]]:
    if not PRIORITY_FILE.exists():
        raise FileNotFoundError(PRIORITY_FILE)

    rows = []

    with PRIORITY_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            classification = (
                row.get("classification")
                or row.get("priority")
                or row.get("class")
                or ""
            ).strip().upper()

            if classification and classification != "PRIORITY":
                continue

            rows.append(row)

            if len(rows) >= limit:
                break

    return rows


def locate_cif(row: dict[str, str]) -> Path | None:
    raw = (
        row.get("cif")
        or row.get("cif_path")
        or ""
    ).strip()

    if raw:
        path = Path(raw)

        if not path.is_absolute():
            path = ROOT / path

        if path.exists():
            return path

    name = (
        row.get("name")
        or row.get("material")
        or ""
    ).strip()

    if not name:
        return None

    roots = [
        ROOT / "MOF_Library" / "MOFXDB_FULL" / "cif",
        ROOT / "MOF_Library" / "METAL_HYDRIDES" / "cif",
        ROOT / "MOF_Library" / "COMPLEXES" / "cif",
    ]

    for root in roots:
        if not root.exists():
            continue

        matches = list(root.glob(f"{name}*.cif"))

        if matches:
            return matches[0]

    return None


def parse_cif(cif: Path) -> dict:
    try:
        from pymatgen.core import Structure

        structure = Structure.from_file(cif)

        elements = sorted({
            site.specie.symbol
            for site in structure.sites
        })

        lattice = structure.lattice

        return {
            "structure": structure,
            "elements": elements,
            "nat": len(structure),
            "a": lattice.a,
            "b": lattice.b,
            "c": lattice.c,
            "alpha": lattice.alpha,
            "beta": lattice.beta,
            "gamma": lattice.gamma,
        }

    except Exception as exc:
        raise RuntimeError(
            f"CIF_PARSE_FAILED: {exc}"
        ) from exc


def choose_pseudopotentials(
    elements: list[str],
    pseudo_dir: Path,
) -> dict[str, str]:
    files = sorted(pseudo_dir.glob("*.UPF"))

    mapping = {}

    for element in elements:
        preferred = ELEMENT_PSEUDO_MAP.get(element)

        if preferred:
            candidate = pseudo_dir / preferred

            if candidate.exists():
                mapping[element] = candidate.name
                continue

        candidates = [
            p for p in files
            if p.name.lower().startswith(
                element.lower()
            )
        ]

        if not candidates:
            raise RuntimeError(
                f"PSEUDOPOTENTIAL_MISSING: {element}"
            )

        mapping[element] = candidates[0].name

    return mapping


def format_species(
    structure,
    pseudo: dict[str, str],
) -> str:
    elements = sorted({
        site.specie.symbol
        for site in structure.sites
    })

    lines = []

    for index, element in enumerate(elements, start=1):
        mass = structure.composition.get_atomic_fraction(element)

        atomic_mass = {
            "H": 1.008,
            "Mg": 24.305,
        }.get(element, 1.0)

        lines.append(
            f"{element:<4} "
            f"{atomic_mass:10.5f} "
            f"{pseudo[element]}"
        )

    return "\n".join(lines)


def format_positions(structure) -> str:
    lines = []

    for site in structure.sites:
        element = site.specie.symbol
        x, y, z = site.frac_coords

        lines.append(
            f"{element:<4} "
            f"{x: .10f} "
            f"{y: .10f} "
            f"{z: .10f}"
        )

    return "\n".join(lines)


def format_cell(structure) -> str:
    matrix = structure.lattice.matrix

    return "\n".join(
        " ".join(
            f"{float(value): .12f}"
            for value in vector
        )
        for vector in matrix
    )


def generate_relax_input(
    structure,
    pseudo: dict[str, str],
    pseudo_dir: Path,
    outdir: Path,
) -> str:

    elements = sorted({
        site.specie.symbol
        for site in structure.sites
    })

    species = format_species(
        structure,
        pseudo,
    )

    positions = format_positions(
        structure,
    )

    cell = format_cell(
        structure,
    )

    return f"""&CONTROL
    calculation = 'relax',
    prefix = 'hydromatai_relax',
    pseudo_dir = '{pseudo_dir}',
    outdir = '{outdir}',
    tstress = .true.,
    tprnfor = .true.,
    verbosity = 'high',
    etot_conv_thr = 1.0d-5,
    forc_conv_thr = 1.0d-4,
/

&SYSTEM
    ibrav = 0,
    nat = {len(structure)},
    ntyp = {len(elements)},
    ecutwfc = 60.0,
    ecutrho = 480.0,
    occupations = 'fixed',
/

&ELECTRONS
    conv_thr = 1.0d-8,
    electron_maxstep = 200,
    mixing_beta = 0.30,
    diagonalization = 'david',
/

&IONS
    ion_dynamics = 'bfgs',
/

ATOMIC_SPECIES
{species}

CELL_PARAMETERS angstrom
{cell}

ATOMIC_POSITIONS crystal
{positions}

K_POINTS gamma
"""


def run_relax(
    pw: Path,
    input_file: Path,
    output_file: Path,
) -> tuple[int, str]:

    command = [
        str(pw),
    ]

    try:
        with input_file.open(
            "r",
            encoding="utf-8",
        ) as stdin_handle, output_file.open(
            "w",
            encoding="utf-8",
        ) as stdout_handle:

            completed = subprocess.run(
                command,
                stdin=stdin_handle,
                stdout=stdout_handle,
                stderr=subprocess.STDOUT,
                cwd=input_file.parent,
                timeout=QE_TIMEOUT,
                check=False,
            )

        return completed.returncode, ""

    except subprocess.TimeoutExpired:
        return -1, "QE_TIMEOUT"

    except Exception as exc:
        return -1, str(exc)


def inspect_output(
    output: Path,
) -> dict:
    if not output.exists():
        return {
            "exists": False,
            "job_done": False,
            "converged": False,
            "category": "OUTPUT_MISSING",
        }

    text = output.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lower = text.lower()

    job_done = "job done." in lower

    converged = (
        "convergence has been achieved"
        in lower
        or "bfgs converged"
        in lower
    )

    patterns = [
        (
            "PSEUDOPOTENTIAL_ERROR",
            [
                "cannot open pseudopotential",
                "file not found",
                "error in routine readpp",
            ],
        ),
        (
            "INPUT_ERROR",
            [
                "error in routine read_namelists",
                "bad parameter",
                "wrong number of",
                "unknown variable",
            ],
        ),
        (
            "SCF_CONVERGENCE_ERROR",
            [
                "convergence not achieved",
                "convergence has not been achieved",
            ],
        ),
        (
            "DIAGONALIZATION_ERROR",
            [
                "diagonalization failed",
                "error in routine cdiaghg",
                "error in routine cegterg",
            ],
        ),
        (
            "MPI_ERROR",
            [
                "mpi_abort",
                "segmentation fault",
                "floating point exception",
            ],
        ),
    ]

    category = "RELAX_FAILED"

    if job_done or converged:
        category = "RELAX_SUCCESS"

    for name, needles in patterns:
        if any(
            needle in lower
            for needle in needles
        ):
            category = name
            break

    energy = None

    matches = re.findall(
        r"!\s+total energy\s+=\s+([-+0-9.EeDd]+)",
        text,
    )

    if matches:
        raw = matches[-1].replace(
            "D",
            "E",
        )

        try:
            energy = float(raw)
        except ValueError:
            pass

    return {
        "exists": True,
        "job_done": job_done,
        "converged": converged,
        "category": category,
        "energy_ry": energy,
        "tail": "\n".join(
            text.splitlines()[-50:]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Autorise un test RELAX QE.",
    )

    args = parser.parse_args()

    PHASE21B_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print(" HydroMatAI — PHASE 21B")
    print(" CORRECTION CHEMIN + TEST RELAX QE")
    print("=" * 80)

    print()
    print("QE")
    print("-" * 80)

    pw = find_pw()

    if pw:
        print(f"pw.x : OK → {pw}")
    else:
        print("pw.x : NON TROUVÉ")
        return 1

    rows = read_priority(args.limit)

    print()
    print("CANDIDATS")
    print("-" * 80)
    print(f"Priority sélectionnés : {len(rows)}")

    results = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        material = (
            row.get("name")
            or row.get("material")
            or row.get("material_id")
            or f"candidate_{index}"
        ).strip()

        print()
        print(
            f"[{index}/{len(rows)}] "
            f"{material}"
        )

        cif = locate_cif(row)

        if not cif:
            print("  CIF    : MISSING")

            results.append({
                "material": material,
                "cif": "",
                "status": "CIF_MISSING",
            })

            continue

        print(f"  CIF    : OK → {cif}")

        try:
            parsed = parse_cif(cif)

            structure = parsed["structure"]
            elements = parsed["elements"]

            print(
                "  Elements : "
                + ", ".join(elements)
            )

            print(
                f"  Atomes   : {parsed['nat']}"
            )

        except Exception as exc:
            print(
                f"  CIF parse : FAILED → {exc}"
            )

            results.append({
                "material": material,
                "cif": str(cif),
                "status": "CIF_PARSE_FAILED",
                "error": str(exc),
            })

            continue

        pseudo_dir = find_pseudo_dir(
            elements
        )

        if pseudo_dir is None:
            print(
                "  Pseudo : NON TROUVÉ"
            )

            results.append({
                "material": material,
                "cif": str(cif),
                "status": "PSEUDO_DIR_MISSING",
            })

            continue

        print(
            f"  Pseudo : {pseudo_dir}"
        )

        try:
            pseudo = choose_pseudopotentials(
                elements,
                pseudo_dir,
            )

        except Exception as exc:
            print(
                f"  Pseudo mapping : FAILED → {exc}"
            )

            results.append({
                "material": material,
                "cif": str(cif),
                "status": "PSEUDO_MAPPING_FAILED",
                "error": str(exc),
            })

            continue

        job_dir = (
            PHASE21B_DIR /
            material.replace("/", "_")
        )

        job_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        outdir = job_dir / "tmp"

        outdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        input_file = (
            job_dir /
            "relax.in"
        )

        output_file = (
            job_dir /
            "relax.out"
        )

        input_text = generate_relax_input(
            structure,
            pseudo,
            pseudo_dir,
            outdir,
        )

        input_file.write_text(
            input_text,
            encoding="utf-8",
        )

        print(
            f"  Input : {input_file}"
        )

        if not args.execute:
            print(
                "  RELAX : NON LANCÉ "
                "(mode diagnostic)"
            )

            results.append({
                "material": material,
                "cif": str(cif),
                "input": str(input_file),
                "status": "INPUT_GENERATED",
                "executed": False,
            })

            continue

        print(
            "  RELAX : LANCEMENT TEST"
        )

        returncode, runtime_error = run_relax(
            pw,
            input_file,
            output_file,
        )

        inspection = inspect_output(
            output_file
        )

        if inspection["converged"] or inspection["job_done"]:
            status = "RELAX_SUCCESS"
        else:
            status = inspection["category"]

        print(
            f"  RELAX : {status}"
        )

        if inspection.get("energy_ry") is not None:
            print(
                f"  Energy : "
                f"{inspection['energy_ry']} Ry"
            )

        if runtime_error:
            print(
                f"  Runtime : {runtime_error}"
            )

        results.append({
            "material": material,
            "cif": str(cif),
            "input": str(input_file),
            "output": str(output_file),
            "status": status,
            "returncode": returncode,
            "energy_ry": inspection.get(
                "energy_ry"
            ),
            "job_done": inspection.get(
                "job_done"
            ),
            "converged": inspection.get(
                "converged"
            ),
            "error": runtime_error,
            "tail": inspection.get(
                "tail",
                "",
            ),
        })

    summary = {
        "phase": "21B",
        "description": (
            "Correction chemin/génération RELAX "
            "et test contrôlé"
        ),
        "qe_executed": bool(args.execute),
        "pw": str(pw),
        "limit": args.limit,
        "results": results,
    }

    summary_file = (
        PHASE21B_DIR /
        "phase21b_summary.json"
    )

    summary_file.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(" PHASE 21B — RÉSULTATS")
    print("=" * 80)

    for result in results:
        print(
            f"{result['material']:<30} "
            f"{result['status']}"
        )

    print()
    print(
        f"SUMMARY : {summary_file}"
    )

    print()
    print("=" * 80)
    print(" PHASE 21B — TERMINÉE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
