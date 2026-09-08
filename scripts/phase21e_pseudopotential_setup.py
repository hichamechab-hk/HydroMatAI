from __future__ import annotations
import os
os.system("clear")

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from pymatgen.core import Structure


ROOT = Path("/home/hk/HydroMatAI")
PSEUDO_DIR = Path("/home/hk/software/qe-7.5/pseudo")

DFT_PRIORITY = ROOT / "reports/global_screening/dft_priority.csv"

OUTPUT_DIR = ROOT / "calculations/phase_21e_pseudopotential_setup"
CSV_PATH = OUTPUT_DIR / "phase21e_pseudopotential_setup.csv"
JSON_PATH = OUTPUT_DIR / "phase21e_pseudopotential_setup.json"

CIF_ROOTS = [
    ROOT / "MOF_Library/MOFXDB_FULL/cif",
    ROOT / "MOF_Library/METAL_HYDRIDES/cif",
    ROOT / "MOF_Library/COMPLEXES/cif",
]

REQUIRED_ELEMENTS = {"C", "H", "N", "O", "F", "Zn"}

# Pseudopotentiels PSLibrary / QE courants.
# IMPORTANT : F est explicitement associé à F, jamais à Fe.
PSEUDO_CANDIDATES = {
    "C": [
        "C.pbe-n-kjpaw_psl.1.0.0.UPF",
        "C.pbe-n-kjpaw_psl.1.0.0.UPF",
        "C.pbe-kjpaw.UPF",
        "C.UPF",
    ],
    "H": [
        "H.pbe-kjpaw_psl.1.0.0.UPF",
        "H.pbe-kjpaw.UPF",
        "H.UPF",
    ],
    "N": [
        "N.pbe-n-kjpaw_psl.1.0.0.UPF",
        "N.pbe-n-kjpaw_psl.1.0.0.UPF",
        "N.pbe-kjpaw.UPF",
        "N.UPF",
    ],
    "O": [
        "O.pbe-n-kjpaw_psl.1.0.0.UPF",
        "O.pbe-n-kjpaw_psl.1.0.0.UPF",
        "O.pbe-kjpaw.UPF",
        "O.UPF",
    ],
    "F": [
        "F.pbe-n-kjpaw_psl.1.0.0.UPF",
        "F.pbe-kjpaw.UPF",
        "F.UPF",
    ],
    "Zn": [
        "Zn.pbe-dn-kjpaw_psl.1.0.0.UPF",
        "Zn.pbe-dn-kjpaw_psl.1.0.0.UPF",
        "Zn.pbe-kjpaw.UPF",
        "Zn.UPF",
    ],
}


def print_header(title: str):
    print("=" * 80)
    print(f" HydroMatAI — PHASE 21E")
    print(f" {title}")
    print("=" * 80)


def normalize_element(value: str) -> str:
    value = value.strip()

    if not value:
        return value

    if len(value) == 1:
        return value.upper()

    return value[0].upper() + value[1:].lower()


def get_cif_from_row(row: dict) -> Path | None:
    candidates = []

    cif_path = (row.get("cif") or "").strip()
    if cif_path:
        candidates.append(Path(cif_path))

    cif_path = (row.get("cif_path") or "").strip()
    if cif_path:
        candidates.append(Path(cif_path))

    name = (row.get("name") or "").strip()

    if name:
        for root in CIF_ROOTS:
            candidates.extend(root.glob(f"*_{name}.cif"))
            candidates.extend(root.glob(f"{name}.cif"))

    for path in candidates:
        if not path.is_absolute():
            path = ROOT / path

        if path.exists():
            return path.resolve()

    return None


def load_priority(limit: int) -> list[dict]:
    if not DFT_PRIORITY.exists():
        raise FileNotFoundError(
            f"DFT priority introuvable : {DFT_PRIORITY}"
        )

    rows = []

    with DFT_PRIORITY.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            classification = (
                row.get("classification")
                or row.get("class")
                or row.get("priority_class")
                or ""
            ).strip().upper()

            # Phase 19 utilise PRIORITY.
            if classification and classification != "PRIORITY":
                continue

            rows.append(row)

            if len(rows) >= limit:
                break

    return rows


def list_upf_files() -> list[Path]:
    if not PSEUDO_DIR.exists():
        return []

    return sorted(PSEUDO_DIR.glob("*.UPF"))


def read_upf_element(path: Path) -> str | None:
    """
    Détermine l'élément réel déclaré dans le fichier UPF.

    On ne fait JAMAIS confiance uniquement au nom du fichier.
    Cela empêche une erreur du type F -> Fe.
    """
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            text = f.read(20000)
    except Exception:
        return None

    patterns = [
        r'<PP_HEADER[^>]*element\s*=\s*"([A-Za-z]+)"',
        r'element\s*=\s*"([A-Za-z]+)"',
        r'<PP_HEADER[^>]*element\s*=\s*\'([A-Za-z]+)\'',
        r'element\s*=\s*\'([A-Za-z]+)\'',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return normalize_element(match.group(1))

    # Fallback très conservateur :
    # on accepte uniquement un nom commençant exactement
    # par le symbole chimique attendu lors du mapping.
    return None


def build_upf_inventory() -> dict[str, list[Path]]:
    inventory: dict[str, list[Path]] = {}

    for path in list_upf_files():
        element = read_upf_element(path)

        if element is None:
            continue

        inventory.setdefault(element, []).append(path)

    return inventory


def strict_filename_element(path: Path) -> str | None:
    """
    Extrait l'élément uniquement depuis le début du nom.
    """
    name = path.name

    match = re.match(
        r"^([A-Z][a-z]?)(?:[._-]|$)",
        name,
    )

    if not match:
        return None

    return normalize_element(match.group(1))


def validate_candidate_for_element(
    element: str,
    path: Path,
) -> bool:
    """
    Validation stricte.

    Exemple :
      element = F
      Fe.pbe...UPF -> REFUSÉ
      F.pbe...UPF  -> accepté si le header confirme F.
    """
    element = normalize_element(element)

    filename_element = strict_filename_element(path)

    if filename_element != element:
        return False

    header_element = read_upf_element(path)

    if header_element is not None:
        return header_element == element

    # Si le header n'est pas lisible, on refuse pour éviter
    # toute attribution scientifique incorrecte.
    return False


def find_existing_pseudo(
    element: str,
    inventory: dict[str, list[Path]],
) -> Path | None:

    element = normalize_element(element)

    # 1. Noms connus.
    for filename in PSEUDO_CANDIDATES.get(element, []):
        path = PSEUDO_DIR / filename

        if path.exists() and validate_candidate_for_element(
            element,
            path,
        ):
            return path.resolve()

    # 2. Recherche stricte dans l'inventaire.
    for path in inventory.get(element, []):
        if validate_candidate_for_element(element, path):
            return path.resolve()

    return None


def structure_elements(cif: Path) -> tuple[list[str], int]:
    structure = Structure.from_file(cif)

    elements = sorted(
        {
            normalize_element(site.specie.symbol)
            for site in structure.sites
        }
    )

    return elements, len(structure)


def safe_download(
    url: str,
    destination: Path,
) -> bool:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = destination.with_suffix(
        destination.suffix + ".part"
    )

    try:
        print(f"  DOWNLOAD : {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HydroMatAI/Phase21E"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            data = response.read()

        if not data:
            return False

        tmp.write_bytes(data)

        tmp.replace(destination)

        return True

    except Exception as exc:
        print(f"  DOWNLOAD FAILED : {exc}")

        if tmp.exists():
            tmp.unlink()

        return False


def try_download_missing(
    missing: list[str],
) -> dict[str, str]:

    """
    Téléchargement optionnel.

    Les URLs sont uniquement des candidates connues PSLibrary.
    Si une URL n'existe plus, on laisse l'élément en MISSING.

    Aucun calcul QE n'est lancé.
    """

    # URLs de secours.
    # Le script ne considérera le fichier valide qu'après
    # vérification de son élément réel dans le header UPF.
    urls = {
        "C": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "C.pbe-n-kjpaw_psl.1.0.0.UPF"
        ),
        "H": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "H.pbe-kjpaw_psl.1.0.0.UPF"
        ),
        "N": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "N.pbe-n-kjpaw_psl.1.0.0.UPF"
        ),
        "O": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "O.pbe-n-kjpaw_psl.1.0.0.UPF"
        ),
        "F": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "F.pbe-n-kjpaw_psl.1.0.0.UPF"
        ),
        "Zn": (
            "https://pseudopotentials.quantum-espresso.org/upf_files/"
            "Zn.pbe-dn-kjpaw_psl.1.0.0.UPF"
        ),
    }

    downloaded = {}

    for element in missing:

        url = urls.get(element)

        if not url:
            continue

        filename = Path(url).name
        destination = PSEUDO_DIR / filename

        if destination.exists():
            downloaded[element] = str(destination)
            continue

        ok = safe_download(
            url,
            destination,
        )

        if ok:
            downloaded[element] = str(destination)

    return downloaded


def audit_pw_x() -> dict:
    result = {
        "pw_x": "",
        "available": False,
    }

    candidates = [
        "/home/hk/software/qe-7.5/bin/pw.x",
        shutil.which("pw.x"),
    ]

    for candidate in candidates:
        if not candidate:
            continue

        path = Path(candidate)

        if path.exists() and path.is_file():
            result["pw_x"] = str(path.resolve())
            result["available"] = True
            break

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "HydroMatAI Phase 21E — "
            "audit/setup pseudopotentiels QE"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de candidats PRIORITY à inspecter.",
    )

    parser.add_argument(
        "--download",
        action="store_true",
        help=(
            "Télécharger les pseudopotentiels manquants "
            "depuis les URLs configurées."
        ),
    )

    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Forcer le mode audit uniquement.",
    )

    args = parser.parse_args()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_header(
        "SETUP / VALIDATION PSEUDOPOTENTIELS QE"
    )

    print()
    print("PROTECTION QE")
    print("-" * 80)
    print("pw.x    : NON LANCÉ")
    print("bands.x : NON LANCÉ")
    print("dos.x   : NON LANCÉ")
    print("RELAX   : NON LANCÉ")
    print("SCF     : NON LANCÉ")
    print("Calcul  : NON LANCÉ")

    qe_info = audit_pw_x()

    print()
    print("ENVIRONNEMENT QE")
    print("-" * 80)

    if qe_info["available"]:
        print(f"pw.x : OK → {qe_info['pw_x']}")
    else:
        print("pw.x : NON DÉTECTÉ")

    print()
    print("PSEUDOPOTENTIELS")
    print("-" * 80)
    print(f"Répertoire : {PSEUDO_DIR}")

    upf_files = list_upf_files()

    print(f"UPF trouvés : {len(upf_files)}")

    inventory = build_upf_inventory()

    print()
    print("ÉLÉMENTS DÉTECTÉS DANS LES UPF")
    print("-" * 80)

    for element in sorted(inventory):
        names = [
            p.name
            for p in inventory[element]
        ]

        print(
            f"{element:<4} : "
            + ", ".join(names)
        )

    try:
        rows = load_priority(args.limit)
    except Exception as exc:
        print()
        print(f"ERREUR : {exc}")
        sys.exit(1)

    print()
    print("CANDIDATS")
    print("-" * 80)
    print(f"Priority sélectionnés : {len(rows)}")

    results = []

    global_missing = set()

    for index, row in enumerate(rows, start=1):

        name = (
            row.get("name")
            or row.get("material")
            or row.get("formula")
            or f"candidate_{index}"
        ).strip()

        print()
        print(f"[{index}/{len(rows)}] {name}")

        cif = get_cif_from_row(row)

        if cif is None:
            print("  CIF    : MISSING")

            results.append(
                {
                    "rank": index,
                    "material": name,
                    "cif": "",
                    "valid_cif": 0,
                    "elements": "",
                    "n_atoms": "",
                    "mapping_status": "CIF_MISSING",
                    "missing_pseudopotentials": "",
                    "pseudo_mapping": "",
                    "ready_for_qe": 0,
                }
            )

            continue

        print(f"  CIF    : OK → {cif}")

        try:
            elements, n_atoms = structure_elements(cif)

        except Exception as exc:
            print(f"  CIF    : FAILED → {exc}")

            results.append(
                {
                    "rank": index,
                    "material": name,
                    "cif": str(cif),
                    "valid_cif": 0,
                    "elements": "",
                    "n_atoms": "",
                    "mapping_status": "CIF_PARSE_FAILED",
                    "missing_pseudopotentials": "",
                    "pseudo_mapping": "",
                    "ready_for_qe": 0,
                }
            )

            continue

        print(
            f"  Elements : {', '.join(elements)}"
        )
        print(f"  Atomes   : {n_atoms}")

        pseudo_mapping = {}
        missing = []

        unsupported = []

        for element in elements:

            # Pour la phase 21E, on n'autorise pas les éléments
            # qui ne disposent pas d'un mapping strict.
            if element not in REQUIRED_ELEMENTS:
                unsupported.append(element)
                pseudo_mapping[element] = "UNSUPPORTED"
                print(
                    f"  {element:<3} → UNSUPPORTED"
                )
                continue

            pseudo = find_existing_pseudo(
                element,
                inventory,
            )

            if pseudo is None:
                pseudo_mapping[element] = "MISSING"
                missing.append(element)

                print(
                    f"  {element:<3} → MISSING"
                )

            else:
                pseudo_mapping[element] = str(pseudo)

                print(
                    f"  {element:<3} → {pseudo.name}"
                )

        for element in missing:
            global_missing.add(element)

        if unsupported:
            mapping_status = "UNSUPPORTED_ELEMENT"

        elif missing:
            mapping_status = "MISSING_PSEUDO"

        else:
            mapping_status = "READY_FOR_QE"

        ready = (
            mapping_status == "READY_FOR_QE"
        )

        if ready:
            print("  STATUS : READY_FOR_QE")
        else:
            print(
                f"  STATUS : {mapping_status}"
            )

        results.append(
            {
                "rank": index,
                "material": name,
                "cif": str(cif),
                "valid_cif": 1,
                "elements": ",".join(elements),
                "n_atoms": n_atoms,
                "mapping_status": mapping_status,
                "missing_pseudopotentials": ",".join(
                    missing
                ),
                "unsupported_elements": ",".join(
                    unsupported
                ),
                "pseudo_mapping": json.dumps(
                    pseudo_mapping,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "ready_for_qe": int(ready),
            }
        )

    # ------------------------------------------------------------------
    # OPTIONAL DOWNLOAD
    # ------------------------------------------------------------------

    downloaded = {}

    if args.download and not args.no_download:

        if global_missing:

            print()
            print("TÉLÉCHARGEMENT OPTIONNEL")
            print("-" * 80)

            missing_sorted = sorted(
                global_missing
            )

            print(
                "Éléments manquants : "
                + ", ".join(missing_sorted)
            )

            downloaded = try_download_missing(
                missing_sorted
            )

            # Reconstruction après téléchargement.
            inventory = build_upf_inventory()

            print()
            print("REVALIDATION APRÈS TÉLÉCHARGEMENT")
            print("-" * 80)

            for result in results:

                if not result["valid_cif"]:
                    continue

                cif = Path(result["cif"])

                try:
                    elements, _ = structure_elements(cif)
                except Exception:
                    continue

                pseudo_mapping = {}
                missing = []
                unsupported = []

                for element in elements:

                    if element not in REQUIRED_ELEMENTS:
                        unsupported.append(element)
                        pseudo_mapping[element] = "UNSUPPORTED"
                        continue

                    pseudo = find_existing_pseudo(
                        element,
                        inventory,
                    )

                    if pseudo is None:
                        missing.append(element)
                        pseudo_mapping[element] = "MISSING"
                    else:
                        pseudo_mapping[element] = str(
                            pseudo
                        )

                if unsupported:
                    status = "UNSUPPORTED_ELEMENT"
                elif missing:
                    status = "MISSING_PSEUDO"
                else:
                    status = "READY_FOR_QE"

                result[
                    "mapping_status"
                ] = status

                result[
                    "missing_pseudopotentials"
                ] = ",".join(missing)

                result[
                    "unsupported_elements"
                ] = ",".join(unsupported)

                result[
                    "pseudo_mapping"
                ] = json.dumps(
                    pseudo_mapping,
                    ensure_ascii=False,
                    sort_keys=True,
                )

                result[
                    "ready_for_qe"
                ] = int(
                    status == "READY_FOR_QE"
                )

    # ------------------------------------------------------------------
    # FINAL COUNTS
    # ------------------------------------------------------------------

    total = len(results)

    cif_valid = sum(
        r["valid_cif"] == 1
        for r in results
    )

    ready = sum(
        r["ready_for_qe"] == 1
        for r in results
    )

    missing = sum(
        r["mapping_status"] == "MISSING_PSEUDO"
        for r in results
    )

    unsupported = sum(
        r["mapping_status"] == "UNSUPPORTED_ELEMENT"
        for r in results
    )

    cif_failed = total - cif_valid

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    fieldnames = [
        "rank",
        "material",
        "cif",
        "valid_cif",
        "elements",
        "n_atoms",
        "mapping_status",
        "missing_pseudopotentials",
        "unsupported_elements",
        "pseudo_mapping",
        "ready_for_qe",
    ]

    with CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(result)

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    summary = {
        "phase": "21E",
        "project": "HydroMatAI",
        "description": (
            "Pseudopotential setup and strict QE mapping"
        ),
        "qe_execution": {
            "pw_x": False,
            "bands_x": False,
            "dos_x": False,
            "relax": False,
            "scf": False,
            "heavy_calculation": False,
        },
        "environment": qe_info,
        "pseudo_directory": str(PSEUDO_DIR),
        "upf_count": len(upf_files),
        "required_elements": sorted(
            REQUIRED_ELEMENTS
        ),
        "candidates": total,
        "cif_valid": cif_valid,
        "cif_failed": cif_failed,
        "ready_for_qe": ready,
        "missing_pseudo": missing,
        "unsupported_element": unsupported,
        "global_missing_elements": sorted(
            global_missing
        ),
        "download_requested": bool(
            args.download and not args.no_download
        ),
        "downloaded": downloaded,
        "strict_mapping": True,
        "f_error_protection": True,
        "results": results,
        "files": {
            "csv": str(CSV_PATH),
            "json": str(JSON_PATH),
        },
    }

    with JSON_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print(" PHASE 21E — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats          : {total}"
    )
    print(
        f"CIF valides        : {cif_valid}"
    )
    print(
        f"CIF FAILED         : {cif_failed}"
    )
    print(
        f"READY_FOR_QE       : {ready}"
    )
    print(
        f"MISSING_PSEUDO     : {missing}"
    )
    print(
        f"UNSUPPORTED        : {unsupported}"
    )

    print()
    print("PSEUDOPOTENTIELS MANQUANTS")
    print("-" * 80)

    if global_missing:
        print(
            ", ".join(
                sorted(global_missing)
            )
        )
    else:
        print("Aucun")

    print()
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV  : {CSV_PATH}")
    print(f"JSON : {JSON_PATH}")

    print()
    print("=" * 80)
    print("PHASE 21E — AUDIT FINAL")
    print("=" * 80)

    print(
        f"QE pw.x détecté              : "
        f"{'OK' if qe_info['available'] else 'FAIL'}"
    )
    print("Aucun calcul QE              : OK")
    print("Aucun CIF modifié            : OK")
    print("Mapping élémentaire strict   : OK")
    print("Protection F → Fe            : OK")
    print("Traçabilité                  : OK")

    if ready == total and total > 0:
        print()
        print("READY_FOR_QE : OUI")
    else:
        print()
        print("READY_FOR_QE : NON")

    print("=" * 80)


if __name__ == "__main__":
    main()
