from __future__ import annotations
import os
os.system("clear")

import csv
import hashlib
import json
import multiprocessing as mp
import time
import warnings
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path("MOF_Library")
REPORT = Path("reports/global_screening")

SOURCES = {
    "MOFXDB": ROOT / "MOFXDB_FULL" / "cif",
    "METAL_HYDRIDES": ROOT / "METAL_HYDRIDES" / "cif",
    "COMPLEXES": ROOT / "COMPLEXES" / "cif",
}

MIN_VOID_FRACTION = 0.50
MIN_SURFACE_AREA = 1000.0
MIN_PLD = 3.0
MIN_LCD = 6.0


def fingerprint(structure: Structure) -> str:
    sites = []

    for site in structure.sites:
        f = site.frac_coords
        sites.append(
            (
                site.specie.symbol,
                round(float(f[0] % 1), 5),
                round(float(f[1] % 1), 5),
                round(float(f[2] % 1), 5),
            )
        )

    sites.sort()

    lattice = structure.lattice

    payload = {
        "lattice": [
            round(float(lattice.a), 4),
            round(float(lattice.b), 4),
            round(float(lattice.c), 4),
            round(float(lattice.alpha), 4),
            round(float(lattice.beta), 4),
            round(float(lattice.gamma), 4),
        ],
        "sites": sites,
    }

    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(raw.encode()).hexdigest()


def load_metadata(source: str) -> dict:
    if source == "MOFXDB":
        path = ROOT / "MOFXDB_FULL" / "metadata.csv"
    elif source == "METAL_HYDRIDES":
        path = ROOT / "METAL_HYDRIDES" / "metadata.csv"
    else:
        path = ROOT / "COMPLEXES" / "metadata.csv"

    result = {}

    if not path.exists():
        return result

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = (row.get("name") or "").strip()
            material_id = (row.get("id") or "").strip()

            if name:
                result[name] = row

            if material_id:
                result[f"id:{material_id}"] = row

    return result


def number(value):
    try:
        if value in (None, "", "None"):
            return None
        return float(value)
    except Exception:
        return None


def mofxdb_score(row):
    vf = number(row.get("void_fraction"))
    sa = number(row.get("surface_area_m2g"))
    pld = number(row.get("pld"))
    lcd = number(row.get("lcd"))

    if None in (vf, sa, pld, lcd):
        return 0.0

    return round(
        0.30 * min(vf / 0.90, 1.0)
        + 0.30 * min(sa / 5000.0, 1.0)
        + 0.20 * min(pld / 20.0, 1.0)
        + 0.20 * min(lcd / 20.0, 1.0),
        6,
    )


def process_source(args):
    source, directory = args

    directory = Path(directory)

    metadata = load_metadata(source)

    files = sorted(directory.glob("*.cif"))

    rows = []

    fingerprints = {}

    valid = 0
    invalid = 0
    duplicates = 0
    candidates = 0

    start = time.time()

    print(
        f"[{source}] START | CIF={len(files):,}",
        flush=True,
    )

    for index, cif_path in enumerate(files, start=1):

        name = cif_path.stem
        meta = metadata.get(name, {})

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                structure = Structure.from_file(cif_path)

            valid += 1

            fp = fingerprint(structure)

            duplicate = fp in fingerprints

            if duplicate:
                duplicates += 1
                duplicate_of = fingerprints[fp]
            else:
                fingerprints[fp] = cif_path.name
                duplicate_of = ""

            formula = structure.composition.reduced_formula

            if source == "MOFXDB":

                vf = number(meta.get("void_fraction"))
                sa = number(meta.get("surface_area_m2g"))
                pld = number(meta.get("pld"))
                lcd = number(meta.get("lcd"))

                passes = (
                    vf is not None
                    and sa is not None
                    and pld is not None
                    and lcd is not None
                    and vf >= MIN_VOID_FRACTION
                    and sa >= MIN_SURFACE_AREA
                    and pld >= MIN_PLD
                    and lcd >= MIN_LCD
                )

                score = mofxdb_score(meta)

            else:

                vf = ""
                sa = ""
                pld = ""
                lcd = ""

                # Les hydrures et complexes sont conservés.
                # Aucun score d'adsorption fictif n'est introduit.
                passes = True

                score = 0.5

            if passes:
                candidates += 1

            rows.append(
                {
                    "source": source,
                    "name": meta.get("name") or name,
                    "material_id": meta.get("id", ""),
                    "cif": str(cif_path),
                    "valid": 1,
                    "duplicate": int(duplicate),
                    "duplicate_of": duplicate_of,
                    "formula": formula,
                    "n_atoms": len(structure),
                    "void_fraction": vf,
                    "surface_area_m2g": sa,
                    "pld": pld,
                    "lcd": lcd,
                    "score": score,
                    "passes_screening": int(passes),
                    "error": "",
                }
            )

        except Exception as exc:

            invalid += 1

            rows.append(
                {
                    "source": source,
                    "name": name,
                    "material_id": meta.get("id", ""),
                    "cif": str(cif_path),
                    "valid": 0,
                    "duplicate": 0,
                    "duplicate_of": "",
                    "formula": "",
                    "n_atoms": "",
                    "void_fraction": "",
                    "surface_area_m2g": "",
                    "pld": "",
                    "lcd": "",
                    "score": 0.0,
                    "passes_screening": 0,
                    "error": str(exc),
                }
            )

        if index % 5000 == 0:
            elapsed = time.time() - start

            print(
                f"[{source}] "
                f"vus={index:,} "
                f"valides={valid:,} "
                f"invalides={invalid:,} "
                f"doublons={duplicates:,} "
                f"candidats={candidates:,} "
                f"temps={elapsed:.1f}s",
                flush=True,
            )

    output = REPORT / f"{source}_audit.csv"

    fieldnames = [
        "source",
        "name",
        "material_id",
        "cif",
        "valid",
        "duplicate",
        "duplicate_of",
        "formula",
        "n_atoms",
        "void_fraction",
        "surface_area_m2g",
        "pld",
        "lcd",
        "score",
        "passes_screening",
        "error",
    ]

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    elapsed = time.time() - start

    print(
        f"[{source}] FIN | "
        f"valides={valid:,} "
        f"invalides={invalid:,} "
        f"doublons={duplicates:,} "
        f"candidats={candidates:,} "
        f"temps={elapsed:.1f}s",
        flush=True,
    )

    return {
        "source": source,
        "cif": len(files),
        "valid": valid,
        "invalid": invalid,
        "duplicates": duplicates,
        "candidates": candidates,
        "rows": rows,
    }


def main():

    REPORT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print(" HydroMatAI — AUDIT + SCREENING PARALLÈLE")
    print("=" * 80)

    print()
    print("===== SOURCES =====")

    for source, path in SOURCES.items():
        count = (
            len(list(path.glob("*.cif")))
            if path.exists()
            else 0
        )

        print(
            f"{source:<20}: "
            f"{count:,} CIF"
        )

    print()
    print("===== LANCEMENT PARALLÈLE =====")
    print("MOFX-DB       : PROCESSUS 1")
    print("HYDRURES      : PROCESSUS 2")
    print("COMPLEXES     : PROCESSUS 3")
    print("QE            : NON LANCÉ")
    print()

    jobs = [
        (source, str(path))
        for source, path in SOURCES.items()
        if path.exists()
    ]

    ctx = mp.get_context("spawn")

    with ctx.Pool(
        processes=len(jobs)
    ) as pool:

        results = pool.map(
            process_source,
            jobs,
        )

    print()
    print("=" * 80)
    print(" FUSION DES RÉSULTATS")
    print("=" * 80)

    all_rows = []

    for result in results:
        all_rows.extend(result["rows"])

    # --------------------------------------------------------------
    # Déduplication globale
    # --------------------------------------------------------------

    global_fingerprints = {}

    global_duplicates = 0

    for row in all_rows:

        if not row["valid"]:
            continue

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                structure = Structure.from_file(
                    row["cif"]
                )

            fp = fingerprint(structure)

        except Exception:
            continue

        if fp in global_fingerprints:
            global_duplicates += 1

            if not row["duplicate"]:
                row["duplicate"] = 1
                row["duplicate_of"] = global_fingerprints[fp]

        else:
            global_fingerprints[fp] = (
                f"{row['source']}:{row['name']}"
            )

    # --------------------------------------------------------------
    # Classement
    # --------------------------------------------------------------

    candidates = [
        row
        for row in all_rows
        if row["valid"] == 1
        and row["passes_screening"] == 1
    ]

    candidates.sort(
        key=lambda row: float(row["score"]),
        reverse=True,
    )

    fieldnames = [
        "source",
        "name",
        "material_id",
        "cif",
        "valid",
        "duplicate",
        "duplicate_of",
        "formula",
        "n_atoms",
        "void_fraction",
        "surface_area_m2g",
        "pld",
        "lcd",
        "score",
        "passes_screening",
        "error",
    ]

    def write_csv(path, rows):

        with path.open(
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
            writer.writerows(rows)

    write_csv(
        REPORT / "global_audit.csv",
        all_rows,
    )

    write_csv(
        REPORT / "TOP100_GLOBAL_H2.csv",
        candidates[:100],
    )

    write_csv(
        REPORT / "TOP20_GLOBAL_H2.csv",
        candidates[:20],
    )

    write_csv(
        REPORT / "dft_priority.csv",
        candidates[:200],
    )

    for source in SOURCES:

        source_candidates = [
            row
            for row in candidates
            if row["source"] == source
        ]

        write_csv(
            REPORT / f"TOP100_{source}_H2.csv",
            source_candidates[:100],
        )

    # --------------------------------------------------------------
    # Résumé
    # --------------------------------------------------------------

    summary = {
        "sources": {},
        "total_cif": len(all_rows),
        "total_valid": sum(
            1 for r in all_rows
            if r["valid"] == 1
        ),
        "total_invalid": sum(
            1 for r in all_rows
            if r["valid"] == 0
        ),
        "global_structural_duplicates": global_duplicates,
        "unique_global_fingerprints": len(
            global_fingerprints
        ),
        "total_screening_candidates": len(candidates),
        "qe_launched": False,
    }

    for result in results:

        summary["sources"][
            result["source"]
        ] = {
            "cif": result["cif"],
            "valid": result["valid"],
            "invalid": result["invalid"],
            "duplicates": result["duplicates"],
            "candidates": result["candidates"],
        }

    with (
        REPORT /
        "global_parallel_screening_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 80)
    print(" RÉSULTATS")
    print("=" * 80)

    for source, data in summary["sources"].items():

        print()
        print(source)

        print(
            f"  CIF          : "
            f"{data['cif']:,}"
        )

        print(
            f"  valides      : "
            f"{data['valid']:,}"
        )

        print(
            f"  invalides    : "
            f"{data['invalid']:,}"
        )

        print(
            f"  doublons     : "
            f"{data['duplicates']:,}"
        )

        print(
            f"  candidats    : "
            f"{data['candidates']:,}"
        )

    print()
    print(
        f"CIF total               : "
        f"{summary['total_cif']:,}"
    )

    print(
        f"CIF valides             : "
        f"{summary['total_valid']:,}"
    )

    print(
        f"CIF invalides           : "
        f"{summary['total_invalid']:,}"
    )

    print(
        f"Doublons structuraux    : "
        f"{summary['global_structural_duplicates']:,}"
    )

    print(
        f"Empreintes uniques      : "
        f"{summary['unique_global_fingerprints']:,}"
    )

    print(
        f"Candidats screening     : "
        f"{summary['total_screening_candidates']:,}"
    )

    print()
    print("=" * 80)
    print(" TOP 20 GLOBAL")
    print("=" * 80)

    print(
        f"{'RANG':<5}"
        f"{'SOURCE':<20}"
        f"{'MATERIAL':<30}"
        f"{'SCORE':>8}"
    )

    print("-" * 80)

    for rank, row in enumerate(
        candidates[:20],
        start=1,
    ):

        print(
            f"{rank:<5}"
            f"{row['source']:<20}"
            f"{row['name'][:29]:<30}"
            f"{float(row['score']):>8.4f}"
        )

    print()
    print("=" * 80)
    print(" FICHIERS")
    print("=" * 80)

    print(
        f"AUDIT GLOBAL : "
        f"{REPORT / 'global_audit.csv'}"
    )

    print(
        f"TOP100       : "
        f"{REPORT / 'TOP100_GLOBAL_H2.csv'}"
    )

    print(
        f"TOP20        : "
        f"{REPORT / 'TOP20_GLOBAL_H2.csv'}"
    )

    print(
        f"DFT PRIORITY : "
        f"{REPORT / 'dft_priority.csv'}"
    )

    print(
        f"RÉSUMÉ       : "
        f"{REPORT / 'global_parallel_screening_summary.json'}"
    )

    print()
    print("=" * 80)
    print(" AUDIT + SCREENING TERMINÉS")
    print("=" * 80)
    print("Aucun CIF supprimé.")
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
