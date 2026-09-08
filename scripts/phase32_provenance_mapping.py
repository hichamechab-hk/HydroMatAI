#!/usr/bin/env python3

import csv
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("/home/hk/HydroMatAI")

H2_CSV = ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"
QE_CSV = ROOT / "calculations/phase_27_ranking/phase27_ranking.csv"
PH30_JSON = ROOT / "calculations/phase_30_h2_mapping_diagnostic/phase30_mapping_diagnostic.json"

OUT = ROOT / "calculations/phase_32_provenance_mapping"
OUT.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT / "phase32_provenance_mapping.csv"
OUT_JSON = OUT / "phase32_provenance_mapping.json"
OUT_MANIFEST = OUT / "phase32_manifest.json"

TOP_N = 25

TOB_RE = re.compile(r"tobmof[-_ ]?(\d+)", re.I)
HMOF_RE = re.compile(r"hMOF[-_ ]?(\d+)", re.I)

# Expressions permettant de retrouver les identifiants même lorsqu'ils
# sont stockés sous forme de colonnes différentes.
ID_KEYS = [
    "name",
    "id",
    "identifier",
    "material",
    "material_id",
    "mof",
    "mof_id",
    "cif",
    "filename",
    "file",
    "path",
    "candidate",
    "structure",
    "structure_id",
    "source",
    "source_id",
    "original_name",
    "original_id",
    "parent",
    "parent_id",
    "database",
    "database_id",
]


def sha256(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def extract_tob(text):
    if text is None:
        return set()

    return {
        f"tobmof-{m.group(1)}"
        for m in TOB_RE.finditer(str(text))
    }


def extract_hmof(text):
    if text is None:
        return set()

    return {
        f"hMOF-{m.group(1)}"
        for m in HMOF_RE.finditer(str(text))
    }


def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    return str(value)


def read_h2():
    rows = []

    if not H2_CSV.exists():
        print("ERREUR H2 CSV absent:", H2_CSV)
        return rows

    with open(H2_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            names = set()

            for value in row.values():
                names |= extract_tob(value)

            if not names:
                continue

            name = sorted(names)[0]

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
                "hydrogen_wt_percent": wt,
                "raw": row
            })

    rows.sort(key=lambda x: x["h2_rank"] if x["h2_rank"] is not None else 999999)

    return rows[:TOP_N]


def read_qe():
    data = {}

    if not QE_CSV.exists():
        return data

    with open(QE_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            names = set()

            for value in row.values():
                names |= extract_hmof(value)

            if not names:
                continue

            hmof = sorted(names)[0]

            try:
                energy = float(row.get("total_energy_ry", ""))
            except Exception:
                energy = None

            data[hmof] = {
                "candidate": hmof,
                "energy": energy,
                "raw": row
            }

    return data


def load_phase30():
    if not PH30_JSON.exists():
        print("ERREUR Phase 30 JSON absent:", PH30_JSON)
        return {}

    try:
        with open(PH30_JSON, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception as e:
        print("ERREUR JSON Phase 30:", e)
        return {}


def collect_paths_from_object(obj, paths):
    if isinstance(obj, dict):
        for key, value in obj.items():

            if isinstance(value, str):
                p = Path(value)

                if p.is_file():
                    paths.add(str(p))

                # Chemin absolu ou chemin relatif au projet
                if not p.is_absolute():
                    p2 = ROOT / value
                    if p2.is_file():
                        paths.add(str(p2))

            collect_paths_from_object(value, paths)

    elif isinstance(obj, list):
        for value in obj:
            collect_paths_from_object(value, paths)


def phase30_cross_files(data):
    paths = set()

    if not data:
        return []

    # Cherche explicitement les fichiers de cross-reference.
    cross = data.get("cross_links", [])

    collect_paths_from_object(cross, paths)

    # Complément : tout chemin fichier présent dans le JSON.
    collect_paths_from_object(data, paths)

    return sorted(paths)


def discover_reference_files():
    """
    Cherche des fichiers susceptibles de contenir une relation entre
    tobmof-* et hMOF-*.

    On évite les CIF et les gros répertoires de données brutes.
    """

    roots = [
        ROOT / "reports",
        ROOT / "calculations",
        ROOT / "scripts",
        ROOT / "data",
        ROOT / "structures",
        ROOT / "MOF_Library",
    ]

    allowed = {
        ".csv",
        ".json",
        ".jsonl",
        ".txt",
        ".tsv",
        ".yaml",
        ".yml",
        ".log",
        ".md",
        ".pkl",
    }

    paths = set()

    for base in roots:
        if not base.exists():
            continue

        try:
            for p in base.rglob("*"):

                if not p.is_file():
                    continue

                if p.suffix.lower() not in allowed:
                    continue

                # Ne pas rescanner les sorties Phase 32.
                if OUT in p.parents:
                    continue

                # Fichiers énormes : on ne veut pas bloquer.
                try:
                    size = p.stat().st_size
                except Exception:
                    continue

                if size > 300 * 1024 * 1024:
                    continue

                paths.add(str(p))

        except Exception:
            continue

    return sorted(paths)


def add_evidence(evidence, tob, hmof, path, kind, confidence, context):
    if not tob or not hmof:
        return

    key = (
        tob,
        hmof,
        str(path),
        kind
    )

    if key not in evidence:
        evidence[key] = {
            "tobmof": tob,
            "hmof": hmof,
            "file": str(path),
            "kind": kind,
            "confidence": confidence,
            "context": context[:2000]
        }


def scan_csv(path, evidence):
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)

            for line_no, row in enumerate(reader, start=2):

                text = " | ".join(
                    f"{k}={clean_text(v)}"
                    for k, v in row.items()
                )

                tobs = extract_tob(text)
                hmofs = extract_hmof(text)

                if tobs and hmofs:
                    for tob in tobs:
                        for hmof in hmofs:
                            add_evidence(
                                evidence,
                                tob,
                                hmof,
                                path,
                                "CSV_SAME_ROW",
                                100,
                                f"line={line_no} | {text}"
                            )

    except Exception:
        scan_text(path, evidence)


def scan_json_value(obj, path, evidence, location="root"):
    if isinstance(obj, dict):

        scalar_text = []

        for key, value in obj.items():

            if key.lower() in ID_KEYS or isinstance(value, (str, int, float)):
                scalar_text.append(
                    f"{key}={clean_text(value)}"
                )

        text = " | ".join(scalar_text)

        tobs = extract_tob(text)
        hmofs = extract_hmof(text)

        if tobs and hmofs:
            for tob in tobs:
                for hmof in hmofs:
                    add_evidence(
                        evidence,
                        tob,
                        hmof,
                        path,
                        "JSON_SAME_OBJECT",
                        100,
                        f"{location} | {text}"
                    )

        for key, value in obj.items():
            scan_json_value(
                value,
                path,
                evidence,
                f"{location}.{key}"
            )

    elif isinstance(obj, list):

        for i, value in enumerate(obj):
            scan_json_value(
                value,
                path,
                evidence,
                f"{location}[{i}]"
            )

    elif isinstance(obj, str):

        tobs = extract_tob(obj)
        hmofs = extract_hmof(obj)

        if tobs and hmofs:
            for tob in tobs:
                for hmof in hmofs:
                    add_evidence(
                        evidence,
                        tob,
                        hmof,
                        path,
                        "JSON_SAME_VALUE",
                        95,
                        f"{location} | {obj}"
                    )


def scan_json(path, evidence):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        scan_json_value(data, path, evidence)

    except Exception:
        scan_text(path, evidence)


def scan_text(path, evidence):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return

    # SAME_LINE
    for i, line in enumerate(lines, start=1):

        tobs = extract_tob(line)
        hmofs = extract_hmof(line)

        if tobs and hmofs:
            for tob in tobs:
                for hmof in hmofs:
                    add_evidence(
                        evidence,
                        tob,
                        hmof,
                        path,
                        "SAME_LINE",
                        95,
                        f"line={i} | {line.strip()}"
                    )

    # Fenêtre locale.
    for i in range(len(lines)):

        start = max(0, i - 3)
        end = min(len(lines), i + 4)

        block = "".join(lines[start:end])

        tobs = extract_tob(block)
        hmofs = extract_hmof(block)

        # Seulement si relation non ambiguë.
        if len(tobs) == 1 and len(hmofs) == 1:

            tob = next(iter(tobs))
            hmof = next(iter(hmofs))

            add_evidence(
                evidence,
                tob,
                hmof,
                path,
                "LOCAL_CONTEXT",
                75,
                f"lines={start+1}-{end} | {block.strip()}"
            )


def scan_file(path, evidence):
    suffix = path.suffix.lower()

    if suffix == ".csv" or suffix == ".tsv":
        scan_csv(path, evidence)
    elif suffix == ".json" or suffix == ".jsonl":
        scan_json(path, evidence)
    else:
        scan_text(path, evidence)


def direct_filename_mapping(path, evidence):
    name = path.name

    tobs = extract_tob(name)
    hmofs = extract_hmof(name)

    if tobs and hmofs:

        for tob in tobs:
            for hmof in hmofs:
                add_evidence(
                    evidence,
                    tob,
                    hmof,
                    path,
                    "FILENAME",
                    100,
                    name
                )


def build_mapping(h2_rows, qe_rows, evidence):

    by_tob = defaultdict(list)

    for ev in evidence.values():
        by_tob[ev["tobmof"]].append(ev)

    results = []

    for h2 in h2_rows:

        tob = h2["h2_name"]

        candidate_groups = defaultdict(list)

        for ev in by_tob.get(tob, []):
            candidate_groups[ev["hmof"]].append(ev)

        candidates = []

        for hmof, evs in candidate_groups.items():

            max_conf = max(
                e["confidence"]
                for e in evs
            )

            evidence_types = sorted(
                set(e["kind"] for e in evs)
            )

            candidates.append({
                "hmof": hmof,
                "max_confidence": max_conf,
                "evidence_count": len(evs),
                "evidence_types": evidence_types,
                "evidence": evs
            })

        candidates.sort(
            key=lambda x: (
                -x["max_confidence"],
                -x["evidence_count"]
            )
        )

        verdict = "NO_MAPPING"
        selected = None

        if len(candidates) == 1:

            c = candidates[0]

            if c["max_confidence"] >= 90:
                verdict = "VALID_MAPPING"
                selected = c
            else:
                verdict = "WEAK_MAPPING"

        elif len(candidates) > 1:

            top = candidates[0]
            second = candidates[1]

            if (
                top["max_confidence"] >= 90
                and top["max_confidence"] > second["max_confidence"]
            ):
                verdict = "VALID_MAPPING"
                selected = top
            else:
                verdict = "AMBIGUOUS_MAPPING"

        hmof = selected["hmof"] if selected else None

        qe = qe_rows.get(hmof)

        results.append({
            "h2_name": tob,
            "h2_rank": h2["h2_rank"],
            "hydrogen_score": h2["hydrogen_score"],
            "hydrogen_wt_percent": h2["hydrogen_wt_percent"],
            "mapping_verdict": verdict,
            "qe_candidate": hmof,
            "mapping_confidence": (
                selected["max_confidence"]
                if selected else None
            ),
            "mapping_evidence_count": (
                selected["evidence_count"]
                if selected else 0
            ),
            "mapping_evidence_types": (
                ";".join(selected["evidence_types"])
                if selected else ""
            ),
            "qe_available": bool(qe),
            "qe_total_energy_ry": (
                qe["energy"] if qe else None
            ),
            "qe_energy_is_information_only": bool(qe),
            "h2_primary_rank": h2["h2_rank"],
            "combined_physical_score": None
        })

    return results


def print_mapping(results):

    print()
    print("=" * 90)
    print("MAPPING H2 -> QE")
    print("=" * 90)

    for r in results:

        print(
            f'{r["h2_name"]:14s} | '
            f'H2={str(r["h2_rank"]):>3s} | '
            f'{r["mapping_verdict"]:18s} | '
            f'QE={str(r["qe_candidate"]):10s} | '
            f'conf={str(r["mapping_confidence"]):>4s} | '
            f'QE_available={r["qe_available"]}'
        )


def main():

    print("=" * 90)
    print("PHASE 32 — PROVENANCE / H2 <-> QE MAPPING")
    print("=" * 90)
    print("MODE: ANALYSIS_ONLY")
    print("pw.x: NO")
    print("QE CALCULATION: NO")
    print("CIF MODIFICATION: NO")
    print()

    h2_rows = read_h2()
    qe_rows = read_qe()
    ph30 = load_phase30()

    print(f"H2 TOP {TOP_N}: {len(h2_rows)}")
    print(f"QE rows: {len(qe_rows)}")

    # Phase 30
    phase30_files = phase30_cross_files(ph30)

    print(
        f"Fichiers explicitement references par Phase 30: "
        f"{len(phase30_files)}"
    )

    # Discovery complémentaire
    discovered = discover_reference_files()

    print(
        f"Fichiers references potentiels decouverts: "
        f"{len(discovered)}"
    )

    all_files = sorted(
        set(phase30_files) | set(discovered)
    )

    print(
        f"Fichiers uniques inspectables: "
        f"{len(all_files)}"
    )

    print()

    evidence = {}

    scanned = 0

    for path_str in all_files:

        path = Path(path_str)

        if not path.exists():
            continue

        # Vérification rapide : fichier contenant au moins
        # un identifiant H2 ou QE.
        try:
            if path.stat().st_size > 300 * 1024 * 1024:
                continue
        except Exception:
            continue

        scanned += 1

        try:
            direct_filename_mapping(path, evidence)

            # Les fichiers de données inutiles peuvent être ignorés
            # après détection des noms.
            scan_file(path, evidence)

        except Exception as e:
            print(f"WARNING {path}: {e}")

    print()
    print(f"Fichiers effectivement scans: {scanned}")
    print(f"Preuves H2<->QE detectees: {len(evidence)}")

    results = build_mapping(
        h2_rows,
        qe_rows,
        evidence
    )

    valid = [
        r for r in results
        if r["mapping_verdict"] == "VALID_MAPPING"
    ]

    valid_qe = [
        r for r in valid
        if r["qe_available"]
    ]

    ambiguous = [
        r for r in results
        if r["mapping_verdict"] == "AMBIGUOUS_MAPPING"
    ]

    weak = [
        r for r in results
        if r["mapping_verdict"] == "WEAK_MAPPING"
    ]

    print_mapping(results)

    print()
    print("=" * 90)
    print("SYNTHESE")
    print("=" * 90)
    print(f"H2 candidats:              {len(results)}")
    print(f"Mappings valides:          {len(valid)}")
    print(f"Mappings + QE disponible:  {len(valid_qe)}")
    print(f"Mappings ambigus:           {len(ambiguous)}")
    print(f"Mappings faibles:           {len(weak)}")
    print(f"Preuves totales:            {len(evidence)}")

    # CSV final
    fields = [
        "h2_name",
        "h2_rank",
        "hydrogen_score",
        "hydrogen_wt_percent",
        "mapping_verdict",
        "qe_candidate",
        "mapping_confidence",
        "mapping_evidence_count",
        "mapping_evidence_types",
        "qe_available",
        "qe_total_energy_ry",
        "qe_energy_is_information_only",
        "h2_primary_rank",
        "combined_physical_score"
    ]

    with open(
        OUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        for row in results:
            writer.writerow(row)

    # JSON
    json_output = {
        "phase": 32,
        "mode": "ANALYSIS_ONLY",
        "status": (
            "MAPPING_RESOLVED"
            if valid
            else "MAPPING_NOT_RESOLVED"
        ),
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "phase30_source": str(PH30_JSON),
        "top_n": TOP_N,
        "h2_count": len(results),
        "qe_count": len(qe_rows),
        "phase30_reference_files": phase30_files,
        "all_scanned_files": all_files,
        "scanned_files": scanned,
        "evidence_count": len(evidence),
        "valid_mappings": len(valid),
        "valid_mappings_with_qe": len(valid_qe),
        "ambiguous_mappings": len(ambiguous),
        "weak_mappings": len(weak),
        "results": results,
        "evidence": list(evidence.values()),
        "scientific_constraints": [
            "Generic numeric ID hits are not accepted as mapping evidence.",
            "A mapping requires explicit co-occurrence of tobmof-* and hMOF-*.",
            "Raw QE total energies are not used as a combined physical score.",
            "QE energy remains informational because compositions differ.",
            "No QE calculation is launched.",
            "No CIF is modified."
        ]
    }

    with open(
        OUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            json_output,
            f,
            indent=2,
            ensure_ascii=False
        )

    manifest = {
        "phase": 32,
        "status": (
            "MAPPING_RESOLVED"
            if valid
            else "MAPPING_NOT_RESOLVED"
        ),
        "mode": "ANALYSIS_ONLY",
        "h2_count": len(results),
        "qe_count": len(qe_rows),
        "scanned_files": scanned,
        "evidence_count": len(evidence),
        "valid_mappings": len(valid),
        "valid_mappings_with_qe": len(valid_qe),
        "ambiguous_mappings": len(ambiguous),
        "weak_mappings": len(weak),
        "no_qe_calculation": True,
        "no_cif_modification": True,
        "output_csv": str(OUT_CSV),
        "output_json": str(OUT_JSON),
        "sha256_csv": sha256(OUT_CSV),
        "sha256_json": sha256(OUT_JSON)
    }

    with open(
        OUT_MANIFEST,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 90)
    print("SORTIES")
    print("=" * 90)
    print(OUT_CSV)
    print(OUT_JSON)
    print(OUT_MANIFEST)
    print()
    print("PHASE 32 TERMINEE")
    print("=" * 90)


if __name__ == "__main__":
    main()
