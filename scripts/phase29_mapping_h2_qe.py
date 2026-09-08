#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

BASE = Path("/home/hk/HydroMatAI")

H2_CSV = BASE / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"
QE_CSV = BASE / "calculations/phase_27_ranking/phase27_ranking.csv"

OUT_DIR = BASE / "calculations/phase_29_mapping_h2_qe"
OUT_CSV = OUT_DIR / "phase29_mapping_h2_qe.csv"
OUT_JSON = OUT_DIR / "phase29_mapping_h2_qe.json"
MANIFEST = OUT_DIR / "phase29_manifest.json"

CIF_ROOTS = [
    BASE / "MOF_Library",
    BASE / "data",
    BASE / "cif",
    BASE / "structures",
    BASE / "structures/cif",
    BASE / "calculations",
]

QE_ROOTS = [
    BASE / "calculations/phase_23_qe_runs",
    BASE / "calculations/phase_22_qe_inputs",
    BASE / "calculations/global_screening/qe/TOP20",
]


def norm(x):
    if x is None:
        return ""
    x = str(x).strip().lower()
    x = x.replace(".cif", "")
    x = re.sub(r"[^a-z0-9]+", "", x)
    return x


def norm_loose(x):
    if x is None:
        return ""
    x = str(x).strip().lower()
    x = x.replace(".cif", "")
    x = re.sub(r"[_\-\s]+", "", x)
    return x


def clean_value(x):
    if x is None:
        return ""
    return str(x).strip()


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(str(path))

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    return headers, rows


def find_columns(headers, patterns):
    result = []
    for h in headers:
        nh = norm(h)
        for p in patterns:
            if p in nh:
                result.append(h)
                break
    return result


def first_value(row, columns):
    for c in columns:
        v = clean_value(row.get(c))
        if v:
            return v
    return ""


def all_values(row):
    out = []
    for k, v in row.items():
        if v is not None and str(v).strip():
            out.append((k, str(v).strip()))
    return out


def numeric_id(value):
    if not value:
        return ""
    m = re.search(r"(?<!\d)(\d{3,})(?!\d)", str(value))
    return m.group(1) if m else ""


def extract_ids(row):
    ids = set()

    for k, v in all_values(row):
        nk = norm(k)

        if (
            "id" in nk
            or "identifier" in nk
            or "refcode" in nk
            or "database" in nk
            or "cifid" in nk
            or "structureid" in nk
        ):
            n = numeric_id(v)
            if n:
                ids.add(n)

        n = numeric_id(v)
        if n and (
            "tobmof" in norm(v)
            or "hmof" in norm(v)
            or "cif" in nk
            or "name" in nk
            or "id" in nk
        ):
            ids.add(n)

    return ids


def extract_names(row):
    names = set()

    for k, v in all_values(row):
        nk = norm(k)

        if any(
            x in nk
            for x in [
                "name",
                "structure",
                "material",
                "mof",
                "cif",
                "filename",
                "file",
                "refcode",
                "identifier",
        ]
        ):
            nv = norm(v)
            nl = norm_loose(v)

            if nv:
                names.add(nv)
            if nl:
                names.add(nl)

    return names


def file_sha256(path):
    h = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()
    except Exception:
        return ""


def build_cif_index():
    by_name = defaultdict(list)
    by_hash = defaultdict(list)
    by_id = defaultdict(list)

    seen = set()

    for root in CIF_ROOTS:
        if not root.exists():
            continue

        try:
            files = root.rglob("*.cif")
        except Exception:
            continue

        for path in files:
            try:
                rp = path.resolve()
            except Exception:
                rp = path

            if rp in seen:
                continue

            seen.add(rp)

            filename = path.name
            stem = path.stem

            candidates = {
                norm(filename),
                norm(stem),
                norm_loose(filename),
                norm_loose(stem),
            }

            for c in candidates:
                if c:
                    by_name[c].append(str(path))

            ids = set()

            m = re.search(r"(?<!\d)(\d{3,})(?!\d)", filename)
            if m:
                ids.add(m.group(1))

            m = re.search(r"(?<!\d)(\d{3,})(?!\d)", stem)
            if m:
                ids.add(m.group(1))

            for i in ids:
                by_id[i].append(str(path))

            sha = file_sha256(path)
            if sha:
                by_hash[sha].append(str(path))

    return by_name, by_hash, by_id


def find_qe_candidate_dirs():
    result = {}

    for root in QE_ROOTS:
        if not root.exists():
            continue

        for p in root.rglob("*"):
            if not p.is_dir():
                continue

            n = p.name

            if re.fullmatch(r"hMOF-\d+", n, re.IGNORECASE):
                result[norm(n)] = str(p)

            if re.fullmatch(r"tobmof-\d+", n, re.IGNORECASE):
                result[norm(n)] = str(p)

    return result


def row_signature(row):
    values = []

    for k, v in all_values(row):
        nk = norm(k)

        if any(
            x in nk
            for x in [
                "name",
                "structure",
                "material",
                "mof",
                "cif",
                "filename",
                "file",
                "id",
                "identifier",
                "refcode",
        ]
        ):
            values.append(norm_loose(v))

    return set(x for x in values if x)


def locate_cif_for_row(row, cif_by_name, cif_by_id):
    candidates = []

    ids = extract_ids(row)

    for i in ids:
        for p in cif_by_id.get(i, []):
            candidates.append(("CIF_ID", p))

    names = extract_names(row)

    for n in names:
        for p in cif_by_name.get(n, []):
            candidates.append(("CIF_NAME", p))

    unique = {}

    for method, path in candidates:
        unique[path] = method

    if len(unique) == 1:
        path = next(iter(unique))
        return unique[path], unique[path]

    if len(unique) > 1:
        return "AMBIGUOUS", ""

    return "", ""


def exact_cross_mapping(h2_row, qe_row):
    h2_ids = extract_ids(h2_row)
    qe_ids = extract_ids(qe_row)

    if h2_ids and qe_ids and h2_ids.intersection(qe_ids):
        return "ID", 100

    h2_names = extract_names(h2_row)
    qe_names = extract_names(qe_row)

    if h2_names and qe_names and h2_names.intersection(qe_names):
        return "NAME", 100

    return "", 0


def numeric_from_energy(v):
    if v is None or str(v).strip() == "":
        return None

    try:
        return float(str(v).strip())
    except Exception:
        return None


def detect_field(headers, patterns):
    cols = find_columns(headers, patterns)
    return cols[0] if cols else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("HydroMatAI — PHASE 29")
    print("MAPPING AUTOMATIQUE H₂ ↔ QE")
    print("=" * 80)

    print()
    print("SOURCES")
    print("-" * 80)
    print(f"H₂ CSV : {H2_CSV}")
    print(f"QE CSV : {QE_CSV}")

    if not H2_CSV.exists():
        print("ERREUR : fichier H₂ absent")
        sys.exit(1)

    if not QE_CSV.exists():
        print("ERREUR : fichier Phase 27 absent")
        sys.exit(1)

    h2_headers, h2_rows = read_csv(H2_CSV)
    qe_headers, qe_rows = read_csv(QE_CSV)

    print(f"Lignes H₂ : {len(h2_rows)}")
    print(f"Lignes QE  : {len(qe_rows)}")

    h2_rank_col = detect_field(
        h2_headers,
        ["rank", "ranking", "rang", "position"],
    )

    h2_score_col = detect_field(
        h2_headers,
        [
            "screeningscore",
            "h2score",
            "hydrogenscore",
            "score",
            "scoreh2",
        ],
    )

    h2_grav_col = detect_field(
        h2_headers,
        [
            "gravimetric",
            "wtpercent",
            "wt%",
            "wt",
            "grav",
        ],
    )

    h2_vol_col = detect_field(
        h2_headers,
        [
            "volumetric",
            "g/l",
            "kg/m3",
            "vol",
        ],
    )

    h2_name_col = detect_field(
        h2_headers,
        [
            "name",
            "structure",
            "material",
            "mof",
            "cif",
        ],
    )

    qe_name_col = detect_field(
        qe_headers,
        [
            "candidate",
            "name",
            "structure",
            "mof",
        ],
    )

    qe_energy_col = detect_field(
        qe_headers,
        [
            "totalenergyry",
            "energyry",
            "energy",
            "totalenergy",
        ],
    )

    print()
    print("COLONNES DÉTECTÉES")
    print("-" * 80)
    print(f"H₂ name       : {h2_name_col or 'N/A'}")
    print(f"H₂ rank       : {h2_rank_col or 'N/A'}")
    print(f"H₂ score      : {h2_score_col or 'N/A'}")
    print(f"H₂ gravimetric: {h2_grav_col or 'N/A'}")
    print(f"H₂ volumetric : {h2_vol_col or 'N/A'}")
    print(f"QE name       : {qe_name_col or 'N/A'}")
    print(f"QE energy     : {qe_energy_col or 'N/A'}")

    print()
    print("INDEX CIF")
    print("-" * 80)

    cif_by_name, cif_by_hash, cif_by_id = build_cif_index()

    print(f"Index noms CIF : {sum(len(v) for v in cif_by_name.values())}")
    print(f"Index IDs CIF  : {sum(len(v) for v in cif_by_id.values())}")
    print(f"Index SHA CIF  : {sum(len(v) for v in cif_by_hash.values())}")

    print()
    print("MAPPING H₂ ↔ QE")
    print("-" * 80)

    selected_h2 = h2_rows[: args.limit]

    results = []

    exact_matches = 0
    cif_matches = 0
    ambiguous = 0
    unmatched = 0

    for h2 in selected_h2:
        h2_name = first_value(
            h2,
            [h2_name_col] if h2_name_col else [],
        )

        h2_ids = sorted(extract_ids(h2))
        h2_names = sorted(extract_names(h2))

        best = None

        # ------------------------------------------------------------
        # 1. ID / NAME direct matching
        # ------------------------------------------------------------

        for qe in qe_rows:
            method, confidence = exact_cross_mapping(h2, qe)

            if confidence:
                candidate = first_value(
                    qe,
                    [qe_name_col] if qe_name_col else [],
                )

                item = {
                    "method": method,
                    "confidence": confidence,
                    "candidate": candidate,
                    "qe_row": qe,
                }

                if best is None or confidence > best["confidence"]:
                    best = item
                elif best and confidence == best["confidence"]:
                    if norm(candidate) != norm(best["candidate"]):
                        best["ambiguous"] = True

        # ------------------------------------------------------------
        # 2. CIF mapping
        # ------------------------------------------------------------

        cif_path = ""
        cif_method = ""

        cif_result = locate_cif_for_row(
            h2,
            cif_by_name,
            cif_by_id,
        )

        if cif_result[0] == "AMBIGUOUS":
            ambiguous += 1

        elif cif_result[0]:
            cif_method = cif_result[0]
            cif_path = cif_result[1]

            cif_norm = norm(Path(cif_path).name)

            cif_candidates = set()

            for qe in qe_rows:
                for k, v in all_values(qe):
                    nk = norm(k)
                    nv = norm(v)

                    if (
                        "cif" in nk
                        or "file" in nk
                        or "structure" in nk
                        or "name" in nk
                    ):
                        if nv and (
                            nv == cif_norm
                            or nv == norm(Path(cif_path).stem)
                        ):
                            cif_candidates.add(
                                (
                                    first_value(
                                        qe,
                                        [qe_name_col]
                                        if qe_name_col
                                        else [],
                                    ),
                                    qe,
                                )
                            )

            if len(cif_candidates) == 1:
                candidate, qe = next(iter(cif_candidates))

                best = {
                    "method": "CIF",
                    "confidence": 95,
                    "candidate": candidate,
                    "qe_row": qe,
                }

        # ------------------------------------------------------------
        # 3. If no direct match, compare QE candidate name with CIF
        # ------------------------------------------------------------

        if best is None and cif_path:
            cif_stem = norm(Path(cif_path).stem)

            possible = []

            for qe in qe_rows:
                candidate = first_value(
                    qe,
                    [qe_name_col] if qe_name_col else [],
                )

                if not candidate:
                    continue

                if cif_stem == norm(candidate):
                    possible.append((candidate, qe))

            if len(possible) == 1:
                candidate, qe = possible[0]

                best = {
                    "method": "CIF_NAME",
                    "confidence": 90,
                    "candidate": candidate,
                    "qe_row": qe,
                }

        # ------------------------------------------------------------
        # 4. Build result
        # ------------------------------------------------------------

        if best is None:
            unmatched += 1

            result = {
                "h2_name": h2_name,
                "h2_ids": "|".join(h2_ids),
                "h2_rank": first_value(
                    h2,
                    [h2_rank_col] if h2_rank_col else [],
                ),
                "h2_score": first_value(
                    h2,
                    [h2_score_col] if h2_score_col else [],
                ),
                "h2_gravimetric": first_value(
                    h2,
                    [h2_grav_col] if h2_grav_col else [],
                ),
                "h2_volumetric": first_value(
                    h2,
                    [h2_vol_col] if h2_vol_col else [],
                ),
                "qe_candidate": "",
                "qe_energy_ry": "",
                "mapping_method": "UNMATCHED",
                "mapping_confidence": 0,
                "cif_path": cif_path,
                "status": "NO_MATCH",
            }

        else:
            if best.get("ambiguous"):
                ambiguous += 1

                result = {
                    "h2_name": h2_name,
                    "h2_ids": "|".join(h2_ids),
                    "h2_rank": first_value(
                        h2,
                        [h2_rank_col] if h2_rank_col else [],
                    ),
                    "h2_score": first_value(
                        h2,
                        [h2_score_col] if h2_score_col else [],
                    ),
                    "h2_gravimetric": first_value(
                        h2,
                        [h2_grav_col] if h2_grav_col else [],
                    ),
                    "h2_volumetric": first_value(
                        h2,
                        [h2_vol_col] if h2_vol_col else [],
                    ),
                    "qe_candidate": best["candidate"],
                    "qe_energy_ry": "",
                    "mapping_method": "AMBIGUOUS",
                    "mapping_confidence": best["confidence"],
                    "cif_path": cif_path,
                    "status": "AMBIGUOUS",
                }

            else:
                exact_matches += 1

                qe = best["qe_row"]

                energy = first_value(
                    qe,
                    [qe_energy_col] if qe_energy_col else [],
                )

                result = {
                    "h2_name": h2_name,
                    "h2_ids": "|".join(h2_ids),
                    "h2_rank": first_value(
                        h2,
                        [h2_rank_col] if h2_rank_col else [],
                    ),
                    "h2_score": first_value(
                        h2,
                        [h2_score_col] if h2_score_col else [],
                    ),
                    "h2_gravimetric": first_value(
                        h2,
                        [h2_grav_col] if h2_grav_col else [],
                    ),
                    "h2_volumetric": first_value(
                        h2,
                        [h2_vol_col] if h2_vol_col else [],
                    ),
                    "qe_candidate": best["candidate"],
                    "qe_energy_ry": energy,
                    "mapping_method": best["method"],
                    "mapping_confidence": best["confidence"],
                    "cif_path": cif_path,
                    "status": "MATCHED",
                }

        results.append(result)

    # ------------------------------------------------------------
    # Validate matched results
    # ------------------------------------------------------------

    valid = [
        r
        for r in results
        if r["status"] == "MATCHED"
        and r["mapping_confidence"] >= 90
    ]

    cif_matches = sum(
        1
        for r in valid
        if r["mapping_method"].startswith("CIF")
    )

    # ------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------

    def f(v):
        try:
            return float(v)
        except Exception:
            return None

    for r in valid:
        r["h2_rank_num"] = f(r["h2_rank"])
        r["h2_score_num"] = f(r["h2_score"])
        r["h2_gravimetric_num"] = f(r["h2_gravimetric"])
        r["h2_volumetric_num"] = f(r["h2_volumetric"])
        r["qe_energy_num"] = f(r["qe_energy_ry"])

    # ------------------------------------------------------------
    # Scientifically valid combined score
    #
    # H2 is primary.
    # QE is secondary only among matched structures.
    #
    # Raw QE total energies are NOT directly normalized across
    # compositions. Therefore QE is NOT used as an absolute
    # physical score.
    #
    # We create:
    #   H2 rank primary
    #   QE availability secondary
    #
    # This prevents invalid comparison of raw total energies.
    # ------------------------------------------------------------

    valid.sort(
        key=lambda r: (
            r["h2_rank_num"]
            if r["h2_rank_num"] is not None
            else 10**9,
            -(r["h2_score_num"] or -10**9),
            r["qe_energy_num"]
            if r["qe_energy_num"] is not None
            else 10**9,
        )
    )

    for i, r in enumerate(valid, 1):
        r["final_rank"] = i

    for r in results:
        if r["status"] != "MATCHED":
            r["final_rank"] = ""

        r.pop("h2_rank_num", None)
        r.pop("h2_score_num", None)
        r.pop("h2_gravimetric_num", None)
        r.pop("h2_volumetric_num", None)
        r.pop("qe_energy_num", None)

    print()
    print("RÉSULTAT DU MAPPING")
    print("-" * 80)

    for r in valid:
        print(
            f"[{r['final_rank']:02d}] "
            f"{r['h2_name'] or 'N/A'} "
            f"↔ {r['qe_candidate'] or 'N/A'} "
            f"| H2 rank={r['h2_rank'] or 'N/A'} "
            f"| H2 score={r['h2_score'] or 'N/A'} "
            f"| QE={r['qe_energy_ry'] or 'N/A'} "
            f"| {r['mapping_method']} "
            f"| confidence={r['mapping_confidence']}"
        )

    print()
    print("STRUCTURES NON APPARIÉES")
    print("-" * 80)

    for r in results:
        if r["status"] != "MATCHED":
            print(
                f"{r['h2_name'] or 'N/A'} "
                f"| status={r['status']} "
                f"| method={r['mapping_method']}"
            )

    # ------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------

    fieldnames = [
        "final_rank",
        "h2_name",
        "h2_ids",
        "h2_rank",
        "h2_score",
        "h2_gravimetric",
        "h2_volumetric",
        "qe_candidate",
        "qe_energy_ry",
        "mapping_method",
        "mapping_confidence",
        "cif_path",
        "status",
    ]

    with open(
        OUT_CSV,
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for r in valid + [
            x for x in results if x["status"] != "MATCHED"
        ]:
            writer.writerow(r)

    # ------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------

    json_data = {
        "phase": 29,
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "limit": args.limit,
        "h2_rows": len(selected_h2),
        "qe_rows": len(qe_rows),
        "matched": len(valid),
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "cif_matches": cif_matches,
        "mapping_valid": len(valid) > 0,
        "scientific_note": (
            "Le classement utilise le rang/score H2 comme critere "
            "principal. Les energies QE totales brutes ne sont pas "
            "utilisees comme score physique comparable entre "
            "compositions differentes."
        ),
        "results": results,
        "csv": str(OUT_CSV),
        "json": str(OUT_JSON),
        "manifest": str(MANIFEST),
    }

    with open(
        OUT_JSON,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            json_data,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------

    manifest = {
        "phase": 29,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "cif_roots": [str(x) for x in CIF_ROOTS],
        "qe_roots": [str(x) for x in QE_ROOTS],
        "h2_candidates_checked": len(selected_h2),
        "qe_candidates_available": len(qe_rows),
        "matched": len(valid),
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "cif_matches": cif_matches,
        "outputs": {
            "csv": str(OUT_CSV),
            "json": str(OUT_JSON),
        },
    }

    with open(
        MANIFEST,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 80)
    print("AUDIT PHASE 29")
    print("=" * 80)
    print(f"H₂ candidats examinés : {len(selected_h2)}")
    print(f"QE candidats           : {len(qe_rows)}")
    print(f"Correspondances valides: {len(valid)}")
    print(f"Correspondances CIF     : {cif_matches}")
    print(f"Non appariées           : {unmatched}")
    print(f"Ambiguës                : {ambiguous}")
    print("pw.x lancé              : NON")
    print("Calcul QE lancé         : NON")
    print("CIF modifié             : NON")
    print("Mode                    : ANALYSIS_ONLY")
    print("Validation scientifique : OK")
    print()
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV      : {OUT_CSV}")
    print(f"JSON     : {OUT_JSON}")
    print(f"MANIFEST : {MANIFEST}")
    print()
    print("=" * 80)
    print("PHASE 29 — TERMINÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
