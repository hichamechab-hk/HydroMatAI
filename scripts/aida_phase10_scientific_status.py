#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = "TiFeH2"

HIST = ROOT / "calculations/top5_dft" / SUBJECT
NEW = ROOT / "calculations/new_campaign" / SUBJECT


# ============================================================================
# CONFIGURATION
# ============================================================================

# Phase 10 is an audit/classification phase.
# It does NOT run Quantum ESPRESSO and does NOT modify scientific data.

ENERGY_TOL_RY = 1.0e-4
FERMI_TOL_EV = 0.05

# These are deliberately conservative.
# They are NOT universal DFT validation criteria.
# They are only used to classify numerical stability inside this audit.
#
# Example:
#   cutoff / k-point / smearing series
#   -> compare energies against the reference within the series.
#
# AIDA will never transform this automatically into "scientifically validated".

STATUS_ORDER = [
    "QE_CONVERGED",
    "QE_COMPLETED",
    "QE_INSUFFICIENT_EVIDENCE",
    "QE_NOT_CONVERGED",
    "QE_FAILED",
]


# ============================================================================
# UTILITIES
# ============================================================================

def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def read_text(path: Path) -> str:
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


def qe_outputs():
    return [
        (generation, path)
        for generation, path in all_files()
        if path.suffix.lower() == ".out"
    ]


def qe_inputs():
    return [
        (generation, path)
        for generation, path in all_files()
        if path.suffix.lower() == ".in"
    ]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


# ============================================================================
# PARSING
# ============================================================================

def extract_energy(text: str):
    values = re.findall(
        r"!\s+total\s+energy\s+=\s+([-+0-9.eE]+)\s+Ry",
        text,
        re.I,
    )

    if not values:
        return None

    try:
        return float(values[-1])
    except ValueError:
        return None


def extract_fermi(text: str):
    patterns = [
        r"the\s+Fermi\s+energy\s+is\s+([-+0-9.eE]+)\s+ev",
        r"EFermi\s*=\s*([-+0-9.eE]+)",
        r"Fermi\s+energy\s*=\s*([-+0-9.eE]+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.I)

        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass

    return None


def extract_iterations(text: str):
    values = re.findall(
        r"iteration\s*#?\s*(\d+)",
        text,
        re.I,
    )

    if not values:
        return None

    try:
        return max(int(value) for value in values)
    except ValueError:
        return None


def extract_input_parameter(text: str, name: str):
    """
    Generic extraction for QE input parameters.

    Handles examples such as:
        ecutwfc = 60
        ecutrho = 240
        degauss = 0.01
        nspin = 2
    """

    pattern = rf"\b{re.escape(name)}\s*=\s*['\"]?([^,\s/]+)"

    match = re.search(pattern, text, re.I)

    if not match:
        return None

    return match.group(1).strip("'\"")


def extract_kpoints(text: str):
    patterns = [
        r"K_POINTS\s+automatic\s*\n\s*(\d+)\s+(\d+)\s+(\d+)",
        r"K_POINTS\s*\{?\s*automatic\s*\}?\s*\n\s*(\d+)\s+(\d+)\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)

        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )

    return None


# ============================================================================
# CALCULATION CLASSIFICATION
# ============================================================================

def classify_calculation(path: Path) -> str:
    name = path.name.lower()
    full = str(path).lower()

    # Specific calculation classes first.
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

    if "cutoff" in full:
        return "CUTOFF"

    if "kpoint" in full or "kpoints" in full:
        return "KPOINTS"

    if "smearing" in full or "degauss" in full:
        return "SMEARING"

    return "OTHER"


# ============================================================================
# STATUS ANALYSIS
# ============================================================================

def has_job_done(text: str) -> bool:
    return bool(re.search(r"\bJOB\s+DONE\.", text, re.I))


def has_explicit_failure(text: str) -> bool:
    failure_patterns = [
        r"convergence\s+NOT\s+achieved",
        r"maximum\s+number\s+of\s+iterations",
        r"error\s+in\s+routine",
        r"cannot\s+open",
        r"fatal\s+error",
        r"error\s+while",
        r"%%%%%%%%%%%%",
    ]

    return any(
        re.search(pattern, text, re.I)
        for pattern in failure_patterns
    )


def has_scf_convergence(text: str) -> bool:
    patterns = [
        r"convergence\s+has\s+been\s+achieved",
        r"convergence\s+has\s+been\s+achieved\s*:",
        r"convergence\s+has\s+been\s+achieved\s+after",
    ]

    return any(
        re.search(pattern, text, re.I)
        for pattern in patterns
    )


def has_relax_convergence(text: str) -> bool:
    patterns = [
        r"End\s+of\s+self-consistent\s+calculation",
        r"convergence\s+has\s+been\s+achieved",
        r"Final\s+energy",
        r"Begin\s+final\s+coordinates",
    ]

    return any(
        re.search(pattern, text, re.I)
        for pattern in patterns
    )


def determine_qe_status(calc_type: str, text: str, energy, iterations):
    """
    Conservative status classification.

    IMPORTANT:
        COMPLETED != CONVERGED
        INSUFFICIENT_EVIDENCE != NOT_CONVERGED
    """

    if has_explicit_failure(text):
        return "QE_FAILED"

    if calc_type in {"SCF", "CUTOFF", "KPOINTS", "SMEARING"}:
        if has_scf_convergence(text):
            return "QE_CONVERGED"

        if has_job_done(text) and energy is not None:
            return "QE_COMPLETED"

        return "QE_INSUFFICIENT_EVIDENCE"

    if calc_type == "RELAX":
        if has_relax_convergence(text):
            return "QE_CONVERGED"

        if has_job_done(text) and energy is not None:
            return "QE_COMPLETED"

        return "QE_INSUFFICIENT_EVIDENCE"

    if calc_type in {"NSCF", "DOS", "BANDS"}:
        # These calculations are not classified by the same SCF criterion.
        # Successful completion + numerical output is sufficient for
        # QE_COMPLETED, but not automatically for scientific validation.

        if has_job_done(text):
            return "QE_COMPLETED"

        if energy is not None:
            return "QE_COMPLETED"

        return "QE_INSUFFICIENT_EVIDENCE"

    if has_job_done(text):
        return "QE_COMPLETED"

    if energy is not None:
        return "QE_COMPLETED"

    return "QE_INSUFFICIENT_EVIDENCE"


# ============================================================================
# RECORD CONSTRUCTION
# ============================================================================

def analyze_output(generation: str, path: Path):
    text = read_text(path)

    calc_type = classify_calculation(path)

    energy = extract_energy(text)
    fermi = extract_fermi(text)
    iterations = extract_iterations(text)

    status = determine_qe_status(
        calc_type,
        text,
        energy,
        iterations,
    )

    return {
        "generation": generation,
        "file": relative(path),
        "path": path,
        "type": calc_type,
        "status": status,
        "energy_Ry": energy,
        "fermi_eV": fermi,
        "iterations": iterations,
        "job_done": has_job_done(text),
        "explicit_failure": has_explicit_failure(text),
        "scf_convergence": has_scf_convergence(text),
        "relax_convergence": has_relax_convergence(text),
    }


# ============================================================================
# PRINTING
# ============================================================================

def print_record(record):
    print()
    print(f"[{record['generation']}]")
    print(f"FILE         : {record['file']}")
    print(f"TYPE         : {record['type']}")
    print(f"STATUS       : {record['status']}")
    print(f"ENERGY (Ry)  : {record['energy_Ry']}")
    print(f"FERMI (eV)   : {record['fermi_eV']}")
    print(f"ITERATIONS   : {record['iterations']}")
    print(f"JOB DONE     : {record['job_done']}")
    print(f"SCF CONV     : {record['scf_convergence']}")
    print(f"RELAX CONV   : {record['relax_convergence']}")


# ============================================================================
# SERIES EXTRACTION
# ============================================================================

def series_records(records, generation, calc_type):
    return [
        record
        for record in records
        if record["generation"] == generation
        and record["type"] == calc_type
        and record["energy_Ry"] is not None
    ]


def energy_range(records):
    energies = [
        record["energy_Ry"]
        for record in records
        if record["energy_Ry"] is not None
    ]

    if not energies:
        return None

    return min(energies), max(energies)


def print_series_analysis(records, generation, calc_type):
    subset = series_records(records, generation, calc_type)

    if not subset:
        print(f"[{generation}] {calc_type}: aucune énergie exploitable.")
        return

    print()
    print(f"[{generation}] {calc_type}")

    for record in subset:
        print(
            f"  {record['file']} "
            f"-> E={record['energy_Ry']:.8f} Ry "
            f"status={record['status']}"
        )

    reference = subset[0]["energy_Ry"]

    print()
    print(f"  Référence de comparaison : {reference:.8f} Ry")

    for record in subset:
        delta = record["energy_Ry"] - reference

        print(
            f"  ΔE {Path(record['file']).name:35} "
            f"= {delta:+.8f} Ry"
        )

    bounds = energy_range(subset)

    if bounds:
        minimum, maximum = bounds
        spread = maximum - minimum

        print(f"  Spread énergétique      : {spread:.8f} Ry")

        if spread <= ENERGY_TOL_RY:
            print(
                "  NUMERICAL STABILITY     : "
                "WITHIN_AIDA_TOLERANCE"
            )
        else:
            print(
                "  NUMERICAL STABILITY     : "
                "VARIATION_ABOVE_AIDA_TOLERANCE"
            )

    print(
        "  [RULE] Cette comparaison mesure uniquement "
        "la stabilité numérique de la série."
    )


# ============================================================================
# INPUT / OUTPUT MATCHING
# ============================================================================

def matching_inputs_outputs():
    inputs = {
        path.with_suffix(".out")
        for _, path in qe_inputs()
    }

    outputs = {
        path
        for _, path in qe_outputs()
    }

    return (
        len(inputs & outputs),
        len(inputs - outputs),
        inputs - outputs,
    )


# ============================================================================
# SCIENTIFIC STATUS
# ============================================================================

def scientific_status(record):
    """
    Converts QE evidence into a deliberately conservative AIDA status.

    This is NOT a scientific validation engine.
    """

    calc_type = record["type"]
    status = record["status"]

    if status == "QE_FAILED":
        return "SCIENTIFICALLY_NOT_ESTABLISHED"

    if status == "QE_INSUFFICIENT_EVIDENCE":
        return "SCIENTIFICALLY_NOT_ESTABLISHED"

    if calc_type in {"SCF", "RELAX", "CUTOFF", "KPOINTS", "SMEARING"}:
        if status == "QE_CONVERGED":
            return "SCIENTIFICALLY_SUPPORTED"

    if calc_type in {"NSCF", "DOS", "BANDS"}:
        if status == "QE_COMPLETED":
            return "SCIENTIFICALLY_SUPPORTED"

    if status == "QE_COMPLETED":
        return "SCIENTIFICALLY_SUPPORTED"

    return "SCIENTIFICALLY_NOT_ESTABLISHED"


# ============================================================================
# MAIN
# ============================================================================

def main():
    banner("AIDA — PHASE 10 : EVIDENCE → SCIENTIFIC STATUS")

    print(f"ROOT    : {ROOT}")
    print(f"SUBJECT : {SUBJECT}")
    print()
    print("MODE : READ-ONLY")
    print("QE   : aucun calcul exécuté")
    print("DATA : aucun fichier scientifique modifié")
    print()
    print("PRINCIPES :")
    print("  LITERATURE != SCREENING != QE RESULT")
    print("  QE CONVERGED != SCIENTIFICALLY VALIDATED")
    print("  INSUFFICIENT_EVIDENCE != NOT_CONVERGED")
    print("  HISTORICAL != NEW_CAMPAIGN")

    # ----------------------------------------------------------------------
    # 10.1
    # ----------------------------------------------------------------------

    banner("PHASE 10.1 — INVENTAIRE DES SORTIES")

    outputs = qe_outputs()

    print(f"OUT détectés : {len(outputs)}")

    if not outputs:
        print("[ERROR] Aucun fichier OUT.")
        return 1

    # ----------------------------------------------------------------------
    # 10.2
    # ----------------------------------------------------------------------

    banner("PHASE 10.2 — CLASSIFICATION TYPE / STATUT")

    records = [
        analyze_output(generation, path)
        for generation, path in outputs
    ]

    for record in records:
        print_record(record)

    # ----------------------------------------------------------------------
    # 10.3
    # ----------------------------------------------------------------------

    banner("PHASE 10.3 — DISTRIBUTION DES STATUTS QE")

    for generation in ("HISTORICAL", "NEW_CAMPAIGN"):
        print()
        print(generation)

        counter = Counter(
            record["status"]
            for record in records
            if record["generation"] == generation
        )

        for status in STATUS_ORDER:
            if counter.get(status):
                print(f"  {status:32} : {counter[status]}")

    # ----------------------------------------------------------------------
    # 10.4
    # ----------------------------------------------------------------------

    banner("PHASE 10.4 — DISTRIBUTION PAR TYPE")

    grouped = defaultdict(Counter)

    for record in records:
        grouped[
            (record["generation"], record["type"])
        ][record["status"]] += 1

    for key in sorted(grouped):
        generation, calc_type = key
        print()
        print(f"[{generation}] {calc_type}")

        for status in STATUS_ORDER:
            count = grouped[key].get(status, 0)
            if count:
                print(f"  {status:32} : {count}")

    # ----------------------------------------------------------------------
    # 10.5
    # ----------------------------------------------------------------------

    banner("PHASE 10.5 — SCF / RELAX EVIDENCE")

    for record in records:
        if record["type"] not in {"SCF", "RELAX"}:
            continue

        print()
        print(f"[{record['generation']}] {record['file']}")
        print(f"  TYPE       : {record['type']}")
        print(f"  STATUS     : {record['status']}")
        print(f"  ENERGY     : {record['energy_Ry']}")
        print(f"  ITERATIONS : {record['iterations']}")
        print(f"  SCF CONV   : {record['scf_convergence']}")
        print(f"  RELAX CONV : {record['relax_convergence']}")

    # ----------------------------------------------------------------------
    # 10.6
    # ----------------------------------------------------------------------

    banner("PHASE 10.6 — CONVERGENCE CUTOFF")

    print_series_analysis(
        records,
        "NEW_CAMPAIGN",
        "CUTOFF",
    )

    # ----------------------------------------------------------------------
    # 10.7
    # ----------------------------------------------------------------------

    banner("PHASE 10.7 — CONVERGENCE K-POINTS")

    print_series_analysis(
        records,
        "NEW_CAMPAIGN",
        "KPOINTS",
    )

    # ----------------------------------------------------------------------
    # 10.8
    # ----------------------------------------------------------------------

    banner("PHASE 10.8 — STABILITÉ SMEARING")

    print_series_analysis(
        records,
        "NEW_CAMPAIGN",
        "SMEARING",
    )

    # ----------------------------------------------------------------------
    # 10.9
    # ----------------------------------------------------------------------

    banner("PHASE 10.9 — DOS / BANDS / NSCF")

    for calc_type in ("DOS", "BANDS", "NSCF"):
        print()
        print(f"TYPE : {calc_type}")

        subset = [
            record
            for record in records
            if record["type"] == calc_type
        ]

        if not subset:
            print("  Aucun résultat.")
            continue

        for record in subset:
            print(
                f"  [{record['generation']}] "
                f"{record['file']} "
                f"-> {record['status']}"
            )

    print()
    print("[RULE]")
    print("DOS/BANDS/NSCF COMPLETED = résultat disponible.")
    print("DOS/BANDS/NSCF COMPLETED != validation électronique automatique.")

    # ----------------------------------------------------------------------
    # 10.10
    # ----------------------------------------------------------------------

    banner("PHASE 10.10 — INPUT / OUTPUT")

    matched, missing, missing_paths = matching_inputs_outputs()

    print(f"Inputs avec OUT correspondant : {matched}")
    print(f"Inputs sans OUT correspondant : {missing}")

    if missing_paths:
        print()
        print("Inputs sans OUT :")

        for path in sorted(missing_paths):
            print(f"  {relative(path.with_suffix('.in'))}")

    # ----------------------------------------------------------------------
    # 10.11
    # ----------------------------------------------------------------------

    banner("PHASE 10.11 — STATUT SCIENTIFIQUE AIDA")

    scientific_counter = Counter()

    for record in records:
        status = scientific_status(record)

        scientific_counter[status] += 1

        print()
        print(f"[{record['generation']}]")
        print(f"FILE              : {record['file']}")
        print(f"TYPE              : {record['type']}")
        print(f"QE STATUS         : {record['status']}")
        print(f"AIDA STATUS       : {status}")

    print()
    print("Résumé :")

    for status, count in sorted(scientific_counter.items()):
        print(f"{status:40} : {count}")

    # ----------------------------------------------------------------------
    # 10.12
    # ----------------------------------------------------------------------

    banner("PHASE 10.12 — FOCUS SMEARING 0.001 Ry")

    target = [
        record
        for record in records
        if "degauss_0.001Ry" in record["file"]
    ]

    if not target:
        print("[INFO] Aucun résultat 0.001 Ry trouvé.")
    else:
        for record in target:
            print(f"FILE       : {record['file']}")
            print(f"STATUS     : {record['status']}")
            print(f"ENERGY     : {record['energy_Ry']}")
            print(f"FERMI      : {record['fermi_eV']}")
            print(f"ITERATIONS : {record['iterations']}")
            print(f"JOB DONE   : {record['job_done']}")
            print(f"SCF CONV   : {record['scf_convergence']}")

            print()
            if record["status"] == "QE_INSUFFICIENT_EVIDENCE":
                print(
                    "[WARNING] 0.001 Ry reste "
                    "INSUFFICIENT_EVIDENCE."
                )
                print(
                    "[RULE] Cela ne signifie PAS "
                    "NOT_CONVERGED."
                )

    # ----------------------------------------------------------------------
    # 10.13
    # ----------------------------------------------------------------------

    banner("PHASE 10.13 — SÉPARATION DES GÉNÉRATIONS")

    historical_count = sum(
        1 for record in records
        if record["generation"] == "HISTORICAL"
    )

    new_count = sum(
        1 for record in records
        if record["generation"] == "NEW_CAMPAIGN"
    )

    print(f"HISTORICAL outputs   : {historical_count}")
    print(f"NEW_CAMPAIGN outputs : {new_count}")

    print()
    print("[OK] Les deux générations restent séparées.")
    print("[OK] Aucun résultat historique n'est remplacé.")
    print("[OK] Aucun résultat de nouvelle campagne n'est injecté dans le score final.")

    # ----------------------------------------------------------------------
    # 10.14
    # ----------------------------------------------------------------------

    banner("PHASE 10.14 — RÈGLES DE NON-SURINTERPRÉTATION")

    print("[RULE 1] QE_CONVERGED != SCIENTIFICALLY_VALIDATED")
    print("[RULE 2] ENERGY_AVAILABLE != MATERIAL_VALIDATION")
    print("[RULE 3] DOS_AVAILABLE != BAND_GAP_VALIDATION")
    print("[RULE 4] BANDS_AVAILABLE != ELECTRONIC_STRUCTURE_VALIDATION")
    print("[RULE 5] CUTOFF_STABLE != UNIVERSAL_CUTOFF_CONVERGENCE")
    print("[RULE 6] KPOINT_STABLE != UNIVERSAL_KPOINT_CONVERGENCE")
    print("[RULE 7] SMEARING_STABLE != UNIVERSAL_SMEARING_CONVERGENCE")
    print("[RULE 8] LITERATURE_H2 != QE_H2_RESULT")
    print("[RULE 9] FINAL_SCREENING_SCORE != DFT_VALIDATION")
    print("[RULE 10] HISTORICAL != NEW_CAMPAIGN")

    # ----------------------------------------------------------------------
    # 10.15
    # ----------------------------------------------------------------------

    banner("PHASE 10.15 — RAPPORT FINAL")

    total = len(records)

    qe_converged = sum(
        1 for record in records
        if record["status"] == "QE_CONVERGED"
    )

    qe_completed = sum(
        1 for record in records
        if record["status"] == "QE_COMPLETED"
    )

    qe_insufficient = sum(
        1 for record in records
        if record["status"] == "QE_INSUFFICIENT_EVIDENCE"
    )

    qe_failed = sum(
        1 for record in records
        if record["status"] == "QE_FAILED"
    )

    scientifically_supported = scientific_counter.get(
        "SCIENTIFICALLY_SUPPORTED",
        0,
    )

    scientifically_not_established = scientific_counter.get(
        "SCIENTIFICALLY_NOT_ESTABLISHED",
        0,
    )

    print(f"Subject                         : {SUBJECT}")
    print(f"OUT analysés                    : {total}")
    print(f"QE_CONVERGED                    : {qe_converged}")
    print(f"QE_COMPLETED                    : {qe_completed}")
    print(f"QE_INSUFFICIENT_EVIDENCE        : {qe_insufficient}")
    print(f"QE_FAILED                       : {qe_failed}")
    print()
    print(
        f"SCIENTIFICALLY_SUPPORTED        : "
        f"{scientifically_supported}"
    )
    print(
        f"SCIENTIFICALLY_NOT_ESTABLISHED  : "
        f"{scientifically_not_established}"
    )
    print()
    print(f"Inputs sans OUT                 : {missing}")

    print()
    print("INTERPRÉTATION AIDA")
    print("--------------------")

    if qe_converged:
        print(
            "[FACT] Des sorties QE contiennent "
            "une preuve explicite de convergence."
        )

    if qe_insufficient:
        print(
            "[WARNING] Certaines sorties ne permettent "
            "pas une classification QE complète."
        )

    if qe_failed:
        print(
            "[WARNING] Au moins une sortie contient "
            "un motif d'échec explicite."
        )

    if missing:
        print(
            "[WARNING] Plusieurs inputs n'ont pas "
            "de sortie correspondante."
        )

    print()
    print(
        "[IMPORTANT] Aucun statut AIDA de cette phase "
        "ne constitue à lui seul une validation scientifique finale."
    )

    print()
    print("=" * 78)
    print("AIDA PHASE 10 TERMINÉE")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
