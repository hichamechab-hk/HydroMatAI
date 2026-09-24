#!/usr/bin/env python3

from pathlib import Path
import ast
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_32_extract_h2_io"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
tree = ast.parse(text)

rows = []

def source(node):
    try:
        return ast.get_source_segment(text, node)
    except Exception:
        return None

for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        code = source(node)
        func = source(node.func)

        if not func:
            continue

        # Toutes les opérations susceptibles de lire/écrire
        # ou transmettre une donnée/fichier.
        keywords = [
            "open",
            "read",
            "load",
            "read_csv",
            "read_json",
            "glob",
            "rglob",
            "listdir",
            "exists",
            "path",
            "write",
            "dump",
            "to_csv",
            "to_json",
            "save",
            "copy",
            "rename",
            "move",
        ]

        if any(k.lower() in func.lower() for k in keywords):

            rows.append({
                "type": "CALL",
                "line": node.lineno,
                "function": func,
                "code": code,
                "args": [
                    source(a) for a in node.args
                ],
                "keywords": [
                    source(k) for k in node.keywords
                ],
            })


    elif isinstance(node, ast.Assign):

        code = source(node)

        if code and any(k in code.lower() for k in [
            "path",
            "file",
            "csv",
            "json",
            "h2",
            "hydrogen",
            "score",
            "rank",
            "mof",
        ]):

            targets = []

            for target in node.targets:
                t = source(target)
                if t:
                    targets.append(t)

            rows.append({
                "type": "ASSIGNMENT",
                "line": node.lineno,
                "function": None,
                "code": code,
                "targets": targets,
            })


rows.sort(key=lambda x: x["line"])

print("=" * 70)
print("PHASE 32 — H2 I/O EXACT TRACE")
print("-" * 70)
print("MODE             : ANALYSIS_ONLY")
print("SCRIPT EXECUTED  : NO")
print("QE CALCULATION   : NO")
print("CIF MODIFICATION : NO")
print("=" * 70)

print(f"OPERATIONS FOUND : {len(rows)}")

for r in rows:

    print("\n" + "-" * 70)
    print(
        f"{r['type']} — LINE {r['line']}"
    )

    if r.get("function"):
        print(
            "FUNCTION :",
            r["function"]
        )

    print(
        "CODE     :",
        r["code"]
    )

    if r.get("args"):
        print("ARGS     :")
        for a in r["args"]:
            print("  ", a)

    if r.get("keywords"):
        print("KEYWORDS :")
        for k in r["keywords"]:
            print("  ", k)

    if r.get("targets"):
        print("TARGETS  :")
        for t in r["targets"]:
            print("  ", t)

csv_out = OUT / "phase32_extract_h2_io.csv"
json_out = OUT / "phase32_extract_h2_io.json"
manifest_out = OUT / "phase32_manifest.json"

with csv_out.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    w = csv.writer(f)

    w.writerow([
        "type",
        "line",
        "function",
        "code",
    ])

    for r in rows:

        w.writerow([
            r.get("type"),
            r.get("line"),
            r.get("function"),
            r.get("code"),
        ])


json_out.write_text(
    json.dumps(
        {
            "phase": 32,
            "mode": "ANALYSIS_ONLY",
            "source": str(SOURCE),
            "operations": rows,
            "no_execution": True,
            "no_qe": True,
            "no_cif_modification": True,
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

manifest_out.write_text(
    json.dumps(
        {
            "phase": 32,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "operations": len(rows),
            "no_execution": True,
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("\n" + "=" * 70)
print("PHASE 32 — RESULT")
print("-" * 70)
print(f"OPERATIONS FOUND : {len(rows)}")
print()
print("CSV     :", csv_out)
print("JSON    :", json_out)
print("MANIFEST:", manifest_out)
print("=" * 70)
