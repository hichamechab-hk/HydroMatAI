#!/usr/bin/env python3

from pathlib import Path
import csv
import json
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
TARGET = ROOT / "reports/dft_h2_priority.csv"

OUT = ROOT / "calculations/phase_36_trace_dft_h2_priority"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("PHASE 36 — TRACE dft_h2_priority.csv")
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
            reader = csv.DictReader(f)
            rows = list(reader)

        print("ROWS   :", len(rows))
        print("FIELDS :", reader.fieldnames)

        for row in rows[:10]:
            print("ROW    :", row)

    except Exception as e:
        print("READ ERROR :", repr(e))

references = []

for base in [
    ROOT / "scripts",
    ROOT / "reports",
    ROOT / "calculations",
]:

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

        needles = [
            "dft_h2_priority.csv",
            "dft_h2_priority",
        ]

        if not any(n in text for n in needles):
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines, 1):

            if any(n in line for n in needles):

                references.append({
                    "file": str(path),
                    "line": i,
                    "text": line,
                    "context": lines[
                        max(0, i - 3):
                        min(len(lines), i + 2)
                    ],
                })

print()
print("=" * 70)
print("REFERENCES")
print("-" * 70)
print("COUNT :", len(references))

for r in references:

    print()
    print("-" * 70)
    print("FILE :", r["file"])
    print("LINE :", r["line"])

    for j, line in enumerate(
        r["context"],
        max(1, r["line"] - 3)
    ):
        print(f"L{j}: {line}")

# Classement simple des vrais candidats producteurs.
candidates = []

for r in references:

    path = Path(r["file"])

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).lower()
    except Exception:
        continue

    score = 10
    reasons = ["TARGET_REFERENCE"]

    for k in [
        "to_csv",
        "writerow",
        "writerows",
        "csv.writer",
        "csv.dictwriter",
    ]:
        if k in text:
            score += 20
            reasons.append(k)

    for k in [
        "hydrogen_score",
        "hydrogen_wt_percent",
        "h2_score",
        "hydrogen",
        "h2",
    ]:
        n = text.count(k)
        if n:
            score += min(n * 3, 30)
            reasons.append(f"{k}={n}")

    lowname = path.name.lower()

    if any(k in lowname for k in [
        "audit",
        "trace",
        "diagnostic",
        "provenance",
        "phase",
    ]):
        score -= 20
        reasons.append("AUDIT_PENALTY")

    candidates.append({
        "score": score,
        "file": str(path),
        "line": r["line"],
        "text": r["text"],
        "reasons": reasons,
    })

candidates.sort(
    key=lambda x: x["score"],
    reverse=True
)

print()
print("=" * 70)
print("TOP PRODUCTEUR CANDIDATES")
print("-" * 70)

for i, r in enumerate(candidates[:15], 1):

    print(
        f"#{i} SCORE={r['score']} "
        f"FILE={r['file']} "
        f"L{r['line']}"
    )
    print("WHY :", ", ".join(r["reasons"]))
    print("CODE:", r["text"])

# Sauvegarde
csv_out = OUT / "phase36_trace_dft_h2_priority.csv"
json_out = OUT / "phase36_trace_dft_h2_priority.json"
manifest_out = OUT / "phase36_manifest.json"

with csv_out.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    w = csv.writer(f)
    w.writerow([
        "score",
        "file",
        "line",
        "text",
        "reasons",
    ])

    for r in candidates:
        w.writerow([
            r["score"],
            r["file"],
            r["line"],
            r["text"],
            ";".join(r["reasons"]),
        ])

json_out.write_text(
    json.dumps(
        {
            "phase": 36,
            "mode": "ANALYSIS_ONLY",
            "target": str(TARGET),
            "target_exists": TARGET.exists(),
            "references": references,
            "candidates": candidates,
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
            "phase": 36,
            "status": "COMPLETE",
            "mode": "ANALYSIS_ONLY",
            "target": str(TARGET),
            "references": len(references),
            "candidates": len(candidates),
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
print("PHASE 36 — RESULT")
print("-" * 70)
print("REFERENCES :", len(references))
print("CANDIDATES :", len(candidates))
print()
print("CSV     :", csv_out)
print("JSON    :", json_out)
print("MANIFEST:", manifest_out)
print("=" * 70)
