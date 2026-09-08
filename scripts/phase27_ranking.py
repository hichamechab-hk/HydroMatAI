#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/hk/HydroMatAI")

PHASE25_JSON = (
    BASE_DIR
    / "calculations"
    / "phase_25_summary"
    / "phase25_summary.json"
)

PHASE26_JSON = (
    BASE_DIR
    / "calculations"
    / "phase_26_analysis"
    / "phase26_analysis.json"
)

OUTPUT_DIR = (
    BASE_DIR
    / "calculations"
    / "phase_27_ranking"
)

OUTPUT_CSV = OUTPUT_DIR / "phase27_ranking.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase27_ranking.json"
MANIFEST_JSON = OUTPUT_DIR / "phase27_manifest.json"


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_ranking(data, limit):
    records = data.get("records", [])

    completed = [
        r for r in records
        if r.get("status") == "COMPLETED"
        and r.get("total_energy_ry") is not None
    ]

    if limit > 0:
        completed = completed[:limit]

    ranked = []

    for rank, item in enumerate(
        sorted(
            completed,
            key=lambda x: x["total_energy_ry"]
        ),
        1
    ):
        ranked.append({
            "rank": rank,
            "candidate": item.get("candidate"),
            "status": item.get("status"),
            "scf_iterations": item.get("scf_iterations"),
            "total_energy_ry": item.get("total_energy_ry"),
            "converged": item.get("converged"),
        })

    return ranked


def write_csv(records):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "rank",
        "candidate",
        "status",
        "scf_iterations",
        "total_energy_ry",
        "converged",
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


def write_json(records, phase25, phase26):
    data = {
        "project": "HydroMatAI",
        "phase": 27,
        "phase_name": "RANKING",
        "mode": "ANALYSIS_ONLY",
        "generated_at": datetime.now().isoformat(),
        "sources": {
            "phase25": str(PHASE25_JSON),
            "phase26": str(PHASE26_JSON),
        },
        "ranking_basis": (
            "Classement des calculs QE terminés "
            "par énergie totale croissante."
        ),
        "warning": (
            "Les énergies totales absolues de systèmes "
            "de compositions différentes ne constituent "
            "pas à elles seules un critère physique de stabilité."
        ),
        "candidates_ranked": len(records),
        "ranking": records,
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


def write_manifest(records):
    manifest = {
        "project": "HydroMatAI",
        "phase": 27,
        "phase_name": "RANKING",
        "status": "COMPLETED",
        "mode": "ANALYSIS_ONLY",
        "source_phases": [25, 26],
        "pw_x_launched": False,
        "qe_calculation_launched": False,
        "cif_modified": False,
        "traceability": "OK",
        "ranked_candidates": len(records),
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


def print_results(records):
    print("=" * 80)
    print("HydroMatAI — PHASE 27")
    print("CLASSEMENT DES RÉSULTATS QE EXISTANTS")
    print("=" * 80)

    print()
    print("CLASSEMENT")
    print("-" * 80)

    if not records:
        print("Aucun calcul QE terminé disponible.")
    else:
        for r in records:
            print(
                f"[{r['rank']}] "
                f"{r['candidate']} | "
                f"E = {r['total_energy_ry']:.12f} Ry | "
                f"SCF = {r['scf_iterations']} | "
                f"Converged = {r['converged']}"
            )

    print()
    print("INTERPRÉTATION")
    print("-" * 80)

    if records:
        print(
            f"Meilleure énergie brute détectée : "
            f"{records[0]['candidate']}"
        )
        print(
            f"Énergie : "
            f"{records[0]['total_energy_ry']:.12f} Ry"
        )

    print()
    print("ATTENTION")
    print("-" * 80)
    print(
        "Le classement par énergie totale brute ne permet "
        "pas de comparer directement des structures de "
        "compositions différentes."
    )
    print(
        "Le classement est donc indicatif et ne remplace "
        "pas une énergie de formation ou une énergie "
        "normalisée."
    )

    print()
    print("=" * 80)
    print("AUDIT PHASE 27")
    print("=" * 80)

    print("Lecture Phase 25       : OK")
    print("Lecture Phase 26       : OK")
    print("Classement             : OK")
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
    print("PHASE 27 — TERMINÉE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)

    args = parser.parse_args()

    phase25 = load_json(PHASE25_JSON)
    phase26 = load_json(PHASE26_JSON)

    records = build_ranking(
        phase26,
        args.limit
    )

    write_csv(records)
    write_json(
        records,
        phase25,
        phase26
    )
    write_manifest(records)

    print_results(records)


if __name__ == "__main__":
    main()
