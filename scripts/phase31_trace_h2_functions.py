#!/usr/bin/env python3

from pathlib import Path
import ast
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_31_trace_h2_functions"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
tree = ast.parse(text)

functions = {}

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        functions[node.name] = node

print("=" * 70, flush=True)
print("PHASE 31 — TRACE H2 FUNCTIONS", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"FUNCTIONS FOUND : {len(functions)}", flush=True)

records = []

for name, node in functions.items():

    calls = []
    strings = []
    variables = []
    returns = []

    for child in ast.walk(node):

        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)

        elif isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                value = child.value

                if any(k.lower() in value.lower() for k in [
                    "h2",
                    "hydrogen",
                    "mof",
                    "cif",
                    "csv",
                    "json",
                    "score",
                    "weight",
                    "mass",
                    "capacity",
                    "path",
                ]):
                    strings.append({
                        "line": getattr(child, "lineno", None),
                        "value": value
                    })

        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    variables.append({
                        "line": child.lineno,
                        "name": target.id,
                        "code": ast.get_source_segment(text, child)
                    })

        elif isinstance(child, ast.Return):
            returns.append({
                "line": child.lineno,
                "code": ast.get_source_segment(text, child)
            })

    calls = sorted(set(calls))

    print("\n" + "-" * 70, flush=True)
    print(
        f"FUNCTION : {name}()  [L{node.lineno}]",
        flush=True
    )

    print("CALLS:", flush=True)
    for c in calls:
        print(f"  -> {c}()", flush=True)

    if strings:
        print("H2/FILE STRINGS:", flush=True)
        for s in strings:
            print(
                f"  L{s['line']}: {s['value']}",
                flush=True
            )

    if variables:
        print("VARIABLES:", flush=True)
        for v in variables:
            code = (v["code"] or "").replace("\n", " ")
            if any(k in code.lower() for k in [
                "h2",
                "hydrogen",
                "mof",
                "cif",
                "csv",
                "json",
                "score",
                "weight",
                "mass",
                "capacity",
                "path",
            ]):
                print(
                    f"  L{v['line']}: {code[:220]}",
                    flush=True
                )

    if returns:
        print("RETURNS:", flush=True)
        for r in returns:
            print(
                f"  L{r['line']}: {r['code']}",
                flush=True
            )

    records.append({
        "function": name,
        "line": node.lineno,
        "calls": calls,
        "strings": strings,
        "variables": variables,
        "returns": returns,
    })

print("\n" + "=" * 70, flush=True)
print("CALL GRAPH INTERNE", flush=True)
print("-" * 70, flush=True)

for r in records:
    internal = [
        c for c in r["calls"]
        if c in functions
    ]

    if internal:
        print(
            f"{r['function']} -> {', '.join(internal)}",
            flush=True
        )

# Cherche aussi les fonctions importées/appelées qui ressemblent
# à une source H2.
interesting_external = set()

for r in records:
    for c in r["calls"]:
        if c not in functions and any(k in c.lower() for k in [
            "h2",
            "hydrogen",
            "cif",
            "mof",
            "score",
            "capacity",
            "weight",
            "mass",
            "formula",
        ]):
            interesting_external.add(c)

print("\nAPPELS EXTERNES POTENTIELLEMENT H2", flush=True)
print("-" * 70, flush=True)

for c in sorted(interesting_external):
    print(c, flush=True)

csv_out = OUT / "phase31_trace_h2_functions.csv"
json_out = OUT / "phase31_trace_h2_functions.json"
manifest_out = OUT / "phase31_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "function",
        "line",
        "calls",
        "h2_file_strings",
    ])

    for r in records:
        w.writerow([
            r["function"],
            r["line"],
            ";".join(r["calls"]),
            ";".join(
                x["value"] for x in r["strings"]
            ),
        ])

result = {
    "phase": 31,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "functions": records,
    "interesting_external_calls": sorted(
        interesting_external
    ),
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
        "phase": 31,
        "status": "COMPLETE",
        "mode": "ANALYSIS_ONLY",
        "source": str(SOURCE),
        "functions": len(functions),
        "interesting_external_calls": len(
            interesting_external
        ),
        "no_script_execution": True,
        "no_qe_calculation": True,
        "no_cif_modification": True,
    }, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 31 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"FUNCTIONS         : {len(functions)}", flush=True)
print(
    f"EXTERNAL H2 CALLS : {len(interesting_external)}",
    flush=True
)
print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
