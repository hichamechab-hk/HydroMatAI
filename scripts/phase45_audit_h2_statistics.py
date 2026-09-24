from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
LITERATURE = ROOT / "data" / "literature" / "published_results.csv"

OUTDIR = ROOT / "calculations" / "phase_45_h2_statistics"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase45_h2_statistics.csv"
JSON_OUT = OUTDIR / "phase45_h2_statistics.json"
MANIFEST = OUTDIR / "phase45_manifest.json"


def f(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def stats(values):
    values = [x for x in values if x is not None]

    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stdev": None,
        }

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


print("=" * 70)
print("PHASE 45 — AUDIT STATISTIQUE H2")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("QE   : NON")
print("CIF  : NON MODIFIE")
print("=" * 70)

if not INPUT.exists():
    print(f"STATUS : INPUT_NOT_FOUND")
    print(f"INPUT  : {INPUT}")
    raise SystemExit(1)

with INPUT.open("r", encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

print(f"\nINPUT : {INPUT}")
print(f"ROWS  : {len(rows)}")

if not rows:
    print("STATUS : EMPTY_INPUT")
    raise SystemExit(1)

fields = list(rows[0].keys())

print("\nCOLUMNS")
print("-" * 70)
for field in fields:
    print(field)

h2 = []
temperature = []
pressure = []
ambient = []
scientific = []
screening = []
confidence = []

for row in rows:
    h2.append(f(row.get("h2_uptake_wt_percent")))
    temperature.append(f(row.get("temperature_k")))
    pressure.append(f(row.get("pressure_mpa")))
    ambient.append(f(row.get("ambient_score")))
    scientific.append(f(row.get("scientific_score")))

    # Le fichier dft_h2_priority ne contient pas nécessairement
    # screening_score : on l'identifie si présent.
    screening.append(f(row.get("screening_score")))

    confidence.append(
        str(row.get("confidence", "")).strip().upper()
    )

datasets = {
    "h2_uptake_wt_percent": h2,
    "temperature_k": temperature,
    "pressure_mpa": pressure,
    "ambient_score": ambient,
    "scientific_score": scientific,
    "screening_score": screening,
}

print("\nSTATISTIQUES")
print("-" * 70)

statistics_result = {}

for name, values in datasets.items():
    s = stats(values)
    statistics_result[name] = s

    print(f"\n{name}")
    print(f"  count  : {s['count']}")
    print(f"  min    : {s['min']}")
    print(f"  max    : {s['max']}")
    print(f"  mean   : {s['mean']}")
    print(f"  median : {s['median']}")
    print(f"  stdev  : {s['stdev']}")

print("\nCONFIDENCE")
print("-" * 70)

confidence_counts = {}

for c in confidence:
    confidence_counts[c] = confidence_counts.get(c, 0) + 1

for c, n in sorted(confidence_counts.items()):
    print(f"{c or '<EMPTY>':10s} : {n}")

print("\nSATURATION / SUSPECT VALUES")
print("-" * 70)

suspects = []

for i, row in enumerate(rows, start=1):

    h2v = f(row.get("h2_uptake_wt_percent"))
    av = f(row.get("ambient_score"))
    sv = f(row.get("scientific_score"))
    sc = f(row.get("screening_score"))
    tv = f(row.get("temperature_k"))
    pv = f(row.get("pressure_mpa"))

    reasons = []

    if av is not None and av >= 0.9999:
        reasons.append("ambient_score≈1")

    if sv is not None and sv >= 0.9999:
        reasons.append("scientific_score≈1")

    if sc is not None and sc >= 0.9999:
        reasons.append("screening_score≈1")

    if h2v is not None and h2v > 10:
        reasons.append("H2>10wt%")

    if tv is not None and not 280 <= tv <= 303:
        reasons.append("temperature_outside_280_303K")

    if pv is not None and pv <= 0:
        reasons.append("nonpositive_pressure")

    if reasons:
        suspects.append({
            "row": i,
            "material": row.get("material"),
            "h2": h2v,
            "temperature": tv,
            "pressure": pv,
            "ambient": av,
            "scientific": sv,
            "screening": sc,
            "reasons": reasons,
        })

    if len(suspects) <= 30 and reasons:
        print(
            f"{i:4d} | "
            f"{row.get('material',''):<20} | "
            f"H2={h2v} | "
            f"T={tv} | "
            f"P={pv} | "
            f"ambient={av} | "
            f"scientific={sv} | "
            f"{','.join(reasons)}"
        )

print(f"\nSUSPECT ROWS : {len(suspects)}")

print("\nTOP 20 — H2 UPTAKE")
print("-" * 70)

rank_h2 = sorted(
    rows,
    key=lambda r: f(r.get("h2_uptake_wt_percent")) or float("-inf"),
    reverse=True,
)

for rank, row in enumerate(rank_h2[:20], start=1):
    print(
        f"{rank:2d}. "
        f"{row.get('material',''):<20} "
        f"H2={f(row.get('h2_uptake_wt_percent'))} wt% "
        f"T={f(row.get('temperature_k'))} K "
        f"P={f(row.get('pressure_mpa'))} MPa "
        f"ambient={f(row.get('ambient_score'))} "
        f"scientific={f(row.get('scientific_score'))}"
    )

print("\nTOP 20 — AMBIENT SCORE")
print("-" * 70)

rank_ambient = sorted(
    rows,
    key=lambda r: f(r.get("ambient_score")) or float("-inf"),
    reverse=True,
)

for rank, row in enumerate(rank_ambient[:20], start=1):
    print(
        f"{rank:2d}. "
        f"{row.get('material',''):<20} "
        f"ambient={f(row.get('ambient_score'))} "
        f"H2={f(row.get('h2_uptake_wt_percent'))} wt% "
        f"T={f(row.get('temperature_k'))} K "
        f"P={f(row.get('pressure_mpa'))} MPa"
    )

print("\nTOP 20 — SCIENTIFIC SCORE")
print("-" * 70)

rank_scientific = sorted(
    rows,
    key=lambda r: f(r.get("scientific_score")) or float("-inf"),
    reverse=True,
)

for rank, row in enumerate(rank_scientific[:20], start=1):
    print(
        f"{rank:2d}. "
        f"{row.get('material',''):<20} "
        f"scientific={f(row.get('scientific_score'))} "
        f"H2={f(row.get('h2_uptake_wt_percent'))} wt% "
        f"ambient={f(row.get('ambient_score'))}"
    )

print("\nTOP 20 — PRIORITY")
print("-" * 70)

for rank, row in enumerate(rows[:20], start=1):
    print(
        f"{rank:2d}. "
        f"{row.get('material',''):<20} "
        f"H2={f(row.get('h2_uptake_wt_percent'))} wt% "
        f"ambient={f(row.get('ambient_score'))} "
        f"scientific={f(row.get('scientific_score'))}"
    )

# Corrélations simples
def correlation(a, b):
    pairs = [
        (x, y)
        for x, y in zip(a, b)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return None

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]

    mx = statistics.mean(xs)
    my = statistics.mean(ys)

    num = sum((x - mx) * (y - my) for x, y in pairs)
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))

    if den_x == 0 or den_y == 0:
        return None

    return num / (den_x * den_y)


corr = {
    "h2_vs_ambient": correlation(h2, ambient),
    "h2_vs_scientific": correlation(h2, scientific),
    "ambient_vs_scientific": correlation(ambient, scientific),
}

print("\nCORRELATIONS")
print("-" * 70)

for name, value in corr.items():
    print(f"{name:25s}: {value}")

# Export compact row audit
audit_rows = []

for i, row in enumerate(rows, start=1):
    audit_rows.append({
        "row": i,
        "material": row.get("material"),
        "h2_uptake_wt_percent": row.get("h2_uptake_wt_percent"),
        "temperature_k": row.get("temperature_k"),
        "pressure_mpa": row.get("pressure_mpa"),
        "ambient_score": row.get("ambient_score"),
        "scientific_score": row.get("scientific_score"),
        "screening_score": row.get("screening_score"),
        "confidence": row.get("confidence"),
        "literature_count": row.get("literature_count"),
    })

with CSV_OUT.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=audit_rows[0].keys(),
    )
    writer.writeheader()
    writer.writerows(audit_rows)

result = {
    "phase": 45,
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "literature_input": str(LITERATURE),
    "row_count": len(rows),
    "columns": fields,
    "statistics": statistics_result,
    "confidence_counts": confidence_counts,
    "suspect_rows": suspects,
    "correlations": corr,
    "status": "COMPLETE",
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
            "phase": 45,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
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
print("PHASE 45 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
