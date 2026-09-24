#!/usr/bin/env python3

import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
OUT = ROOT / "calculations" / "phase_20_final_synthesis"
OUT.mkdir(parents=True, exist_ok=True)

TOP20 = ROOT / "calculations/phase_17b_parallel_audit_fixed/phase17b_fixed.csv"
P19 = ROOT / "calculations/phase_19_analysis/phase19_analysis.csv"

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

top20 = read_csv(TOP20)
p19 = read_csv(P19)

p19_map = {r.get("candidate", ""): r for r in p19}

final = []

for i, r in enumerate(top20[:20], 1):
    candidate = r.get("candidate") or r.get("name") or ""
    a = p19_map.get(candidate, {})

    status = a.get("status", "NO_ANALYSIS")

    if status == "SCF_CONVERGED":
        decision = "RETAIN"
        reason = "SCF converged"
    elif status == "SCF_COMPLETED_NOT_CONFIRMED":
        decision = "REVIEW"
        reason = "SCF completed but convergence not confirmed"
    elif status == "SCF_INCOMPLETE":
        decision = "EXCLUDE_QE"
        reason = "SCF incomplete; no valid QE energy"
    else:
        decision = "NO_QE_EVIDENCE"
        reason = "No usable QE result"

    final.append({
        "rank": i,
        "candidate": candidate,
        "scf_status": status,
        "decision": decision,
        "reason": reason,
        "total_energy_ry": a.get("total_energy_ry", ""),
        "scf_iterations": a.get("scf_iterations", ""),
        "errors": a.get("errors", "")
    })

counts = {}
for r in final:
    counts[r["decision"]] = counts.get(r["decision"], 0) + 1

csv_path = OUT / "phase20_final_synthesis.csv"
json_path = OUT / "phase20_final_synthesis.json"
manifest_path = OUT / "phase20_manifest.json"

fields = [
    "rank", "candidate", "scf_status", "decision", "reason",
    "total_energy_ry", "scf_iterations", "errors"
]

with csv_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(final)

data = {
    "phase": "20",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "top20_analyzed": len(final),
    "decision_counts": counts,
    "results": final,
    "generated_at": datetime.now().isoformat()
}

json_path.write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": "20",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "pw_x_launched": False,
    "new_qe_calculation": False,
    "cif_modified": False,
    "csv": str(csv_path),
    "json": str(json_path)
}

manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("PHASE 20 — FINAL SYNTHESIS")
print("MODE              : ANALYSIS_ONLY")
print("NEW QE CALCULATION: NO")
print("CIF MODIFICATION  : NO")
print()
print(f"TOP20 ANALYZED    : {len(final)}")
for k in ["RETAIN", "REVIEW", "EXCLUDE_QE", "NO_QE_EVIDENCE"]:
    print(f"{k:<18}: {counts.get(k, 0)}")

print()
for r in final:
    print(
        f"{r['rank']:02d} | "
        f"{r['candidate']:<18} | "
        f"{r['decision']:<18} | "
        f"{r['scf_status']}"
    )

print()
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 20 STATUS : COMPLETE")
