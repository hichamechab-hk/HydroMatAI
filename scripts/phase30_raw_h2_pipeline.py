#!/usr/bin/env python3

from pathlib import Path
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_30_raw_h2_pipeline"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
lines = text.splitlines()

KEYWORDS = [
    "hydrogen",
    "hydrogen_score",
    "hydrogen_wt_percent",
    "h2",
    "tobmof",
    "tobMof",
    "hmof",
    "cif",
    "formula",
    "mass",
    "weight",
    "capacity",
    "csv",
    "json",
    "path",
    "glob",
    "read",
    "load",
    "open",
    "write",
    "save",
    "append",
]

matched = []

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k.lower() in low for k in KEYWORDS):
        matched.append(i)

matched = sorted(set(matched))

print("=" * 70, flush=True)
print("PHASE 30 — RAW H2 PIPELINE EXTRACTION", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"SOURCE : {SOURCE}", flush=True)
print(f"TOTAL LINES : {len(lines)}", flush=True)
print(f"MATCHED LINES: {len(matched)}", flush=True)

print("\nCODE SOURCE — LIGNES H2 / FICHIERS", flush=True)
print("-" * 70, flush=True)

blocks = []
seen = set()

for line_no in matched:

    start = max(1, line_no - 5)
    end = min(len(lines), line_no + 5)

    # éviter les blocs presque identiques
    key = (start, end)

    if key in seen:
        continue

    seen.add(key)

    print(
        f"\n### BLOC AUTOUR DE L{line_no}",
        flush=True
    )

    block = []

    for n in range(start, end + 1):
        marker = ">>>" if n == line_no else "   "
        line = lines[n - 1]

        print(
            f"{marker} {n:04d} | {line}",
            flush=True
        )

        block.append({
            "line": n,
            "central": n == line_no,
            "text": line
        })

    blocks.append({
        "central_line": line_no,
        "start": start,
        "end": end,
        "lines": block
    })

print("\n" + "=" * 70, flush=True)
print("CODE COMPLET — FONCTIONS", flush=True)
print("-" * 70, flush=True)

functions = []

for i, line in enumerate(lines, 1):
    stripped = line.strip()

    if (
        stripped.startswith("def ")
        or stripped.startswith("async def ")
    ):
        functions.append({
            "line": i,
            "text": line
        })

        print(
            f"{i:04d} | {line}",
            flush=True
        )

print("\n" + "=" * 70, flush=True)
print("ASSIGNATIONS", flush=True)
print("-" * 70, flush=True)

assignments = []

for i, line in enumerate(lines, 1):

    if "=" in line and not line.strip().startswith("#"):

        left, right = line.split("=", 1)

        if (
            any(k.lower() in line.lower() for k in [
                "path",
                "csv",
                "json",
                "cif",
                "h2",
                "hydrogen",
                "mof",
                "report",
                "screen",
                "rank",
                "score",
                "weight",
                "mass",
                "capacity",
            ])
        ):
            assignments.append({
                "line": i,
                "text": line
            })

            print(
                f"{i:04d} | {line}",
                flush=True
            )

print("\n" + "=" * 70, flush=True)
print("APPELS / OPERATIONS FICHIERS", flush=True)
print("-" * 70, flush=True)

file_ops = []

operations = [
    "open(",
    ".read(",
    ".read_text(",
    ".read_bytes(",
    ".read_csv(",
    ".read_json(",
    ".to_csv(",
    ".to_json(",
    ".write_text(",
    ".write_bytes(",
    ".glob(",
    ".rglob(",
    "json.load(",
    "json.dump(",
    "csv.reader(",
    "csv.writer(",
    "shutil.",
]

for i, line in enumerate(lines, 1):

    if any(op in line for op in operations):

        file_ops.append({
            "line": i,
            "text": line
        })

        print(
            f"{i:04d} | {line}",
            flush=True
        )

csv_out = OUT / "phase30_raw_h2_pipeline.csv"
json_out = OUT / "phase30_raw_h2_pipeline.json"
manifest_out = OUT / "phase30_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "type",
        "line",
        "text"
    ])

    for x in assignments:
        w.writerow([
            "assignment",
            x["line"],
            x["text"]
        ])

    for x in file_ops:
        w.writerow([
            "file_operation",
            x["line"],
            x["text"]
        ])

data = {
    "phase": 30,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "total_lines": len(lines),
    "matched_lines": len(matched),
    "blocks": blocks,
    "functions": functions,
    "assignments": assignments,
    "file_operations": file_ops,
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest_out.write_text(
    json.dumps({
        "phase": 30,
        "status": "COMPLETE",
        "mode": "ANALYSIS_ONLY",
        "source": str(SOURCE),
        "total_lines": len(lines),
        "matched_lines": len(matched),
        "functions": len(functions),
        "assignments": len(assignments),
        "file_operations": len(file_ops),
        "no_script_execution": True,
        "no_qe_calculation": True,
        "no_cif_modification": True,
    }, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 30 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"TOTAL LINES       : {len(lines)}", flush=True)
print(f"MATCHED LINES     : {len(matched)}", flush=True)
print(f"FUNCTIONS         : {len(functions)}", flush=True)
print(f"ASSIGNMENTS       : {len(assignments)}", flush=True)
print(f"FILE OPERATIONS   : {len(file_ops)}", flush=True)
print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
