from pathlib import Path
import ast
import json

ROOT = Path("/home/hk/HydroMatAI")
TARGET = ROOT / "src" / "hydromatai" / "literature.py"

if not TARGET.exists():
    matches = list(ROOT.rglob("literature.py"))
    if matches:
        TARGET = matches[0]

OUTDIR = ROOT / "calculations" / "phase_40_audit_literature_h2"
OUTDIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("PHASE 40 — AUDIT CALCUL DU SCORE H2")
print("-" * 70)
print(f"TARGET : {TARGET}")

if not TARGET.exists():
    print("STATUS : LITERATURE_MODULE_NOT_FOUND")
    raise SystemExit(1)

text = TARGET.read_text(encoding="utf-8")
lines = text.splitlines()

tree = ast.parse(text)

wanted = {
    "import_literature_csv",
    "build_ambient_benchmark",
}

functions = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in wanted:
            functions[node.name] = node

print(f"LINES : {len(lines)}")
print(f"TARGET FUNCTIONS : {len(functions)}")

evidence = []

for name, node in functions.items():
    print()
    print("-" * 70)
    print(f"FUNCTION : {name}")
    print(f"LINES    : {node.lineno}-{node.end_lineno}")
    print("-" * 70)

    for i in range(node.lineno - 1, node.end_lineno):
        line = lines[i]
        print(f"L{i+1}: {line}")

        low = line.lower()

        if any(k in low for k in [
            "score",
            "h2",
            "hydrogen",
            "uptake",
            "temperature",
            "pressure",
            "ambient",
            "weight",
            "normalize",
            "threshold",
            "benchmark",
            "confidence",
        ]):
            evidence.append({
                "function": name,
                "line": i + 1,
                "text": line,
            })

result = {
    "phase": 40,
    "target": str(TARGET),
    "functions_found": list(functions.keys()),
    "evidence": evidence,
    "status": "COMPLETE",
}

json_path = OUTDIR / "phase40_audit.json"
manifest_path = OUTDIR / "phase40_manifest.json"

json_path.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

manifest_path.write_text(
    json.dumps(
        {
            "phase": 40,
            "mode": "ANALYSIS_ONLY",
            "target": str(TARGET),
            "status": "COMPLETE",
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print()
print("=" * 70)
print("PHASE 40 STATUS : COMPLETE")
print(f"JSON     : {json_path}")
print(f"MANIFEST : {manifest_path}")
print("=" * 70)
