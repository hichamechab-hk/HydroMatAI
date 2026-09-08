#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime


BASE_DIR = Path("/home/hk/HydroMatAI")

INPUT_DIR = BASE_DIR / "calculations" / "phase_24_analysis"
INPUT_JSON = INPUT_DIR / "phase24_analysis.json"

OUTPUT_DIR = BASE_DIR / "calculations" / "phase_25_summary"
OUTPUT_CSV = OUTPUT_DIR / "phase25_summary.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase25_summary.json"
MANIFEST_JSON = OUTPUT_DIR / "phase25_manifest.json"


def load_phase24():
    if not INPUT_JSON.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {INPUT_JSON}"
        )

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results")

    if not isinstance(results, list):
        raise RuntimeError(
            "Champ 'results' absent ou invalide dans Phase 24."
        )

    return data, results


def build_records(results, limit):
    records = []

    for item in results:
        candidate = item.get("candidate", "UNKNOWN")

        last_status = str(
            item.get("last_status", "UNKNOWN")
        ).strip().upper()

        completed = bool(
            item.get("completed", False)
        )

        converged = bool(
            item.get("converged", False)
        )

        error = bool(
            item.get("error", False)
        )

        timeout = bool(
            item.get("timeout", False)
        )

        energy = item.get("total_energy_ry")

        scf = item.get("scf_iterations")

        if last_status == "COMPLETED" or completed:
            status = "COMPLETED"
        elif timeout:
            status = "TIMEOUT"
        elif error:
            status = "ERROR"
        elif last_status == "INCOMPLETE":
            status = "INCOMPLETE"
        else:
            status = last_status

        records.append(
            {
                "candidate": candidate,
                "status": status,
                "converged": converged,
                "completed": completed,
                "error": error,
                "timeout": timeout,
                "scf_iterations": scf,
                "total_energy_ry": energy,
            }
        )

    records.sort(
        key=lambda x: x["candidate"]
    )

    if limit > 0:
        records = records[:limit]

    return records


def calculate_statistics(records):
    total = len(records)

    completed = sum(
        r["status"] == "COMPLETED"
        for r in records
    )

    incomplete = sum(
        r["status"] == "INCOMPLETE"
        for r in records
    )

    timeout = sum(
        r["status"] == "TIMEOUT"
        for r in records
    )

    errors = sum(
        r["status"] == "ERROR"
        for r in records
    )

    converged = sum(
        r["converged"]
        for r in records
    )

    energies = [
        r for r in records
        if r["status"] == "COMPLETED"
        and r["total_energy_ry"] is not None
    ]

    lowest = None

    if energies:
        lowest = min(
            energies,
            key=lambda x: x["total_energy_ry"]
        )

    return {
        "total_candidates": total,
        "completed": completed,
        "incomplete": incomplete,
        "timeout": timeout,
        "errors": errors,
        "converged": converged,
        "energies_detected": sum(
            r["total_energy_ry"] is not None
            for r in records
        ),
        "completion_rate_percent": (
            round(
                completed / total * 100,
                2
            )
            if total else 0.0
        ),
        "lowest_completed_energy_ry": (
            lowest["total_energy_ry"]
            if lowest else None
        ),
        "lowest_energy_candidate": (
            lowest["candidate"]
            if lowest else None
        ),
    }


def write_csv(records):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fields = [
        "candidate",
        "status",
        "converged",
        "completed",
        "error",
        "timeout",
        "scf_iterations",
        "total_energy_ry",
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
        writer.writerows(records)


def write_json(records, stats):
    data = {
        "project": "HydroMatAI",
        "phase": 25,
        "phase_name": "SUMMARY",
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
        "phase": 25,
        "phase_name": "SUMMARY",
        "status": "COMPLETED",
        "mode": "ANALYSIS_ONLY",
        "source_phase": 24,
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
    print("HydroMatAI — PHASE 25")
    print("SYNTHÈSE DES RÉSULTATS")
    print("=" * 80)

    print()
    print("RÉSULTATS")
    print("-" * 80)

    print(
        f"Candidats analysés       : "
        f"{stats['total_candidates']}"
    )

    print(
        f"Calculs terminés         : "
        f"{stats['completed']}"
    )

    print(
        f"Convergences détectées  : "
        f"{stats['converged']}"
    )

    print(
        f"Incomplets              : "
        f"{stats['incomplete']}"
    )

    print(
        f"TIMEOUT                 : "
        f"{stats['timeout']}"
    )

    print(
        f"ERREURS                 : "
        f"{stats['errors']}"
    )

    print(
        f"Taux de complétion      : "
        f"{stats['completion_rate_percent']:.2f} %"
    )

    if stats["lowest_energy_candidate"]:
        print()
        print("ÉNERGIE MINIMALE — CALCULS TERMINÉS")
        print("-" * 80)

        print(
            f"Candidat                 : "
            f"{stats['lowest_energy_candidate']}"
        )

        print(
            f"Énergie                  : "
            f"{stats['lowest_completed_energy_ry']:.12f} Ry"
        )

    print()
    print("DÉTAILS")
    print("-" * 80)

    for i, r in enumerate(records, 1):

        energy = (
            f"{r['total_energy_ry']:.12f} Ry"
            if r["total_energy_ry"] is not None
            else "N/A"
        )

        scf = (
            str(r["scf_iterations"])
            if r["scf_iterations"] is not None
            else "N/A"
        )

        print(
            f"[{i}/{len(records)}] "
            f"{r['candidate']} | "
            f"{r['status']} | "
            f"Converged: {r['converged']} | "
            f"Energy: {energy} | "
            f"SCF: {scf}"
        )

    print()
    print("=" * 80)
    print("FICHIERS")
    print("=" * 80)

    print(f"CSV      : {OUTPUT_CSV}")
    print(f"JSON     : {OUTPUT_JSON}")
    print(f"MANIFEST : {MANIFEST_JSON}")

    print()
    print("=" * 80)
    print("PHASE 25 — AUDIT FINAL")
    print("=" * 80)

    print("Lecture Phase 24       : OK")
    print("Synthèse               : OK")
    print("pw.x lancé             : NON")
    print("Calcul QE lancé        : NON")
    print("Aucun CIF modifié      : OK")
    print("Traçabilité            : OK")

    print()
    print("MODE : ANALYSIS_ONLY")

    print("=" * 80)
    print("PHASE 25 — TERMINÉE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=25
    )

    args = parser.parse_args()

    phase24_data, results = load_phase24()

    records = build_records(
        results,
        args.limit
    )

    if not records:
        raise RuntimeError(
            "Aucun résultat Phase 24."
        )

    stats = calculate_statistics(
        records
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
