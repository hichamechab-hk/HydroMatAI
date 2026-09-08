from __future__ import annotations
import os
os.system("clear")


import argparse
import csv
import json
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
PSEUDO_DIR = Path("/home/hk/software/qe-7.5/pseudo")

INPUT = ROOT / "calculations/phase_21c_pseudopotential_audit/phase21c_pseudopotential_audit.csv"
OUT = ROOT / "calculations/phase_21d_pseudopotential_mapping"

PREFERRED = {
    "H": ["H.pbe-kjpaw.UPF"],
    "C": ["C.UPF"],
    "N": ["N.UPF"],
    "O": ["O.UPF"],
    "F": ["F.UPF"],
    "Zn": ["Zn.UPF"],
}


def available():
    return sorted(PSEUDO_DIR.glob("*.UPF"))


def choose(element: str, files):
    names = {p.name for p in files}

    for preferred in PREFERRED.get(element, []):
        if preferred in names:
            return preferred

    candidates = sorted(
        p.name for p in files
        if p.stem.lower().startswith(element.lower())
    )

    return candidates[0] if candidates else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" HydroMatAI — PHASE 21D")
    print(" MAPPING PSEUDOPOTENTIELS QE")
    print("=" * 80)

    if not INPUT.exists():
        raise SystemExit(f"Input absent : {INPUT}")

    files = available()

    print()
    print("PROTECTION QE")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    print()
    print("UPF DISPONIBLES")
    print("-" * 80)
    print(f"Répertoire : {PSEUDO_DIR}")
    print(f"UPF        : {len(files)}")

    with INPUT.open("r", encoding="utf-8", newline="") as f:
        candidates = list(csv.DictReader(f))[:args.limit]

    results = []

    print()
    print("MAPPING")
    print("-" * 80)

    for i, row in enumerate(candidates, 1):
        name = row["name"]
        elements = [
            x.strip()
            for x in row.get("elements", "").split(",")
            if x.strip()
        ]

        mapping = {}
        missing = []

        for element in elements:
            pseudo = choose(element, files)

            if pseudo:
                mapping[element] = pseudo
            else:
                missing.append(element)

        status = "READY_FOR_QE" if not missing else "MISSING_PSEUDO"

        print(f"[{i}/{len(candidates)}] {name}")
        print(f"  Elements : {', '.join(elements)}")

        for element in elements:
            print(
                f"  {element:<3} → "
                f"{mapping.get(element, 'MISSING')}"
            )

        results.append({
            "name": name,
            "cif": row.get("cif", ""),
            "elements": ",".join(elements),
            "missing_pseudo": ",".join(missing),
            "status": status,
            "pseudo_map": json.dumps(
                mapping,
                sort_keys=True,
            ),
        })

    csv_path = OUT / "phase21d_mapping.csv"
    json_path = OUT / "phase21d_mapping.json"

    fields = [
        "name",
        "cif",
        "elements",
        "missing_pseudo",
        "status",
        "pseudo_map",
    ]

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    summary = {
        "phase": "21D",
        "candidates": len(results),
        "ready_for_qe": sum(
            r["status"] == "READY_FOR_QE"
            for r in results
        ),
        "missing_pseudo": sum(
            r["status"] == "MISSING_PSEUDO"
            for r in results
        ),
        "pseudo_directory": str(PSEUDO_DIR),
        "pseudo_count": len(files),
        "pw_x_launched": False,
        "qe_calculation": False,
        "results": results,
    }

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 80)
    print(" PHASE 21D — RÉSULTATS")
    print("=" * 80)
    print(f"Candidats       : {len(results)}")
    print(f"READY_FOR_QE    : {summary['ready_for_qe']}")
    print(f"MISSING_PSEUDO  : {summary['missing_pseudo']}")

    print()
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV  : {csv_path}")
    print(f"JSON : {json_path}")

    print()
    print("=" * 80)
    print("PHASE 21D — TERMINÉE")
    print("=" * 80)
    print("Aucun calcul QE lancé.")
    print("Aucun CIF modifié.")
    print("=" * 80)


if __name__ == "__main__":
    main()
