#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/hk/HydroMatAI")

INPUT_JSON = (
    BASE_DIR
    / "calculations"
    / "phase_25_summary"
    / "phase25_summary.json"
)

OUTPUT_DIR = (
    BASE_DIR
    / "calculations"
    / "phase_26_analysis"
)

OUTPUT_CSV = OUTPUT_DIR / "phase26_analysis.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase26_analysis.json"
MANIFEST_JSON = OUTPUT_DIR / "phase26_manifest.json"


def load_data():
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Fichier introuvable : {INPUT_JSON}")

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze(data, limit):
    records = data.get("records", [])

    if limit > 0:
        records = records[:limit]

    completed = [
        r for r in records
        if r.get("status") == "COMPLETED"
    ]

    incomplete = [
        r for r in records
        if r.get("status") == "INCOMPLETE"
    ]

    errors = [
        r for r in records
        if r.get("status") == "ERROR"
    ]

    timeout = [
        r for r in records
        if r.get("status") == "TIMEOUT"
    ]

    energy_records = [
        r for r in completed
        if r.get("total_energy_ry") is not None
    ]

    lowest = None
    highest = None

    if energy_records:
        lowest = min(
            energy_records,
            key=lambda x: x["total_energy_ry"]
        )

        highest = max(
            energy_records,
            key=lambda x: x["total_energy_ry"]
        )

    stats = {
        "total_candidates": len(records),
        "completed": len(completed),
        "incomplete": len(incomplete),
        "errors": len(errors),
        "timeout": len(timeout),
        "energies_available": len(energy_records),
        "completion_rate_percent": (
            round(len(completed) / len(records) * 100, 2)
            if records else 0.0
        ),
        "lowest_energy_candidate": (
            lowest["candidate"] if lowest else None
        ),
        "lowest_energy_ry": (
            lowest["total_energy_ry"] if lowest else None
        ),
        "highest_energy_candidate": (
            highest["candidate"] if highest else None
        ),
        "highest_energy_ry": (
            highest["total_energy_ry"] if highest else None
        ),
    }

    return records, stats


def write_csv(records):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "candidate",
        "status",
        "completed",
        "converged",
        "scf_iterations",
        "total_energy_ry",
        "error",
        "timeout",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )
        writer.writeheader()

        for r in records:
            writer.writerow({
                field: r.get(field)
                for field in fields
            })


def write_json(records, stats):
    data = {
        "project": "HydroMatAI",
        "phase": 26,
        "phase_name": "ANALYSIS",
        "mode": "ANALYSIS_ONLY",
        "generated_at": datetime.now().isoformat(),
        "source": str(INPUT_JSON),
        "statistics": stats,
        "records": records,
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def write_manifest(stats):
    manifest = {
        "project": "HydroMatAI",
        "phase": 26,
        "phase_name": "ANALYSIS",
        "status": "COMPLETED",
        "mode": "ANALYSIS_ONLY",
        "source_phase": 25,
        "source_file": str(INPUT_JSON),
        "output_directory": str(OUTPUT_DIR),
        "pw_x_launched": False,
        "qe_calculation_launched": False,
        "cif_modified": False,
        "traceability": "OK",
        "statistics": stats,
        "files": {
            "csv": str(OUTPUT_CSV),
            "json": str(OUTPUT_JSON),
            "manifest": str(MANIFEST_JSON),
        },
        "generated_at": datetime.now().isoformat(),
    }

    with open(
        MANIFEST_JSON,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False
        )


def print_results(records, stats):
    print("=" * 80)
    print("HydroMatAI — PHASE 26")
    print("ANALYSE DES RÉSULTATS QE EXISTANTS")
    print("=" * 80)

    print()
    print("STATISTIQUES")
    print("-" * 80)

    print(f"Candidats analysés       : {stats['total_candidates']}")
    print(f"Calculs terminés         : {stats['completed']}")
    print(f"Incomplets               : {stats['incomplete']}")
    print(f"TIMEOUT                  : {stats['timeout']}")
    print(f"ERREURS                  : {stats['errors']}")
    print(f"Énergies disponibles    : {stats['energies_available']}")
    print(f"Taux de complétion      : {stats['completion_rate_percent']:.2f} %")

    if stats["lowest_energy_candidate"]:
        print()
        print("ÉNERGIES DISPONIBLES")
        print("-" * 80)
        print(
            f"Minimum détecté         : "
            f"{stats['lowest_energy_candidate']} | "
            f"{stats['lowest_energy_ry']:.12f} Ry"
        )

        print(
            f"Maximum détecté         : "
            f"{stats['highest_energy_candidate']} | "
            f"{stats['highest_energy_ry']:.12f} Ry"
        )

    print()
    print("CANDIDATS")
    print("-" * 80)

    for r in records:
        energy = (
            f"{r['total_energy_ry']:.12f} Ry"
            if r.get("total_energy_ry") is not None
            else "N/A"
        )

        print(
            f"{r['candidate']} | "
            f"{r['status']} | "
            f"SCF={r.get('scf_iterations', 'N/A')} | "
            f"E={energy}"
        )

    print()
    print("=" * 80)
    print("AUDIT PHASE 26")
    print("=" * 80)

    print("Lecture Phase 25       : OK")
    print("Analyse                : OK")
    print("pw.x lancé             : NON")
    print("Calcul QE lancé        : NON")
    print("CIF modifié            : NON")
    print("Traçabilité            : OK")
    print("Mode                   : ANALYSIS_ONLY")

    print()
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV      : {OUTPUT_CSV}")
    print(f"JSON     : {OUTPUT_JSON}")
    print(f"MANIFEST : {MANIFEST_JSON}")

    print()
    print("=" * 80)
    print("PHASE 26 — TERMINÉE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)

    args = parser.parse_args()

    data = load_data()

    records, stats = analyze(
        data,
        args.limit
    )

    if not records:
        raise RuntimeError(
            "Aucun résultat Phase 25."
        )

    write_csv(records)
    write_json(records, stats)
    write_manifest(stats)

    print_results(
        records,
        stats
    )


if __name__ == "__main__":
    main()
