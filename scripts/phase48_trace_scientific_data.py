from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
WORKFLOW = ROOT / "src" / "hydromatai" / "scientific" / "workflow.py"
OBJECTIVE = ROOT / "src" / "hydromatai" / "literature" / "objective_score.py"
HYDROGEN = ROOT / "src" / "hydromatai" / "literature" / "hydrogen_score.py"

OUTDIR = ROOT / "calculations" / "phase_48_scientific_data_trace"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase48_scientific_data_trace.csv"
JSON_OUT = OUTDIR / "phase48_scientific_data_trace.json"
MANIFEST = OUTDIR / "phase48_manifest.json"


def read_source(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def source_lines(path, keywords):
    text = read_source(path)
    result = []

    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(k.lower() in low for k in keywords):
            result.append({
                "line": i,
                "text": line.strip(),
            })

    return result


def extract_functions(path):
    text = read_source(path)
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


print("=" * 70)
print("PHASE 48 — TRACE DES DONNEES SCIENTIFIQUES")
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

print("\nSOURCE SCIENTIFIC WORKFLOW")
print("-" * 70)

workflow_functions = extract_functions(WORKFLOW)

for fn in workflow_functions:
    print(
        f"{fn['name']:<30} "
        f"L{fn['line']}-L{fn['end_line']}"
    )

workflow_refs = source_lines(
    WORKFLOW,
    [
        "analyze_material",
        "final_score",
        "ScientificWorkflow",
        "literature",
        "material",
        "result",
    ],
)

for x in workflow_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nSOURCE OBJECTIVE SCORE")
print("-" * 70)

objective_functions = extract_functions(OBJECTIVE)

for fn in objective_functions:
    print(
        f"{fn['name']:<30} "
        f"L{fn['line']}-L{fn['end_line']}"
    )

objective_refs = source_lines(
    OBJECTIVE,
    [
        "gravimetric_score",
        "density_score",
        "thermal_score",
        "coverage",
        "confidence",
        "screening",
        "ambient",
        "high_density",
        "global",
        "calculate_hydrogen_storage_score",
    ],
)

for x in objective_refs:
    print(f"L{x['line']}: {x['text']}")

print("\nSOURCE HYDROGEN SCORE")
print("-" * 70)

if HYDROGEN.exists():
    hydrogen_functions = extract_functions(HYDROGEN)

    for fn in hydrogen_functions:
        print(
            f"{fn['name']:<30} "
            f"L{fn['line']}-L{fn['end_line']}"
        )

    hydrogen_refs = source_lines(
        HYDROGEN,
        [
            "gravimetric",
            "volumetric",
            "hydrogen",
            "score",
            "capacity",
            "uptake",
            "theoretical",
        ],
    )

    for x in hydrogen_refs:
        print(f"L{x['line']}: {x['text']}")
else:
    hydrogen_functions = []
    hydrogen_refs = []
    print("HYDROGEN_SCORE_MODULE : NOT_FOUND")

print("\nDONNEES PAR MATERIAU")
print("-" * 70)

audit = []

for row in rows:
    material = row.get("material", "")
    h2 = row.get("h2_uptake_wt_percent", "")
    ambient = row.get("ambient_score", "")
    scientific = row.get("scientific_score", "")
    confidence = row.get("confidence", "")

    item = {
        "material": material,
        "h2_uptake_wt_percent": h2,
        "ambient_score": ambient,
        "scientific_score": scientific,
        "confidence": confidence,
        "scientific_0_5000": scientific in ("0.5", "0.5000"),
    }

    audit.append(item)

    print(
        f"{material:<22} "
        f"H2={h2:<8} "
        f"Ambient={ambient:<8} "
        f"Scientific={scientific:<8} "
        f"Confidence={confidence}"
    )

print("\nANALYSE DES TROIS MOFs")
print("-" * 70)

mofs = [
    r for r in rows
    if r.get("material") in ("IRMOF-6", "IRMOF-8", "JUC-48")
]

for r in mofs:
    print(
        f"{r.get('material',''):<22} "
        f"scientific={r.get('scientific_score','')} "
        f"ambient={r.get('ambient_score','')} "
        f"H2={r.get('h2_uptake_wt_percent','')} "
        f"confidence={r.get('confidence','')}"
    )

print("\nRECHERCHE DES VALEURS 0.5 DANS LE CODE")
print("-" * 70)

zero5_hits = []

for path in [WORKFLOW, OBJECTIVE, HYDROGEN]:
    text = read_source(path)

    for i, line in enumerate(text.splitlines(), 1):
        if "0.5" in line:
            hit = {
                "file": str(path),
                "line": i,
                "text": line.strip(),
            }
            zero5_hits.append(hit)
            print(
                f"{path.name}:L{i}: {line.strip()}"
            )

print("\nRECHERCHE DES FALLBACKS / DEFAULTS")
print("-" * 70)

fallback_hits = []

for path in [WORKFLOW, OBJECTIVE, HYDROGEN]:
    text = read_source(path)

    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()

        if any(
            key in low
            for key in (
                "default",
                "fallback",
                "else:",
                "if not ",
                "or 0",
                "or 0.0",
                "return 0",
                "return 0.0",
            )
        ):
            hit = {
                "file": str(path),
                "line": i,
                "text": line.strip(),
            }
            fallback_hits.append(hit)
            print(
                f"{path.name}:L{i}: {line.strip()}"
            )

print("\nVERDICT")
print("-" * 70)

if len(mofs) == 3 and all(
    r.get("scientific_score") in ("0.5", "0.5000")
    for r in mofs
):
    verdict = (
        "THREE_MOFS_SHARE_SCIENTIFIC_SCORE_0_5: "
        "trace necessaire vers les composantes du score et les donnees "
        "d'entree; 0.5 seul ne prouve pas un fallback."
    )
else:
    verdict = (
        "NO_COMMON_0_5_PATTERN_FOR_ALL_TARGET_MOFS"
    )

print(verdict)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "material",
        "h2_uptake_wt_percent",
        "ambient_score",
        "scientific_score",
        "confidence",
        "scientific_0_5000",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(audit)

result = {
    "phase": 48,
    "mode": "ANALYSIS_ONLY",
    "status": "COMPLETE",
    "input": str(INPUT),
    "materials": audit,
    "workflow_functions": workflow_functions,
    "workflow_references": workflow_refs,
    "objective_functions": objective_functions,
    "objective_references": objective_refs,
    "hydrogen_functions": hydrogen_functions,
    "hydrogen_references": hydrogen_refs,
    "zero5_hits": zero5_hits,
    "fallback_hits": fallback_hits,
    "mof_targets": [
        r for r in audit
        if r["material"] in ("IRMOF-6", "IRMOF-8", "JUC-48")
    ],
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
            "phase": 48,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Trace scientific score components and source data",
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
print("PHASE 48 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
