#!/usr/bin/env python3

import csv
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict

BASE = Path("/home/hk/HydroMatAI")

H2_CSV = BASE / "reports/global_screening/TOP200_GLOBAL_H2_RANKED.csv"
QE_CSV = BASE / "calculations/phase_27_ranking/phase27_ranking.csv"

OUT_DIR = BASE / "calculations/phase_30_h2_mapping_diagnostic"
OUT_CSV = OUT_DIR / "phase30_mapping_diagnostic.csv"
OUT_JSON = OUT_DIR / "phase30_mapping_diagnostic.json"
MANIFEST = OUT_DIR / "phase30_manifest.json"

SEARCH_ROOTS = [
    BASE / "reports",
    BASE / "calculations",
    BASE / "scripts",
    BASE / "MOF_Library",
    BASE / "data",
    BASE / "structures",
]


def norm(x):
    if x is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(x).lower().strip())


def numeric_ids(text):
    if text is None:
        return set()

    return set(
        re.findall(
            r"(?<!\d)(\d{3,})(?!\d)",
            str(text),
        )
    )


def read_csv(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sha256(path):
    h = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while True:
                block = f.read(1024 * 1024)

                if not block:
                    break

                h.update(block)

        return h.hexdigest()

    except Exception:
        return ""


def relevant_columns(headers):
    cols = []

    keywords = [
        "id",
        "name",
        "structure",
        "mof",
        "cif",
        "file",
        "path",
        "refcode",
        "identifier",
        "material",
        "database",
        "source",
        "formula",
        "composition",
        "inchi",
        "smiles",
        "hash",
        "key",
        "code",
    ]

    for h in headers:
        nh = norm(h)

        if any(k in nh for k in keywords):
            cols.append(h)

    return cols


def row_tokens(row, headers):
    tokens = set()

    for h in relevant_columns(headers):
        value = row.get(h, "")

        if not value:
            continue

        tokens.add(norm(value))

        for number in numeric_ids(value):
            tokens.add(number)

        raw = str(value).lower()

        for match in re.findall(
            r"(?:tobmof|hmof)[-_]?\d+",
            raw,
        ):
            tokens.add(norm(match))

    return tokens


def scan_files():
    files = []

    seen = set()

    extensions = {
        ".csv",
        ".json",
        ".txt",
        ".cif",
        ".yaml",
        ".yml",
        ".out",
        ".in",
        ".dat",
    }

    for root in SEARCH_ROOTS:

        if not root.exists():
            continue

        try:
            iterator = root.rglob("*")
        except Exception:
            continue

        for p in iterator:

            try:
                if not p.is_file():
                    continue

                if p.suffix.lower() not in extensions:
                    continue

                rp = str(p.resolve())

                if rp in seen:
                    continue

                seen.add(rp)

                files.append(p)

            except Exception:
                continue

    return files


def search_text_file(path, patterns):

    try:
        data = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    except Exception:
        return []

    matches = []

    low = data.lower()

    for pattern in patterns:

        p = pattern.lower()

        if p in low:
            matches.append(pattern)

    return matches


def main():

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print("HydroMatAI — PHASE 30")
    print("DIAGNOSTIC PROFOND DU MAPPING H₂ ↔ QE")
    print("=" * 80)

    if not H2_CSV.exists():
        print()
        print("ERREUR : fichier H₂ introuvable")
        print(H2_CSV)
        return

    if not QE_CSV.exists():
        print()
        print("ERREUR : fichier QE introuvable")
        print(QE_CSV)
        return

    h2_headers, h2_rows = read_csv(H2_CSV)
    qe_headers, qe_rows = read_csv(QE_CSV)

    print()
    print("SOURCES")
    print("-" * 80)
    print("H₂ :", H2_CSV)
    print("QE :", QE_CSV)
    print("H₂ lignes :", len(h2_rows))
    print("QE lignes :", len(qe_rows))

    print()
    print("COLONNES H₂")
    print("-" * 80)

    for h in h2_headers:
        print(h)

    print()
    print("COLONNES QE")
    print("-" * 80)

    for h in qe_headers:
        print(h)

    # ---------------------------------------------------------
    # Extraction des 25 premiers candidats H2
    # ---------------------------------------------------------

    h2_selected = h2_rows[:25]

    h2_identifiers = set()

    candidate_data = []

    for row in h2_selected:

        tokens = row_tokens(
            row,
            h2_headers,
        )

        identifiers = set()

        for value in row.values():

            if value:

                identifiers.update(
                    numeric_ids(value)
                )

                for match in re.findall(
                    r"(?:tobmof|hmof)[-_]?\d+",
                    str(value).lower(),
                ):
                    identifiers.add(
                        norm(match)
                    )

        name = ""

        for h in h2_headers:

            nh = norm(h)

            if any(
                x in nh
                for x in [
                    "name",
                    "structure",
                    "material",
                    "mof",
                    "cif",
                ]
            ):

                if row.get(h):

                    name = row[h]
                    break

        h2_identifiers.update(identifiers)

        candidate_data.append(
            {
                "name": name,
                "tokens": sorted(tokens),
                "identifiers": sorted(identifiers),
                "row": row,
            }
        )

    print()
    print("CANDIDATS H₂")
    print("-" * 80)

    for i, c in enumerate(
        candidate_data,
        1,
    ):

        print(
            f"{i:02d}. "
            f"{c['name']} "
            f"| IDs={','.join(c['identifiers'])}"
        )

    # ---------------------------------------------------------
    # QE identifiers
    # ---------------------------------------------------------

    qe_data = []

    for row in qe_rows:

        tokens = row_tokens(
            row,
            qe_headers,
        )

        identifiers = set()

        for value in row.values():

            if value:

                identifiers.update(
                    numeric_ids(value)
                )

                for match in re.findall(
                    r"(?:tobmof|hmof)[-_]?\d+",
                    str(value).lower(),
                ):
                    identifiers.add(
                        norm(match)
                    )

        name = ""

        for h in qe_headers:

            nh = norm(h)

            if any(
                x in nh
                for x in [
                    "candidate",
                    "name",
                    "structure",
                    "mof",
                ]
            ):

                if row.get(h):

                    name = row[h]
                    break

        qe_data.append(
            {
                "name": name,
                "tokens": sorted(tokens),
                "identifiers": sorted(identifiers),
                "row": row,
            }
        )

    print()
    print("QE")
    print("-" * 80)

    for q in qe_data:

        print(
            f"{q['name']} "
            f"| IDs={','.join(q['identifiers'])}"
        )

    # ---------------------------------------------------------
    # Recherche directe H2 -> QE
    # ---------------------------------------------------------

    print()
    print("MATCHING DIRECT")
    print("-" * 80)

    direct_matches = []

    for h in candidate_data:

        found = []

        for q in qe_data:

            common_tokens = set(
                h["tokens"]
            ).intersection(
                q["tokens"]
            )

            common_ids = set(
                h["identifiers"]
            ).intersection(
                q["identifiers"]
            )

            if common_ids:

                found.append(
                    {
                        "qe": q["name"],
                        "method": "ID",
                        "confidence": 100,
                        "common": sorted(
                            common_ids
                        ),
                    }
                )

            elif common_tokens:

                found.append(
                    {
                        "qe": q["name"],
                        "method": "TOKEN",
                        "confidence": 80,
                        "common": sorted(
                            common_tokens
                        ),
                    }
                )

        direct_matches.append(
            {
                "h2": h["name"],
                "matches": found,
            }
        )

        if found:

            print(
                h["name"],
                "=>",
                found,
            )

    # ---------------------------------------------------------
    # Recherche globale dans fichiers
    # ---------------------------------------------------------

    print()
    print("SCAN GLOBAL DES FICHIERS")
    print("-" * 80)

    all_files = scan_files()

    print(
        f"Fichiers inspectables : {len(all_files)}"
    )

    # Recherche des noms H2 dans les fichiers
    file_hits = defaultdict(
        lambda: {
            "files": set(),
            "patterns": set(),
        }
    )

    search_patterns = set()

    for c in candidate_data:

        if c["name"]:

            search_patterns.add(
                c["name"]
            )

        for identifier in c["identifiers"]:

            search_patterns.add(
                identifier
            )

    for p in search_patterns:

        if len(p) < 4:
            continue

        for path in all_files:

            try:

                hits = search_text_file(
                    path,
                    [p],
                )

                if hits:

                    file_hits[p]["files"].add(
                        str(path)
                    )

                    file_hits[p]["patterns"].update(
                        hits
                    )

            except Exception:
                continue

    # ---------------------------------------------------------
    # Affichage hits
    # ---------------------------------------------------------

    total_hits = 0

    for pattern, info in file_hits.items():

        if not info["files"]:
            continue

        total_hits += len(
            info["files"]
        )

        print()
        print(
            f"IDENTIFIANT : {pattern}"
        )

        for path in sorted(
            info["files"]
        )[:20]:

            print(
                "   ",
                path,
            )

    print()
    print(
        f"Hits fichiers : {total_hits}"
    )

    # ---------------------------------------------------------
    # Recherche spécifique tobmof <-> hmof
    # ---------------------------------------------------------

    print()
    print("RECHERCHE TOBMOF ↔ HMOF")
    print("-" * 80)

    cross_links = []

    for path in all_files:

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()

        except Exception:
            continue

        tobmofs = set(
            re.findall(
                r"tobmof[-_]?\d+",
                text,
            )
        )

        hmofs = set(
            re.findall(
                r"hmof[-_]?\d+",
                text,
            )
        )

        if tobmofs and hmofs:

            cross_links.append(
                {
                    "file": str(path),
                    "tobmof": sorted(
                        set(
                            norm(x)
                            for x in tobmofs
                        )
                    ),
                    "hmof": sorted(
                        set(
                            norm(x)
                            for x in hmofs
                        )
                    ),
                }
            )

    for link in cross_links:

        print()
        print("FICHIER :", link["file"])
        print(
            "  TOBMOF :",
            ", ".join(link["tobmof"]),
        )
        print(
            "  HMOF   :",
            ", ".join(link["hmof"]),
        )

    # ---------------------------------------------------------
    # Recherche IDs communs globale
    # ---------------------------------------------------------

    print()
    print("RECHERCHE IDs COMMUNS")
    print("-" * 80)

    global_id_hits = []

    for c in candidate_data:

        for identifier in c["identifiers"]:

            matches = []

            for path in all_files:

                try:

                    text = path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )

                except Exception:
                    continue

                if identifier in text:

                    matches.append(
                        str(path)
                    )

            if matches:

                global_id_hits.append(
                    {
                        "h2": c["name"],
                        "id": identifier,
                        "files": matches[:50],
                    }
                )

                print(
                    c["name"],
                    "| ID=",
                    identifier,
                    "| fichiers=",
                    len(matches),
                )

    # ---------------------------------------------------------
    # Verdict
    # ---------------------------------------------------------

    if direct_matches and any(
        x["matches"]
        for x in direct_matches
    ):

        verdict = (
            "DIRECT_MAPPING_FOUND"
        )

    elif cross_links:

        verdict = (
            "CROSS_REFERENCE_FILES_FOUND"
        )

    elif global_id_hits:

        verdict = (
            "IDENTIFIERS_FOUND_BUT_MAPPING_UNRESOLVED"
        )

    else:

        verdict = (
            "NO_MAPPING_SOURCE_FOUND"
        )

    # ---------------------------------------------------------
    # CSV
    # ---------------------------------------------------------

    rows_csv = []

    for c in candidate_data:

        matches = []

        for dm in direct_matches:

            if dm["h2"] == c["name"]:

                matches = dm["matches"]
                break

        rows_csv.append(
            {
                "h2_name": c["name"],
                "h2_ids": "|".join(
                    c["identifiers"]
                ),
                "direct_qe_matches": "|".join(
                    x["qe"]
                    for x in matches
                ),
                "mapping_method": "|".join(
                    x["method"]
                    for x in matches
                ),
                "confidence": "|".join(
                    str(x["confidence"])
                    for x in matches
                ),
                "global_file_hits": sum(
                    1
                    for p, info
                    in file_hits.items()
                    if p in c["identifiers"]
                    and info["files"]
                ),
                "status": (
                    "MATCH"
                    if matches
                    else "NO_MATCH"
                ),
            }
        )

    with open(
        OUT_CSV,
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "h2_name",
                "h2_ids",
                "direct_qe_matches",
                "mapping_method",
                "confidence",
                "global_file_hits",
                "status",
            ],
        )

        writer.writeheader()

        writer.writerows(
            rows_csv
        )

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    json_data = {
        "phase": 30,
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "h2_rows": len(h2_rows),
        "qe_rows": len(qe_rows),
        "h2_checked": len(candidate_data),
        "direct_matches": direct_matches,
        "cross_links": cross_links,
        "global_id_hits": global_id_hits,
        "verdict": verdict,
        "outputs": {
            "csv": str(OUT_CSV),
            "json": str(OUT_JSON),
            "manifest": str(MANIFEST),
        },
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

    # ---------------------------------------------------------
    # Manifest
    # ---------------------------------------------------------

    manifest = {
        "phase": 30,
        "mode": "ANALYSIS_ONLY",
        "calculations_launched": False,
        "pw_x_launched": False,
        "cif_modified": False,
        "h2_source": str(H2_CSV),
        "qe_source": str(QE_CSV),
        "files_scanned": len(all_files),
        "h2_candidates_checked": len(
            candidate_data
        ),
        "direct_matches": sum(
            1
            for x in direct_matches
            if x["matches"]
        ),
        "cross_reference_files": len(
            cross_links
        ),
        "global_identifier_hits": len(
            global_id_hits
        ),
        "verdict": verdict,
        "scientific_rule": (
            "Aucun classement H2+QE n'est produit "
            "sans correspondance structurelle valide."
        ),
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

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("AUDIT PHASE 30")
    print("=" * 80)

    print(
        f"Candidats H₂ examinés : {len(candidate_data)}"
    )

    print(
        "Correspondances directes :",
        sum(
            1
            for x in direct_matches
            if x["matches"]
        ),
    )

    print(
        "Fichiers cross-reference :",
        len(cross_links),
    )

    print(
        "Hits IDs globaux :",
        len(global_id_hits),
    )

    print(
        "VERDICT :",
        verdict,
    )

    print(
        "pw.x lancé : NON"
    )

    print(
        "Calcul QE lancé : NON"
    )

    print(
        "CIF modifié : NON"
    )

    print(
        "Mode : ANALYSIS_ONLY"
    )

    print()
    print("FICHIERS")
    print("-" * 80)

    print(
        "CSV      :",
        OUT_CSV,
    )

    print(
        "JSON     :",
        OUT_JSON,
    )

    print(
        "MANIFEST :",
        MANIFEST,
    )

    print()
    print("=" * 80)
    print("PHASE 30 — TERMINÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
