#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")

SRC = ROOT / "calculations/phase_17b_parallel_audit/phase17b_parallel_audit.csv"
OUT = ROOT / "calculations/phase_17b_parallel_audit_fixed"

OUT.mkdir(parents=True, exist_ok=True)

def load_csv(path):
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return {}

def norm(x):
    return str(x or "").strip().lower()

def candidate_name(row):
    return (
        row.get("candidate")
        or row.get("name")
        or row.get("material")
        or ""
    ).strip()

rows = load_csv(SRC)

# IMPORTANT :
# Phase 17 TOP20 = premières lignes hMOF du fichier,
# jusqu'à obtenir exactement 20 candidats.
top20 = []

for row in rows:
    name = candidate_name(row)

    if not name:
        continue

    if norm(name).startswith("hmof-"):
        top20.append(row)

    if len(top20) == 20:
        break

if len(top20) != 20:
    raise RuntimeError(
        f"TOP20 introuvable : seulement {len(top20)} candidats hMOF détectés."
    )

# Recherche des inputs QE déjà générés
qe_inputs = {}

qe_root = ROOT / "calculations/phase_22_qe_inputs"

if qe_root.exists():
    for p in qe_root.rglob("*.in"):
        text = p.name.lower()

        for row in top20:
            name = candidate_name(row)

            if name.lower() in text:
                qe_inputs[name] = str(p)

# Recherche des répertoires QE Phase 17
phase17_dirs = {}

phase17_qe = ROOT / "calculations/global_screening/qe/TOP20"

if phase17_qe.exists():
    for p in phase17_qe.iterdir():
        if p.is_dir():
            for row in top20:
                name = candidate_name(row)

                if name.lower() in p.name.lower():
                    phase17_dirs[name] = str(p)

# Recherche des CIF correspondants dans le projet
cif_matches = {}

for cif in ROOT.rglob("*.cif"):
    name_lower = cif.stem.lower()

    for row in top20:
        name = candidate_name(row)

        if name.lower() == name_lower:
            cif_matches[name] = str(cif)

# Recherche des sorties Phase 17
outputs = {}

for out in ROOT.rglob("*.out"):
    name_lower = out.stem.lower()

    for row in top20:
        name = candidate_name(row)

        if name.lower() == name_lower:
            outputs[name] = str(out)

result = []

for rank, row in enumerate(top20, 1):

    name = candidate_name(row)

    result.append({
        "phase17_rank": rank,
        "candidate": name,
        "qe_input_found": bool(qe_inputs.get(name)),
        "qe_input": qe_inputs.get(name, ""),
        "phase17_directory_found": bool(phase17_dirs.get(name)),
        "phase17_directory": phase17_dirs.get(name, ""),
        "cif_found": bool(cif_matches.get(name)),
        "cif": cif_matches.get(name, ""),
        "qe_output_found": bool(outputs.get(name)),
        "qe_output": outputs.get(name, ""),
        "h2_rank": row.get("h2_rank", ""),
        "hydrogen_score": row.get("hydrogen_score", ""),
        "hydrogen_wt_percent": row.get("hydrogen_wt_percent", ""),
    })

csv_path = OUT / "phase17b_fixed.csv"

fields = [
    "phase17_rank",
    "candidate",
    "qe_input_found",
    "qe_input",
    "phase17_directory_found",
    "phase17_directory",
    "cif_found",
    "cif",
    "qe_output_found",
    "qe_output",
    "h2_rank",
    "hydrogen_score",
    "hydrogen_wt_percent",
]

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(result)

summary = {
    "phase": "17B",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "top20_count": len(result),
    "qe_inputs_found": sum(x["qe_input_found"] for x in result),
    "phase17_directories_found": sum(
        x["phase17_directory_found"] for x in result
    ),
    "cifs_found": sum(x["cif_found"] for x in result),
    "qe_outputs_found": sum(x["qe_output_found"] for x in result),
    "qe_calculation_launched": False,
    "pw_x_launched": False,
    "cif_modified": False,
    "source": str(SRC),
    "output": str(csv_path),
}

json_path = OUT / "phase17b_fixed.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "summary": summary,
            "candidates": result
        },
        f,
        indent=2,
        ensure_ascii=False
    )

manifest_path = OUT / "phase17b_fixed_manifest.json"

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("=" * 78)
print("PHASE 17B — TOP20 AUDIT CORRIGÉ")
print("=" * 78)
print()
print("MODE              : ANALYSIS_ONLY")
print("pw.x              : NO")
print("QE CALCULATION    : NO")
print("CIF MODIFICATION  : NO")
print()
print(f"TOP20             : {len(result)}")
print(f"QE INPUTS         : {summary['qe_inputs_found']}/20")
print(f"PHASE17 DIR       : {summary['phase17_directories_found']}/20")
print(f"CIF               : {summary['cifs_found']}/20")
print(f"QE OUTPUT         : {summary['qe_outputs_found']}/20")
print()
print("CANDIDATS")
print("-" * 78)

for x in result:
    print(
        f"{x['phase17_rank']:02d} | "
        f"{x['candidate']} | "
        f"INPUT={'YES' if x['qe_input_found'] else 'NO'} | "
        f"CIF={'YES' if x['cif_found'] else 'NO'} | "
        f"OUT={'YES' if x['qe_output_found'] else 'NO'}"
    )

print()
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 17B STATUS : COMPLETE")
print("=" * 78)
