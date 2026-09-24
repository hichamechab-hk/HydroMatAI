from pathlib import Path
import csv
import json
import statistics

ROOT = Path("/home/hk/HydroMatAI")

INPUT = ROOT / "reports" / "dft_h2_priority.csv"
OUTDIR = ROOT / "calculations" / "phase_46_h2_rank_comparison"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase46_rank_comparison.csv"
JSON_OUT = OUTDIR / "phase46_rank_comparison.json"
MANIFEST = OUTDIR / "phase46_manifest.json"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


print("=" * 70)
print("PHASE 46 — COMPARAISON DES CLASSEMENTS H2")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("QE   : NON")
print("CIF  : NON MODIFIE")
print("=" * 70)

if not INPUT.exists():
    print(f"STATUS : INPUT_NOT_FOUND")
    print(INPUT)
    raise SystemExit(1)

with INPUT.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    print("STATUS : EMPTY_INPUT")
    raise SystemExit(1)


def rank_by(field):
    valid = [r for r in rows if num(r.get(field)) is not None]
    valid.sort(key=lambda r: num(r.get(field)), reverse=True)
    return {
        r.get("material"): i
        for i, r in enumerate(valid, start=1)
    }


rank_h2 = rank_by("h2_uptake_wt_percent")
rank_ambient = rank_by("ambient_score")
rank_scientific = rank_by("scientific_score")

rank_priority = {}
for i, r in enumerate(rows, start=1):
    rank_priority[r.get("material")] = i


print(f"\nMATERIAUX : {len(rows)}")

print("\nTOP 20 — H2 UPTAKE")
print("-" * 70)

for i, r in enumerate(
    sorted(
        rows,
        key=lambda x: num(x.get("h2_uptake_wt_percent")) or float("-inf"),
        reverse=True,
    )[:20],
    1,
):
    print(
        f"{i:2d}. {r.get('material',''):<22} "
        f"H2={num(r.get('h2_uptake_wt_percent')):.3f} wt% "
        f"ambient={num(r.get('ambient_score')):.4f} "
        f"scientific={num(r.get('scientific_score')):.4f} "
        f"priority={rank_priority.get(r.get('material'))}"
    )


print("\nTOP 20 — AMBIENT SCORE")
print("-" * 70)

for i, r in enumerate(
    sorted(
        rows,
        key=lambda x: num(x.get("ambient_score")) or float("-inf"),
        reverse=True,
    )[:20],
    1,
):
    print(
        f"{i:2d}. {r.get('material',''):<22} "
        f"ambient={num(r.get('ambient_score')):.4f} "
        f"H2={num(r.get('h2_uptake_wt_percent')):.3f} wt% "
        f"scientific={num(r.get('scientific_score')):.4f} "
        f"priority={rank_priority.get(r.get('material'))}"
    )


print("\nTOP 20 — SCIENTIFIC SCORE")
print("-" * 70)

for i, r in enumerate(
    sorted(
        rows,
        key=lambda x: num(x.get("scientific_score")) or float("-inf"),
        reverse=True,
    )[:20],
    1,
):
    print(
        f"{i:2d}. {r.get('material',''):<22} "
        f"scientific={num(r.get('scientific_score')):.4f} "
        f"H2={num(r.get('h2_uptake_wt_percent')):.3f} wt% "
        f"ambient={num(r.get('ambient_score')):.4f} "
        f"priority={rank_priority.get(r.get('material'))}"
    )


print("\nTOP 20 — PRIORITY FINAL")
print("-" * 70)

for i, r in enumerate(rows[:20], 1):
    print(
        f"{i:2d}. {r.get('material',''):<22} "
        f"priority={i} "
        f"H2={num(r.get('h2_uptake_wt_percent')):.3f} wt% "
        f"ambient={num(r.get('ambient_score')):.4f} "
        f"scientific={num(r.get('scientific_score')):.4f}"
    )


comparison = []

for r in rows:
    material = r.get("material")

    h2r = rank_h2.get(material)
    ar = rank_ambient.get(material)
    sr = rank_scientific.get(material)
    pr = rank_priority.get(material)

    ranks = [x for x in (h2r, ar, sr, pr) if x is not None]

    spread = max(ranks) - min(ranks) if ranks else None

    comparison.append(
        {
            "material": material,
            "h2_uptake_wt_percent": r.get("h2_uptake_wt_percent"),
            "ambient_score": r.get("ambient_score"),
            "scientific_score": r.get("scientific_score"),
            "h2_rank": h2r,
            "ambient_rank": ar,
            "scientific_rank": sr,
            "priority_rank": pr,
            "rank_spread": spread,
            "confidence": r.get("confidence"),
        }
    )


comparison.sort(
    key=lambda x: x["rank_spread"]
    if x["rank_spread"] is not None
    else -1,
    reverse=True,
)

print("\nPLUS GRAND ECART DE CLASSEMENT")
print("-" * 70)

for i, r in enumerate(comparison[:20], 1):
    print(
        f"{i:2d}. {r['material']:<22} "
        f"H2#{r['h2_rank']} "
        f"Ambient#{r['ambient_rank']} "
        f"Scientific#{r['scientific_rank']} "
        f"Priority#{r['priority_rank']} "
        f"spread={r['rank_spread']}"
    )


print("\nANALYSE TOP 10 PRIORITY")
print("-" * 70)

top10 = rows[:10]

for r in top10:
    material = r.get("material")
    print(
        f"{material:<22} "
        f"H2#{rank_h2.get(material)} | "
        f"Ambient#{rank_ambient.get(material)} | "
        f"Scientific#{rank_scientific.get(material)} | "
        f"Priority#{rank_priority.get(material)}"
    )


def spearman(rank_a, rank_b):
    pairs = []

    for material in rank_a:
        if material in rank_b:
            pairs.append((rank_a[material], rank_b[material]))

    if len(pairs) < 2:
        return None

    a = [x for x, _ in pairs]
    b = [y for _, y in pairs]

    ma = statistics.mean(a)
    mb = statistics.mean(b)

    nume = sum((x - ma) * (y - mb) for x, y in pairs)
    dena = sum((x - ma) ** 2 for x in a) ** 0.5
    denb = sum((y - mb) ** 2 for y in b) ** 0.5

    if dena == 0 or denb == 0:
        return None

    return nume / (dena * denb)


correlations = {
    "H2_vs_Ambient": spearman(rank_h2, rank_ambient),
    "H2_vs_Scientific": spearman(rank_h2, rank_scientific),
    "H2_vs_Priority": spearman(rank_h2, rank_priority),
    "Ambient_vs_Scientific": spearman(rank_ambient, rank_scientific),
    "Ambient_vs_Priority": spearman(rank_ambient, rank_priority),
    "Scientific_vs_Priority": spearman(rank_scientific, rank_priority),
}

print("\nCORRELATIONS DE RANG")
print("-" * 70)

for k, v in correlations.items():
    print(f"{k:<28}: {v}")


CSV_FIELDS = [
    "material",
    "h2_uptake_wt_percent",
    "ambient_score",
    "scientific_score",
    "h2_rank",
    "ambient_rank",
    "scientific_rank",
    "priority_rank",
    "rank_spread",
    "confidence",
]

with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(comparison)


result = {
    "phase": 46,
    "mode": "ANALYSIS_ONLY",
    "input": str(INPUT),
    "material_count": len(rows),
    "correlations": correlations,
    "comparison": comparison,
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
            "phase": 46,
            "mode": "ANALYSIS_ONLY",
            "status": "COMPLETE",
            "purpose": "Compare H2, ambient, scientific and final priority rankings",
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
print("PHASE 46 STATUS : COMPLETE")
print(f"CSV      : {CSV_OUT}")
print(f"JSON     : {JSON_OUT}")
print(f"MANIFEST : {MANIFEST}")
print("=" * 70)
