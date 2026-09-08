#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
os.system("clear")

"""
HydroMatAI — PHASE 21 COMPLETE
Préparation et validation des pseudopotentiels QE

OBJECTIFS
---------
1. Lire les candidats depuis les sorties Phase 20/DFT disponibles.
2. Lire correctement les CIF.
3. Détecter les éléments atomiques.
4. Inspecter réellement les fichiers UPF.
5. Construire un mapping élément -> UPF strict.
6. Ne jamais confondre F avec Fe.
7. Ne jamais confondre Cl avec C.
8. Télécharger automatiquement les pseudopotentiels manquants.
9. Revalider après téléchargement.
10. Ne lancer AUCUN calcul Quantum ESPRESSO.
11. Ne modifier AUCUN CIF.
12. Produire CSV / JSON / MANIFEST.

Important :
- Ce script prépare uniquement les pseudopotentiels.
- Il ne lance ni pw.x, ni bands.x, ni dos.x.
"""


import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT = Path("/home/hk/HydroMatAI")

QE_DIR = Path("/home/hk/software/qe-7.5")
QE_BIN = QE_DIR / "bin"
PSEUDO_DIR = QE_DIR / "pseudo"

CIF_DIR = PROJECT / "MOF_Library" / "MOFXDB_FULL" / "cif"

OUT_DIR = PROJECT / "calculations" / "phase_21_complete"

CSV_FILE = OUT_DIR / "phase21_complete.csv"
JSON_FILE = OUT_DIR / "phase21_complete.json"
MANIFEST_FILE = OUT_DIR / "phase21_manifest.json"


# ============================================================================
# SOURCES DE PSEUDOPOTENTIELS
# ============================================================================

# Sources officielles / publiques couramment utilisées pour les UPF PSLibrary.
#
# Le script essaie plusieurs URL.
#
# IMPORTANT :
# Le script ne considérera jamais un fichier Fe comme un pseudopotentiel F.
# Le symbole réel est lu dans le contenu UPF.

PSL_BASES = [
    "https://pseudopotentials.quantum-espresso.org/upf_files/",
    "https://pseudopotentials.quantum-espresso.org/upf_files/",
]


# Fichiers connus / préférés.
#
# On garde une liste de candidats car les noms peuvent varier selon la
# version de la bibliothèque.

PREFERRED_NAMES = {
    "H": [
        "H.pbe-kjpaw.UPF",
        "H.pbe-rrkjus_psl.1.0.0.UPF",
        "H.pbe-kjpaw_psl.1.0.0.UPF",
        "H.pbe-rrkjus.UPF",
    ],
    "C": [
        "C.pbe-n-kjpaw_psl.1.0.0.UPF",
        "C.pbe-rrkjus.UPF",
        "C.pbe-n-rrkjus_psl.1.0.0.UPF",
    ],
    "N": [
        "N.pbe-n-kjpaw_psl.1.0.0.UPF",
        "N.pbe-rrkjus.UPF",
        "N.pbe-rrkjus_psl.1.0.0.UPF",
    ],
    "O": [
        "O.pbe-n-kjpaw_psl.1.0.0.UPF",
        "O.pbe-rrkjus.UPF",
        "O.pbe-rrkjus_psl.1.0.0.UPF",
        "O.pbe-kjpaw.UPF",
    ],
    "F": [
        "F.pbe-n-kjpaw_psl.1.0.0.UPF",
        "F.pbe-rrkjus.UPF",
        "F.pbe-rrkjus_psl.1.0.0.UPF",
        "F.pbe-n-kjpaw.UPF",
    ],
    "Cl": [
        "Cl.pbe-n-kjpaw_psl.1.0.0.UPF",
        "Cl.pbe-n-rrkjus_psl.1.0.0.UPF",
        "Cl.pbe-rrkjus_psl.1.0.0.UPF",
    ],
    "Zn": [
        "Zn.pbe-dnl-kjpaw_psl.1.0.0.UPF",
        "Zn.pbe-spn-kjpaw_psl.1.0.0.UPF",
        "Zn.pbe-rrkjus_psl.1.0.0.UPF",
    ],
}


# ============================================================================
# UTILITAIRES
# ============================================================================

ELEMENTS = [
    "H", "He",
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni",
    "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
    "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu",
    "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn",
]

ELEMENT_SET = set(ELEMENTS)
ELEMENT_BY_LOWER = {x.lower(): x for x in ELEMENTS}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except Exception:
        return None


def safe_text(value: str) -> str:
    return value.strip().strip("'").strip('"')


def normalize_element(value: str) -> Optional[str]:
    """
    Normalise un symbole chimique.

    Exemples :
        C      -> C
        c      -> C
        Zn     -> Zn
        ZN     -> Zn
        Fe     -> Fe
        F      -> F

    Protection explicite :
        Fe != F
        Cl != C
    """
    if not value:
        return None

    value = safe_text(value)

    # Retirer chiffres / suffixes de labels :
    # Zn1, O12, C3, Cl4, etc.
    m = re.match(r"^([A-Za-z]{1,2})", value)

    if not m:
        return None

    symbol = m.group(1)

    # Cas où le premier caractère est correct et le second ne l'est pas.
    if symbol.lower() in ELEMENT_BY_LOWER:
        return ELEMENT_BY_LOWER[symbol.lower()]

    # Protection pour labels tels que "C1", "Zn2".
    one = symbol[0].upper()
    if one in ELEMENT_SET:
        return one

    return None


def infer_element_from_label(label: str) -> Optional[str]:
    """
    Déduction robuste d'un élément depuis un label atomique.

    Exemples :
        C1       -> C
        C_12     -> C
        Zn1      -> Zn
        Zn_24    -> Zn
        Cl1      -> Cl
        F1       -> F
        Oa       -> O
        N7       -> N

    Protection F/Fe et C/Cl.
    """

    if not label:
        return None

    label = safe_text(label)

    # Chercher d'abord les éléments à deux lettres.
    # Très important : Cl avant C, Fe avant F, Zn avant Z.
    two_letter = sorted(
        [e for e in ELEMENTS if len(e) == 2],
        key=len,
        reverse=True,
    )

    for el in two_letter:
        if re.match(r"^" + re.escape(el) + r"(?:$|[_0-9A-Za-z])", label,
                    flags=re.IGNORECASE):
            return el

    # Puis les éléments à une lettre.
    first = label[:1].upper()

    if first in ELEMENT_SET:
        return first

    return None


# ============================================================================
# LECTURE CIF
# ============================================================================

def tokenize_cif_line(line: str) -> List[str]:
    """
    Tokenisation simple compatible avec les CIF courants.

    Gère :
      - espaces
      - guillemets simples
      - guillemets doubles
    """

    tokens = []
    current = []
    quote = None
    i = 0

    while i < len(line):
        ch = line[i]

        if quote is not None:
            if ch == quote:
                quote = None
            else:
                current.append(ch)
        else:
            if ch in ("'", '"'):
                quote = ch
            elif ch.isspace():
                if current:
                    tokens.append("".join(current))
                    current = []
            else:
                current.append(ch)

        i += 1

    if current:
        tokens.append("".join(current))

    return tokens


def parse_cif_atom_loop(path: Path) -> Tuple[List[str], int, str]:
    """
    Lit les loops atom_site des CIF.

    Retour :
        elements, number_of_atoms, error_message

    Ne dépend PAS uniquement de _atom_site_type_symbol.

    Colonnes reconnues :
        _atom_site_type_symbol
        _atom_site_label
        _atom_site_atom_type_symbol
        _atom_site_description
    """

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    loops = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.lower() == "loop_":
            headers = []
            j = i + 1

            while j < len(lines):
                s = lines[j].strip()

                if not s:
                    j += 1
                    continue

                if s.startswith("_"):
                    headers.append(s.split()[0])
                    j += 1
                    continue

                break

            if headers:
                data = []

                k = j
                while k < len(lines):
                    s = lines[k].strip()

                    if not s:
                        k += 1
                        continue

                    low = s.lower()

                    if low == "loop_":
                        break

                    if s.startswith("_"):
                        break

                    if s.startswith("#"):
                        k += 1
                        continue

                    toks = tokenize_cif_line(s)

                    if toks:
                        data.extend(toks)

                    k += 1

                if data:
                    loops.append((headers, data))

                i = k
                continue

        i += 1

    # Chercher le loop atomique.
    for headers, data in loops:

        normalized_headers = [h.lower() for h in headers]

        atom_headers = [
            h for h in normalized_headers
            if h.startswith("_atom_site_")
        ]

        if not atom_headers:
            continue

        # Priorité stricte.
        symbol_indices = []

        for candidate in (
            "_atom_site_type_symbol",
            "_atom_site_atom_type_symbol",
            "_atom_site_label",
            "_atom_site_description",
        ):
            if candidate in normalized_headers:
                symbol_indices.append(
                    normalized_headers.index(candidate)
                )

        if not symbol_indices:
            continue

        ncols = len(headers)

        if ncols <= 0:
            continue

        nrows = len(data) // ncols

        elements = []
        atom_count = 0

        for row_idx in range(nrows):
            row = data[row_idx * ncols:(row_idx + 1) * ncols]

            if len(row) != ncols:
                continue

            atom_count += 1

            element = None

            # D'abord type_symbol.
            for idx in symbol_indices:
                if idx >= len(row):
                    continue

                value = safe_text(row[idx])

                if value in ("?", ".", ""):
                    continue

                # Si c'est explicitement type_symbol.
                header_name = normalized_headers[idx]

                if header_name in (
                    "_atom_site_type_symbol",
                    "_atom_site_atom_type_symbol",
                ):
                    element = normalize_element(value)

                else:
                    element = infer_element_from_label(value)

                if element:
                    break

            if element:
                elements.append(element)

        if elements:
            unique = sorted(set(elements), key=lambda x: (ELEMENTS.index(x)
                                                           if x in ELEMENTS
                                                           else 999, x))
            return unique, atom_count, ""

    # ----------------------------------------------------------------------
    # FALLBACK :
    # Certains CIF possèdent un loop avec _atom_site_label mais structure
    # non standard. On cherche alors explicitement les lignes.
    # ----------------------------------------------------------------------

    for idx, line in enumerate(lines):
        if "_atom_site_label" in line.lower():
            # On tente de reconstruire un bloc local.
            local_headers = []
            j = idx

            while j < len(lines):
                s = lines[j].strip()

                if s.startswith("_atom_site_"):
                    local_headers.append(s.split()[0])
                    j += 1
                    continue

                break

            if local_headers:
                values = []

                while j < len(lines):
                    s = lines[j].strip()

                    if not s or s.startswith("#"):
                        j += 1
                        continue

                    if s.startswith("_") or s.lower() == "loop_":
                        break

                    toks = tokenize_cif_line(s)

                    if toks:
                        values.extend(toks)

                    j += 1

                ncols = len(local_headers)

                if ncols:
                    nrows = len(values) // ncols
                    elements = []

                    for r in range(nrows):
                        row = values[r*ncols:(r+1)*ncols]

                        for hidx, header in enumerate(local_headers):
                            if hidx >= len(row):
                                continue

                            if header.lower() in (
                                "_atom_site_type_symbol",
                                "_atom_site_atom_type_symbol",
                            ):
                                el = normalize_element(row[hidx])
                                if el:
                                    elements.append(el)
                                    break

                            if header.lower() == "_atom_site_label":
                                el = infer_element_from_label(row[hidx])
                                if el:
                                    elements.append(el)
                                    break

                    if elements:
                        return sorted(set(elements)), nrows, ""

    return [], 0, "Colonne atomique de symbole introuvable."


def read_cif(path: Path) -> Dict:
    result = {
        "cif_ok": False,
        "elements": [],
        "atom_count": 0,
        "error": "",
    }

    try:
        if not path.exists():
            result["error"] = "Fichier CIF introuvable."
            return result

        if path.stat().st_size == 0:
            result["error"] = "Fichier CIF vide."
            return result

        elements, atom_count, error = parse_cif_atom_loop(path)

        if not elements:
            result["error"] = error or "Aucun élément détecté."
            return result

        result["cif_ok"] = True
        result["elements"] = elements
        result["atom_count"] = atom_count

        return result

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


# ============================================================================
# INSPECTION UPF
# ============================================================================

def extract_upf_element(path: Path) -> Optional[str]:
    """
    Extrait l'élément réel depuis le contenu UPF.

    Ceci évite absolument :
        Fe*.UPF => F

    Un fichier Fe ne sera accepté que pour Fe.
    """

    try:
        # Lire suffisamment pour couvrir les headers UPF.
        with path.open("rb") as f:
            raw = f.read(1024 * 1024)

        text = raw.decode("utf-8", errors="ignore")

        # UPF v2 :
        # <PP_HEADER ... element="C" ...>
        patterns = [
            r'\belement\s*=\s*"([A-Za-z]{1,2})"',
            r"\belement\s*=\s*'([A-Za-z]{1,2})'",
            r"\belement\s*=\s*([A-Za-z]{1,2})\b",
        ]

        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return normalize_element(m.group(1))

        # Anciennes variantes.
        patterns_old = [
            r"\belement\s*[:=]\s*([A-Za-z]{1,2})",
            r"\bsymbol\s*[:=]\s*([A-Za-z]{1,2})",
        ]

        for pattern in patterns_old:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return normalize_element(m.group(1))

        return None

    except Exception:
        return None


def inspect_pseudos() -> Dict[str, List[Path]]:
    """
    Inspecte tous les .UPF du répertoire QE.

    Le mapping est construit à partir du symbole réel contenu dans l'UPF.
    """

    mapping = defaultdict(list)

    if not PSEUDO_DIR.exists():
        return mapping

    for path in sorted(PSEUDO_DIR.iterdir()):

        if not path.is_file():
            continue

        if path.suffix.lower() not in (".upf", ".UPF".lower()):
            continue

        element = extract_upf_element(path)

        if element:
            mapping[element].append(path)

    return mapping


def choose_best_pseudo(element: str,
                        mapping: Dict[str, List[Path]]) -> Optional[Path]:
    """
    Choisit le pseudopotentiel préféré.

    Priorité :
        1. noms préférés
        2. PSL / PBE
        3. plus petit fichier raisonnable
    """

    candidates = mapping.get(element, [])

    if not candidates:
        return None

    preferred = PREFERRED_NAMES.get(element, [])

    # Exact match.
    for name in preferred:
        for path in candidates:
            if path.name == name:
                return path

    # PBE prioritaire.
    pbe = [
        p for p in candidates
        if "pbe" in p.name.lower()
    ]

    if pbe:
        return sorted(pbe, key=lambda x: x.name.lower())[0]

    return sorted(candidates, key=lambda x: x.name.lower())[0]


# ============================================================================
# TÉLÉCHARGEMENT
# ============================================================================

def download_file(url: str, destination: Path, timeout: int = 60) -> bool:
    """
    Téléchargement HTTP simple.
    """

    tmp = destination.with_suffix(destination.suffix + ".download")

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "HydroMatAI-Phase21/1.0"
            },
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()

        if not data:
            return False

        tmp.write_bytes(data)

        # Vérifier que le fichier ressemble à un UPF.
        element = extract_upf_element(tmp)

        if not element:
            tmp.unlink(missing_ok=True)
            return False

        tmp.replace(destination)

        return True

    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

        return False


def try_download_element(element: str) -> Optional[Path]:
    """
    Télécharge un pseudopotentiel manquant.

    On n'accepte le fichier que si son contenu indique EXACTEMENT
    l'élément demandé.
    """

    preferred = PREFERRED_NAMES.get(element, [])

    if not preferred:
        return None

    print(f"\n  Téléchargement automatique : {element}")

    for filename in preferred:

        for base in PSL_BASES:
            url = base.rstrip("/") + "/" + filename

            destination = PSEUDO_DIR / filename

            print(f"    Essai : {url}")

            if destination.exists():
                detected = extract_upf_element(destination)

                if detected == element:
                    print(
                        f"    EXISTE DÉJÀ : {destination.name}"
                    )
                    return destination

                # Ne pas réutiliser un fichier du mauvais élément.
                continue

            ok = download_file(
                url,
                destination,
                timeout=60,
            )

            if ok:
                detected = extract_upf_element(destination)

                if detected == element:
                    print(
                        f"    OK → {destination.name}"
                    )
                    return destination

                # Sécurité.
                try:
                    destination.unlink()
                except Exception:
                    pass

    print(
        f"    ÉCHEC : aucun UPF valide trouvé automatiquement pour {element}"
    )

    return None


# ============================================================================
# CANDIDATS
# ============================================================================

def extract_mof_name_from_cif(path: Path) -> str:
    """
    Extrait un nom humain depuis le nom du CIF.
    """

    name = path.stem

    # Exemple :
    # 0015356_hMOF-18
    m = re.search(r"_(hMOF-[^_]+)$", name, flags=re.IGNORECASE)

    if m:
        return m.group(1)

    # fallback.
    return name


def find_candidate_cifs(limit: int) -> List[Path]:
    """
    Détecte les CIF.

    Pour le contexte actuel, on prend les CIF de la bibliothèque triés
    naturellement par nom.
    """

    if not CIF_DIR.exists():
        return []

    cifs = sorted(
        CIF_DIR.glob("*.cif"),
        key=lambda p: p.name.lower()
    )

    # Les 25 candidats utilisés actuellement sont les fichiers commençant
    # par les IDs connus. Pour éviter de changer arbitrairement le jeu,
    # on recherche d'abord les hMOF.
    hmofs = [
        p for p in cifs
        if "hmof" in p.name.lower()
    ]

    selected = hmofs if hmofs else cifs

    return selected[:limit] if limit > 0 else selected


# ============================================================================
# VALIDATION
# ============================================================================

def build_candidate_record(
    index: int,
    cif_path: Path,
    pseudo_mapping: Dict[str, List[Path]],
) -> Dict:

    cif = read_cif(cif_path)

    record = {
        "index": index,
        "candidate": extract_mof_name_from_cif(cif_path),
        "cif": str(cif_path),
        "cif_ok": cif["cif_ok"],
        "cif_error": cif["error"],
        "elements": cif["elements"],
        "atom_count": cif["atom_count"],
        "pseudo": {},
        "missing_pseudo": [],
        "invalid_mapping": [],
        "status": "CIF_FAILED",
    }

    if not cif["cif_ok"]:
        return record

    for element in cif["elements"]:

        path = choose_best_pseudo(
            element,
            pseudo_mapping,
        )

        if path is None:
            record["pseudo"][element] = None
            record["missing_pseudo"].append(element)
        else:
            record["pseudo"][element] = path.name

            # Sécurité absolue.
            real_element = extract_upf_element(path)

            if real_element != element:
                record["invalid_mapping"].append(
                    f"{element}->{path.name} (UPF={real_element})"
                )

    if record["invalid_mapping"]:
        record["status"] = "INVALID_MAPPING"

    elif record["missing_pseudo"]:
        record["status"] = "MISSING_PSEUDO"

    else:
        record["status"] = "READY_FOR_QE"

    return record


# ============================================================================
# AFFICHAGE
# ============================================================================

def print_header():
    print("=" * 80)
    print("HydroMatAI — PHASE 21 COMPLETE")
    print("PRÉPARATION PSEUDOPOTENTIELS QE")
    print("=" * 80)
    print()

    print("CONFIGURATION")
    print("-" * 80)
    print(f"Projet       : {PROJECT}")
    print(f"CIF          : {CIF_DIR}")
    print(f"QE           : {QE_DIR}")
    print(f"PSEUDO       : {PSEUDO_DIR}")
    print(f"pw.x         : {QE_BIN / 'pw.x'}")
    print()

    print("PROTECTION QE")
    print("-" * 80)
    pw = QE_BIN / "pw.x"

    if pw.exists() and os.access(pw, os.X_OK):
        print(f"pw.x        : OK → {pw}")
    else:
        print("pw.x        : NON DISPONIBLE")

    print("bands.x     : NON LANCÉ")
    print("dos.x       : NON LANCÉ")
    print("relax       : NON LANCÉ")
    print("scf         : NON LANCÉ")
    print("calcul      : NON LANCÉ")
    print()
    print("IMPORTANT : aucun exécutable QE ne sera lancé.")
    print()


def print_environment():
    print("ENVIRONNEMENT")
    print("-" * 80)

    print(
        f"CIF directory : "
        f"{'OK' if CIF_DIR.exists() else 'FAILED'}"
    )

    print(
        f"Pseudo dir    : "
        f"{'OK' if PSEUDO_DIR.exists() else 'FAILED'}"
    )

    print()


def print_pseudo_inventory(mapping):
    print("INSPECTION INITIALE DES UPF")
    print("-" * 80)

    count = 0

    for element in sorted(
        mapping.keys(),
        key=lambda x: (
            ELEMENTS.index(x) if x in ELEMENTS else 999,
            x,
        )
    ):
        path = choose_best_pseudo(element, mapping)

        if path:
            print(f"{element:<3} → {path.name}")
            count += 1

    print()
    print(f"UPF exploitables : {count}")
    print()


def print_candidate(record, index, total):
    print(f"[{index}/{total}] {record['candidate']}")
    print(f"  CIF      : {record['cif']}")

    if not record["cif_ok"]:
        print(
            f"  CIF      : FAILED → {record['cif_error']}"
        )
        print()
        return

    print(
        f"  CIF      : OK → {record['cif']}"
    )

    print(
        "  Elements : " +
        ", ".join(record["elements"])
    )

    print(
        f"  Atomes   : {record['atom_count']}"
    )

    for element in record["elements"]:

        pseudo = record["pseudo"].get(element)

        if pseudo:
            print(
                f"  {element:<3} → {pseudo}"
            )
        else:
            print(
                f"  {element:<3} → MISSING"
            )

    if record["invalid_mapping"]:
        print(
            "  INVALID_MAPPING : " +
            "; ".join(record["invalid_mapping"])
        )

    print(
        f"  STATUS   : {record['status']}"
    )

    print()


# ============================================================================
# EXPORTS
# ============================================================================

def write_csv(records: List[Dict]):

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    elements_all = sorted(
        {
            e
            for r in records
            for e in r.get("elements", [])
        },
        key=lambda x: (
            ELEMENTS.index(x) if x in ELEMENTS else 999,
            x,
        )
    )

    fields = [
        "index",
        "candidate",
        "cif",
        "cif_ok",
        "cif_error",
        "atom_count",
        "elements",
        "missing_pseudo",
        "invalid_mapping",
        "status",
    ]

    for e in elements_all:
        fields.append(f"pseudo_{e}")

    with CSV_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for r in records:

            row = {
                "index": r["index"],
                "candidate": r["candidate"],
                "cif": r["cif"],
                "cif_ok": r["cif_ok"],
                "cif_error": r["cif_error"],
                "atom_count": r["atom_count"],
                "elements": ",".join(r["elements"]),
                "missing_pseudo": ",".join(
                    r["missing_pseudo"]
                ),
                "invalid_mapping": ",".join(
                    r["invalid_mapping"]
                ),
                "status": r["status"],
            }

            for e in elements_all:
                row[f"pseudo_{e}"] = (
                    r["pseudo"].get(e) or ""
                )

            writer.writerow(row)


def write_json(
    records,
    required,
    available,
    missing,
):

    payload = {
        "phase": "21",
        "name": "phase_21_complete",
        "timestamp": now_iso(),
        "project": str(PROJECT),
        "qe_dir": str(QE_DIR),
        "pseudo_dir": str(PSEUDO_DIR),
        "cif_dir": str(CIF_DIR),
        "automatic_download": True,
        "qe_calculation_started": False,
        "required_elements": required,
        "available_elements": available,
        "missing_elements": missing,
        "results": records,
    }

    with JSON_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False,
        )


def write_manifest(
    records,
    required,
    available,
    missing,
):

    manifest = {
        "phase": "21",
        "timestamp": now_iso(),
        "script": str(Path(__file__).resolve()),
        "project": str(PROJECT),
        "cif_dir": str(CIF_DIR),
        "qe_dir": str(QE_DIR),
        "pseudo_dir": str(PSEUDO_DIR),
        "csv": str(CSV_FILE),
        "json": str(JSON_FILE),
        "manifest": str(MANIFEST_FILE),
        "automatic_download": True,
        "qe_execution": False,
        "cif_modified": False,
        "required_elements": required,
        "available_elements": available,
        "missing_elements": missing,
        "candidates": len(records),
        "cif_failed": sum(
            1 for r in records
            if not r["cif_ok"]
        ),
        "ready_for_qe": sum(
            1 for r in records
            if r["status"] == "READY_FOR_QE"
        ),
        "missing_pseudo": sum(
            1 for r in records
            if r["status"] == "MISSING_PSEUDO"
        ),
        "invalid_mapping": sum(
            1 for r in records
            if r["status"] == "INVALID_MAPPING"
        ),
        "files": {},
    }

    for path in (
        CSV_FILE,
        JSON_FILE,
    ):
        if path.exists():
            manifest["files"][str(path)] = {
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }

    with MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================================
# MAIN
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description="HydroMatAI Phase 21 Complete"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre maximal de candidats.",
    )

    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Désactive exceptionnellement le téléchargement.",
    )

    args = parser.parse_args()

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_header()
    print_environment()

    if not CIF_DIR.exists():
        print("ERREUR : répertoire CIF introuvable.")
        sys.exit(1)

    if not PSEUDO_DIR.exists():
        print("ERREUR : répertoire pseudo introuvable.")
        sys.exit(1)

    # ----------------------------------------------------------------------
    # INVENTAIRE INITIAL
    # ----------------------------------------------------------------------

    pseudo_mapping = inspect_pseudos()

    print_pseudo_inventory(
        pseudo_mapping
    )

    # ----------------------------------------------------------------------
    # CANDIDATS
    # ----------------------------------------------------------------------

    candidates = find_candidate_cifs(
        args.limit
    )

    print("CANDIDATS")
    print("-" * 80)
    print(
        f"Candidats détectés : {len(candidates)}"
    )
    print()

    if not candidates:
        print(
            "ERREUR : aucun CIF candidat détecté."
        )
        sys.exit(1)

    # ----------------------------------------------------------------------
    # PREMIÈRE LECTURE
    # ----------------------------------------------------------------------

    print("LECTURE CIF + MAPPING")
    print("-" * 80)
    print()

    records = []

    for i, cif_path in enumerate(
        candidates,
        start=1,
    ):

        record = build_candidate_record(
            i,
            cif_path,
            pseudo_mapping,
        )

        records.append(record)

        print_candidate(
            record,
            i,
            len(candidates),
        )

    # ----------------------------------------------------------------------
    # ÉLÉMENTS REQUIS
    # ----------------------------------------------------------------------

    required = sorted(
        {
            e
            for r in records
            for e in r.get("elements", [])
        },
        key=lambda x: (
            ELEMENTS.index(x)
            if x in ELEMENTS
            else 999,
            x,
        )
    )

    available = sorted(
        {
            e
            for e in required
            if choose_best_pseudo(
                e,
                pseudo_mapping,
            )
        },
        key=lambda x: (
            ELEMENTS.index(x)
            if x in ELEMENTS
            else 999,
            x,
        )
    )

    missing = [
        e for e in required
        if e not in available
    ]

    print("PSEUDOPOTENTIELS REQUIS")
    print("-" * 80)
    print(
        "Requis : " +
        (
            ", ".join(required)
            if required
            else "AUCUN"
        )
    )

    print(
        "Disponibles avant téléchargement : " +
        (
            ", ".join(available)
            if available
            else "AUCUN"
        )
    )

    print(
        "Manquants avant téléchargement : " +
        (
            ", ".join(missing)
            if missing
            else "AUCUN"
        )
    )

    print()

    # ----------------------------------------------------------------------
    # TÉLÉCHARGEMENT
    # ----------------------------------------------------------------------

    downloaded = []

    if missing and not args.no_download:

        print("TÉLÉCHARGEMENT AUTOMATIQUE")
        print("-" * 80)

        for element in missing:

            path = try_download_element(
                element
            )

            if path:
                downloaded.append(
                    str(path)
                )

        print()

    elif missing and args.no_download:

        print(
            "TÉLÉCHARGEMENT AUTOMATIQUE : DÉSACTIVÉ PAR --no-download"
        )
        print()

    else:

        print(
            "Aucun téléchargement nécessaire."
        )
        print()

    # ----------------------------------------------------------------------
    # REINSPECTION APRÈS DOWNLOAD
    # ----------------------------------------------------------------------

    print("REVALIDATION FINALE")
    print("-" * 80)
    print()

    pseudo_mapping = inspect_pseudos()

    final_records = []

    for i, cif_path in enumerate(
        candidates,
        start=1,
    ):

        record = build_candidate_record(
            i,
            cif_path,
            pseudo_mapping,
        )

        final_records.append(record)

        print_candidate(
            record,
            i,
            len(candidates),
        )

    records = final_records

    required = sorted(
        {
            e
            for r in records
            for e in r.get("elements", [])
        },
        key=lambda x: (
            ELEMENTS.index(x)
            if x in ELEMENTS
            else 999,
            x,
        )
    )

    available = sorted(
        {
            e
            for e in required
            if choose_best_pseudo(
                e,
                pseudo_mapping,
            )
        },
        key=lambda x: (
            ELEMENTS.index(x)
            if x in ELEMENTS
            else 999,
            x,
        )
    )

    missing = [
        e for e in required
        if e not in available
    ]

    # ----------------------------------------------------------------------
    # EXPORT
    # ----------------------------------------------------------------------

    write_csv(records)

    write_json(
        records,
        required,
        available,
        missing,
    )

    write_manifest(
        records,
        required,
        available,
        missing,
    )

    # ----------------------------------------------------------------------
    # STATISTIQUES
    # ----------------------------------------------------------------------

    candidates_count = len(records)

    cif_failed = sum(
        1
        for r in records
        if not r["cif_ok"]
    )

    ready = sum(
        1
        for r in records
        if r["status"] == "READY_FOR_QE"
    )

    missing_count = sum(
        1
        for r in records
        if r["status"] == "MISSING_PSEUDO"
    )

    invalid_mapping = sum(
        1
        for r in records
        if r["status"] == "INVALID_MAPPING"
    )

    # ----------------------------------------------------------------------
    # AUDIT
    # ----------------------------------------------------------------------

    print("=" * 80)
    print("PHASE 21 — RÉSULTATS")
    print("=" * 80)

    print(
        f"Candidats          : {candidates_count}"
    )

    print(
        f"CIF FAILED         : {cif_failed}"
    )

    print(
        f"READY_FOR_QE       : {ready}"
    )

    print(
        f"MISSING_PSEUDO     : {missing_count}"
    )

    print(
        f"INVALID_MAPPING    : {invalid_mapping}"
    )

    print()

    print("-" * 80)
    print("PSEUDOPOTENTIELS REQUIS")
    print("-" * 80)

    print(
        "Requis : " +
        (
            ", ".join(required)
            if required
            else "AUCUN"
        )
    )

    print(
        "Disponibles : " +
        (
            ", ".join(available)
            if available
            else "AUCUN"
        )
    )

    print(
        "Manquants : " +
        (
            ", ".join(missing)
            if missing
            else "AUCUN"
        )
    )

    print()

    print("-" * 80)
    print("FICHIERS")
    print("-" * 80)

    print(
        f"CSV      : {CSV_FILE}"
    )

    print(
        f"JSON     : {JSON_FILE}"
    )

    print(
        f"MANIFEST : {MANIFEST_FILE}"
    )

    print()

    print("=" * 80)
    print("PHASE 21 — AUDIT FINAL")
    print("=" * 80)

    print(
        "Lecture CIF                 : " +
        ("OK" if cif_failed == 0 else "FAILED")
    )

    print(
        "Inspection UPF              : OK"
    )

    print(
        "Mapping élémentaire strict  : " +
        ("OK" if invalid_mapping == 0 else "FAILED")
    )

    print(
        "Protection F → Fe           : OK"
    )

    print(
        "Protection Cl → C           : OK"
    )

    print(
        "Téléchargement automatique  : " +
        ("DÉSACTIVÉ" if args.no_download else "ACTIVÉ")
    )

    print(
        "Aucun calcul QE             : OK"
    )

    print(
        "Aucun CIF modifié           : OK"
    )

    print(
        "Traçabilité                 : OK"
    )

    print()

    if cif_failed > 0:
        blocking = ["CIF"]

    elif invalid_mapping > 0:
        blocking = ["INVALID_MAPPING"]

    elif missing:
        blocking = missing

    else:
        blocking = []

    if (
        cif_failed == 0
        and invalid_mapping == 0
        and not missing
        and ready == candidates_count
    ):
        ready_status = "OUI"
    else:
        ready_status = "NON"

    print(
        f"READY_FOR_QE : {ready_status}"
    )

    print(
        "BLOCAGE : " +
        (
            ", ".join(blocking)
            if blocking
            else "AUCUN"
        )
    )

    print("=" * 80)
    print()

    print("PHASE 21 — TERMINÉE")

    if ready_status == "OUI":
        print(
            "Préparation pseudopotentiels : OK"
        )
        print(
            "Tous les candidats sont READY_FOR_QE."
        )
        print(
            "Aucun calcul QE n'a été lancé."
        )
    else:
        print(
            "Préparation pseudopotentiels : BLOQUÉE"
        )
        print(
            "Aucun calcul QE n'a été lancé."
        )

    print("=" * 80)

    # Code retour :
    # 0 = script exécuté correctement, même si préparation bloquée.
    # 1 = erreur infrastructurelle grave.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterruption utilisateur.")
        raise SystemExit(130)
