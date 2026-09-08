#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

from mofdb_client import fetch


ROOT = Path("MOF_Library")
CIF_DIR = ROOT / "cif"
METADATA = ROOT / "metadata.csv"
MANIFEST = ROOT / "manifest.csv"
ERRORS = ROOT / "errors.csv"


def safe_name(value: str) -> str:
    value = str(value).strip()

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_-.()"
    )

    return "".join(
        char if char in allowed else "_"
        for char in value
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8", errors="ignore")
    ).hexdigest()


def get_value(obj, *names):
    for name in names:
        value = getattr(obj, name, None)

        if value is not None:
            return value

    return None


def initialize_csv(path: Path, fieldnames: list[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()


def main() -> int:

    ROOT.mkdir(parents=True, exist_ok=True)
    CIF_DIR.mkdir(parents=True, exist_ok=True)

    metadata_fields = [
        "name",
        "mofid",
        "mofkey",
        "database",
        "surface_area",
        "void_fraction",
        "pld",
        "lcd",
        "cif_path",
        "sha256",
    ]

    manifest_fields = [
        "name",
        "cif_path",
        "sha256",
        "status",
    ]

    error_fields = [
        "name",
        "error_type",
        "error",
    ]

    initialize_csv(METADATA, metadata_fields)
    initialize_csv(MANIFEST, manifest_fields)
    initialize_csv(ERRORS, error_fields)

    existing_hashes = set()

    if MANIFEST.exists():
        with MANIFEST.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            for row in csv.DictReader(handle):
                if row.get("sha256"):
                    existing_hashes.add(row["sha256"])

    metadata_handle = METADATA.open(
        "a",
        encoding="utf-8",
        newline="",
    )

    manifest_handle = MANIFEST.open(
        "a",
        encoding="utf-8",
        newline="",
    )

    error_handle = ERRORS.open(
        "a",
        encoding="utf-8",
        newline="",
    )

    metadata_writer = csv.DictWriter(
        metadata_handle,
        fieldnames=metadata_fields,
    )

    manifest_writer = csv.DictWriter(
        manifest_handle,
        fieldnames=manifest_fields,
    )

    error_writer = csv.DictWriter(
        error_handle,
        fieldnames=error_fields,
    )

    count = 0
    saved = 0
    skipped = 0
    failed = 0

    print("=" * 90)
    print(" HydroMatAI — IMPORT MOFX-DB → MOF_Library")
    print("=" * 90)
    print()
    print("Destination :", ROOT.resolve())
    print("Mode        : STREAMING")
    print()
    print("Importation démarrée...")
    print()

    try:
        records = fetch(
            telemetry=False,
        )

        for mof in records:

            count += 1

            name = str(
                get_value(mof, "name")
                or get_value(mof, "mofid")
                or f"mof_{count}"
            )

            try:
                cif = get_value(mof, "cif")

                if not cif:
                    failed += 1

                    error_writer.writerow({
                        "name": name,
                        "error_type": "missing_cif",
                        "error": "MOF object contains no CIF",
                    })

                    error_handle.flush()

                    continue

                cif = str(cif)

                digest = sha256_text(cif)

                if digest in existing_hashes:
                    skipped += 1
                    continue

                filename = safe_name(name)

                if not filename:
                    filename = f"mof_{count}"

                cif_path = CIF_DIR / f"{filename}.cif"

                # Avoid collision between different structures
                # having the same display name.
                if cif_path.exists():
                    cif_path = CIF_DIR / (
                        f"{filename}_{digest[:12]}.cif"
                    )

                cif_path.write_text(
                    cif,
                    encoding="utf-8",
                )

                surface_area = get_value(
                    mof,
                    "surface_area",
                    "sa_m2g",
                    "sa_m2g_value",
                )

                void_fraction = get_value(
                    mof,
                    "void_fraction",
                    "vf",
                )

                pld = get_value(
                    mof,
                    "pld",
                )

                lcd = get_value(
                    mof,
                    "lcd",
                )

                mofid = get_value(
                    mof,
                    "mofid",
                )

                mofkey = get_value(
                    mof,
                    "mofkey",
                )

                database = get_value(
                    mof,
                    "database",
                )

                relative_cif = str(
                    cif_path.relative_to(ROOT)
                )

                metadata_writer.writerow({
                    "name": name,
                    "mofid": mofid,
                    "mofkey": mofkey,
                    "database": database,
                    "surface_area": surface_area,
                    "void_fraction": void_fraction,
                    "pld": pld,
                    "lcd": lcd,
                    "cif_path": relative_cif,
                    "sha256": digest,
                })

                manifest_writer.writerow({
                    "name": name,
                    "cif_path": relative_cif,
                    "sha256": digest,
                    "status": "saved",
                })

                metadata_handle.flush()
                manifest_handle.flush()

                existing_hashes.add(digest)

                saved += 1

                if count <= 10 or count % 1000 == 0:
                    print(
                        f"[{count:>8}] "
                        f"saved={saved:<8} "
                        f"skipped={skipped:<8} "
                        f"failed={failed:<8} "
                        f"{name}"
                    )

            except Exception as exc:

                failed += 1

                error_writer.writerow({
                    "name": name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

                error_handle.flush()

                print(
                    f"[ERROR] {name}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

    except KeyboardInterrupt:

        print()
        print("Import interrompu par l'utilisateur.")

    except Exception as exc:

        print()
        print(
            "ERREUR FATALE :",
            type(exc).__name__,
            ":",
            exc,
            file=sys.stderr,
        )

        return 1

    finally:

        metadata_handle.close()
        manifest_handle.close()
        error_handle.close()

    print()
    print("=" * 90)
    print(" IMPORT TERMINÉ")
    print("=" * 90)
    print()
    print(f"Structures parcourues : {count}")
    print(f"CIF sauvegardés       : {saved}")
    print(f"CIF déjà présents     : {skipped}")
    print(f"Erreurs               : {failed}")
    print()
    print(f"Bibliothèque : {ROOT.resolve()}")
    print(f"Metadata     : {METADATA}")
    print(f"Manifest     : {MANIFEST}")
    print(f"Erreurs      : {ERRORS}")
    print()
    print("=" * 90)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
