from pathlib import Path
import ast
import csv
import json

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
OUTDIR = ROOT / "calculations" / "phase_51_priority_audit"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase51_priority_audit.csv"
JSON_OUT = OUTDIR / "phase51_priority_audit.json"
MANIFEST = OUTDIR / "phase51_manifest.json"


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def search_project(term):
    hits = []
    for base in [
        ROOT / "scripts",
        ROOT / "src",
        ROOT / "reports",
    ]:
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for i, line in enumerate(text.splitlines(), 1):
                if term.lower() in line.lower():
                    hits.append({
                        "file": str(path),
                        "line": i,
                        "text": line.strip(),
                    })
    return hits


print("=" * 70)
print("PHASE 51 — AUDIT FORMULE PRIORITY")
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

print("\nCOLONNES")
print("-" * 70)

if rows:
    for col in rows[0].keys():
        print(col)

print("\nRECHERCHE DE LA FORMULE PRIORITY")
print("-" * 70)

terms = [
    "priority",
    "final_score",
    "ambient_score",
    "scientific_score",
    "hydrogen_score",
    "dft_h2_priority",
]

all_hits = {}

for term in terms:
    hits = search_project(term)
    all_hits[term] = hits

    print(f"\n[{term}] : {len(hits)} hits")

    shown = 0
    for hit in hits:
        if "phase_51" in hit["file"]:
            continue

        print(
            f"{hit['file']}:{hit['line']} "
            f"| {hit['text']}"
        )

        shown += 1
        if shown >= 15:
            break

print("\nANALYSE DES 8 CANDIDATS")
print("-" * 70)

audit = []

for row in rows:
    def num(key):
        try:
            return float(row.get(key, ""))
        except Exception:
            return None

    item = {
        "priority": row.get("priority", ""),
        "material": row.get("material", ""),
        "h2_uptake_wt_percent": num("h2_uptake_wt_percent"),
        "ambient_score": num("ambient_score"),
        "scientific_score": num("scientific_score"),
        "confidence": row.get("confidence", ""),
        "literature_count": row.get("literature_count", ""),
    }

    audit.append(item)

    print(
        f"{item['priority']:>2} | "
        f"{item['material']:<22} | "
        f"H2={item['h2_uptake_wt_percent']} | "
        f"Ambient={item['ambient_score']} | "
        f"Scientific={item['scientific_score']} | "
        f"{item['confidence']}"
    )

print("\nRANKINGS INDEPENDANTS")
print("-" * 70)

def ranking(key, reverse=True):
    valid = [
        x for x in audit
        if x[key] is not None
    ]
    return sorted(valid, key=lambda x: x[key], reverse=reverse)


for label, key in [
    ("H2", "h2_uptake_wt_percent"),
    ("AMBIENT", "ambient_score"),
    ("SCIENTIFIC", "scientific_score"),
]:
    print(f"\n{label}")

    for i, item in enumerate(ranking(key), 1):
        print(
            f"{i}. {item['material']} "
            f"({item[key]:.4f})"
        )

print("\nTEST DES FORMULES CANDIDATES")
print("-" * 70)

formulas = {
    "ambient_only": lambda x: x["ambient_score"],
    "h2_only": lambda x: x["h2_uptake_wt_percent"],
    "ambient_70_scientific_30":
        lambda x: 0.70 * x["ambient_score"] +
                  0.30 * x["scientific_score"],
    "ambient_80_scientific_20":
        lambda x: 0.80 * x["ambient_score"] +
                  0.20 * x["scientific_score"],
    "ambient_60_scientific_40":
        lambda x: 0.60 * x["ambient_score"] +
                  0.40 * x["scientific_score"],
    "ambient_50_scientific_50":
        lambda x: 0.50 * x["ambient_score"] +
                  0.50 * x["scientific_score"],
}

formula_results = {}

for name, formula in formulas.items():
    scored = []

    for item in audit:
        try:
            value = formula(item)
        except Exception:
            continue

        scored.append({
            "material": item["material"],
            "score": value,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    formula_results[name] = scored

    print(f"\n{name}")

    for i, x in enumerate(scored, 1):
        print(
            f"{i}. {x['material']} "
            f"score={x['score']:.6f}"
        )

print("\nVERIFICATION DU CLASSEMENT ACTUEL")
print("-" * 70)

current = sorted(
    audit,
    key=lambda x: int(x["priority"])
    if str(x["priority"]).isdigit()
    else 999
)

ambient_rank = {
    x["material"]: i
    for i, x in enumerate(
        ranking("ambient_score"),
        1
    )
}

scientific_rank = {
    x["material"]: i
    for i, x in enumerate(
        ranking("scientific_score"),
        1
    )
}

h2_rank = {
    x["material"]: i
    for i, x in enumerate(
        ranking("h2_uptake_wt_percent"),
        1
    )
}

for item in current:
    material = item["material"]

    print(
        f"{material:<22} "
        f"Priority={item['priority']} "
        f"H2_rank={h2_rank.get(material)} "
        f"Ambient_rank={ambient_rank.get(material)} "
        f"Scientific_rank={scientific_rank.get(material)}"
    )

print("\nDIAGNOSTIC")
print("-" * 70)

priority_list = [x["material"] for x in current]
ambient_list = [
    x["material"]
    for x in ranking("ambient_score")
]

if priority_list == ambient_list:
    verdict = (
        "PRIORITY_EQUALS_AMBIENT_RANKING : "
        "le classement final actuel est identique au classement Ambient."
    )
else:
    verdict = (
        "PRIORITY_DIFFERS_FROM_AMBIENT : "
        "le classement final utilise probablement une autre formule "
        "ou un traitement supplementaire."
    )

print(verdict)

print("\nIMPORTANT")
print("-" * 70)
print(
    "Les scores Scientific=0.5000 des trois MOFs sont des valeurs "
    "neutres par defaut et ne doivent pas etre interpretes comme "
    "une preuve de superiorite scientifique."
)

result = {
    "phase": 51,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "materials": audit,
    "search_hits": all_hits,
    "rankings": {
        "h2": h2_rank,
        "ambient": ambient_rank,
        "scientific": scientific_rank,
    },
    "formula_tests": formula_results,
    "verdict": verdict,
    "no_qe": True,
    "no_cif_modification": True,
}

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "priority",
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
            "phase": 51,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "purpose": "Audit exact priority ranking formula",
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
print("PHASE 51 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
