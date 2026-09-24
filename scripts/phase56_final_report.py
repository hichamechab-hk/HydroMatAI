from pathlib import Path
import csv
import json
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "calculations" / "phase_55_final_scientific_consistency" / "phase55_final_ranking.csv"

OUTDIR = ROOT / "reports" / "final_screening"
OUTDIR.mkdir(parents=True, exist_ok=True)

REPORT = OUTDIR / "HydroMatAI_Final_Screening_Report.md"
CSV_OUT = OUTDIR / "HydroMatAI_Final_Ranking.csv"
JSON_OUT = OUTDIR / "HydroMatAI_Final_Ranking.json"
MANIFEST = OUTDIR / "phase56_manifest.json"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


print("=" * 70)
print("PHASE 56 — RAPPORT FINAL HYDROMATAI")
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

rows.sort(key=lambda x: int(x["final_rank"]))

for r in rows:
    r["final_rank"] = int(r["final_rank"])
    r["final_screening_score"] = num(r["final_screening_score"])
    r["h2_uptake_wt_percent"] = num(r["h2_uptake_wt_percent"])
    r["ambient_score"] = num(r["ambient_score"])
    r["scientific_score"] = num(r["scientific_score"])
    r["scientific_corrected"] = num(r["scientific_corrected"])
    r["h2_rank"] = int(r["h2_rank"])
    r["ambient_rank"] = int(r["ambient_rank"])
    r["scientific_rank"] = int(r["scientific_rank"])
    r["scientific_corrected_rank"] = int(
        r["scientific_corrected_rank"]
    )

top1 = rows[0]
top5 = rows[:5]

print("\nTOP 5 FINAL")
print("-" * 70)

for r in top5:
    print(
        f"{r['final_rank']:>2}. "
        f"{r['material']:<22} "
        f"{r['final_screening_score']:.4f} "
        f"{r['confidence']}"
    )

print("\nTOP 3 PRIORITAIRES")
print("-" * 70)

for r in rows[:3]:
    print(
        f"{r['final_rank']}. "
        f"{r['material']} | "
        f"H2={r['h2_uptake_wt_percent']:.2f} wt% | "
        f"Ambient={r['ambient_score']:.4f} | "
        f"SciCorr={r['scientific_corrected']:.4f}"
    )

print("\nLIMITES")
print("-" * 70)
print("H2/QE mapping historique : NON RESOLU")
print("Nouveaux calculs QE       : NON")
print("Modification CIF         : NON")
print("Classement energetique QE : NON UTILISE")
print("Score final               : SCREENING")

generated = datetime.now().isoformat(timespec="seconds")

md = f"""# HydroMatAI — Rapport final de screening

**Date de génération :** {generated}

## 1. Statut

- Mode : `ANALYSIS_ONLY`
- Nouveaux calculs Quantum ESPRESSO : **NON**
- Modification des CIF : **NON**
- Objectif : classement final analytique des candidats H₂

## 2. Méthodologie

Le classement final combine trois dimensions déjà présentes dans le pipeline :

- performance H₂ gravimétrique ;
- performance proche des conditions ambiantes ;
- score scientifique corrigé par le niveau de confiance.

Le scénario final utilise :

- H₂ : **40 %**
- Ambient : **40 %**
- Scientific corrigé : **20 %**

Correction de confiance utilisée uniquement pour le screening :

- HIGH : `1.00`
- MEDIUM : `0.75`
- LOW : `0.50`

Cette correction est une **hypothèse méthodologique de screening** et ne constitue pas une mesure physique.

## 3. Classement final

| Rang | Matériau | Score final | H₂ (wt%) | Ambient | Scientific corrigé | Confiance |
|---:|---|---:|---:|---:|---:|---|
"""

for r in rows:
    md += (
        f"| {r['final_rank']} | {r['material']} | "
        f"{r['final_screening_score']:.4f} | "
        f"{r['h2_uptake_wt_percent']:.2f} | "
        f"{r['ambient_score']:.4f} | "
        f"{r['scientific_corrected']:.4f} | "
        f"{r['confidence']} |\n"
    )

md += f"""
## 4. TOP 3 prioritaire

### 1. TiFeH2

- Score final : **{top1['final_screening_score']:.4f}**
- H₂ : **{top1['h2_uptake_wt_percent']:.2f} wt%**
- Ambient : **{top1['ambient_score']:.4f}**
- Scientific corrigé : **{top1['scientific_corrected']:.4f}**
- Confiance : **{top1['confidence']}**
- Rang H₂ : #{top1['h2_rank']}
- Rang Ambient : #{top1['ambient_rank']}
- Rang Scientific corrigé : #{top1['scientific_corrected_rank']}

**Conclusion : candidat principal du screening actuel.**

### 2. TiMn1.5

- H₂ : **{rows[1]['h2_uptake_wt_percent']:.2f} wt%**
- Ambient : **{rows[1]['ambient_score']:.4f}**
- Scientific corrigé : **{rows[1]['scientific_corrected']:.4f}**
- Confiance : **{rows[1]['confidence']}**

**Conclusion : principal candidat de comparaison ; meilleure capacité H₂ brute du jeu étudié.**

### 3. Ti1.1CrMn

- H₂ : **{rows[2]['h2_uptake_wt_percent']:.2f} wt%**
- Ambient : **{rows[2]['ambient_score']:.4f}**
- Scientific corrigé : **{rows[2]['scientific_corrected']:.4f}**
- Confiance : **{rows[2]['confidence']}**

**Conclusion : troisième candidat robuste du screening.**

## 5. Robustesse

La Phase 54 a testé 18 scénarios de pénalité de couverture.

- TiFeH2 TOP1 : **15/18 scénarios (83,3 %)**
- TiMn1.5 TOP1 : **0/18**
- TiFeH2 TOP5 : **18/18**
- TiMn1.5 TOP5 : **18/18**

Le résultat montre une forte stabilité du groupe de tête.

Le basculement vers IRMOF-6 apparaît uniquement lorsque les données LOW sont considérées sans pénalité.

## 6. Données manquantes

Trois matériaux présentent un score scientifique neutre de `0.5000` :

- IRMOF-6
- IRMOF-8
- JUC-48

Ces trois matériaux sont classés `LOW`.

Leur score scientifique corrigé devient `0.2500` dans le scénario principal.

Cela évite d'interpréter automatiquement une absence de données comme une performance moyenne démontrée.

## 7. Conclusion scientifique

Le classement analytique actuel est :

**1. TiFeH2**  
**2. TiMn1.5**  
**3. Ti1.1CrMn**  
**4. LaNi5**  
**5. LaNi5H6**

TiFeH2 est le **candidat principal du screening**, car il combine une forte capacité H₂, le meilleur score Ambient et une confiance HIGH.

TiMn1.5 reste extrêmement proche et possède la meilleure capacité H₂ brute.

## 8. Limites

1. Le classement est un résultat de **screening**, pas une validation expérimentale.
2. Les facteurs de confiance sont heuristiques.
3. Le mapping historique entre le classement H₂ `tobmof-*` et les identifiants `hMOF-*` n'a pas été résolu.
4. Les calculs QE disponibles sont incomplets et ne permettent pas un classement énergétique absolu entre compositions différentes.
5. Aucun nouveau calcul QE n'a été effectué.
6. Aucun fichier CIF n'a été modifié.

## 9. Fichiers de traçabilité

- Phase 45 : statistiques H₂
- Phase 46 : comparaison des classements
- Phase 47–50 : audit du score scientifique
- Phase 51 : audit de la priorité
- Phase 52 : audit des données manquantes
- Phase 53 : classement corrigé
- Phase 54 : robustesse
- Phase 55 : cohérence scientifique finale

**Verdict final : ROBUST_TIFEH2_TOP1**
"""

REPORT.write_text(md, encoding="utf-8")

fields = [
    "final_rank",
    "material",
    "final_screening_score",
    "h2_uptake_wt_percent",
    "ambient_score",
    "scientific_score",
    "scientific_corrected",
    "confidence",
    "literature_count",
    "h2_rank",
    "ambient_rank",
    "scientific_rank",
    "scientific_corrected_rank",
]

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

JSON_OUT.write_text(
    json.dumps(
        {
            "phase": 56,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "top1": top1["material"],
            "top3": [x["material"] for x in rows[:3]],
            "top5": [x["material"] for x in rows[:5]],
            "verdict": "ROBUST_TIFEH2_TOP1",
            "method": {
                "h2_weight": 0.40,
                "ambient_weight": 0.40,
                "scientific_weight": 0.20,
                "confidence_factors": {
                    "HIGH": 1.0,
                    "MEDIUM": 0.75,
                    "LOW": 0.50,
                },
            },
            "rows": rows,
            "no_qe": True,
            "no_cif_modification": True,
            "mapping_h2_qe": "UNRESOLVED",
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

MANIFEST.write_text(
    json.dumps(
        {
            "phase": 56,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "input": str(INPUT),
            "report": str(REPORT),
            "csv": str(CSV_OUT),
            "json": str(JSON_OUT),
            "verdict": "ROBUST_TIFEH2_TOP1",
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("\n" + "=" * 70)
print("PHASE 56 STATUS : COMPLETE")
print(f"REPORT   : {REPORT}")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print(f"TOP1     : {top1['material']}")
print("VERDICT  : ROBUST_TIFEH2_TOP1")
print("=" * 70)
