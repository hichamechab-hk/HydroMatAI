#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_26_trace_h2_dependencies"
OUT.mkdir(parents=True, exist_ok=True)

def read(p):
    try:
        return p.read_text(errors="ignore")
    except:
        return ""

text = read(SOURCE)
lines = text.splitlines()

print("=" * 70, flush=True)
print("PHASE 26 — TRACE H2 DEPENDENCIES", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

imports = []

for line in lines:
    m = re.match(r"\s*from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+import", line)
    if m:
        imports.append(m.group(1))

    m = re.match(r"\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)", line)
    if m:
        imports.append(m.group(1))

imports = sorted(set(imports))

print("\n[1/4] IMPORTS", flush=True)
for x in imports:
    print("  ", x, flush=True)

print("\n[2/4] RECHERCHE DES MODULES LOCAUX", flush=True)

modules = {}

for mod in imports:
    if mod in {
        "os","sys","re","json","csv","math","glob","shutil",
        "subprocess","time","datetime","typing","collections",
        "pandas","numpy","pathlib"
    }:
        continue

    candidates = [
        ROOT / "scripts" / f"{mod}.py",
        ROOT / f"{mod}.py",
    ]

    found = None

    for c in candidates:
        if c.exists():
            found = c
            break

    modules[mod] = str(found) if found else None

    print(
        f"  {mod} -> {found if found else 'NOT_FOUND'}",
        flush=True
    )

print("\n[3/4] ANALYSE DES DEPENDANCES", flush=True)

dependency_records = []

for mod, pathstr in modules.items():

    if not pathstr:
        continue

    path = Path(pathstr)
    src = read(path)
    src_lines = src.splitlines()

    print(f"\n--- {path.name} ---", flush=True)

    relevant = []

    keys = [
        "hydrogen",
        "hydrogen_score",
        "hydrogen_wt_percent",
        "h2",
        "tobmof",
        "tobMof",
        "hmof",
        "cif",
        "formula",
        "weight",
        "mass",
        "capacity",
        "to_csv",
        "csv",
        "json",
        "glob",
        "rglob",
        "read_csv",
        "read_json",
    ]

    for i, line in enumerate(src_lines, 1):
        if any(k.lower() in line.lower() for k in keys):
            relevant.append({
                "line": i,
                "text": line.strip()
            })

    for r in relevant:
        print(
            f"  L{r['line']}: {r['text'][:220]}",
            flush=True
        )

    dependency_records.append({
        "module": mod,
        "file": str(path),
        "relevant": relevant,
    })

print("\n[4/4] LIENS ENTRE run_top5_complete.py ET DEPENDANCES", flush=True)

source_refs = []

for i, line in enumerate(lines, 1):

    stripped = line.strip()

    if (
        "hydrogen" in stripped.lower()
        or "h2" in stripped.lower()
        or "tobmof" in stripped.lower()
        or "cif" in stripped.lower()
        or "formula" in stripped.lower()
        or "weight" in stripped.lower()
        or "mass" in stripped.lower()
    ):
        source_refs.append({
            "line": i,
            "text": stripped
        })

for r in source_refs:
    print(
        f"  L{r['line']}: {r['text'][:240]}",
        flush=True
    )

csv_out = OUT / "phase26_trace_h2_dependencies.csv"
json_out = OUT / "phase26_trace_h2_dependencies.json"
manifest_out = OUT / "phase26_manifest.json"

rows = []

for d in dependency_records:
    for r in d["relevant"]:
        rows.append([
            d["module"],
            d["file"],
            r["line"],
            r["text"],
        ])

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["module", "file", "line", "text"])
    w.writerows(rows)

result = {
    "phase": 26,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "imports": imports,
    "local_modules": modules,
    "dependency_records": dependency_records,
    "source_references": source_refs,
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
    "phase": 26,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "imports": len(imports),
    "local_modules_found": sum(
        1 for x in modules.values() if x
    ),
    "dependency_files": len(dependency_records),
    "source_references": len(source_refs),
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

manifest_out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 26 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"IMPORTS           : {len(imports)}", flush=True)
print(
    f"LOCAL MODULES     : {sum(1 for x in modules.values() if x)}",
    flush=True
)
print(f"DEPENDENCY FILES  : {len(dependency_records)}", flush=True)
print(f"SOURCE REFERENCES : {len(source_refs)}", flush=True)

print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
