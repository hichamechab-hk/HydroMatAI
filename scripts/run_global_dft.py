#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from pymatgen.io.cif import CifParser


PROJECT_ROOT = Path("/home/hk/HydroMatAI")

TOP200_CSV = (
    PROJECT_ROOT
    / "reports"
    / "global_screening"
    / "TOP200_GLOBAL_H2_RANKED.csv"
)

QE_ROOT = (
    PROJECT_ROOT
    / "calculations"
    / "global_screening"
    / "qe"
    / "TOP20"
)

INPUT_DIR = QE_ROOT / "inputs"
OUTPUT_DIR = QE_ROOT / "outputs"
PSEUDO_DIR = QE_ROOT / "pseudo"

AUDIT_CSV = QE_ROOT / "global_dft_audit.csv"
MANIFEST_JSON = QE_ROOT / "global_dft_manifest.json"

QE_EXECUTABLE = Path("/home/hk/software/qe-7.5/bin/pw.x")

TOP_N = 20
MAX_PRIMITIVE_ATOMS = 350
SAFE_MAX_ATOMS = 300

ECUTWFC = 60.0
ECUTRHO = 480.0

K_POINTS = "Gamma"

PSEUDO_SEARCH_DIRS = [
    PSEUDO_DIR,
    PROJECT_ROOT / "pseudopotentials",
    PROJECT_ROOT / "data" / "pseudopotentials",
    Path("/home/hk/software/qe-7.5/pseudo"),
]


def now():
    return datetime.now().isoformat(timespec="seconds")


def clean_name(value):
    value = str(value).strip()
    chars = []
    for c in value:
        if c.isalnum() or c in "._-":
            chars.append(c)
        else:
            chars.append("_")
    return "".join(chars)


def resolve_cif_path(cif_value):
    raw = Path(str(cif_value).strip())

    candidates = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(PROJECT_ROOT / "data" / raw)
        candidates.append(PROJECT_ROOT / "MOF_Library" / raw)

    for path in candidates:
        if path.is_file():
            return path.resolve()

    return None


def parse_cif(cif_path):
    errors = []

    try:
        parser = CifParser(
            str(cif_path),
            occupancy_tolerance=1.0,
        )

        try:
            structures = parser.parse_structures(primitive=True)
        except Exception as exc:
            errors.append(f"primitive=True: {exc}")
            structures = []

        if structures:
            return structures[0], "primitive"

        try:
            structures = parser.parse_structures(primitive=False)
        except Exception as exc:
            errors.append(f"primitive=False: {exc}")
            structures = []

        if structures:
            return structures[0], "conventional"

    except Exception as exc:
        errors.append(str(exc))

    raise RuntimeError(" | ".join(errors) if errors else "CIF parse failed")


def get_elements(structure):
    elements = set()

    for site in structure:
        try:
            elements.add(site.specie.symbol)
            continue
        except Exception:
            pass

        try:
            for species in site.species:
                elements.add(species.symbol)
        except Exception:
            pass

    return sorted(elements)


def find_pseudopotentials():
    found = {}

    elements = [
        "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
        "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn"
    ]

    priority_dirs = [
        PSEUDO_DIR,
        PROJECT_ROOT / "pseudopotentials",
        PROJECT_ROOT / "data" / "pseudopotentials",
        Path("/home/hk/software/qe-7.5/pseudo"),
    ]

    for element in elements:
        matches = []

        for directory in priority_dirs:
            if not directory.is_dir():
                continue

            candidates = sorted(directory.glob("*.UPF"))

            for path in candidates:
                stem = path.stem

                if stem.lower() == element.lower():
                    matches.append(path)
                    continue

                if stem.lower().startswith(element.lower() + "."):
                    matches.append(path)

        unique = []
        seen = set()

        for path in matches:
            resolved = str(path.resolve())
            if resolved not in seen:
                seen.add(resolved)
                unique.append(path)

        if not unique:
            continue

        project_matches = [
            path for path in unique
            if path.parent.resolve() == PSEUDO_DIR.resolve()
        ]

        if project_matches:
            found[element] = [project_matches[0]]
        else:
            found[element] = [unique[0]]

    return found

def choose_pseudopotentials(elements, pseudo_candidates):
    selected = {}
    missing = []
    ambiguous = []

    for element in elements:
        candidates = pseudo_candidates.get(element, [])

        if len(candidates) == 0:
            missing.append(element)
            continue

        if len(candidates) > 1:
            ambiguous.append(
                {
                    "element": element,
                    "candidates": [str(p) for p in candidates],
                }
            )
            continue

        selected[element] = candidates[0]

    return selected, missing, ambiguous


def qe_atomic_label(element):
    return element


def make_qe_input(
    structure,
    material_id,
    name,
    pseudopotentials,
    output_file,
):
    elements = get_elements(structure)

    lines = []

    lines.append("&CONTROL")
    lines.append("    calculation = 'scf',")
    lines.append(f"    prefix = '{clean_name(material_id)}',")
    lines.append(f"    outdir = '{OUTPUT_DIR}',")
    lines.append("    pseudo_dir = '" + str(PSEUDO_DIR) + "',")
    lines.append("    tprnfor = .true.,")
    lines.append("    tstress = .true.,")
    lines.append("/")
    lines.append("")

    lines.append("&SYSTEM")
    lines.append("    ibrav = 0,")
    lines.append(f"    nat = {len(structure)},")
    lines.append(f"    ntyp = {len(elements)},")
    lines.append(f"    ecutwfc = {ECUTWFC},")
    lines.append(f"    ecutrho = {ECUTRHO},")
    lines.append("    occupations = 'fixed',")
    lines.append("/")
    lines.append("")

    lines.append("&ELECTRONS")
    lines.append("    conv_thr = 1.0d-8,")
    lines.append("    mixing_beta = 0.30,")
    lines.append("    electron_maxstep = 200,")
    lines.append("/")
    lines.append("")

    lines.append("ATOMIC_SPECIES")

    for element in elements:
        pseudo = pseudopotentials[element]
        mass = structure.composition.get_atomic_fraction(element)

        approximate_mass = {
            "H": 1.008,
            "C": 12.011,
            "N": 14.007,
            "O": 15.999,
            "Si": 28.085,
            "S": 32.06,
            "Cr": 51.996,
            "Cu": 63.546,
            "Zn": 65.38,
        }.get(element, 1.0)

        _ = mass

        lines.append(
            f"    {qe_atomic_label(element):<4} "
            f"{approximate_mass:.6f} "
            f"{pseudo.name}"
        )

    lines.append("")
    lines.append("ATOMIC_POSITIONS crystal")

    for site in structure:
        species = site.specie.symbol
        x, y, z = site.frac_coords
        lines.append(
            f"    {species:<4} "
            f"{x:.12f} "
            f"{y:.12f} "
            f"{z:.12f}"
        )

    lines.append("")
    lines.append("K_POINTS gamma")
    lines.append("")
    lines.append("CELL_PARAMETERS angstrom")

    lattice = structure.lattice.matrix

    for vector in lattice:
        lines.append(
            f"    {vector[0]:.12f} "
            f"{vector[1]:.12f} "
            f"{vector[2]:.12f}"
        )

    lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")


def classify_size(n_atoms):
    if n_atoms <= 200:
        return "SMALL"
    if n_atoms <= SAFE_MAX_ATOMS:
        return "MEDIUM"
    if n_atoms <= MAX_PRIMITIVE_ATOMS:
        return "LARGE"
    return "TOO_LARGE"


def machine_info():
    info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": None,
        "memory": None,
        "qe_executable": str(QE_EXECUTABLE),
        "qe_exists": QE_EXECUTABLE.is_file(),
    }

    try:
        info["cpu_count"] = (
            int(
                subprocess.check_output(
                    ["nproc"],
                    text=True,
                ).strip()
            )
        )
    except Exception:
        pass

    try:
        meminfo = Path("/proc/meminfo").read_text()
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                info["memory"] = line.strip()
                break
    except Exception:
        pass

    return info


def read_top200():
    if not TOP200_CSV.is_file():
        raise FileNotFoundError(
            f"CSV introuvable: {TOP200_CSV}"
        )

    with TOP200_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def numeric(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except Exception:
        return default


def integer(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Prepare QE inputs only; no QE calculation.",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Run QE calculations. Disabled unless explicitly requested.",
    )

    args = parser.parse_args()

    if not args.prepare and not args.run:
        args.prepare = True

    QE_ROOT.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PSEUDO_DIR.mkdir(parents=True, exist_ok=True)

    rows = read_top200()

    pseudo_candidates = find_pseudopotentials()

    audit = []
    eligible = []

    for row in rows:
        material_id = row.get("material_id", "").strip()
        name = row.get("name", "").strip()
        cif_value = row.get("cif", "").strip()

        audit_row = dict(row)

        audit_row["timestamp"] = now()
        audit_row["cif_resolved"] = ""
        audit_row["parse_mode"] = ""
        audit_row["primitive_atoms"] = ""
        audit_row["elements"] = ""
        audit_row["size_class"] = ""
        audit_row["pseudopotentials"] = ""
        audit_row["missing_pseudopotentials"] = ""
        audit_row["ambiguous_pseudopotentials"] = ""
        audit_row["status"] = ""
        audit_row["reason"] = ""
        audit_row["qe_input"] = ""

        cif_path = resolve_cif_path(cif_value)

        if cif_path is None:
            audit_row["status"] = "EXCLUDED"
            audit_row["reason"] = "CIF_NOT_FOUND"
            audit.append(audit_row)
            continue

        audit_row["cif_resolved"] = str(cif_path)

        try:
            structure, parse_mode = parse_cif(cif_path)
        except Exception as exc:
            audit_row["status"] = "EXCLUDED"
            audit_row["reason"] = f"CIF_PARSE_ERROR: {exc}"
            audit.append(audit_row)
            continue

        primitive_atoms = len(structure)
        elements = get_elements(structure)

        audit_row["parse_mode"] = parse_mode
        audit_row["primitive_atoms"] = primitive_atoms
        audit_row["elements"] = ",".join(elements)
        audit_row["size_class"] = classify_size(primitive_atoms)

        if primitive_atoms > MAX_PRIMITIVE_ATOMS:
            audit_row["status"] = "EXCLUDED"
            audit_row["reason"] = "TOO_MANY_PRIMITIVE_ATOMS"
            audit.append(audit_row)
            continue

        selected, missing, ambiguous = choose_pseudopotentials(
            elements,
            pseudo_candidates,
        )

        audit_row["pseudopotentials"] = ";".join(
            f"{element}:{path}"
            for element, path in selected.items()
        )

        audit_row["missing_pseudopotentials"] = ",".join(missing)

        audit_row["ambiguous_pseudopotentials"] = ";".join(
            f"{item['element']}={','.join(item['candidates'])}"
            for item in ambiguous
        )

        if missing:
            audit_row["status"] = "EXCLUDED"
            audit_row["reason"] = "MISSING_PSEUDOPOTENTIAL"
            audit.append(audit_row)
            continue

        if ambiguous:
            audit_row["status"] = "EXCLUDED"
            audit_row["reason"] = "AMBIGUOUS_PSEUDOPOTENTIAL"
            audit.append(audit_row)
            continue

        score = numeric(row, "score")
        hwt = numeric(row, "hydrogen_wt_percent")
        void_fraction = numeric(row, "void_fraction")
        surface_area = numeric(row, "surface_area_m2g")
        rank = integer(row, "rank", 999999)

        candidate = {
            "row": row,
            "structure": structure,
            "material_id": material_id,
            "name": name,
            "primitive_atoms": primitive_atoms,
            "elements": elements,
            "pseudopotentials": selected,
            "score": score,
            "hydrogen_wt_percent": hwt,
            "void_fraction": void_fraction,
            "surface_area_m2g": surface_area,
            "rank": rank,
            "audit_row": audit_row,
        }

        eligible.append(candidate)

    eligible.sort(
        key=lambda x: (
            -x["score"],
            -x["hydrogen_wt_percent"],
            -x["void_fraction"],
            -x["surface_area_m2g"],
            x["primitive_atoms"],
            x["rank"],
        )
    )

    selected_candidates = eligible[:TOP_N]

    for index, candidate in enumerate(selected_candidates, start=1):
        material_id = candidate["material_id"]
        name = candidate["name"]

        filename = (
            f"{index:04d}_"
            f"{clean_name(name or material_id)}.in"
        )

        input_file = INPUT_DIR / filename

        make_qe_input(
            candidate["structure"],
            material_id,
            name,
            candidate["pseudopotentials"],
            input_file,
        )

        audit_row = candidate["audit_row"]

        audit_row["status"] = "SELECTED"
        audit_row["reason"] = (
            "SELECTED_FOR_QE_PREPARATION"
        )
        audit_row["qe_input"] = str(input_file)

        audit.append(audit_row)

    selected_ids = {
        candidate["material_id"]
        for candidate in selected_candidates
    }

    for candidate in eligible[TOP_N:]:
        if candidate["material_id"] not in selected_ids:
            audit_row = candidate["audit_row"]
            audit_row["status"] = "ELIGIBLE_NOT_SELECTED"
            audit_row["reason"] = "OUTSIDE_TOP_N"
            audit.append(audit_row)

    fieldnames = []

    for row in audit:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with AUDIT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in audit:
            writer.writerow(row)

    manifest = {
        "created": now(),
        "project_root": str(PROJECT_ROOT),
        "top200_csv": str(TOP200_CSV),
        "qe_root": str(QE_ROOT),
        "input_dir": str(INPUT_DIR),
        "output_dir": str(OUTPUT_DIR),
        "pseudo_dir": str(PSEUDO_DIR),
        "qe_executable": str(QE_EXECUTABLE),
        "mode": "PREPARE" if args.prepare else "RUN",
        "qe_execution": False,
        "top_n": TOP_N,
        "max_primitive_atoms": MAX_PRIMITIVE_ATOMS,
        "safe_max_atoms": SAFE_MAX_ATOMS,
        "ecutwfc": ECUTWFC,
        "ecutrho": ECUTRHO,
        "k_points": K_POINTS,
        "machine": machine_info(),
        "total_csv_rows": len(rows),
        "parsed_or_processed": len(audit),
        "eligible": len(eligible),
        "selected": len(selected_candidates),
        "selected_structures": [],
    }

    for index, candidate in enumerate(
        selected_candidates,
        start=1,
    ):
        manifest["selected_structures"].append(
            {
                "selection": index,
                "material_id": candidate["material_id"],
                "name": candidate["name"],
                "rank": candidate["rank"],
                "primitive_atoms": candidate["primitive_atoms"],
                "elements": candidate["elements"],
                "size_class": classify_size(
                    candidate["primitive_atoms"]
                ),
                "score": candidate["score"],
                "hydrogen_wt_percent": candidate[
                    "hydrogen_wt_percent"
                ],
                "void_fraction": candidate["void_fraction"],
                "surface_area_m2g": candidate[
                    "surface_area_m2g"
                ],
                "qe_input": str(
                    INPUT_DIR
                    / (
                        f"{index:04d}_"
                        f"{clean_name(candidate['name'] or candidate['material_id'])}.in"
                    )
                ),
            }
        )

    MANIFEST_JSON.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("HYDROMATAI — GLOBAL DFT PREPARATION")
    print("=" * 70)
    print(f"CSV                         : {TOP200_CSV}")
    print(f"Structures in CSV           : {len(rows)}")
    print(f"Structures eligible         : {len(eligible)}")
    print(f"Selected                    : {len(selected_candidates)}")
    print(f"Maximum primitive atoms    : {MAX_PRIMITIVE_ATOMS}")
    print(f"Safe review threshold      : {SAFE_MAX_ATOMS}")
    print()
    print("Pseudopotentiels détectés :")

    for element in sorted(pseudo_candidates):
        for pseudo in pseudo_candidates[element]:
            print(f"  {element:>3} -> {pseudo}")

    print()
    print("Sélection :")

    for index, candidate in enumerate(
        selected_candidates,
        start=1,
    ):
        print(
            f"{index:02d}. "
            f"{candidate['name']} "
            f"| ID={candidate['material_id']} "
            f"| atoms={candidate['primitive_atoms']} "
            f"| size={classify_size(candidate['primitive_atoms'])} "
            f"| rank={candidate['rank']}"
        )

    print()
    print(f"Audit    : {AUDIT_CSV}")
    print(f"Manifest : {MANIFEST_JSON}")
    print(f"Inputs   : {INPUT_DIR}")

    if args.prepare:
        print()
        print("MODE PREPARE : aucun calcul QE n'a été lancé.")
        print("=" * 70)


if __name__ == "__main__":
    main()
