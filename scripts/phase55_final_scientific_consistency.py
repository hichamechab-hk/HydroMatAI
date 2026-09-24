from pathlib import Path
import csv
import json
import statistics

ROOT = Path("/home/hk/HydroMatAI")
INPUT = ROOT / "reports" / "dft_h2_priority.csv"

OUTDIR = ROOT / "calculations" / "phase_55_final_scientific_consistency"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase55_final_ranking.csv"
JSON_OUT = OUTDIR / "phase55_final_ranking.json"
MANIFEST = OUTDIR / "phase55_manifest.json"


def f(v):
    try:
        return float(v)
    except Exception:
        return None


def rank_desc(rows, key):
    valid = [x for x in rows if x[key] is not None]
    valid.sort(key=lambda x: x[key], reverse=True)
    return {x["material"]: i + 1 for i, x in enumerate(valid)}


print("=" * 70)
print("PHASE 55 — AUDIT FINAL DE COHERENCE SCIENTIFIQUE")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("QE   : NON")
print("CIF  : NON MODIFIE")
print("=" * 70)

if not INPUT.exists():
    print("STATUS : INPUT_NOT_FOUND")
    raise SystemExit(1)

with INPUT.open("r", encoding="utf-8", newline="") as fh:
    raw = list(csv.DictReader(fh))

rows = []

for r in raw:
    rows.append({
        "material": r.get("material", ""),
        "h2": f(r.get("h2_uptake_wt_percent")),
        "ambient": f(r.get("ambient_score")),
        "scientific": f(r.get("scientific_score")),
        "confidence": r.get("confidence", ""),
        "literature_count": int(r.get("literature_count") or 0),
    })

print(f"\nMATERIAUX : {len(rows)}")

h2_rank = rank_desc(rows, "h2")
ambient_rank = rank_desc(rows, "ambient")
scientific_rank = rank_desc(rows, "scientific")

print("\nRANGS SOURCES")
print("-" * 70)

for x in rows:
    print(
        f"{x['material']:<22} "
        f"H2={h2_rank.get(x['material'])} "
        f"Ambient={ambient_rank.get(x['material'])} "
        f"Scientific={scientific_rank.get(x['material'])} "
        f"Confidence={x['confidence']:<7} "
        f"Literature={x['literature_count']}"
    )

print("\nCONTROLE DES DONNEES MANQUANTES")
print("-" * 70)

low = []
medium = []
high = []

for x in rows:
    if x["confidence"] == "LOW":
        low.append(x["material"])
    elif x["confidence"] == "MEDIUM":
        medium.append(x["material"])
    elif x["confidence"] == "HIGH":
        high.append(x["material"])

print(f"HIGH   : {len(high)}")
print(f"MEDIUM : {len(medium)}")
print(f"LOW    : {len(low)}")

print("LOW materials :", ", ".join(low) if low else "NONE")

print("\nCONTROLE DES SCORES SCIENTIFIC = 0.5000")
print("-" * 70)

default_scientific = [
    x["material"]
    for x in rows
    if x["scientific"] is not None and abs(x["scientific"] - 0.5) < 1e-9
]

print(
    f"Scientific = 0.5000 : "
    f"{len(default_scientific)}/{len(rows)}"
)

print(
    "Materiaux : ",
    ", ".join(default_scientific) if default_scientific else "NONE"
)

print("\nCLASSEMENT FINAL SCENARIO PRINCIPAL")
print("-" * 70)

# Scenario principal retenu après Phase 54 :
# HIGH = 1.00
# MEDIUM = 0.75
# LOW = 0.50
#
# Le score scientifique corrigé est uniquement un outil
# de screening de confiance, pas une nouvelle mesure physique.

for x in rows:
    if x["scientific"] is None:
        x["scientific_corrected"] = None
    elif x["confidence"] == "HIGH":
        x["scientific_corrected"] = x["scientific"]
    elif x["confidence"] == "MEDIUM":
        x["scientific_corrected"] = x["scientific"] * 0.75
    else:
        x["scientific_corrected"] = x["scientific"] * 0.50

scientific_corrected_rank = rank_desc(
    rows,
    "scientific_corrected",
)

for material, rank in sorted(
    scientific_corrected_rank.items(),
    key=lambda z: z[1],
):
    x = next(a for a in rows if a["material"] == material)
    print(
        f"{rank:>2}. {material:<22} "
        f"score={x['scientific_corrected']:.4f} "
        f"confidence={x['confidence']}"
    )

print("\nCOMPOSITION DU CLASSEMENT FINAL")
print("-" * 70)

h2_values = [x["h2"] for x in rows if x["h2"] is not None]
ambient_values = [x["ambient"] for x in rows if x["ambient"] is not None]
scientific_values = [
    x["scientific_corrected"]
    for x in rows
    if x["scientific_corrected"] is not None
]

max_h2 = max(h2_values) if h2_values else 1.0
max_ambient = max(ambient_values) if ambient_values else 1.0
max_scientific = (
    max(scientific_values)
    if scientific_values
    else 1.0
)

# Score composite de screening :
# 40% H2
# 40% performance ambient
# 20% scientific corrigé par confiance
#
# Il s'agit d'un scénario de synthèse explicite,
# et non d'une modification du score scientifique source.

for x in rows:
    h2_n = x["h2"] / max_h2 if x["h2"] is not None else 0.0
    ambient_n = (
        x["ambient"] / max_ambient
        if x["ambient"] is not None and max_ambient > 0
        else 0.0
    )
    scientific_n = (
        x["scientific_corrected"] / max_scientific
        if x["scientific_corrected"] is not None
        and max_scientific > 0
        else 0.0
    )

    x["h2_normalized"] = h2_n
    x["ambient_normalized"] = ambient_n
    x["scientific_normalized"] = scientific_n

    x["final_screening_score"] = (
        0.40 * h2_n
        + 0.40 * ambient_n
        + 0.20 * scientific_n
    )

final_rank = rank_desc(rows, "final_screening_score")

for material, rank in sorted(
    final_rank.items(),
    key=lambda z: z[1],
):
    x = next(a for a in rows if a["material"] == material)

    print(
        f"{rank:>2}. {material:<22} "
        f"FINAL={x['final_screening_score']:.4f} "
        f"H2={x['h2']:.3f} "
        f"Ambient={x['ambient']:.4f} "
        f"SciCorr={x['scientific_corrected']:.4f} "
        f"{x['confidence']}"
    )

print("\nROBUSTESSE DES TOP CANDIDATS")
print("-" * 70)

for name in ["TiFeH2", "TiMn1.5", "Ti1.1CrMn", "LaNi5", "LaNi5H6"]:
    x = next(a for a in rows if a["material"] == name)

    print(
        f"{name:<22} "
        f"FinalRank={final_rank[name]} "
        f"H2Rank={h2_rank[name]} "
        f"AmbientRank={ambient_rank[name]} "
        f"SciCorrRank={scientific_corrected_rank[name]}"
    )

print("\nTOP MOF CONTROLE")
print("-" * 70)

for name in ["IRMOF-6", "IRMOF-8", "JUC-48"]:
    x = next(a for a in rows if a["material"] == name)

    print(
        f"{name:<22} "
        f"FinalRank={final_rank[name]} "
        f"Scientific={x['scientific']:.4f} "
        f"SciCorr={x['scientific_corrected']:.4f} "
        f"Ambient={x['ambient']:.4f} "
        f"Confidence={x['confidence']}"
    )

print("\nVERDICT FINAL")
print("-" * 70)

top_material = min(final_rank, key=final_rank.get)

tifeh2_rank = final_rank.get("TiFeH2")
timn_rank = final_rank.get("TiMn1.5")

if top_material == "TiFeH2" and tifeh2_rank == 1:
    verdict = "ROBUST_TIFEH2_TOP1"
elif top_material in ["TiFeH2", "TiMn1.5"]:
    verdict = "ROBUST_METAL_HYDRIDE_LEADERS"
else:
    verdict = "SENSITIVE"

print(f"TOP1 FINAL : {top_material}")
print(f"TiFeH2     : #{tifeh2_rank}")
print(f"TiMn1.5    : #{timn_rank}")
print(f"VERDICT    : {verdict}")

print("\nINTERPRETATION")
print("-" * 70)

if verdict == "ROBUST_TIFEH2_TOP1":
    interpretation = (
        "TiFeH2 est le candidat TOP1 du scenario final de screening. "
        "Il combine la meilleure performance ambient, une forte capacite H2 "
        "et une confiance HIGH. Les MOFs a score scientifique 0.5000 "
        "ne dominent plus apres prise en compte de la couverture."
    )
elif verdict == "ROBUST_METAL_HYDRIDE_LEADERS":
    interpretation = (
        "Les hydrures metalliques dominent le scenario final, "
        "mais le TOP1 n'est pas exclusivement TiFeH2."
    )
else:
    interpretation = (
        "Le classement final reste sensible aux hypotheses de scoring "
        "et ne doit pas etre considere comme definitif."
    )

print(interpretation)

print("\nLIMITES")
print("-" * 70)
print("1. Le score final est un scenario de screening.")
print("2. Les penalites de confiance ne sont pas une mesure experimentale.")
print("3. Les energies QE disponibles ne permettent pas un classement energetique inter-composition fiable.")
print("4. Aucune nouvelle simulation QE n'est utilisee.")
print("5. Aucune CIF n'est modifiee.")

output_rows = []

for material, rank in sorted(
    final_rank.items(),
    key=lambda z: z[1],
):
    x = next(a for a in rows if a["material"] == material)

    output_rows.append({
        "final_rank": rank,
        "material": material,
        "final_screening_score": round(
            x["final_screening_score"], 6
        ),
        "h2_uptake_wt_percent": x["h2"],
        "ambient_score": x["ambient"],
        "scientific_score": x["scientific"],
        "scientific_corrected": round(
            x["scientific_corrected"], 6
        ),
        "confidence": x["confidence"],
        "literature_count": x["literature_count"],
        "h2_rank": h2_rank.get(material),
        "ambient_rank": ambient_rank.get(material),
        "scientific_rank": scientific_rank.get(material),
        "scientific_corrected_rank":
            scientific_corrected_rank.get(material),
    })

with CSV_OUT.open("w", encoding="utf-8", newline="") as fh:
    fields = list(output_rows[0].keys())
    writer = csv.DictWriter(fh, fieldnames=fields)
    writer.writeheader()
    writer.writerows(output_rows)

result = {
    "phase": 55,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "final_method": {
        "h2_weight": 0.40,
        "ambient_weight": 0.40,
        "scientific_weight": 0.20,
        "confidence_penalty": {
            "HIGH": 1.0,
            "MEDIUM": 0.75,
            "LOW": 0.50,
        },
    },
    "rankings": {
        "h2": h2_rank,
        "ambient": ambient_rank,
        "scientific": scientific_rank,
        "scientific_corrected": scientific_corrected_rank,
        "final": final_rank,
    },
    "top1": top_material,
    "tifeh2_rank": tifeh2_rank,
    "timn1_rank": timn_rank,
    "verdict": verdict,
    "interpretation": interpretation,
    "limitations": [
        "Scenario de screening",
        "Penalites de confiance heuristiques",
        "Pas de nouveau calcul QE",
        "Pas de modification CIF",
        "Energies QE inter-compositions non utilisees comme classement absolu",
    ],
}

JSON_OUT.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

MANIFEST.write_text(
    json.dumps(
        {
            "phase": 55,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "purpose": "Final scientific consistency audit",
            "input": str(INPUT),
            "output_csv": str(CSV_OUT),
            "output_json": str(JSON_OUT),
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("\n" + "=" * 70)
print("PHASE 55 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
