from pathlib import Path
import ast
import json

ROOT = Path("/home/hk/HydroMatAI")
TARGET = ROOT / "src/hydromatai/literature/objective_score.py"

print("=" * 70)
print("PHASE 43 — FORMULE EXACTE OBJECTIVE SCORE")
print("-" * 70)
print(f"TARGET : {TARGET}")

if not TARGET.exists():
    matches = list(ROOT.rglob("objective_score.py"))
    matches = [
        p for p in matches
        if ".venv" not in p.parts
        and ".git" not in p.parts
    ]

    if matches:
        TARGET = matches[0]

if not TARGET.exists():
    print("STATUS : OBJECTIVE_SCORE_NOT_FOUND")
    raise SystemExit(1)

text = TARGET.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()
tree = ast.parse(text)

print(f"LINES : {len(lines)}")

print()
print("-" * 70)
print("DEFINITIONS")
print("-" * 70)

definitions = []

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        definitions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
        })
    elif isinstance(node, ast.ClassDef):
        definitions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "class": True,
        })

for d in sorted(definitions, key=lambda x: x["line"]):
    kind = "CLASS" if d.get("class") else "FUNCTION"
    print(
        f"{kind} L{d['line']}-L{d['end_line']} : "
        f"{d['name']}"
    )

keywords = (
    "score",
    "screening",
    "confidence",
    "ambient",
    "h2",
    "hydrogen",
    "uptake",
    "temperature",
    "pressure",
    "weight",
    "normalize",
    "threshold",
    "objective",
)

print()
print("-" * 70)
print("SCORING CODE")
print("-" * 70)

evidence = []

for i, line in enumerate(lines, 1):
    low = line.lower()

    if any(k in low for k in keywords):
        print(f"L{i}: {line}")
        evidence.append({
            "line": i,
            "text": line,
        })

print()
print("-" * 70)
print("CALCULATE_OBJECTIVE_SCORE")
print("-" * 70)

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name == "calculate_objective_score":
            print(
                f"FUNCTION L{node.lineno}-L{node.end_lineno}"
            )

            for i in range(node.lineno - 1, node.end_lineno):
                print(f"L{i+1}: {lines[i]}")

result = {
    "phase": 43,
    "mode": "ANALYSIS_ONLY",
    "target": str(TARGET),
    "lines": len(lines),
    "definitions": definitions,
    "scoring_evidence": evidence,
    "status": "COMPLETE",
}

OUTDIR = ROOT / "calculations/phase_43_objective_score"
OUTDIR.mkdir(parents=True, exist_ok=True)

json_path = OUTDIR / "phase43_objective_score.json"
manifest_path = OUTDIR / "phase43_manifest.json"

json_path.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

manifest_path.write_text(
    json.dumps(
        {
            "phase": 43,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "no_qe": True,
            "no_cif_modification": True,
            "target": str(TARGET),
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print()
print("=" * 70)
print("PHASE 43 STATUS : COMPLETE")
print(f"JSON     : {json_path}")
print(f"MANIFEST : {manifest_path}")
print("=" * 70)
