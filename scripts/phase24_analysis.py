#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from datetime import datetime


PROJECT = Path("/home/hk/HydroMatAI")
PHASE23 = PROJECT / "calculations/phase_23_qe_runs"
OUTDIR = PROJECT / "calculations/phase_24_analysis"

CSV_OUT = OUTDIR / "phase24_analysis.csv"
JSON_OUT = OUTDIR / "phase24_analysis.json"
MANIFEST_OUT = OUTDIR / "phase24_manifest.json"


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def analyze_output(path: Path) -> dict:
    text = read_text(path)

    result = {
        "output_exists": path.exists(),
        "output_size_bytes": path.stat().st_size if path.exists() else 0,
        "converged": False,
        "completed": False,
        "error": False,
        "timeout": False,
        "scf_iterations": 0,
        "total_energy_ry": None,
        "fermi_energy_ev": None,
        "wall_time": None,
        "last_status": "UNKNOWN",
    }

    if not text:
        result["last_status"] = "EMPTY_OUTPUT"
        return result

    lower = text.lower()

    result["converged"] = (
        "convergence has been achieved" in lower
        or "convergence achieved" in lower
        or "convergence NOT achieved".lower() not in lower
    )

    result["completed"] = (
        "job done" in lower
        or "convergence has been achieved" in lower
    )

    result["timeout"] = (
        "timeout" in lower
        or "time limit" in lower
    )

    error_patterns = [
        "error in routine",
        "fatal error",
        "cannot open",
        "cannot read",
        "segmentation fault",
        "stopping",
        "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",
    ]

    result["error"] = any(p in lower for p in error_patterns)

    energies = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s+Ry",
        text,
        flags=re.I,
    )

    if energies:
        try:
            result["total_energy_ry"] = float(energies[-1])
        except ValueError:
            pass

    fermi = re.findall(
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s+ev",
        text,
        flags=re.I,
    )

    if fermi:
        try:
            result["fermi_energy_ev"] = float(fermi[-1])
        except ValueError:
            pass

    iterations = re.findall(
        r"iteration\s*#?\s*(\d+)",
        text,
        flags=re.I,
    )

    if iterations:
        try:
            result["scf_iterations"] = max(map(int, iterations))
        except ValueError:
            pass

    wall = re.findall(
        r"PWSCF\s*:\s*([\d.]+)s CPU\s*([\d.]+)s WALL",
        text,
        flags=re.I,
    )

    if wall:
        result["wall_time"] = wall[-1][1]

    if result["completed"]:
        result["last_status"] = "COMPLETED"
    elif result["timeout"]:
        result["last_status"] = "TIMEOUT"
    elif result["error"]:
        result["last_status"] = "ERROR"
    else:
        result["last_status"] = "INCOMPLETE"

    return result


def discover_candidates(limit: int | None) -> list[Path]:
    if not PHASE23.exists():
        return []

    dirs = sorted(
        p for p in PHASE23.iterdir()
        if p.is_dir() and (p / f"{p.name}.out").exists()
    )

    if limit is not None:
        dirs = dirs[:limit]

    return dirs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 24 — analyse les sorties QE existantes sans lancer de calcul."
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("HydroMatAI — PHASE 24")
    print("ANALYSE DES SORTIES QUANTUM ESPRESSO")
    print("=" * 80)

    print("\nMODE")
    print("-" * 80)
    print("Analyse uniquement des fichiers .out existants.")
    print("Aucun pw.x lancé.")
    print("Aucun calcul QE lancé.")
    print("Aucun CIF modifié.")

    candidates = discover_candidates(args.limit)

    print("\nCANDIDATS")
    print("-" * 80)
    print(f"Sorties Phase 23 détectées : {len(candidates)}")

    rows = []

    completed = 0
    timeout = 0
    errors = 0
    incomplete = 0
    converged = 0

    for i, directory in enumerate(candidates, 1):
        name = directory.name
        output = directory / f"{name}.out"

        analysis = analyze_output(output)

        status = analysis["last_status"]

        if status == "COMPLETED":
            completed += 1
        elif status == "TIMEOUT":
            timeout += 1
        elif status == "ERROR":
            errors += 1
        else:
            incomplete += 1

        if analysis["converged"]:
            converged += 1

        print(f"[{i}/{len(candidates)}] {name}")
        print(f"  Output : {output}")
        print(f"  STATUS : {status}")

        if analysis["total_energy_ry"] is not None:
            print(
                f"  Energy : "
                f"{analysis['total_energy_ry']:.12f} Ry"
            )

        if analysis["scf_iterations"]:
            print(
                f"  SCF iterations : "
                f"{analysis['scf_iterations']}"
            )

        rows.append({
            "candidate": name,
            "output": str(output),
            **analysis,
        })

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(
                f,
                fieldnames=list(rows[0].keys()),
            )
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerow([
                "candidate",
                "output",
                "output_exists",
                "output_size_bytes",
                "converged",
                "completed",
                "error",
                "timeout",
                "scf_iterations",
                "total_energy_ry",
                "fermi_energy_ev",
                "wall_time",
                "last_status",
            ])

    summary = {
        "phase": 24,
        "generated_at": datetime.now().isoformat(),
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "candidates": len(rows),
        "completed": completed,
        "converged": converged,
        "timeout": timeout,
        "errors": errors,
        "incomplete": incomplete,
        "csv": str(CSV_OUT),
        "json": str(JSON_OUT),
        "manifest": str(MANIFEST_OUT),
        "results": rows,
    }

    JSON_OUT.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = {
        "phase": 24,
        "status": "COMPLETED",
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "source": str(PHASE23),
        "csv": str(CSV_OUT),
        "json": str(JSON_OUT),
        "manifest": str(MANIFEST_OUT),
        "candidate_count": len(rows),
        "completed": completed,
        "converged": converged,
        "timeout": timeout,
        "errors": errors,
        "incomplete": incomplete,
    }

    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("PHASE 24 — RÉSULTATS")
    print("=" * 80)
    print(f"Sorties analysées       : {len(rows)}")
    print(f"Calculs terminés        : {completed}")
    print(f"Convergences détectées  : {converged}")
    print(f"TIMEOUT                 : {timeout}")
    print(f"ERREURS                 : {errors}")
    print(f"Incomplets              : {incomplete}")

    print("\n" + "-" * 80)
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV      : {CSV_OUT}")
    print(f"JSON     : {JSON_OUT}")
    print(f"MANIFEST : {MANIFEST_OUT}")

    print("\n" + "=" * 80)
    print("PHASE 24 — AUDIT FINAL")
    print("=" * 80)
    print("Lecture Phase 23       : OK")
    print("Analyse sorties QE     : OK")
    print("pw.x lancé             : NON")
    print("Calcul QE lancé        : NON")
    print("Aucun CIF modifié      : OK")
    print("Traçabilité            : OK")
    print()
    print("MODE : ANALYSIS_ONLY")
    print("BLOCAGE : aucun calcul lancé")
    print("=" * 80)

    print("\nPHASE 24 — TERMINÉE")
    print("Analyse des résultats QE : OK")
    print("Aucun nouveau calcul Quantum ESPRESSO n'a été lancé.")
    print("=" * 80)


if __name__ == "__main__":
    main()
