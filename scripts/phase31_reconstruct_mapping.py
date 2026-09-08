#!/usr/bin/env python3

import os
import re
import csv
import json
import hashlib
from pathlib import Path
from collections import defaultdict

ROOT = Path("/home/hk/HydroMatAI")

H2_CSV = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"
QE_CSV = ROOT / "calculations/phase_27_ranking/phase27_ranking.csv"
DIAG_JSON = ROOT / "calculations/phase_30_h2_mapping_diagnostic/phase30_mapping_diagnostic.json"

OUT_DIR = ROOT / "calculations/phase_31_mapping_reconstructed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT_DIR / "phase31_mapping_reconstructed.csv"
OUT_JSON = OUT_DIR / "phase31_mapping_reconstructed.json"
OUT_MANIFEST = OUT_DIR / "phase31_manifest.json"

TOP_N = 25

TOB_RE = re.compile(r"\btobmof-\d+\b", re.I)
HMOF_RE = re.compile(r"\bhMOF-\d+\b", re.I)


def norm_tob(x):
    if not x:
        return None
    m = TOB_RE.search(str(x))
    return m.group(0).lower() if m else None


def norm_hmof(x):
    if not x:
        return None
    m = HMOF_RE.search(str(x))
    return m.group(0) if m else None


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def read_h2():
    rows = []

    with open(H2_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = norm_tob(row.get("name", ""))
            if not name:
                continue

            try:
                rank = int(float(row.get("rank", "")))
            except Exception:
                rank = None

            try:
                score = float(row.get("hydrogen_score", ""))
            except Exception:
                score = None

            try:
                wt = float(row.get("hydrogen_wt_percent", ""))
            except Exception:
                wt = None

            rows.append({
                "h2_name": name,
                "h2_rank": rank,
                "hydrogen_score": score,
                "hydrogen_wt_percent": wt
            })

    rows.sort(key=lambda x: x["h2_rank"] if x["h2_rank"] is not None else 999999)

    return rows[:TOP_N]


def read_qe():
    rows = {}

    if not QE_CSV.exists():
        return rows

    with open(QE_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            hmof = norm_hmof(row.get("candidate", ""))
            if not hmof:
                continue

            try:
                energy = float(row.get("total_energy_ry", ""))
            except Exception:
                energy = None

            rows[hmof] = {
                "qe_candidate": hmof,
                "qe_total_energy_ry": energy,
                "qe_row": row
            }

    return rows


def extract_cross_reference_files():
    if not DIAG_JSON.exists():
        return []

    try:
        with open(DIAG_JSON, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERREUR lecture diagnostic: {e}")
        return []

    files = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("file", "path", "source", "filepath", "file_path"):
                    if isinstance(v, str):
                        p = Path(v)
                        if p.exists():
                            files.add(str(p))
                walk(v)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

        elif isinstance(obj, str):
            p = Path(obj)
            if p.exists() and p.is_file():
                files.add(str(p))

    walk(data)

    # Priorité aux fichiers réellement listés dans cross_links
    try:
        links = data.get("cross_links", [])
        for item in links:
            if isinstance(item, dict):
                for key in ("file", "path", "source", "filepath", "file_path"):
                    value = item.get(key)
                    if isinstance(value, str):
                        p = Path(value)
                        if p.exists() and p.is_file():
                            files.add(str(p))
    except Exception:
        pass

    return sorted(files)


def add_evidence(evidence, tob, hmof, path, evidence_type, confidence, context):
    if not tob or not hmof:
        return

    key = (tob, hmof, str(path), evidence_type)

    evidence[key] = {
        "h2_name": tob,
        "qe_candidate": hmof,
        "evidence_file": str(path),
        "evidence_type": evidence_type,
        "confidence": confidence,
        "context": context[:1000]
    }


def scan_text_file(path, evidence):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return

    for i, line in enumerate(lines):
        tob = sorted(set(norm_tob(x) for x in TOB_RE.findall(line) if norm_tob(x)))
        hmofs = sorted(set(norm_hmof(x) for x in HMOF_RE.findall(line) if norm_hmof(x)))

        if tob and hmofs:
            for t in tob:
                for h in hmofs:
                    add_evidence(
                        evidence,
                        t,
                        h,
                        path,
                        "SAME_LINE",
                        95,
                        line.strip()
                    )

    # Contexte local uniquement si une seule combinaison est identifiable
    for i in range(len(lines)):
        start = max(0, i - 2)
        end = min(len(lines), i + 3)

        block = "".join(lines[start:end])

        tobs = sorted(set(
            norm_tob(x) for x in TOB_RE.findall(block)
            if norm_tob(x)
        ))

        hmofs = sorted(set(
            norm_hmof(x) for x in HMOF_RE.findall(block)
            if norm_hmof(x)
        ))

        if len(tobs) == 1 and len(hmofs) == 1:
            add_evidence(
                evidence,
                tobs[0],
                hmofs[0],
                path,
                "LOCAL_CONTEXT",
                75,
                block.strip()
            )


def scan_csv_file(path, evidence):
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)

            for row in reader:
                text = " | ".join(
                    f"{k}={v}"
                    for k, v in row.items()
                    if v is not None
                )

                tobs = sorted(set(
                    norm_tob(x) for x in TOB_RE.findall(text)
                    if norm_tob(x)
                ))

                hmofs = sorted(set(
                    norm_hmof(x) for x in HMOF_RE.findall(text)
                    if norm_hmof(x)
                ))

                if tobs and hmofs:
                    for t in tobs:
                        for h in hmofs:
                            add_evidence(
                                evidence,
                                t,
                                h,
                                path,
                                "SAME_ROW",
                                100,
                                text
                            )
    except Exception:
        scan_text_file(path, evidence)


def scan_json_object(obj, path, evidence, parent_context=""):
    if isinstance(obj, dict):

        text_parts = []

        for k, v in obj.items():
            if isinstance(v, (str, int, float, bool)):
                text_parts.append(f"{k}={v}")

        text = " | ".join(text_parts)

        tobs = sorted(set(
            norm_tob(x) for x in TOB_RE.findall(text)
            if norm_tob(x)
        ))

        hmofs = sorted(set(
            norm_hmof(x) for x in HMOF_RE.findall(text)
            if norm_hmof(x)
        ))

        if tobs and hmofs:
            for t in tobs:
                for h in hmofs:
                    add_evidence(
                        evidence,
                        t,
                        h,
                        path,
                        "SAME_JSON_OBJECT",
                        100,
                        text
                    )

        for v in obj.values():
            scan_json_object(v, path, evidence, text)

    elif isinstance(obj, list):
        for item in obj:
            scan_json_object(item, path, evidence, parent_context)

    elif isinstance(obj, str):
        tobs = sorted(set(
            norm_tob(x) for x in TOB_RE.findall(obj)
            if norm_tob(x)
        ))

        hmofs = sorted(set(
            norm_hmof(x) for x in HMOF_RE.findall(obj)
            if norm_hmof(x)
        ))

        if tobs and hmofs:
            for t in tobs:
                for h in hmofs:
                    add_evidence(
                        evidence,
                        t,
                        h,
                        path,
                        "SAME_JSON_STRING",
                        95,
                        obj
                    )


def scan_file(path, evidence):
    suffix = path.suffix.lower()

    if suffix == ".csv":
        scan_csv_file(path, evidence)
        return

    if suffix == ".json":
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            scan_json_object(data, path, evidence)
            return

        except Exception:
            pass

    scan_text_file(path, evidence)


def main():

    print("=" * 80)
    print("PHASE 31 — RECONSTRUCTION MAPPING H2 <-> QE")
    print("=" * 80)
    print("ANALYSIS ONLY")
    print("Aucun pw.x")
    print("Aucun calcul QE")
    print("Aucun CIF modifié")
    print()

    h2_rows = read_h2()
    qe_rows = read_qe()
    cross_files = extract_cross_reference_files()

    print(f"H2 TOP {TOP_N}: {len(h2_rows)}")
    print(f"QE candidats: {len(qe_rows)}")
    print(f"Fichiers cross-reference: {len(cross_files)}")
    print()

    evidence = {}

    for path_str in cross_files:
        path = Path(path_str)

        print(f"SCAN: {path}")

        try:
            scan_file(path, evidence)
        except Exception as e:
            print(f"  ERREUR: {e}")

    # Index preuves par tobMof
    by_tob = defaultdict(list)

    for ev in evidence.values():
        by_tob[ev["h2_name"]].append(ev)

    final_rows = []

    for h2 in h2_rows:

        tob = h2["h2_name"]
        candidates = by_tob.get(tob, [])

        # Regroupement par hMOF
        by_hmof = defaultdict(list)

        for ev in candidates:
            by_hmof[ev["qe_candidate"]].append(ev)

        ranked_candidates = []

        for hmof, evs in by_hmof.items():
            max_conf = max(e["confidence"] for e in evs)
            types = sorted(set(e["evidence_type"] for e in evs))

            ranked_candidates.append({
                "hmof": hmof,
                "max_confidence": max_conf,
                "evidence_types": types,
                "evidence_count": len(evs),
                "evidence": evs
            })

        ranked_candidates.sort(
            key=lambda x: (
                -x["max_confidence"],
                -x["evidence_count"]
            )
        )

        accepted = None
        verdict = "NO_MAPPING"

        if ranked_candidates:
            if len(ranked_candidates) == 1:
                candidate = ranked_candidates[0]

                if candidate["max_confidence"] >= 90:
                    accepted = candidate
                    verdict = "VALID_MAPPING"
                else:
                    verdict = "WEAK_MAPPING"

            else:
                top = ranked_candidates[0]
                second = ranked_candidates[1]

                if (
                    top["max_confidence"] >= 90
                    and top["max_confidence"] > second["max_confidence"]
                ):
                    accepted = top
                    verdict = "VALID_MAPPING"

                elif (
                    top["max_confidence"] == second["max_confidence"]
                    and top["max_confidence"] >= 90
                ):
                    verdict = "AMBIGUOUS_MAPPING"
                else:
                    verdict = "AMBIGUOUS_MAPPING"

        hmof = accepted["hmof"] if accepted else None

        qe = qe_rows.get(hmof) if hmof else None

        row = {
            "h2_name": tob,
            "h2_rank": h2["h2_rank"],
            "hydrogen_score": h2["hydrogen_score"],
            "hydrogen_wt_percent": h2["hydrogen_wt_percent"],
            "mapping_verdict": verdict,
            "qe_candidate": hmof,
            "mapping_confidence": (
                accepted["max_confidence"]
                if accepted else None
            ),
            "mapping_evidence_types": (
                ";".join(accepted["evidence_types"])
                if accepted else ""
            ),
            "mapping_evidence_count": (
                accepted["evidence_count"]
                if accepted else 0
            ),
            "qe_available": bool(qe),
            "qe_total_energy_ry": (
                qe["qe_total_energy_ry"]
                if qe else None
            ),
            "qe_information_only": bool(qe),
            "scientific_combined_score": None,
            "h2_primary_rank": h2["h2_rank"]
        }

        final_rows.append(row)

    valid = [
        r for r in final_rows
        if r["mapping_verdict"] == "VALID_MAPPING"
    ]

    valid_qe = [
        r for r in valid
        if r["qe_available"]
    ]

    print()
    print("=" * 80)
    print("RESULTATS")
    print("=" * 80)

    print(f"Mappings valides: {len(valid)}")
    print(f"Mappings valides avec QE: {len(valid_qe)}")
    print()

    for r in final_rows:
        print(
            f'{r["h2_name"]:12s} | '
            f'H2 rank={str(r["h2_rank"]):>3s} | '
            f'{r["mapping_verdict"]:18s} | '
            f'QE={str(r["qe_candidate"]):10s} | '
            f'QE available={r["qe_available"]}'
        )

    # CSV
    fields = list(final_rows[0].keys()) if final_rows else []

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(final_rows)

    # JSON détaillé
    json_data = {
        "phase": 31,
        "mode": "ANALYSIS_ONLY",
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "diagnostic_source": str(DIAG_JSON),
        "top_n": TOP_N,
        "h2_candidates": len(h2_rows),
        "qe_candidates": len(qe_rows),
        "cross_reference_files": len(cross_files),
        "evidence_count": len(evidence),
        "valid_mappings": len(valid),
        "valid_mappings_with_qe": len(valid_qe),
        "raw_qe_energy_is_not_used_as_combined_score": True,
        "scientific_note": (
            "Les energies QE totales brutes de compositions differentes "
            "ne sont pas directement comparables. Elles restent "
            "informationnelles tant qu'une energie de formation ou "
            "normalisation appropriee n'est pas disponible."
        ),
        "cross_reference_files_list": cross_files,
        "results": final_rows,
        "all_evidence": list(evidence.values())
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    manifest = {
        "phase": 31,
        "status": (
            "MAPPING_RESOLVED"
            if valid
            else "MAPPING_NOT_RESOLVED"
        ),
        "mode": "ANALYSIS_ONLY",
        "h2_candidates": len(h2_rows),
        "qe_candidates": len(qe_rows),
        "cross_reference_files": len(cross_files),
        "valid_mappings": len(valid),
        "valid_mappings_with_qe": len(valid_qe),
        "output_csv": str(OUT_CSV),
        "output_json": str(OUT_JSON),
        "sha256_csv": sha256_file(OUT_CSV),
        "sha256_json": sha256_file(OUT_JSON),
        "no_qe_calculation": True,
        "no_cif_modification": True
    }

    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 80)
    print("FICHIERS")
    print("=" * 80)
    print(OUT_CSV)
    print(OUT_JSON)
    print(OUT_MANIFEST)
    print()
    print("PHASE 31 TERMINEE")
    print("=" * 80)


if __name__ == "__main__":
    main()
