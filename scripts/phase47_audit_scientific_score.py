from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
WORKFLOW = ROOT / "src" / "hydromatai" / "scientific" / "workflow.py"
OBJECTIVE = ROOT / "src" / "hydromatai" / "literature" / "objective_score.py"

OUTDIR = ROOT / "calculations" / "phase_47_scientific_score_audit"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase47_scientific_score_audit.csv"
JSON_OUT = OUTDIR / "phase47_scientific_score_audit.json"
MANIFEST = OUTDIR / "phase47_manifest.json"

print("=" * 70)
print("PHASE 47 — AUDIT DU SCIENTIFIC SCORE")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("QE   : NON")
print("CIF  : NON MODIFIE")
print("=" * 70)

if not INPUT.exists():
    print("STATUS : INPUT_NOT_FOUND")
    raise SystemExit(1)

with INPUT.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"\nMATERIAUX : {len(rows)}")

scientific_values = {}

for row in rows:
    material = row.get("material", "")
    value = row.get("scientific_score", "")
    scientific_values.setdefault(value, []).append(material)

print("\nDISTRIBUTION SCIENTIFIC SCORE")
print("-" * 70)

for value, materials in sorted(
    scientific_values.items(),
    key=lambda x: float(x[0]) if x[0] else -1,
    reverse=True,
):
    print(
        f"score={value:<10} "
        f"count={len(materials):2d} "
        f"materials={', '.join(materials)}"
    )

print("\nMATERIAUX AVEC SCIENTIFIC SCORE = 0.5000")
print("-" * 70)

for material in scientific_values.get("0.5000", []):
    print(material)

def inspect_source(path):
    result = {
        "path": str(path),
        "exists": path.exists(),
        "lines": 0,
        "functions": [],
        "classes": [],
        "score_lines": [],
        "default_lines": [],
        "return_lines": [],
    }

    if not path.exists():
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    result["lines"] = len(lines)

    try:
        tree = ast.parse(text)
    except Exception as e:
        result["parse_error"] = str(e)
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(
                {
                    "name": node.name,
                    "line": node.lineno,
                }
            )

        elif isinstance(node, ast.ClassDef):
            result["classes"].append(
                {
                    "name": node.name,
                    "line": node.lineno,
                }
            )

    keywords = (
        "final_score",
        "scientific_score",
        "score",
        "0.5",
        "confidence",
        "coverage",
        "default",
        "fallback",
        "return",
    )

    for i, line in enumerate(lines, start=1):
        low = line.lower()

        if any(k.lower() in low for k in keywords):
            entry = {"line": i, "text": line.strip()}

            result["score_lines"].append(entry)

            if (
                "0.5" in line
                or "default" in low
                or "fallback" in low
                or "else" in low
            ):
                result["default_lines"].append(entry)

            if low.startswith("return ") or " return " in f" {low} ":
                result["return_lines"].append(entry)

    return result


workflow_info = inspect_source(WORKFLOW)
objective_info = inspect_source(OBJECTIVE)

print("\nSOURCE WORKFLOW")
print("-" * 70)
print(f"EXISTS : {workflow_info['exists']}")
print(f"LINES  : {workflow_info['lines']}")

print("\nFUNCTIONS")
for x in workflow_info["functions"]:
    print(f"L{x['line']}: {x['name']}")

print("\nCLASSES")
for x in workflow_info["classes"]:
    print(f"L{x['line']}: {x['name']}")

print("\nWORKFLOW SCORE REFERENCES")
for x in workflow_info["score_lines"]:
    print(f"L{x['line']}: {x['text']}")

print("\nSOURCE OBJECTIVE SCORE")
print("-" * 70)
print(f"EXISTS : {objective_info['exists']}")
print(f"LINES  : {objective_info['lines']}")

print("\nFUNCTIONS")
for x in objective_info["functions"]:
    print(f"L{x['line']}: {x['name']}")

print("\nCLASSES")
for x in objective_info["classes"]:
    print(f"L{x['line']}: {x['name']}")

print("\nOBJECTIVE SCORE REFERENCES")
for x in objective_info["score_lines"]:
    print(f"L{x['line']}: {x['text']}")

print("\nAUDIT DES VALEURS")
print("-" * 70)

audit_rows = []

for row in rows:
    material = row.get("material", "")
    scientific = row.get("scientific_score", "")
    h2 = row.get("h2_uptake_wt_percent", "")
    ambient = row.get("ambient_score", "")

    audit_rows.append(
        {
            "material": material,
            "h2_uptake_wt_percent": h2,
            "ambient_score": ambient,
            "scientific_score": scientific,
            "scientific_is_0_5000": scientific == "0.5000",
        }
    )

    if scientific == "0.5000":
        print(
            f"{material:<22} "
            f"H2={h2:<8} "
            f"Ambient={ambient:<8} "
            f"Scientific={scientific}"
        )

print("\nTEST D'EFFET DE RANG")
print("-" * 70)

scientific_rank = sorted(
    rows,
    key=lambda r: float(r["scientific_score"])
    if r.get("scientific_score")
    else float("-inf"),
    reverse=True,
)

for rank, row in enumerate(scientific_rank, 1):
    print(
        f"{rank:2d}. "
        f"{row.get('material',''):<22} "
        f"scientific={row.get('scientific_score','')}"
    )

print("\nVERDICT PRELIMINAIRE")
print("-" * 70)

half_count = len(scientific_values.get("0.5000", []))

if half_count >= 2:
    verdict = (
        "ANOMALIE_AUDIT_REQUIRED: plusieurs materiaux ont exactement "
        "0.5000; verifier fallback/default/coverage dans le pipeline scientifique."
    )
else:
    verdict = (
        "NO_MASS_0_5000_PATTERN: pas de concentration anormale de 0.5000."
    )

print(verdict)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "material",
            "h2_uptake_wt_percent",
            "ambient_score",
            "scientific_score",
            "scientific_is_0_5000",
        ],
    )
    writer.writeheader()
    writer.writerows(audit_rows)

result = {
    "phase": 47,
    "mode": "ANALYSIS_ONLY",
    "status": "COMPLETE",
    "input": str(INPUT),
    "workflow_source": workflow_info,
    "objective_source": objective_info,
    "scientific_distribution": scientific_values,
    "count_scientific_0_5000": half_count,
    "audit_rows": audit_rows,
    "preliminary_verdict": verdict,
    "no_qe": True,
    "no_cif_modification": True,
}

JSON_OUT.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

MANIFEST.write_text(
    json.dumps(
        {
            "phase": 47,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Audit scientific_score defaults, fallback values and ranking behavior",
            "input": str(INPUT),
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
print("PHASE 47 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
