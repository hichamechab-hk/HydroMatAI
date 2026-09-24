#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
OUT = ROOT / "calculations/phase_22_h2_provenance_source"
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"

print("PHASE 22 — H2 SOURCE PROVENANCE")
print("MODE              : ANALYSIS_ONLY")
print("pw.x              : NO")
print("CIF MODIFICATION  : NO")
print()

if not TARGET.exists():
    print("ERROR: TOP200_GLOBAL_H2_RANKED.csv introuvable")
    raise SystemExit(1)

text_target = TARGET.read_text(encoding="utf-8", errors="ignore")

print(f"SOURCE H2         : {TARGET}")
print(f"SIZE              : {TARGET.stat().st_size} bytes")
print()

# Cherche les scripts et rapports qui mentionnent exactement le fichier H2.
search_roots = [
    ROOT / "scripts",
    ROOT / "reports",
    ROOT / "calculations",
]

files = []
for base in search_roots:
    if not base.exists():
        continue
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if p == TARGET:
            continue
        if p.stat().st_size > 15 * 1024 * 1024:
            continue
        if p.suffix.lower() in {
            ".py", ".sh", ".bash", ".csv", ".json",
            ".txt", ".md", ".log", ".yaml", ".yml"
        }:
            files.append(p)

files = list(dict.fromkeys(files))

print(f"FICHIERS A TESTER : {len(files)}")
print("Recherche de la provenance...")

hits = []

patterns = [
    "TOP200_GLOBAL_H2_RANKED.csv",
    "GLOBAL_H2_RANKED",
    "hydrogen_score",
    "hydrogen_wt_percent",
]

for i, p in enumerate(files, 1):
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    found = [x for x in patterns if x in txt]

    if found:
        hits.append({
            "file": str(p),
            "matches": found
        })
        print(f"[{i}/{len(files)}] {p}")

print()
print(f"PROVENANCE HITS   : {len(hits)}")

# Cherche aussi les producteurs probables : scripts contenant écriture CSV
# et champs spécifiques du ranking H2.
producers = []

for h in hits:
    p = Path(h["file"])
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    score = 0

    if "TOP200_GLOBAL_H2_RANKED.csv" in txt:
        score += 5
    if "hydrogen_score" in txt:
        score += 2
    if "hydrogen_wt_percent" in txt:
        score += 2
    if "csv.writer" in txt or "DictWriter" in txt:
        score += 1
    if "to_csv" in txt:
        score += 1
    if "open(" in txt:
        score += 1

    producers.append({
        "file": str(p),
        "score": score,
        "matches": h["matches"]
    })

producers.sort(key=lambda x: (-x["score"], x["file"]))

# Cherche dans les producteurs les références tobMof/hMOF et les chemins CIF.
relations = []

for pinfo in producers:
    p = Path(pinfo["file"])
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    tob = sorted(set(re.findall(r"\btob[mM]of-\d+\b", txt)))
    hmo = sorted(set(re.findall(r"\bhMOF-\d+\b", txt)))

    cif_paths = sorted(set(
        re.findall(r"[^\s\"']+\.cif", txt, flags=re.I)
    ))

    if tob or hmo or cif_paths:
        relations.append({
            "file": str(p),
            "tobmof_ids": tob[:100],
            "hmof_ids": hmo[:100],
            "cif_paths": cif_paths[:100]
        })

csv_path = OUT / "phase22_h2_provenance_source.csv"
json_path = OUT / "phase22_h2_provenance_source.json"
manifest_path = OUT / "phase22_manifest.json"

rows = []

for p in producers:
    rows.append({
        "file": p["file"],
        "score": p["score"],
        "matches": ";".join(p["matches"])
    })

with csv_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=["file", "score", "matches"]
    )
    w.writeheader()
    w.writerows(rows)

payload = {
    "phase": "22",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "pw_x": False,
    "new_qe_calculation": False,
    "cif_modification": False,
    "target": str(TARGET),
    "target_exists": True,
    "target_size": TARGET.stat().st_size,
    "files_tested": len(files),
    "provenance_hits": len(hits),
    "producer_candidates": producers,
    "provenance_relations": relations,
    "generated_at": datetime.now().isoformat()
}

json_path.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": "22",
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "pw_x_launched": False,
    "new_qe_calculation": False,
    "cif_modified": False,
    "provenance_hits": len(hits),
    "csv": str(csv_path),
    "json": str(json_path)
}

manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("TOP PRODUCER CANDIDATES")
print("----------------------------")

for p in producers[:15]:
    print(
        f"{p['score']:02d} | {p['file']} | "
        f"{';'.join(p['matches'])}"
    )

print()
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 22 STATUS : COMPLETE")
