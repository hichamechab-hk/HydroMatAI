#!/usr/bin/env python3

from pathlib import Path
import re
import json
import csv
import ast
from datetime import datetime

ROOT = Path("/home/hk/HydroMatAI")
TARGET = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"

OUTDIR = ROOT / "calculations/phase_23_trace_h2_pipeline"
OUTDIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = OUTDIR / "phase23_trace_h2_pipeline.csv"
JSON_OUT = OUTDIR / "phase23_trace_h2_pipeline.json"
MANIFEST_OUT = OUTDIR / "phase23_manifest.json"

CANDIDATES = [
    ROOT / "scripts/rank_global_h2.py",
    ROOT / "scripts/dft_prescreen_global.py",
    ROOT / "scripts/dft_global_complete.py",
    ROOT / "scripts/run_global_dft.py",
]

KEYWORDS = [
    "TOP200_GLOBAL_H2_RANKED.csv",
    "GLOBAL_H2_RANKED",
    "hydrogen_score",
    "hydrogen_wt_percent",
    "tobmof",
    "tobMof",
    "hMOF",
    "cif",
    "to_csv",
    "write_text",
    "open(",
    "shutil.copy",
    "copyfile",
    "rename",
    "move",
]

def read_text(path):
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""

def line_hits(text, keywords):
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(k.lower() in line.lower() for k in keywords):
            rows.append({
                "line": i,
                "text": line.strip()
            })
    return rows

def python_ast_info(path, text):
    result = {
        "functions": [],
        "imports": [],
        "writes_target": [],
        "csv_writes": [],
        "path_constants": [],
    }

    try:
        tree = ast.parse(text)
    except Exception as e:
        result["parse_error"] = str(e)
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno
            })

        elif isinstance(node, ast.Import):
            for n in node.names:
                result["imports"].append(n.name)

        elif isinstance(node, ast.ImportFrom):
            result["imports"].append(node.module or "")

        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if (
                "TOP200_GLOBAL_H2_RANKED" in value
                or "GLOBAL_H2_RANKED" in value
                or "hydrogen_score" in value
                or "hydrogen_wt_percent" in value
                or "tobmof" in value.lower()
                or "hmof" in value.lower()
            ):
                result["path_constants"].append({
                    "line": getattr(node, "lineno", None),
                    "value": value
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func

            if isinstance(func, ast.Attribute):
                name = func.attr

                if name == "to_csv":
                    result["csv_writes"].append({
                        "line": node.lineno,
                        "code": ast.get_source_segment(text, node) or "to_csv(...)"
                    })

                if name in ("write_text", "write_bytes"):
                    result["writes_target"].append({
                        "line": node.lineno,
                        "method": name,
                        "code": ast.get_source_segment(text, node) or name
                    })

    return result

def classify_target_write(text):
    patterns = [
        r'\.to_csv\s*\([^)]*TOP200_GLOBAL_H2_RANKED\.csv',
        r'\.to_csv\s*\([^)]*GLOBAL_H2_RANKED',
        r'open\s*\([^)]*TOP200_GLOBAL_H2_RANKED\.csv[^)]*[\'"]w',
        r'open\s*\([^)]*GLOBAL_H2_RANKED[^)]*[\'"]w',
        r'write_text\s*\([^)]*TOP200_GLOBAL_H2_RANKED',
        r'write_text\s*\([^)]*GLOBAL_H2_RANKED',
        r'copy(?:file)?\s*\([^)]*TOP200_GLOBAL_H2_RANKED',
        r'rename\s*\([^)]*TOP200_GLOBAL_H2_RANKED',
        r'move\s*\([^)]*TOP200_GLOBAL_H2_RANKED',
    ]

    hits = []
    for p in patterns:
        for m in re.finditer(p, text, flags=re.I):
            line = text.count("\n", 0, m.start()) + 1
            hits.append({
                "line": line,
                "pattern": p,
                "match": m.group(0)
            })
    return hits

def extract_input_paths(text):
    paths = set()

    patterns = [
        r'["\']([^"\']+\.csv)["\']',
        r'["\']([^"\']+\.json)["\']',
        r'["\']([^"\']+\.cif)["\']',
        r'["\']([^"\']+\.xyz)["\']',
        r'["\']([^"\']+\.out)["\']',
        r'["\']([^"\']+\.pkl)["\']',
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            value = m.group(1)
            if "TOP200_GLOBAL_H2_RANKED" not in value:
                paths.add(value)

    return sorted(paths)

def candidate_record(path):
    exists = path.exists()
    text = read_text(path) if exists else ""

    return {
        "file": str(path),
        "exists": exists,
        "size": path.stat().st_size if exists else 0,
        "target_write_hits": classify_target_write(text),
        "keyword_hits": line_hits(text, KEYWORDS),
        "input_paths": extract_input_paths(text),
        "ast": python_ast_info(path, text) if exists else {},
    }

def nearby_python_files():
    files = []

    for base in [
        ROOT / "scripts",
        ROOT / "calculations/global_screening",
        ROOT / "reports/global_screening",
    ]:
        if not base.exists():
            continue

        for p in base.glob("*.py"):
            files.append(p)

    return sorted(set(files))

print("=" * 70, flush=True)
print("PHASE 23 — DIRECT H2 PIPELINE TRACE", flush=True)
print("MODE              : ANALYSIS_ONLY", flush=True)
print("pw.x              : NO", flush=True)
print("QE CALCULATION    : NO", flush=True)
print("CIF MODIFICATION  : NO", flush=True)
print("=" * 70, flush=True)

print(f"TARGET            : {TARGET}", flush=True)
print(f"TARGET EXISTS     : {TARGET.exists()}", flush=True)

records = []

print("\n[1/4] Inspection des producteurs probables...", flush=True)

for path in CANDIDATES:
    print(f"  -> {path.name}", flush=True)
    rec = candidate_record(path)
    records.append(rec)

print("\n[2/4] Recherche ciblée des autres scripts Python...", flush=True)

for path in nearby_python_files():
    if path in CANDIDATES:
        continue

    text = read_text(path)

    if any(
        x.lower() in text.lower()
        for x in [
            "TOP200_GLOBAL_H2_RANKED",
            "GLOBAL_H2_RANKED",
            "hydrogen_score",
            "hydrogen_wt_percent",
        ]
    ):
        print(f"  -> {path.name}", flush=True)
        records.append(candidate_record(path))

print("\n[3/4] Détermination du producteur réel...", flush=True)

direct_writers = [
    r for r in records
    if r["target_write_hits"]
]

for r in direct_writers:
    print(f"\nDIRECT WRITER : {r['file']}", flush=True)
    for hit in r["target_write_hits"]:
        print(f"  line {hit['line']} : {hit['match']}", flush=True)

if not direct_writers:
    print("  Aucun writer direct détecté.", flush=True)

print("\n[4/4] Résumé des entrées amont...", flush=True)

all_input_paths = {}

for r in records:
    for p in r["input_paths"]:
        all_input_paths.setdefault(p, []).append(r["file"])

for p, owners in sorted(all_input_paths.items()):
    if any(x in p.lower() for x in [
        "h2", "hydrogen", "mof", "cif", "dft",
        "screen", "rank", "global"
    ]):
        print(f"  {p}", flush=True)
        for owner in owners:
            print(f"      <- {owner}", flush=True)

status = "DIRECT_PRODUCER_FOUND" if direct_writers else "DIRECT_PRODUCER_NOT_FOUND"

producer_files = [r["file"] for r in direct_writers]

result = {
    "phase": 23,
    "status": status,
    "mode": "ANALYSIS_ONLY",
    "target": str(TARGET),
    "target_exists": TARGET.exists(),
    "direct_producer_found": bool(direct_writers),
    "producer_files": producer_files,
    "candidate_files_scanned": len(records),
    "records": records,
    "timestamp": datetime.now().isoformat(),
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "file",
        "exists",
        "size",
        "direct_target_writer",
        "target_write_lines",
        "keyword_hit_count",
        "input_path_count",
    ])

    for r in records:
        writer.writerow([
            r["file"],
            r["exists"],
            r["size"],
            bool(r["target_write_hits"]),
            ";".join(str(x["line"]) for x in r["target_write_hits"]),
            len(r["keyword_hits"]),
            len(r["input_paths"]),
        ])

JSON_OUT.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

manifest = {
    "phase": 23,
    "status": status,
    "mode": "ANALYSIS_ONLY",
    "target": str(TARGET),
    "direct_producer_found": bool(direct_writers),
    "producer_files": producer_files,
    "files_scanned": len(records),
    "no_qe_calculation": True,
    "no_cif_modification": True,
}

MANIFEST_OUT.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\n" + "=" * 70, flush=True)
print("PHASE 23 — RESULT", flush=True)
print("-" * 70, flush=True)
print(f"FILES SCANNED     : {len(records)}", flush=True)
print(f"DIRECT PRODUCER   : {len(direct_writers)}", flush=True)
print(f"STATUS            : {status}", flush=True)

if direct_writers:
    print("\nPRODUCTEUR(S) DIRECT(S)", flush=True)
    for p in producer_files:
        print(f"  {p}", flush=True)

print("\nCSV     :", CSV_OUT, flush=True)
print("JSON    :", JSON_OUT, flush=True)
print("MANIFEST:", MANIFEST_OUT, flush=True)
print("=" * 70, flush=True)
