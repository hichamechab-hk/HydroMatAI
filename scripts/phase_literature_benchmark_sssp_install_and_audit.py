#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
PHASE — LITERATURE BENCHMARK SSSP INSTALL & AUDIT
==============================================================================

Objectif
--------
Installer et auditer SSSP 1.3.0 PBE precision pour les benchmarks
littérature HydroMatAI.

Éléments requis
---------------
H, K, Rb, Ge, Sn, Na, Ca, Sr, Pd, Ru

Garanties
---------
- clear au démarrage
- aucun pw.x
- aucun calcul DFT
- aucun fichier scientifique existant modifié
- téléchargement limité à l'archive SSSP officielle
- vérification MD5
- extraction dans un espace dédié
- inspection des fichiers UPF
- identification élément / type / fonctionnelle / ZVAL
- comparaison avec les métadonnées SSSP JSON
- manifest final CSV + TXT
- SHA256 des fichiers retenus
- journalisation de la provenance

Référence SSSP
--------------
SSSP 1.3.0 PBE precision
Materials Cloud Archive
MCID: 2023.61
DOI: 10.24435/materialscloud:eg-28

Archive:
SSSP_1.3.0_PBE_precision.tar.gz

MD5 officiel:
fde94756886f32ada7bf597547557eb5

IMPORTANT
---------
Le script n'utilise PAS les pseudopotentiels existants de HydroMatAI
comme substituts silencieux.

Il constitue une bibliothèque SSSP séparée.
==============================================================================

"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


# ============================================================================
# 0. CLEAR
# ============================================================================

print("\033[2J\033[H", end="")


# ============================================================================
# 1. CONFIGURATION
# ============================================================================

BASE = Path("/home/hk/HydroMatAI")

REPORT_DIR = BASE / "reports" / "literature_benchmarks"
SSSP_ROOT = BASE / "data" / "literature_benchmarks" / "sssp"
DOWNLOAD_DIR = SSSP_ROOT / "download"
EXTRACT_DIR = SSSP_ROOT / "extracted"
SELECTED_DIR = SSSP_ROOT / "selected"
META_DIR = SSSP_ROOT / "metadata"

ARCHIVE_NAME = "SSSP_1.3.0_PBE_precision.tar.gz"
META_NAME = "SSSP_1.3.0_PBE_precision.json"

# Materials Cloud / SSSP 1.3.0
ARCHIVE_MD5 = "fde94756886f32ada7bf597547557eb5"
META_MD5 = "1692c5c9ce89e1c7c783f8f0eee0cbfa"

# Materials Cloud record.
# Le script essaie plusieurs URL possibles afin d'être robuste
# aux changements de routage de l'archive.
ARCHIVE_URLS = [
    "https://archive.materialscloud.org/api/records/rcyfm-68h65/files/SSSP_1.3.0_PBE_precision.tar.gz/content",
]

META_URLS = [
    "https://archive.materialscloud.org/api/records/rcyfm-68h65/files/SSSP_1.3.0_PBE_precision.json/content",
]

ELEMENTS = [
    "H",
    "K",
    "Rb",
    "Ge",
    "Sn",
    "Na",
    "Ca",
    "Sr",
    "Pd",
    "Ru",
]

EXPECTED_COUNT = len(ELEMENTS)

REPORT_CSV = REPORT_DIR / "literature_benchmark_sssp_inventory.csv"
REPORT_TXT = REPORT_DIR / "literature_benchmark_sssp_install_audit.txt"

DOWNLOAD_ARCHIVE = DOWNLOAD_DIR / ARCHIVE_NAME
DOWNLOAD_META = DOWNLOAD_DIR / META_NAME

SELECTED_MANIFEST = SELECTED_DIR / "SSSP_1.3.0_PBE_precision_SELECTED.csv"


# ============================================================================
# 2. OUTILS
# ============================================================================

def log(msg: str = "") -> None:
    print(msg)


def fail(msg: str) -> None:
    print()
    print("[FATAL] " + msg)
    sys.exit(1)


def md5_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.md5()

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def download_with_fallback(
    urls: list[str],
    destination: Path,
    expected_md5: str | None = None,
) -> str:

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Si le fichier existe déjà et que son MD5 est correct,
    # aucun téléchargement n'est nécessaire.
    if destination.exists():

        log(f"[INFO] Fichier déjà présent : {destination}")

        if expected_md5:
            observed = md5_file(destination)

            if observed.lower() == expected_md5.lower():
                log("[PASS] MD5 existant correct")
                return str(destination)

            log(
                "[WARN] MD5 incorrect pour le fichier existant : "
                f"{observed}"
            )

    last_error = None

    for url in urls:

        log()
        log("[DOWNLOAD] " + url)

        temporary = destination.with_suffix(destination.suffix + ".part")

        try:

            if temporary.exists():
                temporary.unlink()

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "HydroMatAI/SSSP-audit "
                        "(scientific reproducibility)"
                    )
                },
            )

            with urllib.request.urlopen(request, timeout=120) as response:

                total = response.headers.get("Content-Length")

                if total:
                    total = int(total)
                    log(f"[INFO] Taille annoncée : {total / 1024 / 1024:.2f} MiB")

                downloaded = 0

                with temporary.open("wb") as out:

                    while True:

                        chunk = response.read(1024 * 1024)

                        if not chunk:
                            break

                        out.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            pct = 100.0 * downloaded / total

                            print(
                                f"\r[DOWNLOAD] {pct:6.2f}% "
                                f"({downloaded / 1024 / 1024:.2f} MiB)",
                                end="",
                                flush=True,
                            )

                print()

            temporary.replace(destination)

            if expected_md5:

                observed = md5_file(destination)

                if observed.lower() != expected_md5.lower():

                    destination.unlink(missing_ok=True)

                    raise RuntimeError(
                        "MD5 incorrect : "
                        f"observé={observed}, attendu={expected_md5}"
                    )

                log("[PASS] MD5 officiel vérifié")

            return str(destination)

        except Exception as exc:

            last_error = exc

            log(f"[WARN] Échec : {exc}")

            temporary.unlink(missing_ok=True)

    raise RuntimeError(
        f"Impossible de télécharger {destination.name}. "
        f"Dernière erreur : {last_error}"
    )


def find_upf_files(root: Path) -> list[Path]:

    files = []

    for path in root.rglob("*"):

        if path.is_file() and path.suffix.lower() == ".upf":
            files.append(path)

    return sorted(files)


def clean_text(value: str | None) -> str:

    if value is None:
        return ""

    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def first_regex(text: str, patterns: list[str]) -> str:

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if match:
            return clean_text(match.group(1))

    return ""


def inspect_upf(path: Path) -> dict:

    try:
        # Les UPF sont généralement des fichiers texte.
        # errors=replace évite qu'un caractère exotique bloque l'audit.
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception as exc:

        return {
            "path": str(path),
            "file": path.name,
            "element": "",
            "type": "",
            "functional": "",
            "zval": "",
            "zval_num": None,
            "pseudo": "",
            "generator": "",
            "status": "READ_ERROR",
            "error": str(exc),
        }

    element = first_regex(
        text,
        [
            r'\belement\s*=\s*["\']([^"\']+)["\']',
            r"\belement\s*=\s*([A-Za-z]{1,3})",
        ],
    )

    pseudo_type = first_regex(
        text,
        [
            r'\tpseudo_type\s*=\s*["\']([^"\']+)["\']',
            r'\bpseudo_type\s*=\s*["\']([^"\']+)["\']',
        ],
    )

    functional = first_regex(
        text,
        [
            r'\tfunctional\s*=\s*["\']([^"\']+)["\']',
            r'\bfunctional\s*=\s*["\']([^"\']+)["\']',
        ],
    )

    zval = first_regex(
        text,
        [
            r'\tz_valence\s*=\s*["\']([^"\']+)["\']',
            r'\bz_valence\s*=\s*["\']([^"\']+)["\']',
            r'\bzval\s*=\s*["\']([^"\']+)["\']',
        ],
    )

    pseudo = first_regex(
        text,
        [
            r'\tpseudo\s*=\s*["\']([^"\']+)["\']',
            r'\bpseudo\s*=\s*["\']([^"\']+)["\']',
        ],
    )

    generated = first_regex(
        text,
        [
            r'\tgenerator\s*=\s*["\']([^"\']+)["\']',
            r'\bgenerated\s+by\s+["\']?([^"\']+)["\']?',
        ],
    )

    # Fallback élément depuis le nom de fichier.
    if not element:

        stem = path.stem

        for symbol in ELEMENTS:

            if re.search(
                rf"(^|[^A-Za-z]){re.escape(symbol)}([^A-Za-z]|$)",
                stem,
            ):
                element = symbol
                break

    zval_num = None

    if zval:

        try:
            zval_num = float(
                zval.replace("D", "E").replace("d", "e")
            )

        except ValueError:
            zval_num = None

    status = "OK"

    if not element:
        status = "NO_ELEMENT"

    return {
        "path": str(path),
        "file": path.name,
        "element": element,
        "type": pseudo_type,
        "functional": functional,
        "zval": zval,
        "zval_num": zval_num,
        "pseudo": pseudo,
        "generator": generated,
        "status": status,
        "error": "",
    }


def normalize_element(value: str) -> str:

    value = value.strip()

    if not value:
        return ""

    # Capitalisation chimique standard.
    return value[0].upper() + value[1:].lower()


def load_metadata(path: Path) -> dict:

    try:

        return json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception as exc:

        log(f"[WARN] Impossible de lire le JSON SSSP : {exc}")
        return {}


def walk_metadata_for_elements(
    obj,
    target_elements: set[str],
    found: dict,
) -> None:

    if isinstance(obj, dict):

        for key, value in obj.items():

            # Si une clé ressemble à un élément, garder sa structure.
            key_norm = normalize_element(str(key))

            if key_norm in target_elements:

                found.setdefault(
                    key_norm,
                    value,
                )

            walk_metadata_for_elements(
                value,
                target_elements,
                found,
            )

    elif isinstance(obj, list):

        for item in obj:

            walk_metadata_for_elements(
                item,
                target_elements,
                found,
            )


def extract_metadata_entries(
    metadata: dict,
) -> dict:

    target = set(ELEMENTS)

    result = {}

    walk_metadata_for_elements(
        metadata,
        target,
        result,
    )

    return result


def copy_selected(source: Path, element: str) -> Path:

    SELECTED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = SELECTED_DIR / source.name

    # Ne pas écraser silencieusement un fichier différent.
    if destination.exists():

        old_hash = sha256_file(destination)
        new_hash = sha256_file(source)

        if old_hash != new_hash:

            destination = (
                SELECTED_DIR
                / f"{element}_{source.name}"
            )

    shutil.copy2(
        source,
        destination,
    )

    return destination


# ============================================================================
# 3. HEADER
# ============================================================================

log("=" * 78)
log("PHASE — LITERATURE BENCHMARK SSSP INSTALL & AUDIT")
log("=" * 78)
log()
log("[INFO] MODE = INSTALL + AUDIT")
log("[INFO] Aucun pw.x")
log("[INFO] Aucun calcul DFT")
log("[INFO] Aucun fichier scientifique existant modifié")
log("[INFO] Bibliothèque séparée SSSP 1.3.0 PBE precision")
log()
log(f"[INFO] BASE       : {BASE}")
log(f"[INFO] SSSP ROOT  : {SSSP_ROOT}")
log(f"[INFO] REPORT CSV : {REPORT_CSV}")
log(f"[INFO] REPORT TXT : {REPORT_TXT}")
log()


# ============================================================================
# 4. VALIDATION ENVIRONNEMENT
# ============================================================================

if not BASE.exists():
    fail(f"Répertoire HydroMatAI absent : {BASE}")

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXTRACT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SELECTED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

META_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# 5. DOWNLOAD ARCHIVE
# ============================================================================

log("=" * 78)
log("1. ARCHIVE SSSP")
log("-" * 78)

try:

    download_with_fallback(
        ARCHIVE_URLS,
        DOWNLOAD_ARCHIVE,
        expected_md5=ARCHIVE_MD5,
    )

except Exception as exc:

    fail(str(exc))


archive_sha256 = sha256_file(
    DOWNLOAD_ARCHIVE
)

archive_md5 = md5_file(
    DOWNLOAD_ARCHIVE
)

log(f"[INFO] Archive : {DOWNLOAD_ARCHIVE}")
log(f"[INFO] MD5     : {archive_md5}")
log(f"[INFO] SHA256  : {archive_sha256}")
log(f"[INFO] Taille  : {DOWNLOAD_ARCHIVE.stat().st_size / 1024 / 1024:.2f} MiB")


# ============================================================================
# 6. DOWNLOAD JSON METADATA
# ============================================================================

log()
log("=" * 78)
log("2. METADONNEES SSSP")
log("-" * 78)

try:

    download_with_fallback(
        META_URLS,
        DOWNLOAD_META,
        expected_md5=META_MD5,
    )

except Exception as exc:

    log(f"[WARN] JSON SSSP non téléchargé : {exc}")
    log("[WARN] L'audit UPF continuera sans comparaison JSON.")


meta_sha256 = ""

if DOWNLOAD_META.exists():

    meta_sha256 = sha256_file(
        DOWNLOAD_META
    )

    shutil.copy2(
        DOWNLOAD_META,
        META_DIR / META_NAME,
    )

    log(f"[PASS] Metadata : {DOWNLOAD_META}")
    log(f"[INFO] SHA256   : {meta_sha256}")


# ============================================================================
# 7. EXTRACTION
# ============================================================================

log()
log("=" * 78)
log("3. EXTRACTION")
log("-" * 78)

# Détection de la présence d'un fichier UPF déjà extrait.
existing_upfs = find_upf_files(EXTRACT_DIR)

if existing_upfs:

    log(
        f"[INFO] Extraction déjà présente : "
        f"{len(existing_upfs)} UPF"
    )

else:

    log("[INFO] Extraction de l'archive...")

    try:

        with tarfile.open(
            DOWNLOAD_ARCHIVE,
            mode="r:gz",
        ) as tar:

            # Sécurité contre path traversal.
            root = EXTRACT_DIR.resolve()

            members = tar.getmembers()

            for member in members:

                member_path = (
                    EXTRACT_DIR
                    / member.name
                ).resolve()

                if not str(member_path).startswith(
                    str(root) + os.sep
                ):
                    fail(
                        "Archive dangereuse : "
                        f"{member.name}"
                    )

            tar.extractall(
                EXTRACT_DIR
            )

    except Exception as exc:

        fail(
            f"Extraction SSSP impossible : {exc}"
        )

    existing_upfs = find_upf_files(
        EXTRACT_DIR
    )

log(
    f"[PASS] UPF trouvés après extraction : "
    f"{len(existing_upfs)}"
)


# ============================================================================
# 8. INSPECTION UPF
# ============================================================================

log()
log("=" * 78)
log("4. INVENTAIRE UPF SSSP")
log("-" * 78)

records = []

for upf in existing_upfs:

    info = inspect_upf(upf)

    info["element"] = normalize_element(
        info.get("element", "")
    )

    records.append(
        info
    )

element_records = {
    element: []
    for element in ELEMENTS
}

for record in records:

    element = record["element"]

    if element in element_records:

        element_records[element].append(
            record
        )


# ============================================================================
# 9. SELECTION PAR ELEMENT
# ============================================================================

log()
log("=" * 78)
log("5. SELECTION DES PSEUDOPOTENTIELS")
log("-" * 78)

selected = {}

for element in ELEMENTS:

    candidates = element_records.get(
        element,
        [],
    )

    log()
    log(f"[{element}] candidats : {len(candidates)}")

    if not candidates:

        log(f"[FAIL] {element} : aucun UPF SSSP trouvé")
        continue

    # On préfère les fichiers dont le contenu UPF confirme
    # explicitement l'élément.
    explicit = [
        item
        for item in candidates
        if item["element"] == element
    ]

    if explicit:
        candidates = explicit

    # Score de sélection.
    def score(item):

        value = 0

        if item["functional"]:
            value += 4

        if item["type"]:
            value += 3

        if item["zval_num"] is not None:
            value += 3

        if item["pseudo"]:
            value += 1

        if item["generator"]:
            value += 1

        return value

    candidates = sorted(
        candidates,
        key=score,
        reverse=True,
    )

    chosen = candidates[0]

    selected[element] = chosen

    log(
        f"[SELECT] {chosen['file']}"
    )
    log(
        f"          TYPE       = "
        f"{chosen['type'] or 'UNKNOWN'}"
    )
    log(
        f"          FUNCTIONAL = "
        f"{chosen['functional'] or 'UNKNOWN'}"
    )
    log(
        f"          ZVAL       = "
        f"{chosen['zval'] or 'UNKNOWN'}"
    )
    log(
        f"          PATH       = "
        f"{chosen['path']}"
    )


# ============================================================================
# 10. COPIE DES PSEUDOS RETENUS
# ============================================================================

log()
log("=" * 78)
log("6. INSTALLATION DU JEU RETENU")
log("-" * 78)

installed = {}

for element in ELEMENTS:

    if element not in selected:
        continue

    source = Path(
        selected[element]["path"]
    )

    destination = copy_selected(
        source,
        element,
    )

    installed[element] = destination

    log(
        f"[PASS] {element} -> "
        f"{destination.name}"
    )


# ============================================================================
# 11. JSON SSSP
# ============================================================================

metadata = {}

if DOWNLOAD_META.exists():

    metadata = load_metadata(
        DOWNLOAD_META
    )

metadata_entries = {}

if metadata:

    metadata_entries = extract_metadata_entries(
        metadata
    )


# ============================================================================
# 12. AUDIT FINAL
# ============================================================================

log()
log("=" * 78)
log("7. AUDIT FINAL")
log("-" * 78)

final_rows = []

for element in ELEMENTS:

    if element not in selected:

        final_rows.append(
            {
                "element": element,
                "status": "MISSING",
                "file": "",
                "path": "",
                "type": "",
                "functional": "",
                "zval": "",
                "sha256": "",
                "metadata_found": (
                    "YES"
                    if element in metadata_entries
                    else "NO"
                ),
            }
        )

        log(
            f"[FAIL] {element:<3} : MISSING"
        )

        continue

    info = selected[element]

    source = Path(
        info["path"]
    )

    destination = installed.get(
        element
    )

    sha256 = ""

    if destination and destination.exists():

        sha256 = sha256_file(
            destination
        )

    status = "PASS"

    if normalize_element(
        info["element"]
    ) != element:

        status = "FAIL_ELEMENT"

    if not info["functional"]:

        status = "WARN_FUNCTIONAL"

    if info["zval_num"] is None:

        status = (
            "WARN_ZVAL"
            if status == "PASS"
            else status
        )

    final_rows.append(
        {
            "element": element,
            "status": status,
            "file": source.name,
            "path": str(
                destination
                if destination
                else source
            ),
            "type": info["type"],
            "functional": info["functional"],
            "zval": info["zval"],
            "sha256": sha256,
            "metadata_found": (
                "YES"
                if element in metadata_entries
                else "NO"
            ),
        }
    )

    log(
        f"[{status}] {element:<3} : "
        f"{source.name}"
    )


# ============================================================================
# 13. MANIFEST CSV
# ============================================================================

log()
log("=" * 78)
log("8. ECRITURE DES RAPPORTS")
log("-" * 78)

fieldnames = [
    "element",
    "status",
    "file",
    "path",
    "type",
    "functional",
    "zval",
    "sha256",
    "metadata_found",
]

with REPORT_CSV.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    writer.writerows(
        final_rows
    )


with SELECTED_MANIFEST.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    writer.writerows(
        final_rows
    )


# ============================================================================
# 14. RAPPORT TEXTE
# ============================================================================

found_count = sum(
    1
    for row in final_rows
    if row["status"] not in {"MISSING"}
)

pass_count = sum(
    1
    for row in final_rows
    if row["status"] == "PASS"
)

missing_elements = [
    row["element"]
    for row in final_rows
    if row["status"] == "MISSING"
]

warning_elements = [
    row["element"]
    for row in final_rows
    if row["status"].startswith("WARN")
]


report_lines = []

report_lines.append(
    "=" * 78
)

report_lines.append(
    "PHASE — LITERATURE BENCHMARK SSSP INSTALL & AUDIT"
)

report_lines.append(
    "=" * 78
)

report_lines.append("")

report_lines.append(
    "SSSP_VERSION : 1.3.0"
)

report_lines.append(
    "SSSP_FAMILY  : PBE precision"
)

report_lines.append(
    "MATERIALS_CLOUD_RECORD : 2023.61"
)

report_lines.append(
    "DOI : 10.24435/materialscloud:eg-28"
)

report_lines.append(
    f"ARCHIVE : {ARCHIVE_NAME}"
)

report_lines.append(
    f"ARCHIVE_MD5_EXPECTED : {ARCHIVE_MD5}"
)

report_lines.append(
    f"ARCHIVE_MD5_OBSERVED : {archive_md5}"
)

report_lines.append(
    f"ARCHIVE_SHA256 : {archive_sha256}"
)

report_lines.append("")

report_lines.append(
    f"METADATA : {META_NAME}"
)

report_lines.append(
    f"METADATA_MD5_EXPECTED : {META_MD5}"
)

if DOWNLOAD_META.exists():

    report_lines.append(
        f"METADATA_MD5_OBSERVED : "
        f"{md5_file(DOWNLOAD_META)}"
    )

    report_lines.append(
        f"METADATA_SHA256 : {meta_sha256}"
    )

else:

    report_lines.append(
        "METADATA_STATUS : NOT_AVAILABLE"
    )

report_lines.append("")

report_lines.append(
    f"REQUIRED_ELEMENTS : {EXPECTED_COUNT}"
)

report_lines.append(
    f"FOUND_ELEMENTS    : {found_count}"
)

report_lines.append(
    f"PASS_ELEMENTS     : {pass_count}"
)

report_lines.append(
    f"MISSING_ELEMENTS  : "
    f"{', '.join(missing_elements) if missing_elements else 'NONE'}"
)

report_lines.append(
    f"WARNING_ELEMENTS  : "
    f"{', '.join(warning_elements) if warning_elements else 'NONE'}"
)

report_lines.append("")

report_lines.append(
    "ELEMENT | STATUS | FILE | TYPE | FUNCTIONAL | ZVAL | SHA256"
)

report_lines.append(
    "-" * 78
)

for row in final_rows:

    report_lines.append(
        " | ".join(
            [
                row["element"],
                row["status"],
                row["file"],
                row["type"] or "UNKNOWN",
                row["functional"] or "UNKNOWN",
                row["zval"] or "UNKNOWN",
                row["sha256"] or "UNKNOWN",
            ]
        )
    )

report_lines.append("")
report_lines.append(
    "INSTALLATION_DIRECTORY"
)

report_lines.append(
    str(SELECTED_DIR)
)

report_lines.append("")

report_lines.append(
    "SECURITY / REPRODUCIBILITY"
)

report_lines.append(
    "- Aucun pw.x exécuté."
)

report_lines.append(
    "- Aucun input QE scientifique modifié."
)

report_lines.append(
    "- Aucun pseudopotentiel existant remplacé."
)

report_lines.append(
    "- Le jeu SSSP est installé dans un répertoire séparé."
)

report_lines.append(
    "- Chaque pseudo retenu possède un SHA256."
)

report_lines.append(
    "- Le MD5 de l'archive officielle est vérifié."
)

report_lines.append("")

report_lines.append(
    "IMPORTANT"
)

report_lines.append(
    "La présence d'un UPF SSSP ne constitue pas encore une validation"
)

report_lines.append(
    "de convergence DFT. Les cutoffs SSSP devront être récupérés et"
)

report_lines.append(
    "audités avant la génération des inputs QE de production."
)

REPORT_TXT.write_text(
    "\n".join(report_lines) + "\n",
    encoding="utf-8",
)


# ============================================================================
# 15. RESUME TERMINAL
# ============================================================================

log()
log("=" * 78)
log("SUMMARY")
log("=" * 78)

for row in final_rows:

    print(
        f"{row['element']:<3} : "
        f"{row['status']:<16} "
        f"{row['file'] or '-'}"
    )

log()
log(
    f"FOUND : {found_count}/{EXPECTED_COUNT}"
)

log(
    f"PASS  : {pass_count}/{EXPECTED_COUNT}"
)

if missing_elements:

    log(
        "[ACTION] Éléments manquants : "
        + ", ".join(missing_elements)
    )

if warning_elements:

    log(
        "[ACTION] Métadonnées à contrôler : "
        + ", ".join(warning_elements)
    )

log()
log(
    f"[REPORT CSV] {REPORT_CSV}"
)

log(
    f"[REPORT TXT] {REPORT_TXT}"
)

log(
    f"[SELECTED]   {SELECTED_MANIFEST}"
)

log(
    f"[SSSP ROOT]  {SSSP_ROOT}"
)

log()
log("=" * 78)

if pass_count == EXPECTED_COUNT:

    log(
        "RESULT : PASS — jeu SSSP complet pour les 10 éléments"
    )

    log(
        "NEXT : audit des cutoffs SSSP puis préparation QE."
    )

else:

    log(
        "RESULT : INCOMPLETE — ne pas lancer les benchmarks QE."
    )

log("=" * 78)

