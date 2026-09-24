#!/usr/bin/env python3

from pathlib import Path
import json
from collections import defaultdict

ROOT = Path("/home/hk/HydroMatAI")

SRC = ROOT / "calculations/phase_34_find_top5_h2_producer/phase34_find_top5_h2_producer.json"

print("=" * 70)
print("PHASE 35 — RANK H2 PRODUCERS")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("EXECUTION : NO")
print("QE : NO")
print("CIF MODIFICATION : NO")
print("=" * 70)

data = json.loads(SRC.read_text(encoding="utf-8"))

refs = data.get("references", [])

by_file = defaultdict(list)

for r in refs:
    by_file[r["file"]].append(r)

print()
print("FICHIERS UNIQUES :", len(by_file))
print()

ranked = []

for file, entries in by_file.items():

    path = Path(file)

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        text = ""

    low = text.lower()

    score = 0
    reasons = []

    # Référence directe au fichier cible
    score += 10
    reasons.append("TARGET_REFERENCE")

    # Indices forts de génération
    strong = [
        "to_csv",
        "writerow",
        "writerows",
        "csv.writer",
        "csv.dictwriter",
        ".open(\"w\"",
        ".open('w'",
    ]

    for k in strong:
        if k in low:
            score += 20
            reasons.append(k)

    # Indices de calcul H2
    h2_terms = [
        "hydrogen_score",
        "hydrogen_wt_percent",
        "h2_score",
        "h2_capacity",
        "hydrogen",
        "h2",
    ]

    h2_hits = sum(low.count(k) for k in h2_terms)

    if h2_hits:
        score += min(h2_hits * 3, 30)
        reasons.append(f"H2_TERMS={h2_hits}")

    # Indices de génération de top5
    for k in [
        "top5",
        "rank",
        "sort_values",
        "nlargest",
        "head(5)",
        "[:5]",
    ]:
        if k in low:
            score += 5
            reasons.append(k)

    # Pénalité forte pour scripts d'audit / trace
    if any(k in path.name.lower() for k in [
        "audit",
        "trace",
        "diagnostic",
        "provenance",
        "phase",
    ]):
        score -= 15
        reasons.append("AUDIT_TRACE_PENALTY")

    ranked.append({
        "score": score,
        "file": file,
        "references": len(entries),
        "reasons": reasons,
    })

ranked.sort(
    key=lambda x: (
        x["score"],
        x["references"]
    ),
    reverse=True
)

print("=" * 70)
print("CLASSEMENT")
print("-" * 70)

for i, r in enumerate(ranked, 1):

    print()
    print(f"#{i} SCORE={r['score']} REFERENCES={r['references']}")
    print("FILE :", r["file"])
    print("WHY  :", ", ".join(r["reasons"]))

print()
print("=" * 70)
print("TOP 10 — INSPECTION")
print("-" * 70)

for i, r in enumerate(ranked[:10], 1):

    print()
    print(f"[{i}] {r['file']}")

    path = Path(r["file"])

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    # Affiche uniquement les lignes qui peuvent produire le CSV,
    # calculer H2 ou sélectionner le TOP5.
    shown = set()

    for n, line in enumerate(lines, 1):

        low = line.lower()

        if any(k in low for k in [
            "top5_dft_h2",
            "hydrogen_score",
            "hydrogen_wt_percent",
            "h2_score",
            "h2_capacity",
            "to_csv",
            "writerow",
            "writerows",
            "sort_values",
            "nlargest",
            "head(5)",
            "hydrogen",
        ]):

            start = max(1, n - 2)
            end = min(len(lines), n + 2)

            for j in range(start, end + 1):

                if j not in shown:
                    print(
                        f"L{j}: {lines[j-1]}"
                    )
                    shown.add(j)

print()
print("=" * 70)
print("FIN PHASE 35")
print("=" * 70)
