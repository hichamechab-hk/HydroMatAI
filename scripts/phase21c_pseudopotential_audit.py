from __future__ import annotations
import os
os.system("clear")


import argparse
import csv
import json
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path("/home/hk/HydroMatAI")
PSEUDO_DIR = Path("/home/hk/software/qe-7.5/pseudo")
PRIORITY = ROOT / "reports/global_screening/dft_priority.csv"
OUT = ROOT / "calculations/phase_21c_pseudopotential_audit"

ELEMENTS = {
    "H": ["H.pbe-kjpaw_psl.1.0.0.UPF", "H.pbe-rrkjus_psl.1.0.0.UPF"],
    "C": ["C.pbe-n-kjpaw_psl.1.0.0.UPF", "C.pbe-rrkjus_psl.1.0.0.UPF"],
    "N": ["N.pbe-n-kjpaw_psl.1.0.0.UPF", "N.pbe-rrkjus_psl.1.0.0.UPF"],
    "O": ["O.pbe-n-kjpaw_psl.1.0.0.UPF", "O.pbe-rrkjus_psl.1.0.0.UPF"],
    "F": ["F.pbe-n-kjpaw_psl.1.0.0.UPF", "F.pbe-rrkjus_psl.1.0.0.UPF"],
    "Zn": ["Zn.pbe-dn-kjpaw_psl.1.0.0.UPF", "Zn.pbe-d-rrkjus_psl.1.0.0.UPF"],
}


def load_candidates(limit: int):
    with PRIORITY.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    rows = [
        r for r in rows
        if (r.get("classification") or "PRIORITY").upper() == "PRIORITY"
        or not r.get("classification")
    ]

    return rows[:limit]


def find_cif(row):
    path = row.get("cif", "").strip()

    if path:
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return p

    name = row.get("name", "").strip()

    matches = list(
        (ROOT / "MOF_Library/MOFXDB_FULL/cif").glob(
            f"*_{name}.cif"
        )
    )

    return matches[0] if matches else None


def available_pseudos():
    if not PSEUDO_DIR.exists():
        return set()

    return {
        p.name
        for p in PSEUDO_DIR.glob("*.UPF")
    }


def choose_pseudo(element, available):
    candidates = ELEMENTS.get(element, [])

    for name in candidates:
        if name in available:
            return name

    # Recherche tolérante par élément.
    matches = sorted(
        p for p in available
        if p.lower().startswith(element.lower() + ".")
    )

    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" HydroMatAI — PHASE 21C")
    print(" AUDIT PSEUDOPOTENTIELS QE")
    print("=" * 80)

    print()
    print("PROTECTION")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    print()
    print("PSEUDOPOTENTIELS")
    print("-" * 80)
    print(f"Répertoire : {PSEUDO_DIR}")

    available = available_pseudos()

    print(f"UPF trouvés : {len(available)}")

    rows = []
    candidates = load_candidates(args.limit)

    print()
    print("CANDIDATS")
    print("-" * 80)
    print(f"Priority inspectés : {len(candidates)}")

    for i, row in enumerate(candidates, 1):
        name = row.get("name", "").strip()

        print()
        print(f"[{i}/{len(candidates)}] {name}")

        cif = find_cif(row)

        if cif is None:
            print("  CIF    : MISSING")
            rows.append({
                "name": name,
                "cif": "",
                "valid": 0,
                "elements": "",
                "missing_pseudo": "",
                "pseudo_mapping": "CIF_MISSING",
            })
            continue

        try:
            structure = Structure.from_file(cif)
            elements = sorted(
                {site.specie.symbol for site in structure.sites}
            )
        except Exception as exc:
            print(f"  CIF    : PARSE_FAILED → {exc}")
            rows.append({
                "name": name,
                "cif": str(cif),
                "valid": 0,
                "elements": "",
                "missing_pseudo": "",
                "pseudo_mapping": "CIF_PARSE_FAILED",
            })
            continue

        missing = []
        mapping = {}

        for element in elements:
            pseudo = choose_pseudo(element, available)

            if pseudo is None:
                missing.append(element)
            else:
                mapping[element] = pseudo

        status = (
            "OK"
            if not missing
            else "PSEUDOPOTENTIAL_MISSING"
        )

        print(f"  CIF    : OK → {cif}")
        print(f"  Elements : {', '.join(elements)}")
        print(f"  Mapping  : {status}")

        if missing:
            print(f"  Missing  : {', '.join(missing)}")

        for element, pseudo in mapping.items():
            print(f"    {element:<3} → {pseudo}")

        rows.append({
            "name": name,
            "cif": str(cif),
            "valid": 1,
            "elements": ",".join(elements),
            "missing_pseudo": ",".join(missing),
            "pseudo_mapping": status,
            "pseudo_map": json.dumps(
                mapping,
                ensure_ascii=False,
                sort_keys=True,
            ),
        })

    json_path = OUT / "phase21c_pseudopotential_audit.json"
    csv_path = OUT / "phase21c_pseudopotential_audit.csv"

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        fields = [
            "name",
            "cif",
            "valid",
            "elements",
            "missing_pseudo",
            "pseudo_mapping",
            "pseudo_map",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "phase": "21C",
        "candidates": len(rows),
        "valid_cif": sum(r["valid"] == 1 for r in rows),
        "mapping_ok": sum(
            r["pseudo_mapping"] == "OK"
            for r in rows
        ),
        "mapping_failed": sum(
            r["pseudo_mapping"] == "PSEUDOPOTENTIAL_MISSING"
            for r in rows
        ),
        "cif_failed": sum(
            r["valid"] == 0
            for r in rows
        ),
        "pseudo_directory": str(PSEUDO_DIR),
        "pseudo_count": len(available),
        "pw_x_launched": False,
        "qe_calculation": False,
        "results": rows,
    }

    with json_path.open(
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
    print(" PHASE 21C — RÉSULTATS")
    print("=" * 80)
    print(f"Candidats         : {len(rows)}")
    print(f"CIF valides       : {summary['valid_cif']}")
    print(f"Mapping OK        : {summary['mapping_ok']}")
    print(f"Mapping FAILED    : {summary['mapping_failed']}")
    print(f"CIF FAILED        : {summary['cif_failed']}")

    print()
    print("FICHIERS")
    print("-" * 80)
    print(f"JSON : {json_path}")
    print(f"CSV  : {csv_path}")

    print()
    print("=" * 80)
    print("PHASE 21C — TERMINÉE")
    print("=" * 80)
    print("Aucun calcul QE lancé.")
    print("Aucun fichier scientifique modifié.")
    print("=" * 80)


if __name__ == "__main__":
    main()
