#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = "TiFeH2"

HIST = ROOT / "calculations/top5_dft" / SUBJECT
NEW = ROOT / "calculations/new_campaign" / SUBJECT


def banner(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def read_text(path):
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def all_files():
    result = []

    for root, generation in (
        (HIST, "HISTORICAL"),
        (NEW, "NEW_CAMPAIGN"),
    ):
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if path.is_file():
                result.append((generation, path))

    return result


def qe_out_files():
    return [
        (generation, path)
        for generation, path in all_files()
        if path.suffix.lower() == ".out"
    ]


def extract(text, pattern):
    match = re.search(pattern, text, re.I | re.M)
    return match.group(1) if match else None


def analyze_status(text):
    if "JOB DONE." in text:
        return "COMPLETED"

    failure_patterns = [
        r"convergence\s+NOT\s+achieved",
        r"maximum\s+number\s+of\s+iterations",
        r"error\s+in\s+routine",
        r"%%%%%%%%%%%%",
        r"cannot\s+open",
        r"stopping",
    ]

    for pattern in failure_patterns:
        if re.search(pattern, text, re.I):
            return "INCOMPLETE_OR_FAILED"

    return "INSUFFICIENT_EVIDENCE"


def analyze_convergence(text):
    if re.search(r"convergence\s+has\s+been\s+achieved", text, re.I):
        return "CONVERGED"

    if re.search(r"convergence\s+NOT\s+achieved", text, re.I):
        return "NOT_CONVERGED"

    if re.search(r"converged", text, re.I):
        return "CONVERGED"

    return "INSUFFICIENT_EVIDENCE"


def extract_energy(text):
    values = re.findall(
        r"!\s+total energy\s+=\s+([-+0-9.eE]+)\s+Ry",
        text,
        re.I,
    )

    if not values:
        return None

    try:
        return float(values[-1])
    except ValueError:
        return None


def extract_fermi(text):
    patterns = [
        r"the\s+Fermi\s+energy\s+is\s+([-+0-9.eE]+)\s+ev",
        r"EFermi\s*=\s*([-+0-9.eE]+)",
        r"the\s+Fermi\s+energy\s+is\s+([-+0-9.eE]+)",
    ]

    for pattern in patterns:
        value = extract(text, pattern)

        if value is not None:
            try:
                return float(value)
            except ValueError:
                pass

    return None


def extract_iterations(text):
    patterns = [
        r"iteration\s*#?\s*(\d+)",
        r"iteration\s+(\d+)",
    ]

    values = []

    for pattern in patterns:
        values.extend(re.findall(pattern, text, re.I))

    if not values:
        return None

    try:
        return max(int(x) for x in values)
    except ValueError:
        return None


def classify_calculation(path):
    name = path.name.lower()
    parent = str(path.parent).lower()

    if "bands" in name:
        return "BANDS"

    if "dos" in name:
        return "DOS"

    if "nscf" in name:
        return "NSCF"

    if "relax" in name:
        return "RELAX"

    if "scf" in name:
        return "SCF"

    if "cutoff" in parent or "cutoff" in name:
        return "CUTOFF"

    if "kpoint" in parent or "kpoint" in name:
        return "KPOINTS"

    if "smearing" in parent or "degauss" in name:
        return "SMEARING"

    return "OTHER"


def analyze_output(generation, path):
    text = read_text(path)

    return {
        "generation": generation,
        "file": str(path.relative_to(ROOT)),
        "type": classify_calculation(path),
        "status": analyze_status(text),
        "convergence": analyze_convergence(text),
        "energy_Ry": extract_energy(text),
        "fermi_eV": extract_fermi(text),
        "iterations": extract_iterations(text),
        "has_scf_iterations": bool(
            re.search(r"iteration", text, re.I)
        ),
        "has_dos_data": bool(
            re.search(r"\bdosup\b|\bdosdw\b|Int\s+dos", text, re.I)
        ),
        "has_band_data": bool(
            re.search(r"k\s*=\s*.*bands|bands", text, re.I)
        ),
    }


def print_record(record):
    print()
    print(f"[{record['generation']}]")
    print(f"FILE         : {record['file']}")
    print(f"TYPE         : {record['type']}")
    print(f"STATUS       : {record['status']}")
    print(f"CONVERGENCE  : {record['convergence']}")
    print(f"ENERGY (Ry)  : {record['energy_Ry']}")
    print(f"FERMI (eV)   : {record['fermi_eV']}")
    print(f"ITERATIONS   : {record['iterations']}")

    if record["has_dos_data"]:
        print("DOS DATA     : DETECTED")

    if record["has_band_data"]:
        print("BAND DATA    : DETECTED")


def main():
    banner("AIDA — PHASE 9 : SCIENTIFIC EVIDENCE ENGINE")
    print(f"ROOT    : {ROOT}")
    print(f"SUBJECT : {SUBJECT}")
    print()
    print("MODE : READ-ONLY")
    print("QE   : aucun calcul exécuté")
    print("DATA : aucun fichier modifié")
    print("RULE : présence d'un résultat ≠ validation scientifique")

    # ------------------------------------------------------------------
    # 9.1
    # ------------------------------------------------------------------
    banner("PHASE 9.1 — LECTURE SCIENTIFIQUE DES .OUT")

    outputs = qe_out_files()

    print(f"Fichiers OUT détectés : {len(outputs)}")

    if not outputs:
        print("[WARNING] Aucun fichier .out trouvé.")
        return 1

    records = [
        analyze_output(generation, path)
        for generation, path in outputs
    ]

    # ------------------------------------------------------------------
    # 9.2
    # ------------------------------------------------------------------
    banner("PHASE 9.2 — STATUT RÉEL DES CALCULS")

    statuses = Counter(record["status"] for record in records)

    for status, count in sorted(statuses.items()):
        print(f"{status:24} : {count}")

    # ------------------------------------------------------------------
    # 9.3
    # ------------------------------------------------------------------
    banner("PHASE 9.3 — ÉNERGIE / FERMI / ITERATIONS")

    numerical_energy = 0
    fermi_values = 0
    iteration_values = 0

    for record in records:
        if record["energy_Ry"] is not None:
            numerical_energy += 1

        if record["fermi_eV"] is not None:
            fermi_values += 1

        if record["iterations"] is not None:
            iteration_values += 1

        print_record(record)

    print()
    print(f"Energies extraites    : {numerical_energy}")
    print(f"Fermi extraits        : {fermi_values}")
    print(f"Iterations extraites  : {iteration_values}")

    # ------------------------------------------------------------------
    # 9.4
    # ------------------------------------------------------------------
    banner("PHASE 9.4 — CONVERGENCE / NON-CONVERGENCE")

    convergence = Counter(
        record["convergence"]
        for record in records
    )

    for status, count in sorted(convergence.items()):
        print(f"{status:24} : {count}")

    # ------------------------------------------------------------------
    # 9.5
    # ------------------------------------------------------------------
    banner("PHASE 9.5 — ANALYSE DOS")

    dos_records = [
        record for record in records
        if record["type"] == "DOS"
        or record["has_dos_data"]
    ]

    print(f"Résultats DOS identifiés : {len(dos_records)}")

    for record in dos_records:
        print(
            f"[{record['generation']}] "
            f"{record['file']} -> "
            f"status={record['status']} "
            f"convergence={record['convergence']}"
        )

    # ------------------------------------------------------------------
    # 9.6
    # ------------------------------------------------------------------
    banner("PHASE 9.6 — ANALYSE BANDES")

    band_records = [
        record for record in records
        if record["type"] == "BANDS"
        or record["has_band_data"]
    ]

    print(f"Résultats BANDS identifiés : {len(band_records)}")

    for record in band_records:
        print(
            f"[{record['generation']}] "
            f"{record['file']} -> "
            f"status={record['status']} "
            f"convergence={record['convergence']}"
        )

    # ------------------------------------------------------------------
    # 9.7
    # ------------------------------------------------------------------
    banner("PHASE 9.7 — COHÉRENCE INPUT / OUTPUT")

    input_paths = {
        path.with_suffix(".out")
        for _, path in all_files()
        if path.suffix.lower() == ".in"
    }

    output_paths = {
        path
        for _, path in outputs
    }

    matched = len(input_paths & output_paths)
    missing = len(input_paths - output_paths)

    print(f"Inputs avec OUT correspondant : {matched}")
    print(f"Inputs sans OUT correspondant : {missing}")

    # ------------------------------------------------------------------
    # 9.8
    # ------------------------------------------------------------------
    banner("PHASE 9.8 — CLASSIFICATION DES PREUVES")

    evidence_counter = Counter()

    for record in records:
        if record["status"] == "COMPLETED":
            evidence_counter["COMPLETED"] += 1

        if record["convergence"] == "CONVERGED":
            evidence_counter["CONVERGED"] += 1

        if record["energy_Ry"] is not None:
            evidence_counter["ENERGY_AVAILABLE"] += 1

        if record["fermi_eV"] is not None:
            evidence_counter["FERMI_AVAILABLE"] += 1

        if record["convergence"] == "NOT_CONVERGED":
            evidence_counter["NOT_CONVERGED"] += 1

    for key, value in sorted(evidence_counter.items()):
        print(f"{key:24} : {value}")

    print()
    print("[RULE]")
    print("COMPLETED  != CONVERGED")
    print("CONVERGED  != SCIENTIFICALLY VALIDATED")
    print("ENERGY     != MATERIAL VALIDATION")
    print("DOS/BANDS  != AUTOMATIC ELECTRONIC VALIDATION")

    # ------------------------------------------------------------------
    # 9.9
    # ------------------------------------------------------------------
    banner("PHASE 9.9 — RAPPORT EVIDENCE ENGINE")

    print(f"Subject                 : {SUBJECT}")
    print(f"OUT analysés            : {len(records)}")
    print(f"Completed               : {statuses.get('COMPLETED', 0)}")
    print(f"Converged               : {convergence.get('CONVERGED', 0)}")
    print(f"Not converged           : {convergence.get('NOT_CONVERGED', 0)}")
    print(f"Energy available        : {numerical_energy}")
    print(f"Fermi available         : {fermi_values}")
    print(f"Inputs sans output      : {missing}")

    print()
    print("INTERPRÉTATION AIDA")
    print("--------------------")

    if convergence.get("CONVERGED", 0):
        print("[FACT] Certains calculs contiennent une indication de convergence.")

    if convergence.get("NOT_CONVERGED", 0):
        print("[WARNING] Au moins un calcul contient une indication de non-convergence.")

    if missing:
        print(
            "[WARNING] Certains inputs n'ont pas de fichier OUT correspondant."
        )

    print(
        "[INFO] AIDA ne transforme aucune de ces observations "
        "en validation scientifique automatique."
    )

    print()
    print("=" * 78)
    print("FIN AIDA PHASE 9")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
