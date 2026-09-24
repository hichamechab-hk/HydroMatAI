from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
ANALYSIS = ROOT / "src" / "hydromatai" / "scientific" / "analysis.py"
RANKING = ROOT / "src" / "hydromatai" / "scientific" / "ranking.py"

OUTDIR = ROOT / "calculations" / "phase_52_missing_data_audit"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase52_missing_data.csv"
JSON_OUT = OUTDIR / "phase52_missing_data.json"
MANIFEST = OUTDIR / "phase52_manifest.json"


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def extract_function(path, name):
    text = read(path)

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    lines = text.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            return [
                {"line": i, "text": lines[i - 1].strip()}
                for i in range(start, end + 1)
            ]

    return []


print("=" * 70)
print("PHASE 52 — AUDIT DES DONNEES MANQUANTES")
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

print("\nSOURCE ANALYSIS.PY")
print("-" * 70)

analysis_source = extract_function(ANALYSIS, "analyze_material")

for item in analysis_source:
    print(f"L{item['line']}: {item['text']}")

print("\nSOURCE RANKING.PY")
print("-" * 70)

ranking_source = extract_function(RANKING, "calculate_material_score")

for item in ranking_source:
    print(f"L{item['line']}: {item['text']}")

print("\nAUDIT DES DONNEES DISPONIBLES")
print("-" * 70)

audit = []

for row in rows:
    material = row.get("material", "")

    h2 = row.get("h2_uptake_wt_percent", "")
    ambient = row.get("ambient_score", "")
    scientific = row.get("scientific_score", "")
    confidence = row.get("confidence", "")
    literature = row.get("literature_count", "")

    try:
        h2_value = float(h2)
    except Exception:
        h2_value = None

    try:
        ambient_value = float(ambient)
    except Exception:
        ambient_value = None

    try:
        scientific_value = float(scientific)
    except Exception:
        scientific_value = None

    try:
        literature_value = int(float(literature))
    except Exception:
        literature_value = 0

    missing_h2 = h2_value is None
    missing_ambient = ambient_value is None or ambient_value == 0.0
    neutral_scientific = scientific_value == 0.5

    if neutral_scientific:
        data_quality = "LOW"
    elif confidence == "MEDIUM":
        data_quality = "MEDIUM"
    else:
        data_quality = "HIGH"

    item = {
        "material": material,
        "h2_uptake_wt_percent": h2_value,
        "ambient_score": ambient_value,
        "scientific_score": scientific_value,
        "confidence": confidence,
        "literature_count": literature_value,
        "missing_h2": missing_h2,
        "missing_ambient": missing_ambient,
        "neutral_scientific_default": neutral_scientific,
        "data_quality": data_quality,
    }

    audit.append(item)

    print(
        f"{material:<22} "
        f"H2={'MISSING' if missing_h2 else f'{h2_value:.3f}':<8} "
        f"Ambient={'MISSING' if missing_ambient else f'{ambient_value:.4f}':<8} "
        f"Scientific={'DEFAULT_0.5' if neutral_scientific else f'{scientific_value:.4f}':<11} "
        f"Literature={literature_value:<2} "
        f"Quality={data_quality}"
    )

print("\nANALYSE DES VALEURS PAR DEFAUT")
print("-" * 70)

default_candidates = [
    x for x in audit
    if x["neutral_scientific_default"]
]

print(
    f"SCIENTIFIC_DEFAULT_0.5 : "
    f"{len(default_candidates)}/{len(audit)}"
)

for x in default_candidates:
    print(
        f"- {x['material']} | "
        f"Ambient={x['ambient_score']} | "
        f"H2={x['h2_uptake_wt_percent']} | "
        f"Confidence={x['confidence']} | "
        f"Literature={x['literature_count']}"
    )

print("\nSIMULATION DE PENALITES DE COVERAGE")
print("-" * 70)

simulation = []

for x in audit:
    scientific = x["scientific_score"]
    ambient = x["ambient_score"]

    if scientific is None:
        continue

    if x["data_quality"] == "LOW":
        coverage_factor = 0.5
    elif x["data_quality"] == "MEDIUM":
        coverage_factor = 0.75
    else:
        coverage_factor = 1.0

    penalized_scientific = scientific * coverage_factor

    simulation.append({
        "material": x["material"],
        "current_scientific": scientific,
        "coverage_factor": coverage_factor,
        "penalized_scientific": round(penalized_scientific, 4),
        "ambient_score": ambient,
        "current_confidence": x["confidence"],
    })

    print(
        f"{x['material']:<22} "
        f"Current={scientific:.4f} "
        f"Factor={coverage_factor:.2f} "
        f"Penalized={penalized_scientific:.4f}"
    )

print("\nTEST DE ROBUSTESSE")
print("-" * 70)

for x in audit:
    current = x["scientific_score"]

    if current is None:
        continue

    if x["neutral_scientific_default"]:
        interpretation = (
            "SCORE_NEUTRE_NON_DEMONSTRATIF"
        )
    elif x["confidence"] == "MEDIUM":
        interpretation = (
            "SCORE_UTILISABLE_AVEC_RESERVE"
        )
    else:
        interpretation = (
            "SCORE_BASE_SUR_DONNEES"
        )

    print(
        f"{x['material']:<22} "
        f"Scientific={current:.4f} | "
        f"{interpretation}"
    )

print("\nVERDICT")
print("-" * 70)

if len(default_candidates) > 0:
    verdict = (
        "MISSING_DATA_DEFAULTS_CONFIRMED : "
        "des donnees absentes produisent un score scientifique neutre "
        "de 0.5. Ce score ne doit pas etre traite comme une preuve "
        "de performance."
    )
else:
    verdict = (
        "NO_NEUTRAL_DEFAULT_GROUP_FOUND"
    )

print(verdict)

print("\nRECOMMANDATION")
print("-" * 70)

recommendation = (
    "NE PAS modifier le scoring actuel sans nouvelle validation. "
    "Pour le ranking scientifique, distinguer score de performance "
    "et score de confiance/coverage. Une absence de donnees devrait "
    "etre conservee comme absence de preuve plutot que comme "
    "performance moyenne."
)

print(recommendation)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "material",
        "h2_uptake_wt_percent",
        "ambient_score",
        "scientific_score",
        "confidence",
        "literature_count",
        "missing_h2",
        "missing_ambient",
        "neutral_scientific_default",
        "data_quality",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(audit)

result = {
    "phase": 52,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "analysis_source": str(ANALYSIS),
    "ranking_source": str(RANKING),
    "analysis_function": analysis_source,
    "ranking_function": ranking_source,
    "materials": audit,
    "default_candidates": default_candidates,
    "coverage_simulation": simulation,
    "verdict": verdict,
    "recommendation": recommendation,
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
            "phase": 52,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "purpose": "Audit missing-data defaults and confidence",
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
print("PHASE 52 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
