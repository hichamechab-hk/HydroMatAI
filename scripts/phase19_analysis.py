#!/usr/bin/env python3

import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
OUTDIR = ROOT / "calculations" / "phase_19_analysis"
OUTDIR.mkdir(parents=True, exist_ok=True)

TOP20 = ROOT / "calculations" / "phase_17b_parallel_audit_fixed" / "phase17b_fixed.csv"
SCF = ROOT / "calculations" / "phase_18_scf_analysis" / "phase18_scf_analysis.csv"

rows = []

if TOP20.exists():
    with TOP20.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

scf_data = {}
if SCF.exists():
    with SCF.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = r.get("candidate", "")
            if c:
                scf_data[c] = r

results = []

for i, r in enumerate(rows[:20], 1):
    candidate = r.get("candidate") or r.get("name") or ""
    s = scf_data.get(candidate, {})

    status = "NOT_ANALYZED"

    if candidate == "hMOF-5064089":
        status = "SCF_INCOMPLETE"
    elif s:
        completed = str(s.get("completed", "")).lower()
        converged = str(s.get("converged", "")).lower()

        if completed == "true" and converged == "true":
            status = "SCF_CONVERGED"
        elif completed == "true":
            status = "SCF_COMPLETED_NOT_CONFIRMED"
        else:
            status = "SCF_INCOMPLETE"
    else:
        status = "NO_SCF_RESULT"

    results.append({
        "top20_rank": i,
        "candidate": candidate,
        "status": status,
        "total_energy_ry": s.get("total_energy_ry", ""),
        "scf_iterations": s.get("scf_iterations", ""),
        "errors": s.get("errors", ""),
        "source": "phase17b_fixed + phase18"
    })

csv_path = OUTDIR / "phase19_analysis.csv"
json_path = OUTDIR / "phase19_analysis.json"
manifest_path = OUTDIR / "phase19_manifest.json"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys() if results else [
        "top20_rank","candidate","status","total_energy_ry",
        "scf_iterations","errors","source"
    ])
    writer.writeheader()
    writer.writerows(results)

summary = {
    "phase": "19",
    "mode": "ANALYSIS_ONLY",
    "pw_x_launched": False,
    "new_qe_calculation": False,
    "cif_modified": False,
    "top20_count": len(results),
    "scf_converged": sum(x["status"] == "SCF_CONVERGED" for x in results),
    "scf_incomplete": sum(x["status"] == "SCF_INCOMPLETE" for x in results),
    "no_scf_result": sum(x["status"] == "NO_SCF_RESULT" for x in results),
    "generated_at": datetime.now().isoformat(),
    "results": results
}

json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

manifest = {
    "phase": "19",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "csv": str(csv_path),
    "json": str(json_path)
}

manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

print()
print("PHASE 19 — FINAL TOP20 ANALYSIS")
print("MODE              : ANALYSIS_ONLY")
print("pw.x              : NO")
print("NEW QE CALCULATION: NO")
print("CIF MODIFICATION  : NO")
print()
print(f"TOP20 ANALYZED    : {len(results)}")
print(f"SCF CONVERGED     : {summary['scf_converged']}")
print(f"SCF INCOMPLETE    : {summary['scf_incomplete']}")
print(f"NO SCF RESULT     : {summary['no_scf_result']}")
print()
for x in results:
    print(
        f"{x['top20_rank']:02d} | "
        f"{x['candidate']:<18} | "
        f"{x['status']}"
    )

print()
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 19 STATUS : COMPLETE")
