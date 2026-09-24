#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
SOURCE = ROOT / "scripts/run_top5_complete.py"

OUT = ROOT / "calculations/phase_28_trace_h2_inputs"
OUT.mkdir(parents=True, exist_ok=True)

def read(p):
    try:
        return p.read_text(errors="ignore")
    except:
        return ""

source = read(SOURCE)
lines = source.splitlines()

# Extraire tous les fichiers explicitement référencés par run_top5_complete.py
refs = []

patterns = [
    r'["\']([^"\']+\.(?:csv|json|cif|txt|out|pkl|db))["\']',
    r'Path\s*\(\s*["\']([^"\']+)["\']',
]

for i, line in enumerate(lines, 1):
    for pat in patterns:
        for m in re.finditer(pat, line, re.I):
            refs.append({
                "line": i,
                "path": m.group(1),
                "source_line": line.strip()
            })

# Dédupliquer
unique = {}
for r in refs:
    key = r["path"]
    if key not in unique:
        unique[key] = r

refs = list(unique.values())

print("=" * 70, flush=True)
print("PHASE 28 — TRACE H2 INPUTS", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("SCRIPT EXECUTED   : NO", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"SOURCE : {SOURCE}", flush=True)
print(f"REFERENCES : {len(refs)}", flush=True)

results = []

for r in refs:
    raw = r["path"]

    candidates = [
        ROOT / raw,
        SOURCE.parent / raw,
    ]

    found = None

    for c in candidates:
        if c.exists():
            found = c
            break

    if found:
        exists = True
        size = found.stat().st_size
        suffix = found.suffix.lower()
        content = read(found) if suffix in {
            ".csv", ".json", ".txt", ".out"
        } else ""

        h2_hits = []

        for n, line in enumerate(content.splitlines(), 1):
            if any(k in line.lower() for k in [
                "hydrogen",
                "hydrogen_score",
                "hydrogen_wt_percent",
                "tobmof",
                "tobmof-",
                "h2",
            ]):
                h2_hits.append({
                    "line": n,
                    "text": line.strip()
                })

        results.append({
            "reference": raw,
            "reference_line": r["line"],
            "resolved": str(found),
            "exists": exists,
            "size": size,
            "h2_hits": h2_hits[:50],
        })

        print(
            f"\nFOUND  : {found}",
            flush=True
        )
        print(
            f"SIZE   : {size} bytes",
            flush=True
        )
        print(
            f"H2 HITS: {len(h2_hits)}",
            flush=True
        )

        for h in h2_hits[:8]:
            print(
                f"  L{h['line']}: {h['text'][:220]}",
                flush=True
            )

    else:
        results.append({
            "reference": raw,
            "reference_line": r["line"],
            "resolved": None,
            "exists": False,
            "size": 0,
            "h2_hits": [],
        })

        print(
            f"\nNOT FOUND : {raw}",
            flush=True
        )

# Chercher les producteurs de chaque fichier trouvé,
# mais uniquement dans scripts/ et sans exécuter quoi que ce soit.
print("\n" + "=" * 70, flush=True)
print("RECHERCHE DES PRODUCTEURS DES INPUTS", flush=True)
print("-" * 70, flush=True)

script_files = sorted(
    (ROOT / "scripts").glob("*.py")
)

producer_hits = []

for result in results:

    resolved = result.get("resolved")

    if not resolved:
        continue

    target_name = Path(resolved).name

    for script in script_files:

        if script == SOURCE:
            continue

        txt = read(script)

        patterns = [
            rf'\.to_csv\s*\([^)]*{re.escape(target_name)}',
            rf'open\s*\([^)]*{re.escape(target_name)}',
            rf'write_text\s*\([^)]*{re.escape(target_name)}',
            rf'copy(?:file)?\s*\([^)]*{re.escape(target_name)}',
            rf'{re.escape(target_name)}',
        ]

        matched = False

        for pat in patterns:
            if re.search(pat, txt, re.I):
                matched = True
                break

        if matched:
            producer_hits.append({
                "input": target_name,
                "script": str(script)
            })

            print(
                f"{target_name} <- {script}",
                flush=True
            )

csv_out = OUT / "phase28_trace_h2_inputs.csv"
json_out = OUT / "phase28_trace_h2_inputs.json"
manifest_out = OUT / "phase28_manifest.json"

with csv_out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "reference",
        "reference_line",
        "resolved",
        "exists",
        "size",
        "h2_hit_count",
    ])

    for r in results:
        w.writerow([
            r["reference"],
            r["reference_line"],
            r["resolved"],
            r["exists"],
            r["size"],
            len(r["h2_hits"]),
        ])

data = {
    "phase": 28,
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "references": refs,
    "resolved_inputs": results,
    "producer_hits": producer_hits,
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
    "timestamp": datetime.now().isoformat(),
}

json_out.write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": 28,
    "status": "COMPLETE",
    "mode": "ANALYSIS_ONLY",
    "source": str(SOURCE),
    "references": len(refs),
    "resolved_inputs": sum(
        1 for r in results if r["exists"]
    ),
    "producer_hits": len(producer_hits),
    "no_script_execution": True,
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

manifest_out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 28 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"REFERENCES         : {len(refs)}", flush=True)
print(
    f"INPUTS FOUND       : {sum(1 for r in results if r['exists'])}",
    flush=True
)
print(f"PRODUCER HITS      : {len(producer_hits)}", flush=True)
print("\nCSV     :", csv_out, flush=True)
print("JSON    :", json_out, flush=True)
print("MANIFEST:", manifest_out, flush=True)
print("=" * 70, flush=True)
