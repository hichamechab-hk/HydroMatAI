from pathlib import Path
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")
INPUT = ROOT / "reports" / "dft_h2_priority.csv"

OUTDIR = ROOT / "calculations" / "phase_53_corrected_ranking"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase53_corrected_ranking.csv"
JSON_OUT = OUTDIR / "phase53_corrected_ranking.json"
MANIFEST = OUTDIR / "phase53_manifest.json"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


print("=" * 70)
print("PHASE 53 — CLASSEMENT CORRIGE PAR COVERAGE")
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

materials = []

for row in rows:
    scientific = num(row.get("scientific_score"))
    ambient = num(row.get("ambient_score"))
    h2 = num(row.get("h2_uptake_wt_percent"))
    confidence = row.get("confidence", "")

    if confidence == "HIGH":
        factor = 1.00
    elif confidence == "MEDIUM":
        factor = 0.75
    else:
        factor = 0.50

    corrected_scientific = (
        scientific * factor
        if scientific is not None
        else None
    )

    materials.append({
        "material": row.get("material", ""),
        "original_priority": row.get("priority", ""),
        "h2_uptake_wt_percent": h2,
        "ambient_score": ambient,
        "scientific_score": scientific,
        "confidence": confidence,
        "coverage_factor": factor,
        "corrected_scientific_score": (
            round(corrected_scientific, 4)
            if corrected_scientific is not None
            else None
        ),
    })

print("\nCLASSEMENT SCIENTIFIC ORIGINAL")
print("-" * 70)

original = sorted(
    materials,
    key=lambda x: x["scientific_score"]
    if x["scientific_score"] is not None else -1,
    reverse=True,
)

for i, x in enumerate(original, 1):
    print(
        f"{i}. {x['material']:<22} "
        f"{x['scientific_score']:.4f} "
        f"[{x['confidence']}]"
    )

print("\nCLASSEMENT SCIENTIFIC CORRIGE")
print("-" * 70)

corrected = sorted(
    materials,
    key=lambda x: x["corrected_scientific_score"]
    if x["corrected_scientific_score"] is not None else -1,
    reverse=True,
)

for i, x in enumerate(corrected, 1):
    x["corrected_scientific_rank"] = i

    print(
        f"{i}. {x['material']:<22} "
        f"{x['corrected_scientific_score']:.4f} "
        f"[{x['confidence']}]"
    )

print("\nCLASSEMENT AMBIENT")
print("-" * 70)

ambient_ranked = sorted(
    materials,
    key=lambda x: x["ambient_score"]
    if x["ambient_score"] is not None else -1,
    reverse=True,
)

for i, x in enumerate(ambient_ranked, 1):
    x["ambient_rank"] = i

    print(
        f"{i}. {x['material']:<22} "
        f"{x['ambient_score']:.4f}"
    )

print("\nCLASSEMENT H2")
print("-" * 70)

h2_ranked = sorted(
    materials,
    key=lambda x: x["h2_uptake_wt_percent"]
    if x["h2_uptake_wt_percent"] is not None else -1,
    reverse=True,
)

for i, x in enumerate(h2_ranked, 1):
    x["h2_rank"] = i

    print(
        f"{i}. {x['material']:<22} "
        f"{x['h2_uptake_wt_percent']:.3f}"
    )

print("\nCOMPARAISON DES RANGS")
print("-" * 70)

original_rank = {
    x["material"]: i
    for i, x in enumerate(original, 1)
}

corrected_rank = {
    x["material"]: i
    for i, x in enumerate(corrected, 1)
}

rank_changes = []

for x in materials:
    material = x["material"]
    old = original_rank[material]
    new = corrected_rank[material]
    delta = old - new

    x["original_scientific_rank"] = old
    x["corrected_scientific_rank"] = new
    x["rank_change"] = delta

    rank_changes.append(abs(delta))

    print(
        f"{material:<22} "
        f"Original={old} "
        f"Corrige={new} "
        f"Delta={delta:+d}"
    )

print("\nTEST DE ROBUSTESSE DU TOP 5")
print("-" * 70)

top5_original = [
    x["material"] for x in original[:5]
]

top5_corrected = [
    x["material"] for x in corrected[:5]
]

print("TOP5 ORIGINAL :")
for i, name in enumerate(top5_original, 1):
    print(f"{i}. {name}")

print("\nTOP5 CORRIGE :")
for i, name in enumerate(top5_corrected, 1):
    print(f"{i}. {name}")

top5_stable = top5_original == top5_corrected

print(
    f"\nTOP5 IDENTIQUE : "
    f"{'OUI' if top5_stable else 'NON'}"
)

print("\nFOCUS TOP1")
print("-" * 70)

original_top1 = original[0]["material"]
corrected_top1 = corrected[0]["material"]

print(f"TOP1 ORIGINAL : {original_top1}")
print(f"TOP1 CORRIGE  : {corrected_top1}")

if original_top1 == corrected_top1:
    top1_verdict = "TOP1_ROBUST"
else:
    top1_verdict = "TOP1_SENSITIVE"

print(f"VERDICT TOP1 : {top1_verdict}")

print("\nVERDICT GLOBAL")
print("-" * 70)

max_change = max(rank_changes) if rank_changes else 0

if top5_stable and original_top1 == corrected_top1:
    verdict = "ROBUST"
elif original_top1 == corrected_top1:
    verdict = "TOP1_ROBUST_TOP5_SENSITIVE"
else:
    verdict = "SENSITIVE"

print(f"MAX_RANK_CHANGE : {max_change}")
print(f"VERDICT         : {verdict}")

print("\nCONCLUSION")
print("-" * 70)

if original_top1 == corrected_top1:
    conclusion = (
        f"{original_top1} reste TOP1 apres correction de coverage. "
        "Le choix du TOP1 est donc robuste vis-a-vis de la penalisation "
        "des donnees manquantes."
    )
else:
    conclusion = (
        "Le TOP1 change apres correction de coverage. "
        "Le classement actuel est sensible aux donnees manquantes."
    )

print(conclusion)

fields = [
    "material",
    "original_priority",
    "h2_uptake_wt_percent",
    "ambient_score",
    "scientific_score",
    "confidence",
    "coverage_factor",
    "corrected_scientific_score",
    "original_scientific_rank",
    "corrected_scientific_rank",
    "rank_change",
    "ambient_rank",
    "h2_rank",
]

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(materials)

result = {
    "phase": 53,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "original_scientific_ranking": original,
    "corrected_scientific_ranking": corrected,
    "ambient_ranking": ambient_ranked,
    "h2_ranking": h2_ranked,
    "top5_original": top5_original,
    "top5_corrected": top5_corrected,
    "top5_identical": top5_stable,
    "original_top1": original_top1,
    "corrected_top1": corrected_top1,
    "top1_verdict": top1_verdict,
    "max_rank_change": max_change,
    "verdict": verdict,
    "conclusion": conclusion,
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
            "phase": 53,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "purpose": "Correct scientific ranking using missing-data coverage",
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
print("PHASE 53 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
