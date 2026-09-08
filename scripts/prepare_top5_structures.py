from __future__ import annotations
import os
os.system("clear")

import csv
import urllib.parse
import urllib.request
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path.home() / "HydroMatAI"
TOP5 = ROOT / "reports" / "top5_dft_h2.csv"
OUT = ROOT / "structures" / "top5"
REPORT = ROOT / "reports" / "top5_structures.csv"

TOP5_NAMES = [
    "TiFeH2",
    "TiMn1.5",
    "Ti1.1CrMn",
    "LaNi5",
    "LaNi5H6",
]


def normalize(text: str) -> str:
    return "".join(
        char.lower()
        for char in text
        if char.isalnum()
    )


def find_existing(material: str) -> Path | None:
    target = normalize(material)

    for path in ROOT.rglob("*.cif"):
        if ".venv" in path.parts:
            continue

        name = normalize(path.stem)

        if target in name or name in target:
            return path

    return None


def download_cod(material: str, destination: Path) -> Path | None:
    """
    Try COD text search and download a matching CIF.

    No calculation is performed here.
    """
    query = urllib.parse.quote(material)

    url = (
        "https://www.crystallography.net/cod/"
        f"result?formula={query}&format=json"
    )

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = response.read().decode("utf-8")
    except Exception:
        return None

    if not data.strip():
        return None

    # COD search responses can vary; only use an explicit CIF URL.
    import json

    try:
        records = json.loads(data)
    except Exception:
        return None

    if not isinstance(records, list) or not records:
        return None

    for record in records:
        cod_id = record.get("codid") or record.get("id")
        if not cod_id:
            continue

        cif_url = (
            "https://www.crystallography.net/cod/"
            f"{cod_id}.cif"
        )

        try:
            with urllib.request.urlopen(cif_url, timeout=15) as response:
                content = response.read()

            destination.write_bytes(content)
            return destination

        except Exception:
            continue

    return None


def validate(path: Path) -> tuple[bool, str]:
    try:
        structure = Structure.from_file(path)

        if len(structure) == 0:
            return False, "EMPTY_STRUCTURE"

        elements = sorted(
            {str(site.specie.element) for site in structure}
        )

        return True, ",".join(elements)

    except Exception as exc:
        return False, f"INVALID_CIF: {exc}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []

    print("=" * 70)
    print(" HydroMatAI — TOP 5 STRUCTURE PREPARATION")
    print("=" * 70)
    print()

    for material in TOP5_NAMES:
        destination = OUT / f"{material.replace('/', '_')}.cif"

        print(f"{material:20s}", end="")

        existing = find_existing(material)

        if existing:
            destination.write_bytes(existing.read_bytes())
            source = str(existing)
            print(" FOUND", end="")
        else:
            downloaded = download_cod(material, destination)

            if downloaded:
                source = "COD"
                print(" DOWNLOADED", end="")
            else:
                source = ""
                print(" MISSING", end="")

        if destination.exists():
            ok, info = validate(destination)

            if ok:
                print(f"  VALID  elements={info}")

                rows.append({
                    "material": material,
                    "status": "READY",
                    "structure": str(destination),
                    "source": source,
                    "details": info,
                })
            else:
                print(f"  INVALID  {info}")

                rows.append({
                    "material": material,
                    "status": "INVALID",
                    "structure": str(destination),
                    "source": source,
                    "details": info,
                })
        else:
            print()

            rows.append({
                "material": material,
                "status": "STRUCTURE_MISSING",
                "structure": "",
                "source": "",
                "details": "",
            })

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    with REPORT.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "material",
                "status",
                "structure",
                "source",
                "details",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    ready = sum(row["status"] == "READY" for row in rows)

    print()
    print("=" * 70)
    print(" RESULTAT")
    print("=" * 70)
    print(f"Structures TOP 5 : {len(rows)}")
    print(f"Structures valides : {ready}")
    print(f"Structures manquantes/invalides : {len(rows) - ready}")
    print()
    print(f"Rapport : {REPORT}")

    if ready == 5:
        print()
        print("OK — LES 5 STRUCTURES SONT PRETES POUR LA VALIDATION DFT")
    else:
        print()
        print("ATTENTION — QE N'EST PAS LANCE")
        print("Les structures manquantes doivent être récupérées/validées.")


if __name__ == "__main__":
    main()
