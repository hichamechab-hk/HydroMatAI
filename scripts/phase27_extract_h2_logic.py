#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_27_extract_h2_logic"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
lines = text.splitlines()

KEYS = [
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
    "to_csv",
    "read_csv",
    "glob",
    "rglob",
]

matches = []

for i, line in enumerate(lines, 1):
    if any(k.lower() in line.lower() for k in KEYS):
        matches.append(i)

matches = sorted(set(matches))

print("=" * 70, flush=True)
print("PHASE 27 — EXTRACTION LOGIQUE H2", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"SOURCE : {SOURCE}", flush=True)
print(f"LINES  : {len(lines)}", flush=True)
print(f"MATCHES: {len(matches)}", flush=True)

print("\nCONTEXTE EXACT DES REFERENCES H2", flush=True)
print("-" * 70, flush=True)

contexts = []

for line_no in matches:
    start = max(1, line_no - 3)
    end = min(len(lines), line_no + 3)

    print(f"\n--- LIGNE CENTRALE {line_no} ---", flush=True)

    block = []

    for n in range(start, end + 1):
        marker = ">>>" if n == line_no else "   "
        line = lines[n - 1]

        print(
            f"{marker} L{n:<5}: {line}",
            flush=True
        )

        block.append({
            "line": n,
            "central": n == line_no,
            "text": line
        })

    contexts.append({
        "central_line": line_no,
        "context": block
    })

print("\nSTRUCTURES DE SORTIE", flush=True)
print("-" * 70, flush=True)

output_patterns = [
    r"\.to_csv",
    r"csv\.writer",
    r"DictWriter",
    r"TOP200_GLOBAL_H2_RANKED",
    r"GLOBAL_H2_RANKED",
    r"hydrogen_score",
    r"hydrogen_wt_percent",
]

outputs = []

for i, line in enumerate(lines, 1):
    if any(re.search(p, line, re.I) for p in output_patterns):
        outputs.append({
            "line": i,
            "text": line.strip()
        })
        print(
            f"L{i:<5}: {line.strip()}",
            flush=True
        )

print("\nLECTURE DES CHEMINS POTENTIELS", flush=True)
print("-" * 70, flush=True)

paths = []

for i, line in enumerate(lines, 1):
    found = re.findall(
        r'["\']([^"\']+\.(?:csv|json|cif|txt|out))["\']',
        line,
        re.I
    )

    for p in found:
        paths.append({
            "line": i,
            "path": p
        })
        print(
            f"L{i:<5}: {p}",
            flush=True
        )

csv_out = OUT / "phase27_extract_h2_logic.csv"
json_out = OUT / "phase27_extract_h2_logic.json"
manifest_out = OUT / "phase27_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["central_line", "line", "central", "text"])

    for c in contexts:
        for x in c["context"]:
            w.writerow([
                c["central_line"],
                x["line"],
                x["central"],
                x["text"],
            ])

result = {
    "phase": 27,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "source_exists": SOURCE.exists(),
    "source_lines": len(lines),
    "reference_count": len(matches),
    "contexts": contexts,
    "outputs": outputs,
    "paths": paths,
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

with manifest_out.open("w", encoding="utf-8") as f:
    json.dump({
        "phase": 27,
        "status": "COMPLETE",
        "mode": "ANALYSIS_ONLY",
        "source": str(SOURCE),
        "reference_count": len(matches),
        "no_script_execution": True,
        "no_qe_calculation": True,
        "no_cif_modification": True,
    }, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 70, flush=True)
print("PHASE 27 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"SOURCE LINES      : {len(lines)}", flush=True)
print(f"H2 REFERENCES     : {len(matches)}", flush=True)
print(f"OUTPUT REFERENCES: {len(outputs)}", flush=True)
print(f"PATH REFERENCES  : {len(paths)}", flush=True)
print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
