#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")


import csv
import json
import re
import sys
from pathlib import Path

import mofdb_client


ROOT = Path("MOF_Library/MOFXDB_FULL")
CIF_DIR = ROOT / "cif"
METADATA_FILE = ROOT / "metadata.csv"
SUMMARY_FILE = ROOT / "import_summary.json"

BATCH_SIZE = 50000


def safe_name(name: str, mof_id: int) -> str:
    """Create a filesystem-safe unique filename."""
    value = str(name).strip()
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = value.strip("._")

    if not value:
        value = "MOF"

    return f"{mof_id:07d}_{value}.cif"


def get_value(obj, attr, default=None):
    value = getattr(obj, attr, default)
    return default if value is None else value


def extract_metadata(mof) -> dict:
    return {
        "id": get_value(mof, "id"),
        "name": get_value(mof, "name"),
        "cif_file": safe_name(
            get_value(mof, "name", "MOF"),
            get_value(mof, "id", 0),
        ),
        "void_fraction": get_value(mof, "void_fraction"),
        "surface_area_m2g": get_value(mof, "surface_area_m2g"),
        "surface_area_m2cm3": get_value(mof, "surface_area_m2cm3"),
        "pld": get_value(mof, "pld"),
        "lcd": get_value(mof, "lcd"),
        "database": get_value(mof, "database"),
        "mofid": get_value(mof, "mofid"),
        "mofkey": get_value(mof, "mofkey"),
        "url": get_value(mof, "url"),
        "batch_number": get_value(mof, "batch_number"),
        "n_isotherms": len(get_value(mof, "isotherms", []) or []),
        "n_heats": len(get_value(mof, "heats", []) or []),
        "n_adsorbates": len(get_value(mof, "adsorbates", []) or []),
        "n_elements": len(get_value(mof, "elements", []) or []),
    }


def main() -> int:
    print("=" * 80)
    print(" HydroMatAI — IMPORT MASSIF MOFX-DB")
    print("=" * 80)

    CIF_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print("===== CONNEXION MOFX-DB =====")

    try:
        records = mofdb_client.fetch(
            limit=BATCH_SIZE,
            telemetry=False,
        )
    except Exception as exc:
        print(f"ERREUR FETCH : {type(exc).__name__}: {exc}")
        return 1

    print("Connexion : OK")
    print()
    print("===== IMPORT DES CIF =====")

    fieldnames = [
        "id",
        "name",
        "cif_file",
        "void_fraction",
        "surface_area_m2g",
        "surface_area_m2cm3",
        "pld",
        "lcd",
        "database",
        "mofid",
        "mofkey",
        "url",
        "batch_number",
        "n_isotherms",
        "n_heats",
        "n_adsorbates",
        "n_elements",
    ]

    existing = {}

    if METADATA_FILE.exists():
        try:
            with METADATA_FILE.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                for row in csv.DictReader(handle):
                    if row.get("id"):
                        existing[str(row["id"])] = row
        except Exception as exc:
            print(f"AVERTISSEMENT lecture metadata.csv : {exc}")

    imported = 0
    skipped = 0
    failed = 0
    total_seen = 0

    rows = dict(existing)

    try:
        for mof in records:
            total_seen += 1

            mof_id = get_value(mof, "id")
            name = get_value(mof, "name", "MOF")
            cif = get_value(mof, "cif")

            if mof_id is None:
                failed += 1
                print("  ERREUR : MOF sans ID")
                continue

            if not cif:
                failed += 1
                print(f"  SANS CIF : {name} ({mof_id})")
                continue

            filename = safe_name(name, mof_id)
            cif_path = CIF_DIR / filename

            if cif_path.exists():
                skipped += 1
            else:
                try:
                    cif_path.write_text(
                        str(cif),
                        encoding="utf-8",
                    )
                    imported += 1
                except Exception as exc:
                    failed += 1
                    print(
                        f"  ERREUR CIF : {name} ({mof_id}) : "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue

            row = extract_metadata(mof)
            rows[str(mof_id)] = {
                key: "" if value is None else str(value)
                for key, value in row.items()
            }

            if total_seen % 100 == 0:
                print(
                    f"  vus={total_seen:,} "
                    f"nouveaux={imported:,} "
                    f"existants={skipped:,} "
                    f"erreurs={failed:,}"
                )

    except KeyboardInterrupt:
        print()
        print("INTERRUPTION UTILISATEUR — sauvegarde des résultats.")

    except Exception as exc:
        print()
        print(
            f"ERREUR pendant l'import : "
            f"{type(exc).__name__}: {exc}"
        )

    print()
    print("===== SAUVEGARDE METADONNEES =====")

    with METADATA_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for key in sorted(
            rows,
            key=lambda x: int(x) if str(x).isdigit() else str(x),
        ):
            writer.writerow(rows[key])

    summary = {
        "total_seen_this_run": total_seen,
        "new_cifs_this_run": imported,
        "existing_cifs_skipped": skipped,
        "errors_this_run": failed,
        "total_metadata_records": len(rows),
        "cif_directory": str(CIF_DIR),
        "metadata_file": str(METADATA_FILE),
    }

    SUMMARY_FILE.write_text(
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
    print(f" Structures vues       : {total_seen:,}")
    print(f" Nouveaux CIF          : {imported:,}")
    print(f" CIF déjà présents     : {skipped:,}")
    print(f" Erreurs               : {failed:,}")
    print(f" Total metadata        : {len(rows):,}")
    print()
    print(f" CIF      : {CIF_DIR}")
    print(f" Metadata : {METADATA_FILE}")
    print(f" Résumé   : {SUMMARY_FILE}")
    print()
    print("QE : NON LANCÉ")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
