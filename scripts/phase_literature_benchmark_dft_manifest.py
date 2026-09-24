#!/usr/bin/env python3

import csv
import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF_DIR = BASE / "data/literature_benchmarks/cif"
REPORT_DIR = BASE / "reports/literature_benchmarks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = REPORT_DIR / "literature_benchmark_dft_manifest.csv"
OUTPUT_TXT = REPORT_DIR / "literature_benchmark_dft_manifest.txt"

BENCHMARKS = {
    "K2GeH6": {
        "family": "A2BH6",
        "article": "Exploration of A2BH6 (A=K,Rb; B=Ge,Sn) hydrides",
        "space_group": "Fm-3m",
        "number": 225,
        "a": 7.968,
        "volume": 505.991,
        "z": 4,
        "h2_wt": 3.84,
        "literature_code": "CASTEP",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "680 eV",
        "literature_kmesh": "8x8x8",
        "literature_pp": "OTFG ultrasoft",
        "literature_relax": "ionic convergence -0.001 eV/A",
        "literature_scf": "1e-6 eV",
        "literature_electronic": "HSE06",
    },
    "K2SnH6": {
        "family": "A2BH6",
        "article": "Exploration of A2BH6 (A=K,Rb; B=Ge,Sn) hydrides",
        "space_group": "Fm-3m",
        "number": 225,
        "a": 8.338,
        "volume": 579.679,
        "z": 4,
        "h2_wt": 2.97,
        "literature_code": "CASTEP",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "680 eV",
        "literature_kmesh": "8x8x8",
        "literature_pp": "OTFG ultrasoft",
        "literature_relax": "ionic convergence -0.001 eV/A",
        "literature_scf": "1e-6 eV",
        "literature_electronic": "HSE06",
    },
    "Rb2GeH6": {
        "family": "A2BH6",
        "article": "Exploration of A2BH6 (A=K,Rb; B=Ge,Sn) hydrides",
        "space_group": "Fm-3m",
        "number": 225,
        "a": 8.318,
        "volume": 575.574,
        "z": 4,
        "h2_wt": 2.48,
        "literature_code": "CASTEP",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "680 eV",
        "literature_kmesh": "8x8x8",
        "literature_pp": "OTFG ultrasoft",
        "literature_relax": "ionic convergence -0.001 eV/A",
        "literature_scf": "1e-6 eV",
        "literature_electronic": "HSE06",
    },
    "Rb2SnH6": {
        "family": "A2BH6",
        "article": "Exploration of A2BH6 (A=K,Rb; B=Ge,Sn) hydrides",
        "space_group": "Fm-3m",
        "number": 225,
        "a": 8.666,
        "volume": 650.974,
        "z": 4,
        "h2_wt": 2.09,
        "literature_code": "CASTEP",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "680 eV",
        "literature_kmesh": "8x8x8",
        "literature_pp": "OTFG ultrasoft",
        "literature_relax": "ionic convergence -0.001 eV/A",
        "literature_scf": "1e-6 eV",
        "literature_electronic": "HSE06",
    },
    "NaPdH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.61,
        "volume": 47.08,
        "z": 1,
        "h2_wt": 2.28,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
    "CaPdH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.72,
        "volume": 51.46,
        "z": 1,
        "h2_wt": 2.02,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
    "SrPdH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.84,
        "volume": 56.60,
        "z": 1,
        "h2_wt": 1.53,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
    "NaRuH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.53,
        "volume": 43.87,
        "z": 1,
        "h2_wt": 2.38,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
    "CaRuH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.64,
        "volume": 48.21,
        "z": 1,
        "h2_wt": 2.10,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
    "SrRuH3": {
        "family": "APdH3_ARuH3",
        "article": "Toward Efficient Hydrogen Storage: Physical and Hydrogen Storage Properties of APdH3 and ARuH3",
        "space_group": "Pm-3m",
        "number": 221,
        "a": 3.77,
        "volume": 53.42,
        "z": 1,
        "h2_wt": 1.58,
        "literature_code": "Quantum ESPRESSO",
        "literature_functional": "PBE-GGA",
        "literature_cutoff": "500 eV",
        "literature_kmesh": "15x15x15",
        "literature_pp": "Vanderbilt ultrasoft",
        "literature_relax": "BFGS; force 0.02 eV/A",
        "literature_scf": "1e-6 eV/atom",
        "literature_electronic": "AIMD 300/600 K",
    },
}


def parse_cif(path):
    text = path.read_text(errors="replace")

    def tag(pattern, default=""):
        m = re.search(pattern, text, re.I | re.M)
        return m.group(1).strip().strip("'\"") if m else default

    formula = tag(r"^\s*_chemical_formula_sum\s+(.+)$")
    sg = tag(r"^\s*_(?:symmetry_space_group_name_H-M_alt|space_group\.name_H-M_alt)\s+(.+)$")
    sg_no = tag(r"^\s*_(?:symmetry_Int_Tables_number|space_group\.IT_number)\s+(.+)$")

    a = float(tag(r"^\s*_cell_length_a\s+([0-9.Ee+\-]+)$", "nan"))
    b = float(tag(r"^\s*_cell_length_b\s+([0-9.Ee+\-]+)$", "nan"))
    c = float(tag(r"^\s*_cell_length_c\s+([0-9.Ee+\-]+)$", "nan"))

    atoms = []
    in_loop = False
    headers = []

    for line in text.splitlines():
        s = line.strip()

        if s.lower() == "loop_":
            in_loop = True
            headers = []
            continue

        if in_loop and s.startswith("_"):
            headers.append(s)
            continue

        if in_loop and headers and not s:
            continue

        if in_loop and headers and not s.startswith("_"):
            parts = s.split()
            if len(parts) >= len(headers):
                record = dict(zip(headers, parts))
                if any(k.lower() == "_atom_site_type_symbol" for k in record):
                    atoms.append(record)
            elif s.startswith("data_"):
                in_loop = False

    elements = []
    for atom in atoms:
        key = next(
            (k for k in atom if k.lower() == "_atom_site_type_symbol"),
            None
        )
        if key:
            elements.append(atom[key])

    return {
        "formula": formula,
        "space_group": sg,
        "space_group_number": sg_no,
        "a": a,
        "b": b,
        "c": c,
        "nat": len(atoms),
        "elements": ",".join(sorted(set(elements))),
    }


print("=" * 78)
print("LITERATURE BENCHMARKS — DFT PREPARATION MANIFEST")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun CIF modifié")
print("[INFO] Aucun calcul DFT")
print()

rows = []

for material, ref in BENCHMARKS.items():
    cif = CIF_DIR / f"{material}.cif"

    if not cif.exists():
        print(f"[ERROR] CIF absent : {cif}")
        status = "MISSING_CIF"
        data = {
            "formula": "",
            "space_group": "",
            "space_group_number": "",
            "a": "",
            "b": "",
            "c": "",
            "nat": "",
            "elements": "",
        }
    else:
        data = parse_cif(cif)
        status = "READY_FOR_DFT_PREPARATION"

    row = {
        "material": material,
        "family": ref["family"],
        "cif": str(cif),
        "source_article": ref["article"],
        "publication_status": "PUBLISHED_ARTICLE",
        "structure_status": "RECONSTRUCTED_FROM_PUBLISHED_PARAMETERS",
        "experimental_status": "NOT_EXPERIMENTAL_CIF",
        "formula": data["formula"],
        "elements": data["elements"],
        "nat": data["nat"],
        "space_group_cif": data["space_group"],
        "space_group_expected": f'{ref["space_group"]} #{ref["number"]}',
        "a_cif_A": data["a"],
        "b_cif_A": data["b"],
        "c_cif_A": data["c"],
        "a_published_A": ref["a"],
        "volume_published_A3": ref["volume"],
        "Z_expected": ref["z"],
        "H2_wt_percent_published": ref["h2_wt"],
        "literature_code": ref["literature_code"],
        "literature_functional": ref["literature_functional"],
        "literature_cutoff": ref["literature_cutoff"],
        "literature_kmesh": ref["literature_kmesh"],
        "literature_pseudopotentials": ref["literature_pp"],
        "literature_relaxation": ref["literature_relax"],
        "literature_scf": ref["literature_scf"],
        "literature_electronic": ref["literature_electronic"],
        "qe_status": "NOT_GENERATED",
        "calculation_status": status,
    }

    rows.append(row)

    print(f"{material:10s} | {status}")
    print(f"  CIF : {data['formula']} | {data['nat']} atoms | "
          f"{data['space_group']} #{data['space_group_number']}")
    print(f"  a,b,c : {data['a']} {data['b']} {data['c']} A")
    print(f"  Literature : {ref['literature_code']} | "
          f"{ref['literature_functional']} | "
          f"{ref['literature_cutoff']} | {ref['literature_kmesh']}")
    print()

fields = list(rows[0].keys())

with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

with OUTPUT_TXT.open("w", encoding="utf-8") as f:
    f.write("=" * 78 + "\n")
    f.write("LITERATURE BENCHMARKS — DFT PREPARATION MANIFEST\n")
    f.write("=" * 78 + "\n")
    f.write("MODE = READ-ONLY\n")
    f.write("No pw.x / No CIF modification / No DFT calculation\n\n")

    for r in rows:
        f.write(
            f"{r['material']} | {r['family']} | "
            f"{r['structure_status']} | "
            f"{r['calculation_status']}\n"
        )
        f.write(
            f"  SG={r['space_group_expected']} | "
            f"a={r['a_published_A']} A | "
            f"V={r['volume_published_A3']} A3 | "
            f"Z={r['Z_expected']}\n"
        )
        f.write(
            f"  Literature={r['literature_code']} / "
            f"{r['literature_functional']} / "
            f"{r['literature_cutoff']} / "
            f"{r['literature_kmesh']}\n"
        )
        f.write(
            f"  QE status={r['qe_status']}\n\n"
        )

ready = sum(r["calculation_status"] == "READY_FOR_DFT_PREPARATION" for r in rows)

print("=" * 78)
print("SUMMARY")
print("=" * 78)
print(f"TOTAL BENCHMARKS : {len(rows)}")
print(f"READY             : {ready}/{len(rows)}")
print(f"QE INPUTS         : NOT GENERATED")
print(f"PW.X              : NOT EXECUTED")
print()
print(f"[REPORT] {OUTPUT_CSV}")
print(f"[REPORT] {OUTPUT_TXT}")
