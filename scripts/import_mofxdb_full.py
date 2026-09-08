from __future__ import annotations
import os
os.system("clear")

import csv
import json
from pathlib import Path

from mofdb_client import fetch


ROOT = Path("MOF_Library/MOFXDB_FULL")
CIF_DIR = ROOT / "cif"
METADATA = ROOT / "metadata.csv"
SUMMARY = ROOT / "import_summary.json"

LIMIT = 168_534


def existing_cif_ids() -> set[str]:
    ids: set[str] = set()

    for path in CIF_DIR.glob("*.cif"):
        stem = path.stem

        if "_" not in stem:
            continue

        mof_id = stem.split("_", 1)[0]

        if mof_id.isdigit():
            ids.add(str(int(mof_id)))

    return ids


def safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    CIF_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" HydroMatAI — IMPORT COMPLET MOFX-DB")
    print("=" * 80)

    existing = existing_cif_ids()

    print()
    print("===== ÉTAT INITIAL =====")
    print(f"CIF existants : {len(existing):,}")
    print(f"Limite cible  : {LIMIT:,}")

    rows = []
    seen = set()

    new_cif = 0
    already_present = 0
    errors = 0

    print()
    print("===== IMPORT MOFX-DB =====")

    for count, mof in enumerate(fetch(limit=LIMIT), start=1):
        mof_id = str(mof.id)

        if mof_id in seen:
            continue

        seen.add(mof_id)

        filename = f"{mof_id.zfill(7)}_{mof.name}.cif"
        cif_path = CIF_DIR / filename

        try:
            if mof_id not in existing:
                cif_path.write_text(
                    mof.cif,
                    encoding="utf-8",
                )
                new_cif += 1
            else:
                already_present += 1

            rows.append(
                {
                    "id": mof.id,
                    "name": mof.name,
                    "mofkey": mof.mofkey or "",
                    "void_fraction": safe_float(mof.void_fraction),
                    "surface_area_m2g": safe_float(mof.surface_area_m2g),
                    "surface_area_m2cm3": safe_float(
                        mof.surface_area_m2cm3
                    ),
                    "pld": safe_float(mof.pld),
                    "lcd": safe_float(mof.lcd),
                    "cif_path": str(cif_path),
                }
            )

        except Exception as exc:
            errors += 1
            print(
                f"ERREUR id={mof_id} name={mof.name}: {exc}"
            )

        if count % 5000 == 0:
            print(
                f"  vus={count:,} "
                f"nouveaux={new_cif:,} "
                f"existants={already_present:,} "
                f"erreurs={errors:,}"
            )

    rows.sort(key=lambda r: int(r["id"]))

    print()
    print("===== SAUVEGARDE METADONNEES =====")

    fields = [
        "id",
        "name",
        "mofkey",
        "void_fraction",
        "surface_area_m2g",
        "surface_area_m2cm3",
        "pld",
        "lcd",
        "cif_path",
    ]

    with METADATA.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    actual_cifs = len(list(CIF_DIR.glob("*.cif")))

    summary = {
        "requested": LIMIT,
        "structures_seen": len(seen),
        "new_cif": new_cif,
        "already_present": already_present,
        "errors": errors,
        "metadata_rows": len(rows),
        "cif_files": actual_cifs,
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(" IMPORT MOFX-DB TERMINÉ")
    print("=" * 80)
    print(f" Structures vues       : {len(seen):,}")
    print(f" Nouveaux CIF          : {new_cif:,}")
    print(f" CIF déjà présents     : {already_present:,}")
    print(f" Erreurs               : {errors:,}")
    print(f" Total metadata        : {len(rows):,}")
    print(f" Total CIF sur disque  : {actual_cifs:,}")
    print()
    print(f" CIF      : {CIF_DIR}")
    print(f" Metadata : {METADATA}")
    print(f" Résumé   : {SUMMARY}")
    print()
    print("QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
