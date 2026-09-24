#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_25_audit_h2_generator"
OUT.mkdir(parents=True, exist_ok=True)

def read(path):
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""

text = read(SOURCE)
lines = text.splitlines()

print("=" * 70, flush=True)
print("PHASE 25 — AUDIT H2 GENERATOR", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"SOURCE : {SOURCE}", flush=True)
print(f"EXISTS : {SOURCE.exists()}", flush=True)
print(f"SIZE   : {len(text)} bytes", flush=True)

patterns = {
    "H2_SCORE": [
        r"hydrogen_score",
        r"h2_score",
        r"score.*hydrogen",
        r"hydrogen.*score",
    ],
    "H2_WEIGHT": [
        r"hydrogen_wt_percent",
        r"h2_wt",
        r"wt_percent",
        r"weight.*hydrogen",
        r"hydrogen.*weight",
    ],
    "CIF": [
        r"\.cif",
        r"glob.*cif",
        r"rglob.*cif",
        r"read.*cif",
        r"cif.*read",
    ],
    "TOBMOF": [
        r"tobmof",
        r"tobMof",
    ],
    "HMOF": [
        r"hMOF",
    ],
    "CSV": [
        r"\.csv",
        r"to_csv",
        r"csv\.reader",
        r"DictReader",
        r"DictWriter",
    ],
    "JSON": [
        r"\.json",
        r"json\.load",
        r"json\.dump",
    ],
    "IMPORT": [
        r"from .* import",
        r"import ",
    ],
    "SUBPROCESS": [
        r"subprocess",
        r"os\.system",
        r"subprocess\.run",
        r"subprocess\.Popen",
    ],
}

hits = []

for category, pats in patterns.items():
    for i, line in enumerate(lines, 1):
        for pat in pats:
            if re.search(pat, line, re.I):
                hits.append({
                    "category": category,
                    "line": i,
                    "text": line.strip()
                })
                break

print("\nRELEVANT LINES", flush=True)
print("-" * 70, flush=True)

for h in hits:
    print(
        f"[{h['category']:<12}] "
        f"L{h['line']:<4} {h['text'][:220]}",
        flush=True
    )

print("\nFUNCTIONS / CLASSES", flush=True)
print("-" * 70, flush=True)

functions = []

for i, line in enumerate(lines, 1):
    m = re.match(r"\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
    if m:
        functions.append({
            "name": m.group(1),
            "line": i
        })
        print(f"L{i:<4} {m.group(1)}()", flush=True)

classes = []

for i, line in enumerate(lines, 1):
    m = re.match(r"\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", line)
    if m:
        classes.append({
            "name": m.group(1),
            "line": i
        })
        print(f"L{i:<4} class {m.group(1)}", flush=True)

print("\nPATHS / FILES REFERENCED", flush=True)
print("-" * 70, flush=True)

paths = set()

path_patterns = [
    r'["\']([^"\']+\.(?:csv|json|cif|out|in|txt))["\']',
    r'Path\s*\(\s*["\']([^"\']+)["\']',
]

for pat in path_patterns:
    for m in re.finditer(pat, text, re.I):
        paths.add(m.group(1))

for p in sorted(paths):
    print(p, flush=True)

print("\nIMPORTED LOCAL MODULES", flush=True)
print("-" * 70, flush=True)

local_imports = []

for line in lines:
    m1 = re.match(r"\s*from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+import", line)
    m2 = re.match(r"\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)", line)

    module = None
    if m1:
        module = m1.group(1)
    elif m2:
        module = m2.group(1)

    if module and not module.startswith((
        "os", "sys", "re", "json", "csv", "pathlib",
        "math", "glob", "shutil", "subprocess",
        "time", "datetime", "typing", "collections",
        "pandas", "numpy"
    )):
        local_imports.append(module)

for x in sorted(set(local_imports)):
    print(x, flush=True)

print("\nPOTENTIAL H2 CALCULATION EXPRESSIONS", flush=True)
print("-" * 70, flush=True)

calc_keywords = [
    "H2",
    "hydrogen",
    "wt",
    "mass",
    "molecular_weight",
    "atomic_weight",
    "composition",
    "formula",
    "weight_percent",
    "capacity",
]

calc_lines = []

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k.lower() in low for k in calc_keywords):
        if any(op in line for op in ["=", "+", "-", "*", "/", "append", "return"]):
            calc_lines.append({
                "line": i,
                "text": line.strip()
            })

for x in calc_lines:
    print(f"L{x['line']:<4} {x['text'][:240]}", flush=True)

csv_out = OUT / "phase25_audit_h2_generator.csv"
json_out = OUT / "phase25_audit_h2_generator.json"
manifest_out = OUT / "phase25_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["category", "line", "text"])

    for h in hits:
        w.writerow([
            h["category"],
            h["line"],
            h["text"]
        ])

result = {
    "phase": 25,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "exists": SOURCE.exists(),
    "size": len(text),
    "relevant_hits": hits,
    "functions": functions,
    "classes": classes,
    "referenced_paths": sorted(paths),
    "local_imports": sorted(set(local_imports)),
    "calculation_lines": calc_lines,
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": 25,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "relevant_lines": len(hits),
    "functions": len(functions),
    "referenced_paths": len(paths),
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

manifest_out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 25 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"FUNCTIONS         : {len(functions)}", flush=True)
print(f"RELEVANT LINES    : {len(hits)}", flush=True)
print(f"REFERENCED PATHS  : {len(paths)}", flush=True)
print(f"LOCAL IMPORTS     : {len(set(local_imports))}", flush=True)
print(f"H2 CALC LINES     : {len(calc_lines)}", flush=True)
print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
