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

OUT = ROOT / "calculations/phase_33_provenance_trace"
OUT.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT / "phase33_provenance_trace.csv"
OUT_JSON = OUT / "phase33_provenance_trace.json"
OUT_MANIFEST = OUT / "phase33_manifest.json"

TOP_N = 25

TOB_RE = re.compile(r"tobmof[-_ ]?(\d+)", re.I)
HMOF_RE = re.compile(r"hMOF[-_ ]?(\d+)", re.I)

# Identifiants numériques intéressants, mais jamais acceptés seuls
# comme preuve finale.
NUMBER_RE = re.compile(r"(?<!\d)(\d{2,8})(?!\d)")

HASH_RE = re.compile(
    r"\b[a-fA-F0-9]{32}\b|"
    r"\b[a-fA-F0-9]{40}\b|"
    r"\b[a-fA-F0-9]{64}\b"
)

CIF_RE = re.compile(
    r"[\w./-]+\.cif\b",
    re.I
)

KEYWORDS = [
    "id",
    "identifier",
    "name",
    "filename",
    "file",
    "path",
    "source",
    "source_id",
    "original",
    "parent",
    "structure",
    "structure_id",
    "material",
    "material_id",
    "cif",
    "hash",
    "sha",
    "uuid",
    "index",
    "database",
    "db",
    "mof",
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


def tob_names(text):
    if text is None:
        return set()

    return {
        f"tobmof-{m.group(1)}"
        for m in TOB_RE.finditer(str(text))
    }


def hmof_names(text):
    if text is None:
        return set()

    return {
        f"hMOF-{m.group(1)}"
        for m in HMOF_RE.finditer(str(text))
    }


def numeric_tokens(text):
    if text is None:
        return set()

    return set(NUMBER_RE.findall(str(text)))


def hashes(text):
    if text is None:
        return set()

    return {
        x.lower()
        for x in HASH_RE.findall(str(text))
    }


def cif_names(text):
    if text is None:
        return set()

    return {
        x.lower()
        for x in CIF_RE.findall(str(text))
    }


def text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        try:
            return json.dumps(
                value,
                ensure_ascii=False
            )
        except Exception:
            return str(value)

    return str(value)


def load_h2():
    result = []

    with open(
        H2_CSV,
        newline="",
        encoding="utf-8",
        errors="replace"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            names = set()

            for value in row.values():
                names |= tob_names(value)

            if not names:
                continue

            name = sorted(names)[0]

            try:
                rank = int(float(row.get("rank", "")))
            except Exception:
                rank = None

            try:
                score = float(
                    row.get("hydrogen_score", "")
                )
            except Exception:
                score = None

            try:
                wt = float(
                    row.get("hydrogen_wt_percent", "")
                )
            except Exception:
                wt = None

            result.append({
                "tobmof": name,
                "rank": rank,
                "hydrogen_score": score,
                "hydrogen_wt_percent": wt,
                "raw": row
            })

    result.sort(
        key=lambda x:
        x["rank"] if x["rank"] is not None else 999999
    )

    return result[:TOP_N]


def load_qe():
    result = {}

    if not QE_CSV.exists():
        return result

    with open(
        QE_CSV,
        newline="",
        encoding="utf-8",
        errors="replace"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            names = set()

            for value in row.values():
                names |= hmof_names(value)

            if not names:
                continue

            hmof = sorted(names)[0]

            try:
                energy = float(
                    row.get("total_energy_ry", "")
                )
            except Exception:
                energy = None

            result[hmof] = {
                "energy": energy,
                "raw": row
            }

    return result


def load_phase30():

    if not PH30_JSON.exists():
        return {}

    try:
        with open(
            PH30_JSON,
            encoding="utf-8",
            errors="replace"
        ) as f:
            return json.load(f)
    except Exception:
        return {}


def discover_files():

    roots = [
        ROOT / "reports",
        ROOT / "calculations",
        ROOT / "scripts",
        ROOT / "data",
        ROOT / "structures",
        ROOT / "MOF_Library",
    ]

    extensions = {
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".txt",
        ".log",
        ".yaml",
        ".yml",
        ".md",
    }

    files = set()

    for base in roots:

        if not base.exists():
            continue

        try:
            for p in base.rglob("*"):

                if not p.is_file():
                    continue

                if p.suffix.lower() not in extensions:
                    continue

                if OUT in p.parents:
                    continue

                try:
                    if p.stat().st_size > 300 * 1024 * 1024:
                        continue
                except Exception:
                    continue

                files.add(p)

        except Exception:
            pass

    return sorted(files)


def extract_phase30_paths(data):

    paths = set()

    def walk(obj):

        if isinstance(obj, dict):

            for key, value in obj.items():

                if isinstance(value, str):

                    p = Path(value)

                    if p.is_file():
                        paths.add(p)

                    if not p.is_absolute():

                        p2 = ROOT / value

                        if p2.is_file():
                            paths.add(p2)

                walk(value)

        elif isinstance(obj, list):

            for value in obj:
                walk(value)

    walk(data)

    return sorted(paths)


def make_file_summary(path):

    summary = {
        "file": str(path),
        "size": None,
        "sha256": None,
        "tobmof": set(),
        "hmof": set(),
        "numbers": set(),
        "hashes": set(),
        "cifs": set(),
        "keywords": set(),
    }

    try:
        summary["size"] = path.stat().st_size
        summary["sha256"] = sha256(path)
    except Exception:
        return summary

    try:
        with open(
            path,
            encoding="utf-8",
            errors="replace"
        ) as f:

            content = f.read()

    except Exception:
        return summary

    summary["tobmof"] = tob_names(content)
    summary["hmof"] = hmof_names(content)
    summary["numbers"] = numeric_tokens(content)
    summary["hashes"] = hashes(content)
    summary["cifs"] = cif_names(content)

    low = content.lower()

    for key in KEYWORDS:
        if key in low:
            summary["keywords"].add(key)

    return summary


def extract_field_relations_csv(path):

    relations = []

    try:
        with open(
            path,
            newline="",
            encoding="utf-8",
            errors="replace"
        ) as f:

            reader = csv.DictReader(f)

            headers = reader.fieldnames or []

            for line_no, row in enumerate(reader, start=2):

                field_values = {
                    k: text(v)
                    for k, v in row.items()
                    if v is not None
                }

                tobs = set()
                hmofs = set()

                for value in field_values.values():
                    tobs |= tob_names(value)
                    hmofs |= hmof_names(value)

                if tobs or hmofs:

                    relations.append({
                        "file": str(path),
                        "line": line_no,
                        "headers": headers,
                        "fields": field_values,
                        "tobmof": sorted(tobs),
                        "hmof": sorted(hmofs)
                    })

    except Exception:
        pass

    return relations


def extract_json_relations(path):

    relations = []

    try:
        with open(
            path,
            encoding="utf-8",
            errors="replace"
        ) as f:

            data = json.load(f)

    except Exception:
        return relations

    def walk(obj, location="root"):

        if isinstance(obj, dict):

            fields = {
                str(k): text(v)
                for k, v in obj.items()
                if not isinstance(v, (dict, list))
            }

            combined = " | ".join(
                f"{k}={v}"
                for k, v in fields.items()
            )

            tobs = tob_names(combined)
            hmofs = hmof_names(combined)

            if tobs or hmofs:

                relations.append({
                    "file": str(path),
                    "location": location,
                    "fields": fields,
                    "tobmof": sorted(tobs),
                    "hmof": sorted(hmofs)
                })

            for key, value in obj.items():
                walk(
                    value,
                    f"{location}.{key}"
                )

        elif isinstance(obj, list):

            for i, value in enumerate(obj):

                walk(
                    value,
                    f"{location}[{i}]"
                )

    walk(data)

    return relations


def add_relation(
    relations,
    tob,
    hmof,
    path,
    kind,
    confidence,
    reason,
    bridge=None
):

    if not tob or not hmof:
        return

    relations.append({
        "tobmof": tob,
        "hmof": hmof,
        "file": str(path),
        "kind": kind,
        "confidence": confidence,
        "reason": reason,
        "bridge": bridge or ""
    })


def analyze_numeric_bridge(
    h2_names,
    qe_names,
    file_summaries,
    relations
):

    """
    Cherche un pont numérique entre tobmof-* et hMOF-*.

    IMPORTANT :
    un nombre commun seul n'est jamais accepté comme mapping valide.
    Il produit seulement une piste.
    """

    h2_numbers = {
        tob: {
            tob.split("-")[-1]
        }
        for tob in h2_names
    }

    qe_numbers = {
        hmof: {
            hmof.split("-")[-1]
        }
        for hmof in qe_names
    }

    for summary in file_summaries:

        nums = summary["numbers"]

        tob_hits = []

        for tob, nums_tob in h2_numbers.items():

            if nums_tob & nums:
                tob_hits.append(tob)

        hmof_hits = []

        for hmof, nums_hmof in qe_numbers.items():

            if nums_hmof & nums:
                hmof_hits.append(hmof)

        if len(tob_hits) == 1 and len(hmof_hits) == 1:

            tob = tob_hits[0]
            hmof = hmof_hits[0]

            shared = sorted(
                h2_numbers[tob] & nums &
                qe_numbers[hmof]
            )

            if shared:

                add_relation(
                    relations,
                    tob,
                    hmof,
                    summary["file"],
                    "NUMERIC_BRIDGE",
                    40,
                    "Même identifiant numérique présent dans le fichier",
                    ",".join(shared)
                )


def analyze_filename_bridge(
    h2_names,
    qe_names,
    files,
    relations
):

    for path in files:

        name = path.name.lower()

        tobs = tob_names(name)
        hmofs = hmof_names(name)

        if len(tobs) == 1 and len(hmofs) == 1:

            add_relation(
                relations,
                next(iter(tobs)),
                next(iter(hmofs)),
                path,
                "FILENAME",
                100,
                "Les deux identifiants sont présents dans le nom du fichier"
            )


def analyze_cif_bridge(
    h2_names,
    qe_names,
    file_summaries,
    relations
):

    """
    Cherche les chemins/noms CIF associés aux deux systèmes.
    """

    h2_cif_files = defaultdict(set)
    qe_cif_files = defaultdict(set)

    for summary in file_summaries:

        cifs = summary["cifs"]

        for tob in summary["tobmof"]:

            for cif in cifs:
                h2_cif_files[tob].add(cif)

        for hmof in summary["hmof"]:

            for cif in cifs:
                qe_cif_files[hmof].add(cif)

    for tob, cifs1 in h2_cif_files.items():

        for hmof, cifs2 in qe_cif_files.items():

            shared = cifs1 & cifs2

            if shared:

                add_relation(
                    relations,
                    tob,
                    hmof,
                    "CIF_PATH_SHARED",
                    "CIF_SHARED_REFERENCE",
                    90,
                    "Même référence CIF retrouvée dans les deux chaînes",
                    ";".join(sorted(shared))
                )


def consolidate(
    h2_rows,
    qe_rows,
    relations
):

    by_tob = defaultdict(lambda: defaultdict(list))

    for rel in relations:

        by_tob[
            rel["tobmof"]
        ][
            rel["hmof"]
        ].append(rel)

    results = []

    for h2 in h2_rows:

        tob = h2["tobmof"]

        candidates = []

        for hmof, rels in by_tob.get(tob, {}).items():

            max_conf = max(
                r["confidence"]
                for r in rels
            )

            kinds = sorted(
                set(r["kind"] for r in rels)
            )

            candidates.append({
                "hmof": hmof,
                "confidence": max_conf,
                "count": len(rels),
                "kinds": kinds,
                "relations": rels
            })

        candidates.sort(
            key=lambda x: (
                -x["confidence"],
                -x["count"]
            )
        )

        verdict = "NO_MAPPING"
        selected = None

        if len(candidates) == 1:

            c = candidates[0]

            if c["confidence"] >= 90:

                verdict = "VALID_MAPPING"
                selected = c

            elif c["confidence"] >= 40:

                verdict = "TRACE_ONLY"
                selected = c

        elif len(candidates) > 1:

            top = candidates[0]
            second = candidates[1]

            if (
                top["confidence"] >= 90
                and top["confidence"] > second["confidence"]
            ):

                verdict = "VALID_MAPPING"
                selected = top

            else:

                verdict = "AMBIGUOUS_TRACE"

        hmof = selected["hmof"] if selected else None

        qe = qe_rows.get(hmof)

        results.append({

            "tobmof": tob,
            "h2_rank": h2["rank"],
            "hydrogen_score": h2["hydrogen_score"],
            "hydrogen_wt_percent": h2["hydrogen_wt_percent"],

            "mapping_verdict": verdict,

            "hmof": hmof,

            "confidence": (
                selected["confidence"]
                if selected else None
            ),

            "evidence_count": (
                selected["count"]
                if selected else 0
            ),

            "evidence_types": (
                ";".join(selected["kinds"])
                if selected else ""
            ),

            "qe_available": bool(qe),

            "qe_total_energy_ry": (
                qe["energy"]
                if qe else None
            ),

            "qe_energy_information_only": bool(qe),

            # Jamais de combinaison artificielle.
            "combined_score": None,

            "h2_primary_rank": h2["rank"]
        })

    return results


def main():

    print("=" * 90)
    print("PHASE 33 — PROVENANCE TRACE INDIRECT")
    print("=" * 90)
    print("MODE: ANALYSIS_ONLY")
    print("pw.x: NO")
    print("QE: NO")
    print("CIF MODIFICATION: NO")
    print()

    h2_rows = load_h2()
    qe_rows = load_qe()
    ph30 = load_phase30()

    h2_names = {
        x["tobmof"]
        for x in h2_rows
    }

    qe_names = set(qe_rows.keys())

    print(f"H2 TOP25: {len(h2_rows)}")
    print(f"QE candidats: {len(qe_rows)}")

    phase30_files = extract_phase30_paths(ph30)
    discovered = discover_files()

    all_files = sorted(
        set(phase30_files) |
        set(discovered)
    )

    print(
        f"Fichiers Phase30: {len(phase30_files)}"
    )

    print(
        f"Fichiers projet inspectables: {len(all_files)}"
    )

    print()

    # Résumés fichiers
    summaries = []

    for i, path in enumerate(all_files, start=1):

        try:
            summary = make_file_summary(path)

            # On garde surtout les fichiers qui ont
            # au moins un identifiant ou un hash/CIF.
            if (
                summary["tobmof"]
                or summary["hmof"]
                or summary["cifs"]
                or summary["hashes"]
            ):

                summaries.append(summary)

        except Exception:
            pass

    print(
        f"Fichiers contenant des marqueurs pertinents: "
        f"{len(summaries)}"
    )

    relations = []

    # 1. Noms de fichiers
    analyze_filename_bridge(
        h2_names,
        qe_names,
        [Path(s["file"]) for s in summaries],
        relations
    )

    # 2. Pont CIF
    analyze_cif_bridge(
        h2_names,
        qe_names,
        summaries,
        relations
    )

    # 3. Pont numérique
    analyze_numeric_bridge(
        h2_names,
        qe_names,
        summaries,
        relations
    )

    # 4. CSV
    for path in all_files:

        if path.suffix.lower() != ".csv":
            continue

        csv_relations = extract_field_relations_csv(path)

        for r in csv_relations:

            if (
                len(r["tobmof"]) == 1
                and len(r["hmof"]) == 1
            ):

                add_relation(
                    relations,
                    r["tobmof"][0],
                    r["hmof"][0],
                    path,
                    "CSV_DIRECT",
                    100,
                    "Même ligne CSV",
                    json.dumps(
                        r["fields"],
                        ensure_ascii=False
                    )
                )

    # 5. JSON
    for path in all_files:

        if path.suffix.lower() not in {
            ".json",
            ".jsonl"
        }:
            continue

        json_relations = extract_json_relations(path)

        for r in json_relations:

            if (
                len(r["tobmof"]) == 1
                and len(r["hmof"]) == 1
            ):

                add_relation(
                    relations,
                    r["tobmof"][0],
                    r["hmof"][0],
                    path,
                    "JSON_DIRECT",
                    100,
                    "Même objet JSON",
                    json.dumps(
                        r["fields"],
                        ensure_ascii=False
                    )
                )

    # Déduplication
    unique = {}

    for r in relations:

        key = (
            r["tobmof"],
            r["hmof"],
            r["file"],
            r["kind"],
            r["bridge"]
        )

        unique[key] = r

    relations = list(unique.values())

    print(
        f"Relations candidates detectees: "
        f"{len(relations)}"
    )

    results = consolidate(
        h2_rows,
        qe_rows,
        relations
    )

    valid = [
        r for r in results
        if r["mapping_verdict"] == "VALID_MAPPING"
    ]

    trace = [
        r for r in results
        if r["mapping_verdict"] == "TRACE_ONLY"
    ]

    ambiguous = [
        r for r in results
        if r["mapping_verdict"] == "AMBIGUOUS_TRACE"
    ]

    valid_qe = [
        r for r in valid
        if r["qe_available"]
    ]

    print()
    print("=" * 90)
    print("RESULTATS")
    print("=" * 90)

    for r in results:

        print(
            f'{r["tobmof"]:14s} | '
            f'H2={str(r["h2_rank"]):>3s} | '
            f'{r["mapping_verdict"]:18s} | '
            f'QE={str(r["hmof"]):10s} | '
            f'conf={str(r["confidence"]):>4s} | '
            f'QE={r["qe_available"]}'
        )

    print()
    print("=" * 90)
    print("SYNTHESE")
    print("=" * 90)
    print(f"H2 TOP25:              {len(results)}")
    print(f"Relations candidates:  {len(relations)}")
    print(f"Mappings valides:      {len(valid)}")
    print(f"Traces indirectes:     {len(trace)}")
    print(f"Traces ambiguës:       {len(ambiguous)}")
    print(f"Mappings + QE:         {len(valid_qe)}")

    # CSV
    fields = [
        "tobmof",
        "h2_rank",
        "hydrogen_score",
        "hydrogen_wt_percent",
        "mapping_verdict",
        "hmof",
        "confidence",
        "evidence_count",
        "evidence_types",
        "qe_available",
        "qe_total_energy_ry",
        "qe_energy_information_only",
        "combined_score",
        "h2_primary_rank"
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
    output = {

        "phase": 33,

        "mode": "ANALYSIS_ONLY",

        "status": (
            "MAPPING_RESOLVED"
            if valid
            else "MAPPING_NOT_RESOLVED"
        ),

        "h2_count": len(h2_rows),

        "qe_count": len(qe_rows),

        "phase30_files": [
            str(x)
            for x in phase30_files
        ],

        "all_files": [
            str(x)
            for x in all_files
        ],

        "relevant_files": len(summaries),

        "relations_count": len(relations),

        "valid_mappings": len(valid),

        "trace_only": len(trace),

        "ambiguous_trace": len(ambiguous),

        "valid_mappings_with_qe": len(valid_qe),

        "results": results,

        "relations": relations,

        "scientific_constraints": [

            "Numeric ID coincidence alone is not a valid mapping.",

            "A valid mapping requires explicit provenance evidence.",

            "Indirect numeric bridges are marked TRACE_ONLY.",

            "Raw QE total energies are not combined with H2 scores.",

            "No QE calculation was launched.",

            "No CIF was modified."
        ]
    }

    with open(
        OUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    manifest = {

        "phase": 33,

        "status": (
            "MAPPING_RESOLVED"
            if valid
            else "MAPPING_NOT_RESOLVED"
        ),

        "mode": "ANALYSIS_ONLY",

        "h2_count": len(h2_rows),

        "qe_count": len(qe_rows),

        "files_scanned": len(all_files),

        "relevant_files": len(summaries),

        "relations": len(relations),

        "valid_mappings": len(valid),

        "trace_only": len(trace),

        "ambiguous_trace": len(ambiguous),

        "valid_mappings_with_qe": len(valid_qe),

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
    print("PHASE 33 TERMINEE")
    print("=" * 90)


if __name__ == "__main__":
    main()
