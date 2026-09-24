#!/usr/bin/env python3

from pathlib import Path
import ast
import csv
import json
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
TARGET = ROOT / "reports/top5_dft_h2.csv"

OUT = ROOT / "calculations/phase_34_find_top5_h2_producer"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("PHASE 34 — PRODUCTEUR top5_dft_h2.csv")
print("-" * 70)
print("MODE : ANALYSIS_ONLY")
print("EXECUTION : NO")
print("QE : NO")
print("CIF MODIFICATION : NO")
print("=" * 70)

print("TARGET :", TARGET)
print("EXISTS :", TARGET.exists())

if TARGET.exists():
    print("SIZE   :", TARGET.stat().st_size)

    try:
        with TARGET.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        print("ROWS   :", len(rows))
        print("HEADER :", rows[0] if rows else None)

        for row in rows[:6]:
            print("ROW    :", row)

    except Exception as e:
        print("READ ERROR :", repr(e))

results = []

# Recherche uniquement dans les scripts et fichiers texte pertinents.
search_roots = [
    ROOT / "scripts",
    ROOT / "reports",
    ROOT / "calculations",
]

for base in search_roots:

    if not base.exists():
        continue

    for path in base.rglob("*"):

        if not path.is_file():
            continue

        if path == TARGET:
            continue

        if path.stat().st_size > 10_000_000:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        # Plusieurs formes possibles de référence.
        needles = [
            "top5_dft_h2.csv",
            "top5_dft_h2",
        ]

        if not any(n in text for n in needles):
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines, 1):

            if any(n in line for n in needles):

                context = []

                for j in range(
                    max(0, i - 3),
                    min(len(lines), i + 2)
                ):
                    context.append({
                        "line": j + 1,
                        "text": lines[j]
                    })

                results.append({
                    "file": str(path),
                    "line": i,
                    "text": line,
                    "context": context,
                })

print()
print("=" * 70)
print("REFERENCES TROUVEES")
print("-" * 70)
print("COUNT :", len(results))

for r in results:

    print()
    print("-" * 70)
    print("FILE :", r["file"])
    print("LINE :", r["line"])

    for c in r["context"]:
        print(
            f"L{c['line']}: {c['text']}"
        )

# Recherche spécifique des écritures CSV potentielles
producer_candidates = []

for r in results:

    text = r["text"].lower()

    if any(k in text for k in [
        "write",
        "writer",
        "to_csv",
        "csv",
        "open",
    ]):

        producer_candidates.append(r)

print()
print("=" * 70)
print("CANDIDATS PRODUCTEURS")
print("-" * 70)
print("COUNT :", len(producer_candidates))

for r in producer_candidates:
    print(
        f"{r['file']} : L{r['line']} : {r['text']}"
    )

csv_out = OUT / "phase34_find_top5_h2_producer.csv"
json_out = OUT / "phase34_find_top5_h2_producer.json"
manifest_out = OUT / "phase34_manifest.json"

with csv_out.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    w = csv.writer(f)
    w.writerow([
        "file",
        "line",
        "text",
    ])

    for r in results:
        w.writerow([
            r["file"],
            r["line"],
            r["text"],
        ])

json_out.write_text(
    json.dumps(
        {
            "phase": 34,
            "mode": "ANALYSIS_ONLY",
            "target": str(TARGET),
            "target_exists": TARGET.exists(),
            "references": results,
            "producer_candidates": producer_candidates,
            "no_execution": True,
            "no_qe": True,
            "no_cif_modification": True,
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8"
)

manifest_out.write_text(
    json.dumps(
        {
            "phase": 34,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "target": str(TARGET),
            "references": len(results),
            "producer_candidates": len(
                producer_candidates
            ),
            "no_execution": True,
            "no_qe": True,
            "no_cif_modification": True,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("PHASE 34 — RESULT")
print("-" * 70)
print("REFERENCES :", len(results))
print("PRODUCERS  :", len(producer_candidates))
print()
print("CSV     :", csv_out)
print("JSON    :", json_out)
print("MANIFEST:", manifest_out)
print("=" * 70)
