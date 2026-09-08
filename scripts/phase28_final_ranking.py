#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/hk/HydroMatAI")

PHASE27_JSON = (
    BASE_DIR
    / "calculations"
    / "phase_27_ranking"
    / "phase27_ranking.json"
)

H2_CSV = (
    BASE_DIR
    / "reports"
    / "global_screening"
    / "TOP200_GLOBAL_H2_RANKED.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "calculations"
    / "phase_28_final_ranking"
)

OUTPUT_CSV = OUTPUT_DIR / "phase28_final_ranking.csv"
OUTPUT_JSON = OUTPUT_DIR / "phase28_final_ranking.json"
MANIFEST_JSON = OUTPUT_DIR / "phase28_manifest.json"


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def find_field(row, names):
    normalized = {
        normalize(k): k
        for k in row.keys()
    }

    for name in names:
        key = normalized.get(normalize(name))

        if key is not None:
            return row[key]

    return None


def load_h2():
    if not H2_CSV.exists():
        raise FileNotFoundError(
            f"Fichier H₂ introuvable : {H2_CSV}"
        )

    records = []

    with open(
        H2_CSV,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            candidate = find_field(
                row,
                [
                    "candidate",
                    "name",
                    "structure",
                    "material",
                    "cif_name",
                    "cif",
                    "id",
                    "mof",
                    "mof_name"
                ]
            )

            score = find_field(
                row,
                [
                    "h2_score",
                    "H2_score",
                    "score_h2",
                    "screening_score",
                    "final_score",
                    "score"
                ]
            )

            rank = find_field(
                row,
                [
                    "rank",
                    "h2_rank",
                    "ranking",
                    "global_rank"
                ]
            )

            if candidate is None:
                continue

            try:
                score = float(score)
            except (TypeError, ValueError):
                score = None

            try:
                rank = int(float(rank))
            except (TypeError, ValueError):
                rank = None

            records.append({
                "candidate": str(candidate).strip(),
                "h2_score": score,
                "h2_rank": rank
            })

    return records


def match_h2(candidate, h2_records):
    target = normalize(candidate)

    for record in h2_records:
        value = normalize(record["candidate"])

        if value == target:
            return record

    for record in h2_records:
        value = normalize(record["candidate"])

        if target in value or value in target:
            return record

    return None


def build_results(phase27, h2_records, limit):
    qe_records = phase27.get("ranking", [])

    results = []

    for qe in qe_records:
        candidate = qe.get("candidate")

        h2 = match_h2(
            candidate,
            h2_records
        )

        results.append({
            "candidate": candidate,
            "h2_rank": (
                h2["h2_rank"]
                if h2 else None
            ),
            "h2_score": (
                h2["h2_score"]
                if h2 else None
            ),
            "qe_rank": qe.get("rank"),
            "qe_energy_ry": qe.get("total_energy_ry"),
            "scf_iterations": qe.get("scf_iterations"),
            "qe_converged": qe.get("converged"),
            "h2_available": h2 is not None,
        })

    results.sort(
        key=lambda x: (
            x["h2_rank"]
            if x["h2_rank"] is not None
            else 999999,
            x["qe_rank"]
            if x["qe_rank"] is not None
            else 999999
        )
    )

    for i, result in enumerate(results, 1):
        result["final_rank"] = i

    if limit > 0:
        results = results[:limit]

    return results


def write_csv(results):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fields = [
        "final_rank",
        "candidate",
        "h2_rank",
        "h2_score",
        "h2_available",
        "qe_rank",
        "qe_energy_ry",
        "scf_iterations",
        "qe_converged"
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
        writer.writerows(results)


def write_json(results):
    data = {
        "project": "HydroMatAI",
        "phase": 28,
        "phase_name": "FINAL_RANKING",
        "mode": "ANALYSIS_ONLY",
        "generated_at": datetime.now().isoformat(),
        "sources": {
            "phase27": str(PHASE27_JSON),
            "h2_screening": str(H2_CSV)
        },
        "method": (
            "H2 global screening rank is used as the "
            "primary screening criterion. QE results "
            "are attached as secondary validation data."
        ),
        "warning": (
            "QE total energies are not directly comparable "
            "between structures with different compositions."
        ),
        "candidates": len(results),
        "h2_matches": sum(
            r["h2_available"]
            for r in results
        ),
        "results": results
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


def write_manifest(results):
    manifest = {
        "project": "HydroMatAI",
        "phase": 28,
        "phase_name": "FINAL_RANKING",
        "status": "COMPLETED",
        "mode": "ANALYSIS_ONLY",
        "source_phases": [25, 26, 27],
        "h2_source": str(H2_CSV),
        "h2_matches": sum(
            r["h2_available"]
            for r in results
        ),
        "pw_x_launched": False,
        "qe_calculation_launched": False,
        "cif_modified": False,
        "traceability": "OK",
        "files": {
            "csv": str(OUTPUT_CSV),
            "json": str(OUTPUT_JSON),
            "manifest": str(MANIFEST_JSON)
        },
        "generated_at": datetime.now().isoformat()
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


def print_results(results):
    matches = sum(
        r["h2_available"]
        for r in results
    )

    print("=" * 80)
    print("HydroMatAI — PHASE 28")
    print("CLASSEMENT FINAL H₂ + QE")
    print("=" * 80)

    print()
    print("SOURCE H₂")
    print("-" * 80)
    print(f"{H2_CSV}")
    print(f"Correspondances H₂ : {matches}/{len(results)}")

    print()
    print("CLASSEMENT")
    print("-" * 80)

    for r in results:
        h2_rank = (
            str(r["h2_rank"])
            if r["h2_rank"] is not None
            else "N/A"
        )

        h2_score = (
            f"{r['h2_score']:.6f}"
            if r["h2_score"] is not None
            else "N/A"
        )

        qe_energy = (
            f"{r['qe_energy_ry']:.12f} Ry"
            if r["qe_energy_ry"] is not None
            else "N/A"
        )

        print(
            f"[{r['final_rank']}] "
            f"{r['candidate']} | "
            f"H2 rank={h2_rank} | "
            f"H2 score={h2_score} | "
            f"QE={qe_energy}"
        )

    print()
    print("=" * 80)
    print("AUDIT PHASE 28")
    print("=" * 80)

    print("Lecture Phase 27       : OK")
    print("Lecture screening H₂   : OK")
    print("Fusion H₂ + QE         : OK")
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
    print("PHASE 28 — TERMINÉE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=25
    )

    args = parser.parse_args()

    phase27 = load_json(PHASE27_JSON)
    h2_records = load_h2()

    results = build_results(
        phase27,
        h2_records,
        args.limit
    )

    if not results:
        raise RuntimeError(
            "Aucun candidat QE disponible."
        )

    write_csv(results)
    write_json(results)
    write_manifest(results)

    print_results(results)


if __name__ == "__main__":
    main()
