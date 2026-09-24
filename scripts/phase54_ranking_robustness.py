from pathlib import Path
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")
INPUT = ROOT / "reports" / "dft_h2_priority.csv"

OUTDIR = ROOT / "calculations" / "phase_54_ranking_robustness"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase54_ranking_robustness.csv"
JSON_OUT = OUTDIR / "phase54_ranking_robustness.json"
MANIFEST = OUTDIR / "phase54_manifest.json"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


print("=" * 70)
print("PHASE 54 — VALIDATION ROBUSTESSE DU CLASSEMENT")
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
        base_coverage = 1.0
    elif confidence == "MEDIUM":
        base_coverage = 0.75
    else:
        base_coverage = 0.50

    materials.append({
        "material": row.get("material", ""),
        "h2": h2,
        "ambient": ambient,
        "scientific": scientific,
        "confidence": confidence,
        "base_coverage": base_coverage,
    })

print(f"\nMATERIAUX : {len(materials)}")

print("\nTEST DE SENSIBILITE AUX PENALITES")
print("-" * 70)

# LOW = différentes pénalités
# MEDIUM reste à 0.75
low_factors = [0.0, 0.25, 0.50, 0.60, 0.75, 1.0]
medium_factors = [0.50, 0.75, 1.0]

scenarios = []

for low_factor in low_factors:
    for medium_factor in medium_factors:

        scored = []

        for x in materials:
            if x["scientific"] is None:
                continue

            if x["confidence"] == "LOW":
                factor = low_factor
            elif x["confidence"] == "MEDIUM":
                factor = medium_factor
            else:
                factor = 1.0

            corrected = x["scientific"] * factor

            scored.append({
                "material": x["material"],
                "score": corrected,
            })

        scored.sort(key=lambda z: z["score"], reverse=True)

        ranks = {
            x["material"]: i + 1
            for i, x in enumerate(scored)
        }

        top1 = scored[0]["material"]
        top5 = [x["material"] for x in scored[:5]]

        scenario = {
            "low_factor": low_factor,
            "medium_factor": medium_factor,
            "top1": top1,
            "top5": top5,
            "ranks": ranks,
        }

        scenarios.append(scenario)

        print(
            f"LOW={low_factor:.2f} "
            f"MEDIUM={medium_factor:.2f} "
            f"-> TOP1={top1:<22} "
            f"TOP5={', '.join(top5)}"
        )

print("\nSTABILITE DU TOP1")
print("-" * 70)

top1_counts = {}

for s in scenarios:
    top1_counts[s["top1"]] = top1_counts.get(s["top1"], 0) + 1

total = len(scenarios)

for material, count in sorted(
    top1_counts.items(),
    key=lambda z: z[1],
    reverse=True,
):
    print(
        f"{material:<22} "
        f"{count}/{total} scenarios "
        f"({100.0 * count / total:.1f}%)"
    )

print("\nSTABILITE DES CANDIDATS")
print("-" * 70)

candidate_stats = {}

for x in materials:
    ranks = []

    for s in scenarios:
        ranks.append(s["ranks"][x["material"]])

    candidate_stats[x["material"]] = {
        "min_rank": min(ranks),
        "max_rank": max(ranks),
        "mean_rank": round(sum(ranks) / len(ranks), 3),
        "top5_count": sum(1 for r in ranks if r <= 5),
    }

    print(
        f"{x['material']:<22} "
        f"rank={min(ranks)}-{max(ranks)} "
        f"mean={sum(ranks)/len(ranks):.2f} "
        f"TOP5={sum(1 for r in ranks if r <= 5)}/{total}"
    )

print("\nCOMPARAISON H2 / AMBIENT / SCIENTIFIC")
print("-" * 70)

def rank_by(key):
    valid = [
        x for x in materials
        if x[key] is not None
    ]
    valid.sort(key=lambda x: x[key], reverse=True)
    return valid


h2_rank = [x["material"] for x in rank_by("h2")]
ambient_rank = [x["material"] for x in rank_by("ambient")]
scientific_rank = [x["material"] for x in rank_by("scientific")]

print("H2      :", " > ".join(h2_rank))
print("AMBIENT :", " > ".join(ambient_rank))
print("SCIENTIFIC :", " > ".join(scientific_rank))

print("\nFOCUS TiFeH2 / TiMn1.5")
print("-" * 70)

for name in ["TiFeH2", "TiMn1.5"]:
    stats = candidate_stats[name]

    print(
        f"{name:<22} "
        f"min={stats['min_rank']} "
        f"max={stats['max_rank']} "
        f"mean={stats['mean_rank']:.2f} "
        f"TOP5={stats['top5_count']}/{total}"
    )

print("\nVERDICT")
print("-" * 70)

ti_fe_top1 = top1_counts.get("TiFeH2", 0)
ti_mn_top1 = top1_counts.get("TiMn1.5", 0)

if ti_fe_top1 == total:
    verdict = "ROBUST_TOP1_TIFEH2"
elif ti_fe_top1 + ti_mn_top1 == total:
    verdict = "ROBUST_METAL_HYDRIDE_TOP1"
else:
    verdict = "SENSITIVE"

print(f"TOP1 TiFeH2 : {ti_fe_top1}/{total}")
print(f"TOP1 TiMn1.5 : {ti_mn_top1}/{total}")
print(f"VERDICT : {verdict}")

print("\nCONCLUSION")
print("-" * 70)

if verdict == "ROBUST_TOP1_TIFEH2":
    conclusion = (
        "TiFeH2 reste TOP1 dans tous les scenarios testes. "
        "Le choix du TOP1 est robuste."
    )
elif verdict == "ROBUST_METAL_HYDRIDE_TOP1":
    conclusion = (
        "Le TOP1 varie entre TiFeH2 et TiMn1.5, mais aucun MOF "
        "ne devient TOP1. Le domaine des hydrures metalliques est robuste."
    )
else:
    conclusion = (
        "Le classement reste sensible aux hypotheses de coverage. "
        "Un classement definitif necessite une regle de coverage explicite."
    )

print(conclusion)

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "material",
        "min_rank",
        "max_rank",
        "mean_rank",
        "top5_count",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for material, stats in candidate_stats.items():
        writer.writerow({
            "material": material,
            **stats,
        })

result = {
    "phase": 54,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "materials": materials,
    "scenarios": scenarios,
    "top1_counts": top1_counts,
    "candidate_statistics": candidate_stats,
    "h2_ranking": h2_rank,
    "ambient_ranking": ambient_rank,
    "scientific_ranking": scientific_rank,
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
            "phase": 54,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "purpose": "Sensitivity analysis of corrected scientific ranking",
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
print("PHASE 54 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
