from __future__ import annotations
import os
os.system("clear")

import csv
import json
import multiprocessing as mp
import re
import time
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path("MOF_Library")
REPORT = Path("reports/dft_preparation")
OUTPUT = ROOT / "DFT_CANDIDATES"

QE_PSEUDO_DIRS = [
    Path("/usr/share/espresso/pseudo"),
    Path("/home/hk/software/qe-7.5/pseudo"),
]

MAX_ATOMS = 300


def find_pseudo_dir():
    for path in QE_PSEUDO_DIRS:
        if path.exists():
            return path
    return None


def pseudo_elements(pseudo_dir):
    elements = set()

    if pseudo_dir is None:
        return elements

    for file in pseudo_dir.iterdir():
        if not file.is_file():
            continue

        name = file.name

        # Exemples :
        # C.pbe-n-kjpaw_psl.1.0.0.UPF
        # Zn.pbe-spn-kjpaw_psl.1.0.0.UPF
        # H_ONCV_PBE-1.0.upf

        match = re.match(r"^([A-Z][a-z]?)", name)

        if match:
            elements.add(match.group(1))

    return elements


def source_dirs():

    return {
        "MOFXDB": ROOT / "MOFXDB_FULL" / "cif",
        "METAL_HYDRIDES": ROOT / "METAL_HYDRIDES" / "cif",
        "COMPLEXES": ROOT / "COMPLEXES" / "cif",
    }


def process_file(args):

    source, path, pseudo_elements_set = args

    path = Path(path)

    result = {
        "source": source,
        "name": path.stem,
        "cif": str(path),
        "valid": 0,
        "formula": "",
        "n_atoms": "",
        "elements": "",
        "pseudo_ok": 0,
        "missing_pseudo": "",
        "qe_compatible": 0,
        "reason": "",
    }

    try:

        structure = Structure.from_file(path)

        result["valid"] = 1
        result["formula"] = structure.composition.reduced_formula
        result["n_atoms"] = len(structure)

        elements = sorted(
            {
                site.specie.symbol
                for site in structure.sites
            }
        )

        result["elements"] = ",".join(elements)

        missing = sorted(
            set(elements) - pseudo_elements_set
        )

        result["missing_pseudo"] = ",".join(missing)

        result["pseudo_ok"] = int(not missing)

        compatible = True
        reasons = []

        if len(structure) > MAX_ATOMS:
            compatible = False
            reasons.append(
                f"too_many_atoms>{MAX_ATOMS}"
            )

        if missing:
            compatible = False
            reasons.append("missing_pseudopotential")

        if not structure.is_ordered:
            compatible = False
            reasons.append("disordered_structure")

        result["qe_compatible"] = int(compatible)
        result["reason"] = ";".join(reasons)

    except Exception as exc:

        result["reason"] = f"parse_error:{exc}"

    return result


def main():

    start = time.time()

    REPORT.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print(" HydroMatAI — PRÉPARATION DFT")
    print("=" * 80)

    print()
    print("===== PSEUDOPOTENTIELS QE =====")

    pseudo_dir = find_pseudo_dir()

    if pseudo_dir is None:

        print("Répertoire UPF : NON TROUVÉ")
        pseudo_set = set()

    else:

        print(f"Répertoire UPF : {pseudo_dir}")

        pseudo_set = pseudo_elements(
            pseudo_dir
        )

        print(
            f"Éléments détectés : "
            f"{len(pseudo_set)}"
        )

        print(
            "Exemples : "
            + ", ".join(
                sorted(pseudo_set)[:30]
            )
        )

    print()
    print("===== SOURCES =====")

    dirs = source_dirs()

    jobs = []

    for source, directory in dirs.items():

        if not directory.exists():

            print(
                f"{source:<20}: ABSENT"
            )

            continue

        files = sorted(
            directory.glob("*.cif")
        )

        print(
            f"{source:<20}: "
            f"{len(files):,} CIF"
        )

        for path in files:

            jobs.append(
                (
                    source,
                    str(path),
                    pseudo_set,
                )
            )

    print()
    print(
        f"TOTAL CIF À ANALYSER : "
        f"{len(jobs):,}"
    )

    print()
    print("===== ANALYSE PARALLÈLE =====")

    workers = min(
        3,
        os.cpu_count() or 1,
    )

    print(
        f"Workers : {workers}"
    )

    results = []

    ctx = mp.get_context("spawn")

    with ctx.Pool(
        processes=workers
    ) as pool:

        for index, result in enumerate(
            pool.imap_unordered(
                process_file,
                jobs,
                chunksize=50,
            ),
            start=1,
        ):

            results.append(result)

            if index % 5000 == 0:

                print(
                    f"  analysés={index:,}"
                    f"/{len(jobs):,}",
                    flush=True,
                )

    print()
    print("===== ANALYSE TERMINÉE =====")

    # --------------------------------------------------------------
    # Statistiques
    # --------------------------------------------------------------

    stats = {}

    for source in dirs:

        rows = [
            r
            for r in results
            if r["source"] == source
        ]

        stats[source] = {
            "total": len(rows),
            "valid": sum(
                r["valid"] for r in rows
            ),
            "pseudo_ok": sum(
                r["pseudo_ok"] for r in rows
            ),
            "qe_compatible": sum(
                r["qe_compatible"]
                for r in rows
            ),
        }

    # --------------------------------------------------------------
    # CSV global
    # --------------------------------------------------------------

    fields = [
        "source",
        "name",
        "cif",
        "valid",
        "formula",
        "n_atoms",
        "elements",
        "pseudo_ok",
        "missing_pseudo",
        "qe_compatible",
        "reason",
    ]

    results.sort(
        key=lambda r: (
            r["source"],
            r["name"],
        )
    )

    global_csv = (
        REPORT /
        "dft_compatibility_global.csv"
    )

    with global_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(results)

    # --------------------------------------------------------------
    # DFT READY
    # --------------------------------------------------------------

    ready = [
        r
        for r in results
        if r["valid"]
        and r["qe_compatible"]
    ]

    ready_csv = (
        REPORT /
        "DFT_READY.csv"
    )

    with ready_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(ready)

    # --------------------------------------------------------------
    # Missing pseudopotentials
    # --------------------------------------------------------------

    missing = [
        r
        for r in results
        if r["valid"]
        and not r["pseudo_ok"]
    ]

    missing_csv = (
        REPORT /
        "missing_pseudopotentials.csv"
    )

    with missing_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(missing)

    # --------------------------------------------------------------
    # Structures trop grandes
    # --------------------------------------------------------------

    large = [
        r
        for r in results
        if r["valid"]
        and r["n_atoms"]
        and int(r["n_atoms"]) > MAX_ATOMS
    ]

    large_csv = (
        REPORT /
        "large_structures.csv"
    )

    with large_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(large)

    # --------------------------------------------------------------
    # Résumé
    # --------------------------------------------------------------

    summary = {
        "pseudo_directory": (
            str(pseudo_dir)
            if pseudo_dir
            else None
        ),
        "pseudo_elements": sorted(
            pseudo_set
        ),
        "max_atoms": MAX_ATOMS,
        "workers": workers,
        "sources": stats,
        "total_cif": len(results),
        "total_valid": sum(
            r["valid"] for r in results
        ),
        "total_pseudo_ok": sum(
            r["pseudo_ok"] for r in results
        ),
        "total_qe_compatible": sum(
            r["qe_compatible"]
            for r in results
        ),
        "total_dft_ready": len(ready),
        "total_missing_pseudo": len(missing),
        "total_large_structures": len(large),
        "qe_launched": False,
        "elapsed_seconds": round(
            time.time() - start,
            2,
        ),
    }

    summary_path = (
        REPORT /
        "dft_preparation_summary.json"
    )

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------------
    # Affichage
    # --------------------------------------------------------------

    print()
    print("=" * 80)
    print(" RÉSULTATS")
    print("=" * 80)

    for source, data in stats.items():

        print()
        print(source)

        print(
            f"  CIF              : "
            f"{data['total']:,}"
        )

        print(
            f"  valides          : "
            f"{data['valid']:,}"
        )

        print(
            f"  pseudopotentiels : "
            f"{data['pseudo_ok']:,}"
        )

        print(
            f"  QE compatibles   : "
            f"{data['qe_compatible']:,}"
        )

    print()
    print(
        f"CIF total          : "
        f"{summary['total_cif']:,}"
    )

    print(
        f"CIF valides        : "
        f"{summary['total_valid']:,}"
    )

    print(
        f"Pseudo OK          : "
        f"{summary['total_pseudo_ok']:,}"
    )

    print(
        f"QE compatibles     : "
        f"{summary['total_qe_compatible']:,}"
    )

    print(
        f"DFT READY          : "
        f"{summary['total_dft_ready']:,}"
    )

    print(
        f"Pseudo manquants   : "
        f"{summary['total_missing_pseudo']:,}"
    )

    print(
        f"> {MAX_ATOMS} atomes  : "
        f"{summary['total_large_structures']:,}"
    )

    print()
    print("=" * 80)
    print(" FICHIERS")
    print("=" * 80)

    print(
        f"GLOBAL : {global_csv}"
    )

    print(
        f"READY  : {ready_csv}"
    )

    print(
        f"UPF    : {missing_csv}"
    )

    print(
        f"LARGE  : {large_csv}"
    )

    print(
        f"SUMMARY: {summary_path}"
    )

    print()
    print("=" * 80)
    print(" PRÉPARATION DFT TERMINÉE")
    print("=" * 80)
    print("Aucun CIF supprimé.")
    print("Aucun CIF modifié.")
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
