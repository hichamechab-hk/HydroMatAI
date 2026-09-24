#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
OUT = ROOT / "calculations/phase_24_trace_h2_source"
OUT.mkdir(parents=True, exist_ok=True)

TARGET = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"

KEYS = [
    "hydrogen_score",
    "hydrogen_wt_percent",
    "hydrogen",
    "H2",
    "tobmof",
    "tobMof",
    "TOP200_GLOBAL_H2_RANKED",
    "GLOBAL_H2_RANKED",
]

ROOTS = [
    ROOT / "scripts",
    ROOT / "reports/global_screening",
    ROOT / "calculations/global_screening",
]

def read(p):
    try:
        return p.read_text(errors="ignore")
    except:
        return ""

def hits(text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(k.lower() in low for k in KEYS):
            out.append((n, line.strip()))
    return out

def producer_score(text):
    score = 0

    patterns = [
        r"hydrogen_score\s*=",
        r"hydrogen_wt_percent\s*=",
        r"hydrogen_score.*to_csv",
        r"hydrogen_wt_percent.*to_csv",
        r"hydrogen_score.*append",
        r"hydrogen_wt_percent.*append",
        r"tobmof.*hydrogen",
        r"cif.*hydrogen",
        r"read.*cif",
        r"glob.*cif",
        r"rglob.*cif",
        r"formula",
        r"molecular_weight",
        r"hydrogen.*weight",
    ]

    for p in patterns:
        score += len(re.findall(p, text, re.I))

    return score

files = []

for base in ROOTS:
    if not base.exists():
        continue
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in {
            ".py", ".csv", ".json", ".txt", ".md"
        }:
            files.append(p)

files = sorted(set(files))

print("=" * 70, flush=True)
print("PHASE 24 — TRACE H2 SOURCE", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"TARGET : {TARGET}", flush=True)
print(f"FILES TO SCAN : {len(files)}", flush=True)

results = []

for i, p in enumerate(files, 1):
    if i % 25 == 0:
        print(f"Progression : {i}/{len(files)}", flush=True)

    text = read(p)

    hs = hits(text)

    if not hs:
        continue

    score = producer_score(text)

    results.append({
        "file": str(p),
        "score": score,
        "hit_count": len(hs),
        "hits": [
            {"line": n, "text": line}
            for n, line in hs
        ]
    })

results.sort(
    key=lambda x: (x["score"], x["hit_count"]),
    reverse=True
)

print("\nTOP SOURCES POTENTIELLES", flush=True)
print("-" * 70, flush=True)

for i, r in enumerate(results[:30], 1):
    print(
        f"{i:02d} | SCORE={r['score']:02d} | "
        f"HITS={r['hit_count']:02d} | {r['file']}",
        flush=True
    )

    for h in r["hits"][:4]:
        print(
            f"      L{h['line']} : {h['text'][:180]}",
            flush=True
        )

csv_out = OUT / "phase24_trace_h2_source.csv"
json_out = OUT / "phase24_trace_h2_source.json"
manifest_out = OUT / "phase24_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "rank",
        "file",
        "score",
        "hit_count",
    ])

    for i, r in enumerate(results, 1):
        w.writerow([
            i,
            r["file"],
            r["score"],
            r["hit_count"],
        ])

data = {
    "phase": 24,
    "mode": "ANALYSIS_ONLY",
    "target": str(TARGET),
    "target_exists": TARGET.exists(),
    "files_scanned": len(files),
    "files_with_h2_evidence": len(results),
    "top_sources": results[:30],
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": 24,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "files_scanned": len(files),
    "files_with_h2_evidence": len(results),
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

manifest_out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 24 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"FILES SCANNED       : {len(files)}", flush=True)
print(f"H2 EVIDENCE FILES   : {len(results)}", flush=True)

if results:
    print(f"TOP SOURCE          : {results[0]['file']}", flush=True)
    print(f"TOP SCORE           : {results[0]['score']}", flush=True)
else:
    print("SOURCE H2           : NOT FOUND", flush=True)

print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
