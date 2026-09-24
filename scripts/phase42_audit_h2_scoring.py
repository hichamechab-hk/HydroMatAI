from pathlib import Path
import ast
import json

ROOT = Path("/home/hk/HydroMatAI")

TARGETS = {
    "importer": ROOT / "src/hydromatai/literature/importer.py",
    "ambient": ROOT / "src/hydromatai/literature/ambient_benchmark.py",
    "workflow": ROOT / "src/hydromatai/scientific/workflow.py",
}

OUTDIR = ROOT / "calculations" / "phase_42_audit_h2_scoring"
OUTDIR.mkdir(parents=True, exist_ok=True)

KEYWORDS = (
    "score",
    "h2",
    "hydrogen",
    "uptake",
    "temperature",
    "pressure",
    "ambient",
    "benchmark",
    "confidence",
    "weight",
    "normalize",
    "threshold",
    "objective",
)

print("=" * 70)
print("PHASE 42 — AUDIT COMPLET DU SCORING H2")
print("=" * 70)

result = {
    "phase": 42,
    "mode": "ANALYSIS_ONLY",
    "files": {},
}

for label, path in TARGETS.items():

    print()
    print("-" * 70)
    print(f"[{label.upper()}]")
    print(f"FILE : {path}")
    print("-" * 70)

    if not path.exists():
        print("STATUS : NOT_FOUND")
        result["files"][label] = {
            "path": str(path),
            "status": "NOT_FOUND",
        }
        continue

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    tree = ast.parse(text)

    functions = []
    classes = []
    relevant = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno,
            })

        elif isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno,
            })

    for i, line in enumerate(lines, 1):
        low = line.lower()

        if any(k in low for k in KEYWORDS):
            relevant.append({
                "line": i,
                "text": line,
            })

    print(f"LINES       : {len(lines)}")
    print(f"FUNCTIONS   : {len(functions)}")
    print(f"CLASSES     : {len(classes)}")
    print(f"RELEVANT    : {len(relevant)}")

    print()
    print("FUNCTIONS / CLASSES")
    print("-" * 70)

    for x in functions:
        print(
            f"FUNCTION L{x['line']}-L{x['end_line']} : "
            f"{x['name']}"
        )

    for x in classes:
        print(
            f"CLASS    L{x['line']}-L{x['end_line']} : "
            f"{x['name']}"
        )

    print()
    print("RELEVANT CODE")
    print("-" * 70)

    for x in relevant:
        print(f"L{x['line']}: {x['text']}")

    result["files"][label] = {
        "path": str(path),
        "status": "FOUND",
        "lines": len(lines),
        "functions": functions,
        "classes": classes,
        "relevant": relevant,
    }

result["status"] = "COMPLETE"

json_path = OUTDIR / "phase42_h2_scoring.json"
manifest_path = OUTDIR / "phase42_manifest.json"

json_path.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

manifest_path.write_text(
    json.dumps(
        {
            "phase": 42,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Trace exact H2 screening and scientific scoring formulas",
            "no_qe": True,
            "no_cif_modification": True,
            "targets": {
                k: str(v) for k, v in TARGETS.items()
            },
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print()
print("=" * 70)
print("PHASE 42 STATUS : COMPLETE")
print(f"JSON     : {json_path}")
print(f"MANIFEST : {manifest_path}")
print("=" * 70)
