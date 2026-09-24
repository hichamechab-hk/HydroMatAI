#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
TOP1 = "hMOF-5064089"

QE_DIR = ROOT / "calculations/global_screening/qe/TOP20/0001_hMOF-5064089"
OUT_DIR = ROOT / "calculations/phase_18_scf_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def find_output():
    candidates = [
        QE_DIR / f"{TOP1}.out",
        QE_DIR / "scf.out",
        QE_DIR / f"{TOP1}.log",
    ]

    for p in candidates:
        if p.exists():
            return p

    found = list(QE_DIR.glob("*.out")) + list(QE_DIR.glob("*.log"))
    if found:
        return found[0]

    return None

def extract_energy(text):
    matches = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text
    )
    if matches:
        return float(matches[-1])

    return None

def extract_scf_iterations(text):
    return len(
        re.findall(
            r"iteration\s*#?\s*\d+",
            text,
            re.IGNORECASE
        )
    )

def extract_convergence(text):
    if re.search(
        r"convergence has been achieved",
        text,
        re.IGNORECASE
    ):
        return True

    if re.search(
        r"convergence NOT achieved|convergence not achieved",
        text,
        re.IGNORECASE
    ):
        return False

    return None

def extract_bfgs(text):
    return bool(
        re.search(
            r"BFGS|End of BFGS",
            text,
            re.IGNORECASE
        )
    )

def extract_error(text):
    errors = []

    patterns = [
        r"Error in routine[^\n]*",
        r"error[^\n]*",
        r"stopping[^\n]*",
        r"maximum number of iterations[^\n]*",
    ]

    for pattern in patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            line = m.strip()
            if line and line not in errors:
                errors.append(line)

    return errors[-10:]

def extract_nscf(text):
    values = re.findall(
        r"number of k points\s*=\s*(\d+)",
        text,
        re.IGNORECASE
    )

    return int(values[-1]) if values else None

output_file = find_output()

if output_file is None:
    status = "SCF_OUTPUT_NOT_FOUND"

    result = {
        "phase": "18",
        "candidate": TOP1,
        "status": status,
        "output_file": None,
        "completed": False,
        "converged": None,
        "total_energy_ry": None,
        "scf_iterations": None,
        "errors": [],
        "qe_calculation_launched": False,
        "analysis_only": True,
    }

else:
    text = output_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    energy = extract_energy(text)
    iterations = extract_scf_iterations(text)
    converged = extract_convergence(text)
    errors = extract_error(text)

    completed = bool(
        energy is not None
        and converged is True
    )

    if errors:
        status = "QE_ERROR"
    elif completed:
        status = "SCF_CONVERGED"
    elif energy is not None:
        status = "ENERGY_FOUND_NOT_CONFIRMED"
    else:
        status = "SCF_INCOMPLETE"

    result = {
        "phase": "18",
        "candidate": TOP1,
        "status": status,
        "output_file": str(output_file),
        "completed": completed,
        "converged": converged,
        "total_energy_ry": energy,
        "scf_iterations": iterations,
        "errors": errors,
        "qe_calculation_launched": False,
        "analysis_only": True,
    }

json_path = OUT_DIR / "phase18_scf_analysis.json"
csv_path = OUT_DIR / "phase18_scf_analysis.csv"
manifest_path = OUT_DIR / "phase18_manifest.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "phase",
            "candidate",
            "status",
            "output_file",
            "completed",
            "converged",
            "total_energy_ry",
            "scf_iterations",
            "errors",
            "qe_calculation_launched",
            "analysis_only",
        ]
    )
    writer.writeheader()

    row = dict(result)
    row["errors"] = " | ".join(result["errors"])
    writer.writerow(row)

manifest = {
    "phase": "18",
    "title": "SCF TOP1 ANALYSIS",
    "candidate": TOP1,
    "status": result["status"],
    "analysis_only": True,
    "qe_calculation_launched": False,
    "cif_modified": False,
    "output_file": result["output_file"],
    "total_energy_ry": result["total_energy_ry"],
    "converged": result["converged"],
    "scf_iterations": result["scf_iterations"],
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print("=" * 78)
print("PHASE 18 — SCF TOP1 ANALYSIS")
print("=" * 78)
print()
print("MODE              : ANALYSIS_ONLY")
print("CANDIDATE         :", TOP1)
print("pw.x              : NO NEW CALCULATION")
print("CIF MODIFICATION  : NO")
print()
print("STATUS            :", result["status"])
print("OUTPUT            :", result["output_file"] or "NOT FOUND")
print("COMPLETED         :", result["completed"])
print("CONVERGED         :", result["converged"])
print(
    "TOTAL ENERGY      :",
    result["total_energy_ry"],
    "Ry" if result["total_energy_ry"] is not None else ""
)
print("SCF ITERATIONS    :", result["scf_iterations"])
print("ERRORS            :", len(result["errors"]))
print()
print("CSV     :", csv_path)
print("JSON    :", json_path)
print("MANIFEST:", manifest_path)
print()
print("PHASE 18 STATUS   :", result["status"])
print("=" * 78)
