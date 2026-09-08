#!/usr/bin/env python3
import os
os.system("clear")
"""
HydroMatAI — PHASE 21A
Diagnostic des chemins RELAX issus de Phase 20.
Aucun calcul QE.
Aucun fichier scientifique modifié.
"""

from pathlib import Path
import argparse
import csv
import json
import re

ROOT = Path("/home/hk/HydroMatAI")
PRIORITY = ROOT / "reports/global_screening/dft_priority.csv"
CIF_ROOT = ROOT / "MOF_Library/MOFXDB_FULL/cif"
OUT = ROOT / "calculations/phase_21_relax_diagnostic"


def norm(x):
    return str(x).strip().lower().replace(" ", "_")


def find_col(cols, names):
    for n in names:
        for c in cols:
            if norm(c) == norm(n):
                return c
    return None


def load_candidates(limit):
    with PRIORITY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    cls = find_col(rows[0].keys(), ["CLASS", "class"])
    material = find_col(rows[0].keys(), ["MATERIAL", "material", "name"])
    source = find_col(rows[0].keys(), ["SOURCE", "source"])

    rows = [r for r in rows if str(r.get(cls, "")).upper() == "PRIORITY"]
    return rows[:limit], material, source


def locate_cif(material):
    matches = list(CIF_ROOT.glob(f"*{material}*.cif"))
    return matches[0] if matches else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    rows, material_col, source_col = load_candidates(args.limit)
    results = []

    print("=" * 80)
    print(" HydroMatAI — PHASE 21A")
    print(" DIAGNOSTIC / CORRECTION RELAX QE")
    print("=" * 80)
    print()
    print("PROTECTION QE")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("Calcul  : NON LANCÉ")
    print()
    print("CANDIDATS INSPECTÉS :", len(rows))

    for i, r in enumerate(rows, 1):
        material = r[material_col]
        cif = locate_cif(material)

        if cif is None:
            status = "CIF_MISSING"
        else:
            status = "JOB_DIRECTORY_MISSING"

        results.append({
            "material": material,
            "source": r.get(source_col, ""),
            "cif": str(cif) if cif else None,
            "status": status,
        })

        print(f"\n[{i}/{len(rows)}] {material}")
        print("  CIF    :", "OK" if cif else "FAILED")
        print("  RELAX  :", status)
        if status == "JOB_DIRECTORY_MISSING":
            print("  ACTION : Vérifier le chemin de sortie utilisé par Phase 20.")

    csv_path = OUT / "phase21_diagnostic.csv"
    json_path = OUT / "phase21_diagnostic.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 80)
    print(" PHASE 21A — TERMINÉE")
    print("=" * 80)
    print("JSON :", json_path)
    print("CSV  :", csv_path)
    print("Aucun calcul QE lancé.")
    print("Aucun fichier scientifique modifié.")


if __name__ == "__main__":
    main()
