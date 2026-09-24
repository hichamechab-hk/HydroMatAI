#!/usr/bin/env python3

from pathlib import Path
import ast
import json
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_dft_h2_priority.py"

OUT = ROOT / "calculations/phase_38_audit_run_dft_h2_priority"
OUT.mkdir(parents=True, exist_ok=True)

text = SOURCE.read_text(errors="ignore")
lines = text.splitlines()
tree = ast.parse(text)

print("=" * 70)
print("PHASE 38 — AUDIT PRODUCTEUR H2")
print("-" * 70)
print("SOURCE :", SOURCE)
print("MODE   : ANALYSIS_ONLY")
print("EXECUTION : NO")
print("QE : NO")
print("CIF MODIFICATION : NO")
print("=" * 70)

print()
print("TOTAL LINES :", len(lines))

# ------------------------------------------------------------
# 1. IMPORTS
# ------------------------------------------------------------

print()
print("=" * 70)
print("IMPORTS")
print("-" * 70)

imports = []

for node in ast.walk(tree):

    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.append({
                "line": node.lineno,
                "name": alias.name,
                "type": "import",
            })
            print(
                f"L{node.lineno}: import {alias.name}"
            )

    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        names = ", ".join(
            a.name for a in node.names
        )

        imports.append({
            "line": node.lineno,
            "name": module,
            "from": names,
            "type": "from",
        })

        print(
            f"L{node.lineno}: from {module} import {names}"
        )

# ------------------------------------------------------------
# 2. FONCTIONS
# ------------------------------------------------------------

print()
print("=" * 70)
print("FUNCTIONS")
print("-" * 70)

functions = []

for node in tree.body:

    if isinstance(node, ast.FunctionDef):

        functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(
                node,
                "end_lineno",
                None
            ),
        })

        print(
            f"{node.name}() "
            f"L{node.lineno}-L{getattr(node,'end_lineno', '?')}"
        )

# ------------------------------------------------------------
# 3. H2 / SCORE / INPUT / OUTPUT
# ------------------------------------------------------------

keywords = [
    "h2",
    "hydrogen",
    "score",
    "weight",
    "capacity",
    "wt_percent",
    "material",
    "mof",
    "cif",
    "csv",
    "json",
    "input",
    "output",
    "rank",
    "priority",
]

matched = []

print()
print("=" * 70)
print("LIGNES CRITIQUES")
print("-" * 70)

for i, line in enumerate(lines, 1):

    low = line.lower()

    if any(k in low for k in keywords):

        matched.append({
            "line": i,
            "text": line,
        })

        print(f"L{i}: {line}")

# ------------------------------------------------------------
# 4. APPELS DE FONCTIONS
# ------------------------------------------------------------

print()
print("=" * 70)
print("CALLS")
print("-" * 70)

calls = []

for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        func = ""

        if isinstance(node.func, ast.Name):
            func = node.func.id

        elif isinstance(node.func, ast.Attribute):
            func = node.func.attr

        if func:

            item = {
                "line": node.lineno,
                "function": func,
                "code": ast.get_source_segment(
                    text,
                    node
                ),
            }

            calls.append(item)

            print(
                f"L{node.lineno}: {func}()"
            )

# ------------------------------------------------------------
# 5. ASSIGNATIONS
# ------------------------------------------------------------

print()
print("=" * 70)
print("ASSIGNMENTS")
print("-" * 70)

assignments = []

for node in ast.walk(tree):

    if isinstance(node, ast.Assign):

        code = ast.get_source_segment(
            text,
            node
        )

        if code:

            item = {
                "line": node.lineno,
                "code": code,
            }

            assignments.append(item)

            print(
                f"L{node.lineno}: {code}"
            )

# ------------------------------------------------------------
# 6. OPERATIONS FICHIERS
# ------------------------------------------------------------

print()
print("=" * 70)
print("FILE OPERATIONS")
print("-" * 70)

file_ops = []

file_keywords = [
    "open",
    "read_csv",
    "read_json",
    "to_csv",
    "write",
    "writerow",
    "writerows",
    "glob",
    "rglob",
    "listdir",
]

for node in ast.walk(tree):

    if isinstance(node, ast.Call):

        func = ""

        if isinstance(node.func, ast.Name):
            func = node.func.id

        elif isinstance(node.func, ast.Attribute):
            func = node.func.attr

        if any(
            k.lower() in func.lower()
            for k in file_keywords
        ):

            code = ast.get_source_segment(
                text,
                node
            )

            file_ops.append({
                "line": node.lineno,
                "function": func,
                "code": code,
            })

            print(
                f"L{node.lineno}: {code}"
            )

# ------------------------------------------------------------
# 7. LIGNES AVEC FORMULES NUMERIQUES
# ------------------------------------------------------------

print()
print("=" * 70)
print("FORMULES / CALCULS POTENTIELS")
print("-" * 70)

formula_lines = []

for i, line in enumerate(lines, 1):

    low = line.lower()

    if any(k in low for k in [
        "score",
        "weight",
        "capacity",
        "mass",
        "percent",
        "hydrogen",
        "h2",
    ]):

        if any(op in line for op in [
            "+",
            "-",
            "*",
            "/",
            "**",
            "max(",
            "min(",
            "sum(",
        ]):

            formula_lines.append({
                "line": i,
                "text": line,
            })

            print(f"L{i}: {line}")

# ------------------------------------------------------------
# 8. CONTEXTE AUTOUR DES FORMULES
# ------------------------------------------------------------

print()
print("=" * 70)
print("CONTEXTE FORMULES")
print("-" * 70)

for item in formula_lines:

    n = item["line"]

    print()
    print(
        f"--- autour de L{n} ---"
    )

    for j in range(
        max(1, n - 3),
        min(len(lines), n + 3) + 1
    ):

        print(
            f"L{j}: {lines[j-1]}"
        )

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

result = {
    "phase": 38,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "total_lines": len(lines),
    "imports": imports,
    "functions": functions,
    "matched_lines": matched,
    "calls": calls,
    "assignments": assignments,
    "file_operations": file_ops,
    "formula_lines": formula_lines,
    "no_execution": True,
    "no_qe": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out = OUT / "phase38_audit.json"
manifest_out = OUT / "phase38_manifest.json"

json_out.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

manifest_out.write_text(
    json.dumps(
        {
            "phase": 38,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "source": str(SOURCE),
            "total_lines": len(lines),
            "imports": len(imports),
            "functions": len(functions),
            "matched_lines": len(matched),
            "calls": len(calls),
            "assignments": len(assignments),
            "file_operations": len(file_ops),
            "formula_lines": len(formula_lines),
            "no_execution": True,
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("PHASE 38 — RESULT")
print("-" * 70)
print("IMPORTS          :", len(imports))
print("FUNCTIONS        :", len(functions))
print("MATCHED LINES    :", len(matched))
print("CALLS            :", len(calls))
print("ASSIGNMENTS      :", len(assignments))
print("FILE OPERATIONS  :", len(file_ops))
print("FORMULA LINES    :", len(formula_lines))
print()
print("JSON     :", json_out)
print("MANIFEST :", manifest_out)
print("=" * 70)
