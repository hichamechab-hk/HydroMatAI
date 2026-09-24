from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
RANKING = ROOT / "src" / "hydromatai" / "scientific" / "ranking.py"
ANALYSIS = ROOT / "src" / "hydromatai" / "scientific" / "analysis.py"

OUTDIR = ROOT / "calculations" / "phase_50_material_score"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase50_material_score.csv"
JSON_OUT = OUTDIR / "phase50_material_score.json"
MANIFEST = OUTDIR / "phase50_manifest.json"


def read(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def get_functions(path):
    text = read(path)
    if not text:
        return []

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    result = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            })

    return sorted(result, key=lambda x: x["line"])


def get_relevant_lines(path, keywords):
    text = read(path)
    result = []

    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()

        if any(k.lower() in low for k in keywords):
            result.append({
                "line": i,
                "text": line.strip(),
            })

    return result


print("=" * 70)
print("PHASE 50 — TRACE DU MATERIAL SCORE")
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

print("\nMODULE RANKING")
print("-" * 70)
print(f"EXISTS : {RANKING.exists()}")
print(f"LINES  : {len(read(RANKING).splitlines())}")

ranking_functions = get_functions(RANKING)

for fn in ranking_functions:
    print(
        f"{fn['name']:<35} "
        f"L{fn['line']}-L{fn['end_line']}"
    )

ranking_refs = get_relevant_lines(
    RANKING,
    [
        "calculate_material_score",
        "electronic",
        "optical",
        "hydrogen",
        "stability",
        "score",
        "weight",
        "return",
        "0.5",
    ],
)

print("\nREFERENCES RANKING")
for x in ranking_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nMODULE ANALYSIS")
print("-" * 70)

analysis_refs = get_relevant_lines(
    ANALYSIS,
    [
        "electronic_score",
        "optical_score",
        "stability",
        "hydrogen_score",
        "calculate_material_score",
        "final",
        "return",
        "0.5",
    ],
)

for x in analysis_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nSTRUCTURE DU SCORE")
print("-" * 70)

ranking_text = read(RANKING)
score_function = None

try:
    tree = ast.parse(ranking_text)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_material_score":
            score_function = node
            break

except Exception:
    pass

score_source = []

if score_function is not None:
    lines = ranking_text.splitlines()

    start = score_function.lineno
    end = getattr(score_function, "end_lineno", start)

    for i in range(start, end + 1):
        score_source.append({
            "line": i,
            "text": lines[i - 1].strip(),
        })
        print(f"L{i}: {lines[i - 1].strip()}")

else:
    print("CALCULATE_MATERIAL_SCORE_NOT_FOUND")

print("\nRECONSTRUCTION THEORIQUE")
print("-" * 70)

print(
    "Le score scientifique provient de calculate_material_score("
    "electronic_score, optical_score, hydrogen_score, stability)."
)

print(
    "La valeur hydrogen_score est initialisee a 0.5 dans analysis.py "
    "lorsqu'aucun score H2 ambient utilisable ne remplace cette valeur."
)

print("\nDONNEES DISPONIBLES")
print("-" * 70)

audit = []

for row in rows:
    material = row.get("material", "")
    scientific = row.get("scientific_score", "")
    ambient = row.get("ambient_score", "")
    confidence = row.get("confidence", "")
    h2 = row.get("h2_uptake_wt_percent", "")
    literature_count = row.get("literature_count", "")

    item = {
        "material": material,
        "h2_uptake_wt_percent": h2,
        "ambient_score": ambient,
        "scientific_score": scientific,
        "confidence": confidence,
        "literature_count": literature_count,
    }

    audit.append(item)

    print(
        f"{material:<22} "
        f"H2={h2:<8} "
        f"Ambient={ambient:<8} "
        f"Scientific={scientific:<8} "
        f"Confidence={confidence:<8} "
        f"Literature={literature_count}"
    )

print("\nFOCUS SUR LE SCORE 0.5000")
print("-" * 70)

targets = []

for item in audit:
    if item["scientific_score"] in ("0.5", "0.5000"):
        targets.append(item)

for item in targets:
    print(
        f"{item['material']:<22} "
        f"scientific={item['scientific_score']} "
        f"ambient={item['ambient_score']} "
        f"literature={item['literature_count']} "
        f"confidence={item['confidence']}"
    )

print("\nDIAGNOSTIC")
print("-" * 70)

if len(targets) == 3:
    diagnostic = (
        "Les 3 materiaux a 0.5000 ont confidence LOW et ambient_score 0.0. "
        "Le score neutre H2=0.5 dans analysis.py est donc fortement suspect "
        "comme composante dominante du scientific_score. "
        "Le code exact de ranking.py ci-dessus doit confirmer la ponderation."
    )
else:
    diagnostic = (
        "Le groupe 0.5000 ne correspond pas exactement aux trois MOFs attendus."
    )

print(diagnostic)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "material",
        "h2_uptake_wt_percent",
        "ambient_score",
        "scientific_score",
        "confidence",
        "literature_count",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(audit)

result = {
    "phase": 50,
    "mode": "ANALYSIS_ONLY",
    "status": "COMPLETE",
    "input": str(INPUT),
    "ranking_source": str(RANKING),
    "analysis_source": str(ANALYSIS),
    "ranking_functions": ranking_functions,
    "ranking_references": ranking_refs,
    "analysis_references": analysis_refs,
    "calculate_material_score_source": score_source,
    "materials": audit,
    "targets_0_5000": targets,
    "diagnostic": diagnostic,
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
            "phase": 50,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Trace exact weighting of electronic, optical, hydrogen and stability scores",
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
print("PHASE 50 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
