#!/usr/bin/env python3

import csv
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path("/home/hk/HydroMatAI")
OUT = ROOT / "calculations" / "phase_17b_parallel_audit"
OUT.mkdir(parents=True, exist_ok=True)

QE_ROOT = ROOT / "calculations"
REPORT_ROOT = ROOT / "reports"

def load_csv(path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def load_json(path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return None

def find_files(pattern):
    return list(ROOT.rglob(pattern))

def normalize_name(x):
    return str(x or "").strip().lower()

def number(x):
    try:
        return float(x)
    except Exception:
        return None

def find_top20():
    candidates = []

    files = (
        find_files("phase17*.csv")
        + find_files("phase16*.csv")
        + find_files("*TOP20*.csv")
        + find_files("*top20*.csv")
    )

    seen = set()

    for p in files:
        if str(p) in seen:
            continue
        seen.add(str(p))

        rows = load_csv(p)

        for r in rows:
            name = (
                r.get("candidate")
                or r.get("name")
                or r.get("material")
                or r.get("id")
                or ""
            ).strip()

            if not name:
                continue

            if (
                "hmof" in name.lower()
                or "tobmof" in name.lower()
            ):
                candidates.append({
                    "candidate": name,
                    "source_file": str(p),
                    **r
                })

    unique = {}
    for r in candidates:
        unique[normalize_name(r["candidate"])] = r

    return list(unique.values())

def find_h2_sources():
    files = [
        REPORT_ROOT / "global_screening" / "TOP200_GLOBAL_H2_RANKED.csv",
        REPORT_ROOT / "global_screening" / "TOP20_GLOBAL_H2_RANKED.csv",
    ]

    for p in files:
        if p.exists():
            return p, load_csv(p)

    matches = find_files("*H2*RANKED*.csv")
    if matches:
        return matches[0], load_csv(matches[0])

    return None, []

def find_phase21():
    files = [
        QE_ROOT / "phase_21_complete" / "phase21_complete.csv",
        QE_ROOT / "phase_21_complete" / "phase21_complete.json",
    ]

    for p in files:
        if p.suffix == ".csv" and p.exists():
            return p, load_csv(p)
        if p.suffix == ".json" and p.exists():
            data = load_json(p)
            if isinstance(data, list):
                return p, data
            if isinstance(data, dict):
                for k in ["candidates", "results", "data", "entries"]:
                    if isinstance(data.get(k), list):
                        return p, data[k]

    return None, []

def find_phase22():
    p = QE_ROOT / "phase_22_qe_inputs" / "phase22_qe_inputs.csv"
    return p, load_csv(p)

def extract_numeric(value):
    if value is None:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(m.group()) if m else None

def first_value(row, keys):
    for k in keys:
        if k in row and str(row[k]).strip():
            return row[k]
    return ""

top20 = find_top20()
h2_path, h2_rows = find_h2_sources()
p21_path, p21_rows = find_phase21()
p22_path, p22_rows = find_phase22()

h2_by_name = {
    normalize_name(
        r.get("name")
        or r.get("candidate")
        or r.get("material")
        or ""
    ): r
    for r in h2_rows
}

p21_by_name = {
    normalize_name(
        r.get("candidate")
        or r.get("name")
        or r.get("material")
        or ""
    ): r
    for r in p21_rows
}

p22_by_name = {
    normalize_name(
        r.get("candidate")
        or r.get("name")
        or r.get("material")
        or ""
    ): r
    for r in p22_rows
}

audit = []

for i, r in enumerate(top20, 1):

    candidate = r["candidate"]
    key = normalize_name(candidate)

    h2 = h2_by_name.get(key, {})
    p21 = p21_by_name.get(key, {})
    p22 = p22_by_name.get(key, {})

    wt = first_value(
        h2,
        [
            "hydrogen_wt_percent",
            "h2_wt_percent",
            "wt_percent",
            "H2_wt_percent"
        ]
    )

    h2_score = first_value(
        h2,
        [
            "hydrogen_score",
            "h2_score",
            "score"
        ]
    )

    h2_rank = first_value(
        h2,
        [
            "rank",
            "h2_rank"
        ]
    )

    elements = first_value(
        p21,
        [
            "elements",
            "element_set",
            "species",
            "formula"
        ]
    )

    status = first_value(
        p21,
        [
            "status",
            "validation_status",
            "qe_status"
        ]
    )

    qe_ready = first_value(
        p21,
        [
            "qe_ready",
            "QE_READY",
            "ready_for_qe"
        ]
    )

    input_file = first_value(
        p22,
        [
            "input_file",
            "qe_input",
            "path",
            "file"
        ]
    )

    audit.append({
        "audit_rank": i,
        "candidate": candidate,
        "h2_rank": h2_rank,
        "hydrogen_score": h2_score,
        "hydrogen_wt_percent": wt,
        "elements": elements,
        "phase21_status": status,
        "qe_ready": qe_ready,
        "qe_input": input_file,
        "h2_source": str(h2_path) if h2_path else "",
        "phase21_source": str(p21_path) if p21_path else "",
    })

# Si aucun TOP20 exploitable n'est trouvé, utiliser les candidats Phase21.
if not audit and p21_rows:
    for i, r in enumerate(p21_rows[:20], 1):
        candidate = (
            r.get("candidate")
            or r.get("name")
            or r.get("material")
            or ""
        )
        audit.append({
            "audit_rank": i,
            "candidate": candidate,
            "h2_rank": "",
            "hydrogen_score": "",
            "hydrogen_wt_percent": "",
            "elements": first_value(r, ["elements", "element_set", "species", "formula"]),
            "phase21_status": first_value(r, ["status", "validation_status", "qe_status"]),
            "qe_ready": first_value(r, ["qe_ready", "QE_READY", "ready_for_qe"]),
            "qe_input": "",
            "h2_source": str(h2_path) if h2_path else "",
            "phase21_source": str(p21_path) if p21_path else "",
        })

# Contrôles
names = [normalize_name(x["candidate"]) for x in audit if x["candidate"]]
duplicates = [
    name for name, count in Counter(names).items()
    if count > 1
]

ready_count = sum(
    1 for x in audit
    if str(x["qe_ready"]).strip().lower()
    in {"true", "yes", "1", "ok", "qe_ready"}
)

h2_count = sum(
    1 for x in audit
    if x["h2_rank"] or x["hydrogen_score"] or x["hydrogen_wt_percent"]
)

missing_h2 = sum(
    1 for x in audit
    if not (
        x["h2_rank"]
        or x["hydrogen_score"]
        or x["hydrogen_wt_percent"]
    )
)

# Export CSV
csv_path = OUT / "phase17b_parallel_audit.csv"

fields = [
    "audit_rank",
    "candidate",
    "h2_rank",
    "hydrogen_score",
    "hydrogen_wt_percent",
    "elements",
    "phase21_status",
    "qe_ready",
    "qe_input",
    "h2_source",
    "phase21_source",
]

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(audit)

summary = {
    "phase": "17B",
    "title": "PARALLEL TOP20 AUDIT",
    "mode": "ANALYSIS_ONLY",
    "qe_calculation": False,
    "pw_x_launched": False,
    "cif_modified": False,
    "top20_audited": len(audit),
    "h2_linked_candidates": h2_count,
    "missing_h2_data": missing_h2,
    "qe_ready_detected": ready_count,
    "duplicate_candidates": duplicates,
    "h2_source": str(h2_path) if h2_path else None,
    "phase21_source": str(p21_path) if p21_path else None,
    "phase22_source": str(p22_path) if p22_path else None,
    "output_csv": str(csv_path),
    "status": "AUDIT_COMPLETE"
}

json_path = OUT / "phase17b_parallel_audit.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "summary": summary,
            "candidates": audit
        },
        f,
        indent=2,
        ensure_ascii=False
    )

manifest_path = OUT / "phase17b_manifest.json"

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("=" * 78)
print("PHASE 17B — PARALLEL TOP20 AUDIT")
print("=" * 78)
print()
print("MODE              : ANALYSIS_ONLY")
print("pw.x              : NO")
print("QE CALCULATION    : NO")
print("CIF MODIFICATION  : NO")
print()
print(f"TOP20 AUDITED     : {len(audit)}")
print(f"H2 LINKED         : {h2_count}")
print(f"H2 MISSING        : {missing_h2}")
print(f"QE_READY DETECTED : {ready_count}")
print(f"DUPLICATES        : {len(duplicates)}")
print()
print("OUTPUTS")
print(f"CSV     : {csv_path}")
print(f"JSON    : {json_path}")
print(f"MANIFEST: {manifest_path}")
print()
print("PHASE 17B STATUS : AUDIT_COMPLETE")
print("=" * 78)

for x in audit:
    print(
        f"{x['audit_rank']:02d} | "
        f"{x['candidate']} | "
        f"H2 rank={x['h2_rank'] or 'N/A'} | "
        f"H2 wt={x['hydrogen_wt_percent'] or 'N/A'} | "
        f"QE_READY={x['qe_ready'] or 'N/A'}"
    )
