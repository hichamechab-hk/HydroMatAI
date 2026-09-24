#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
OUT = ROOT / "calculations/phase_21_h2_provenance_final"
OUT.mkdir(parents=True, exist_ok=True)

TOP20 = ROOT / "calculations/phase_17b_parallel_audit_fixed/phase17b_fixed.csv"
H2 = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))

top20 = read_csv(TOP20)
h2 = read_csv(H2)

qe_names = []
for row in top20[:20]:
    name = row.get("candidate") or row.get("name") or ""
    if name.startswith("hMOF-"):
        qe_names.append(name)

print("PHASE 21 — H2 / QE PROVENANCE")
print("MODE              : ANALYSIS_ONLY")
print("pw.x              : NO")
print("CIF MODIFICATION  : NO")
print()
print(f"QE TOP20          : {len(qe_names)}")
print(f"H2 ROWS           : {len(h2)}")
print("Recherche ciblée  : démarrage...")

# Fichiers ciblés uniquement : provenance, screening et résultats de phases.
target_dirs = [
    ROOT / "reports",
    ROOT / "calculations/phase_17b_parallel_audit_fixed",
    ROOT / "calculations/phase_19_analysis",
    ROOT / "calculations/phase_20_final_synthesis",
    ROOT / "calculations/phase_29_mapping_h2_qe",
    ROOT / "calculations/phase_30_h2_mapping_diagnostic",
    ROOT / "calculations/phase_31_mapping_reconstructed",
    ROOT / "calculations/phase_32_provenance_mapping",
    ROOT / "calculations/phase_33_provenance_trace",
]

files = []

for d in target_dirs:
    if not d.exists():
        continue
    for p in d.rglob("*"):
        if not p.is_file():
            continue
        if p.stat().st_size > 20 * 1024 * 1024:
            continue
        if p.suffix.lower() in {
            ".csv", ".json", ".txt", ".log", ".out",
            ".md", ".tsv", ".yaml", ".yml"
        }:
            files.append(p)

files = list(dict.fromkeys(files))

print(f"Fichiers ciblés   : {len(files)}")

evidence = []

qe_pattern = re.compile(r"\bhMOF-\d+\b", re.I)
h2_pattern = re.compile(r"\btobmof-\d+\b", re.I)

for idx, path in enumerate(files, 1):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    # Seulement les fichiers contenant au moins un nom TOP20.
    qmatches = {
        x.lower(): x for x in qe_pattern.findall(text)
        if x.lower() in {q.lower() for q in qe_names}
    }

    if not qmatches:
        continue

    hmatches = set(h2_pattern.findall(text))

    if not hmatches:
        continue

    for q in qmatches.values():
        for h in sorted(hmatches):
            evidence.append({
                "qe_candidate": q,
                "h2_candidate": h,
                "file": str(path),
                "evidence_type": "EXPLICIT_CO_OCCURRENCE"
            })

    print(f"  [{idx}/{len(files)}] preuve trouvée : {path.name}")

# Déduplication
seen = set()
clean = []

for e in evidence:
    key = (
        e["qe_candidate"].lower(),
        e["h2_candidate"].lower(),
        e["file"]
    )
    if key not in seen:
        seen.add(key)
        clean.append(e)

evidence = clean

h2_map = {
    r.get("name", "").lower(): r
    for r in h2
    if r.get("name")
}

results = []

for rank, qe in enumerate(qe_names, 1):
    matches = [
        e for e in evidence
        if e["qe_candidate"].lower() == qe.lower()
    ]

    h2names = sorted({
        e["h2_candidate"] for e in matches
    })

    if len(h2names) == 1:
        hname = h2names[0]
        hrow = h2_map.get(hname.lower(), {})

        status = "VALIDATED"
        score = hrow.get("hydrogen_score", "")
        wt = hrow.get("hydrogen_wt_percent", "")

    elif len(h2names) > 1:
        status = "AMBIGUOUS"
        hname = ";".join(h2names)
        score = ""
        wt = ""

    else:
        status = "NO_MAPPING"
        hname = ""
        score = ""
        wt = ""

    results.append({
        "qe_rank": rank,
        "qe_candidate": qe,
        "mapping_status": status,
        "h2_candidate": hname,
        "hydrogen_score": score,
        "hydrogen_wt_percent": wt,
        "evidence_files": len(matches)
    })

validated = sum(
    r["mapping_status"] == "VALIDATED" for r in results
)
ambiguous = sum(
    r["mapping_status"] == "AMBIGUOUS" for r in results
)
unmapped = sum(
    r["mapping_status"] == "NO_MAPPING" for r in results
)

csv_path = OUT / "phase21_h2_provenance_final.csv"
json_path = OUT / "phase21_h2_provenance_final.json"
manifest_path = OUT / "phase21_manifest.json"

fields = [
    "qe_rank",
    "qe_candidate",
    "mapping_status",
    "h2_candidate",
    "hydrogen_score",
    "hydrogen_wt_percent",
    "evidence_files"
]

with csv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

payload = {
    "phase": "21",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "pw_x": False,
    "new_qe_calculation": False,
    "cif_modification": False,
    "qe_top20": len(qe_names),
    "h2_rows": len(h2),
    "files_scanned": len(files),
    "evidence_count": len(evidence),
    "validated_mappings": validated,
    "ambiguous_mappings": ambiguous,
    "unmapped": unmapped,
    "results": results,
    "evidence": evidence,
    "generated_at": datetime.now().isoformat()
}

json_path.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": "21",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "pw_x_launched": False,
    "new_qe_calculation": False,
    "cif_modified": False,
    "validated_mappings": validated,
    "ambiguous_mappings": ambiguous,
    "unmapped": unmapped,
    "csv": str(csv_path),
    "json": str(json_path)
}

manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("PHASE 21 — RESULT")
print("----------------------------")
print(f"QE TOP20          : {len(qe_names)}")
print(f"H2 ROWS           : {len(h2)}")
print(f"FILES SCANNED     : {len(files)}")
print(f"EXPLICIT EVIDENCE : {len(evidence)}")
print(f"VALIDATED         : {validated}")
print(f"AMBIGUOUS         : {ambiguous}")
print(f"NO MAPPING        : {unmapped}")
print()

for r in results:
    print(
        f"{r['qe_rank']:02d} | "
        f"{r['qe_candidate']:<18} | "
        f"{r['mapping_status']:<10} | "
        f"{r['h2_candidate'] or '-'}"
    )

print()
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 21 STATUS : COMPLETE")
