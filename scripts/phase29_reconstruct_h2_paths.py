#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_29_reconstruct_h2_paths"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
lines = text.splitlines()

print("=" * 70, flush=True)
print("PHASE 29 — RECONSTRUCTION H2 PATHS", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

# ------------------------------------------------------------------
# 1. VARIABLES DE CHEMINS
# ------------------------------------------------------------------

assignments = []

assign_patterns = [
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*Path\s*\((.+)\)',
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\'](.+)["\']',
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*f["\'](.+)["\']',
]

for i, line in enumerate(lines, 1):
    for pat in assign_patterns:
        m = re.match(pat, line)
        if m:
            assignments.append({
                "line": i,
                "variable": m.group(1),
                "value": m.group(2),
                "text": line.strip()
            })
            break

print("\n[1/5] PATH VARIABLES", flush=True)
print("-" * 70, flush=True)

for a in assignments:
    if any(k in a["text"].lower() for k in [
        "path", "csv", "json", "h2", "hydrogen",
        "mof", "report", "screen", "cif", "rank"
    ]):
        print(
            f"L{a['line']:<4} {a['variable']} = {a['value']}",
            flush=True
        )

# ------------------------------------------------------------------
# 2. APPELS DE LECTURE
# ------------------------------------------------------------------

read_calls = []

read_patterns = [
    r'\.read_csv\s*\((.+)\)',
    r'\.read_json\s*\((.+)\)',
    r'\.read_text\s*\((.*)\)',
    r'open\s*\((.+)\)',
    r'Path\s*\((.+)\)\.read_text',
    r'\.glob\s*\((.+)\)',
    r'\.rglob\s*\((.+)\)',
]

print("\n[2/5] APPELS DE LECTURE", flush=True)
print("-" * 70, flush=True)

for i, line in enumerate(lines, 1):
    for pat in read_patterns:
        m = re.search(pat, line, re.I)
        if m:
            item = {
                "line": i,
                "call": m.group(0),
                "text": line.strip()
            }
            read_calls.append(item)
            print(
                f"L{i:<4}: {line.strip()}",
                flush=True
            )
            break

# ------------------------------------------------------------------
# 3. VARIABLES H2
# ------------------------------------------------------------------

h2_vars = []

print("\n[3/5] VARIABLES / OBJETS H2", flush=True)
print("-" * 70, flush=True)

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k in low for k in [
        "hydrogen",
        "hydrogen_score",
        "hydrogen_wt_percent",
        "h2",
        "tobmof",
        "hmof"
    ]):
        print(f"L{i:<4}: {line.strip()}", flush=True)

        h2_vars.append({
            "line": i,
            "text": line.strip()
        })

# ------------------------------------------------------------------
# 4. CONSTRUCTION DYNAMIQUE DES CHEMINS
# ------------------------------------------------------------------

print("\n[4/5] CONSTRUCTIONS DYNAMIQUES", flush=True)
print("-" * 70, flush=True)

dynamic = []

for i, line in enumerate(lines, 1):

    if any(x in line for x in [
        " / ",
        "join(",
        "joinpath(",
        "f\"",
        "f'",
        ".format(",
        "% ",
        "str(",
    ]) and any(k in line.lower() for k in [
        "csv",
        "json",
        "cif",
        "h2",
        "hydrogen",
        "mof",
        "report",
        "screen",
        "rank",
        "path",
    ]):
        dynamic.append({
            "line": i,
            "text": line.strip()
        })

        print(
            f"L{i:<4}: {line.strip()}",
            flush=True
        )

# ------------------------------------------------------------------
# 5. RÉSOUDRE LES VARIABLES SIMPLES
# ------------------------------------------------------------------

print("\n[5/5] RESOLUTION DES CHEMINS", flush=True)
print("-" * 70, flush=True)

env = {}

for a in assignments:
    value = a["value"]

    # Nettoyage simple des chaînes
    value = value.strip()

    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        value = value[1:-1]

    # Remplacement de variables déjà connues
    for _ in range(5):
        changed = False

        for var, val in env.items():
            if var in value:
                value2 = value.replace(var, val)
                if value2 != value:
                    value = value2
                    changed = True

        if not changed:
            break

    env[a["variable"]] = value

resolved = []

for var, value in env.items():

    low = value.lower()

    if any(k in low for k in [
        "csv", "json", "cif", "h2", "hydrogen",
        "mof", "report", "screen", "rank"
    ]):
        resolved.append({
            "variable": var,
            "value": value
        })

        print(
            f"{var} -> {value}",
            flush=True
        )

# ------------------------------------------------------------------
# RECHERCHE DES CIBLES CONNUES DANS LE SCRIPT
# ------------------------------------------------------------------

target_refs = []

for i, line in enumerate(lines, 1):
    if any(k.lower() in line.lower() for k in [
        "TOP200_GLOBAL_H2_RANKED",
        "GLOBAL_H2_RANKED",
        "hydrogen_score",
        "hydrogen_wt_percent",
    ]):
        target_refs.append({
            "line": i,
            "text": line.strip()
        })

print("\nREFERENCES H2 PRINCIPALES", flush=True)
print("-" * 70, flush=True)

for x in target_refs:
    print(
        f"L{x['line']}: {x['text']}",
        flush=True
    )

# ------------------------------------------------------------------
# SORTIES
# ------------------------------------------------------------------

csv_out = OUT / "phase29_reconstruct_h2_paths.csv"
json_out = OUT / "phase29_reconstruct_h2_paths.json"
manifest_out = OUT / "phase29_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["type", "line", "variable", "value", "text"])

    for a in assignments:
        w.writerow([
            "assignment",
            a["line"],
            a["variable"],
            a["value"],
            a["text"],
        ])

    for r in read_calls:
        w.writerow([
            "read_call",
            r["line"],
            "",
            "",
            r["text"],
        ])

    for r in dynamic:
        w.writerow([
            "dynamic_path",
            r["line"],
            "",
            "",
            r["text"],
        ])

result = {
    "phase": 29,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "path_assignments": assignments,
    "read_calls": read_calls,
    "h2_references": h2_vars,
    "dynamic_paths": dynamic,
    "resolved_paths": resolved,
    "target_references": target_refs,
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest_out.write_text(
    json.dumps({
        "phase": 29,
        "status": "COMPLETE",
        "mode": "ANALYSIS_ONLY",
        "path_assignments": len(assignments),
        "read_calls": len(read_calls),
        "h2_references": len(h2_vars),
        "dynamic_paths": len(dynamic),
        "resolved_paths": len(resolved),
        "no_script_execution": True,
        "no_qe_calculation": True,
        "no_cif_modification": True,
    }, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 29 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"PATH ASSIGNMENTS : {len(assignments)}", flush=True)
print(f"READ CALLS       : {len(read_calls)}", flush=True)
print(f"H2 REFERENCES    : {len(h2_vars)}", flush=True)
print(f"DYNAMIC PATHS    : {len(dynamic)}", flush=True)
print(f"RESOLVED PATHS   : {len(resolved)}", flush=True)
print(f"TARGET REFS      : {len(target_refs)}", flush=True)

print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
