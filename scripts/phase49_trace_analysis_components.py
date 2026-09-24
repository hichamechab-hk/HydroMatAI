from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
ANALYSIS = ROOT / "src" / "hydromatai" / "scientific" / "analysis.py"
HYDROGEN = ROOT / "src" / "hydromatai" / "literature" / "hydrogen_score.py"
OBJECTIVE = ROOT / "src" / "hydromatai" / "literature" / "objective_score.py"

OUTDIR = ROOT / "calculations" / "phase_49_analysis_components"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase49_analysis_components.csv"
JSON_OUT = OUTDIR / "phase49_analysis_components.json"
MANIFEST = OUTDIR / "phase49_manifest.json"


def read(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def functions(path):
    text = read(path)
    if not text:
        return []

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            })

    return sorted(out, key=lambda x: x["line"])


def relevant_lines(path, keywords):
    text = read(path)
    out = []

    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(k.lower() in low for k in keywords):
            out.append({
                "line": i,
                "text": line.strip(),
            })

    return out


print("=" * 70)
print("PHASE 49 — TRACE DES COMPOSANTES DU SCIENTIFIC SCORE")
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

print("\nMODULE ANALYSIS")
print("-" * 70)
print(f"EXISTS : {ANALYSIS.exists()}")
print(f"LINES  : {len(read(ANALYSIS).splitlines())}")

analysis_functions = functions(ANALYSIS)

for fn in analysis_functions:
    print(
        f"{fn['name']:<35} "
        f"L{fn['line']}-L{fn['end_line']}"
    )

analysis_refs = relevant_lines(
    ANALYSIS,
    [
        "analyze_material",
        "scientific",
        "literature",
        "objective",
        "score",
        "coverage",
        "confidence",
        "hydrogen",
        "result",
    ],
)

print("\nREFERENCES ANALYSIS")
for x in analysis_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nCOMPOSANTES HYDROGEN SCORE")
print("-" * 70)

hydrogen_refs = relevant_lines(
    HYDROGEN,
    [
        "gravimetric_score",
        "volumetric_score",
        "deliverable_score",
        "surface_area_score",
        "thermal_score",
        "coverage",
        "final_score",
        "criteria",
    ],
)

for x in hydrogen_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nCOMPOSANTES OBJECTIVE SCORE")
print("-" * 70)

objective_refs = relevant_lines(
    OBJECTIVE,
    [
        "base.gravimetric_score",
        "density_score",
        "thermal_score",
        "coverage",
        "confidence",
        "raw =",
        "screening =",
        "components",
    ],
)

for x in objective_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nDONNEES DISPONIBLES DANS DFT_H2_PRIORITY")
print("-" * 70)

if rows:
    print("COLONNES :")
    for field in rows[0].keys():
        print(f"- {field}")

print("\nVALEURS PAR MATERIAU")
print("-" * 70)

audit = []

for row in rows:
    material = row.get("material", "")

    item = {
        "material": material,
        "h2_uptake_wt_percent": row.get("h2_uptake_wt_percent", ""),
        "ambient_score": row.get("ambient_score", ""),
        "scientific_score": row.get("scientific_score", ""),
        "confidence": row.get("confidence", ""),
    }

    audit.append(item)

    print(
        f"{material:<22} "
        f"H2={item['h2_uptake_wt_percent']:<8} "
        f"Ambient={item['ambient_score']:<8} "
        f"Scientific={item['scientific_score']:<8} "
        f"Confidence={item['confidence']}"
    )

print("\nFOCUS MOFs")
print("-" * 70)

for row in rows:
    if row.get("material") in ("IRMOF-6", "IRMOF-8", "JUC-48"):
        print(
            f"{row.get('material'):<22} "
            f"Scientific={row.get('scientific_score')} "
            f"Confidence={row.get('confidence')}"
        )

print("\nCONCLUSION TECHNIQUE")
print("-" * 70)

analysis_exists = ANALYSIS.exists()
hydrogen_exists = HYDROGEN.exists()
objective_exists = OBJECTIVE.exists()

if analysis_exists and hydrogen_exists and objective_exists:
    verdict = (
        "ANALYSIS_CHAIN_IDENTIFIED: "
        "analysis.py -> hydrogen_score.py -> objective_score.py. "
        "Les valeurs intermediaires doivent maintenant etre exposees "
        "pour confirmer l'origine du 0.5000."
    )
else:
    verdict = "SOURCE_MODULE_MISSING"

print(verdict)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "material",
        "h2_uptake_wt_percent",
        "ambient_score",
        "scientific_score",
        "confidence",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(audit)

result = {
    "phase": 49,
    "mode": "ANALYSIS_ONLY",
    "status": "COMPLETE",
    "input": str(INPUT),
    "analysis_source": {
        "path": str(ANALYSIS),
        "exists": analysis_exists,
        "functions": analysis_functions,
        "references": analysis_refs,
    },
    "hydrogen_source": {
        "path": str(HYDROGEN),
        "exists": hydrogen_exists,
        "references": hydrogen_refs,
    },
    "objective_source": {
        "path": str(OBJECTIVE),
        "exists": objective_exists,
        "references": objective_refs,
    },
    "materials": audit,
    "verdict": verdict,
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
            "phase": 49,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Trace analysis.py and expose scientific score components",
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
print("PHASE 49 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
