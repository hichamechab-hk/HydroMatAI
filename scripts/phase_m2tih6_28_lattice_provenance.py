#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import hashlib
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")

TARGETS = {
    "Ba2TiH6": ROOT / "reports/m2tih6_reconstructed/Ba2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
    "Sr2TiH6": ROOT / "reports/m2tih6_reconstructed/Sr2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
}

EXTENSIONS = {
    ".cif", ".txt", ".md", ".csv", ".json", ".yaml", ".yml",
    ".py", ".sh", ".in", ".out", ".log", ".dat"
}

TARGET_PATTERNS = [
    r"Ba2TiH6",
    r"Ba₂TiH₆",
    r"Sr2TiH6",
    r"Sr₂TiH₆",
    r"Ba2.*Ti.*H6",
    r"Sr2.*Ti.*H6",
    r"M2TiH6",
    r"TiH6",
]

LATTICE_PATTERNS = [
    r"_cell_length_a",
    r"_cell_length_b",
    r"_cell_length_c",
    r"\balat\b",
    r"\ba\s*=",
    r"\bb\s*=",
    r"\bc\s*=",
    r"lattice",
    r"lattice_parameter",
    r"lattice parameter",
    r"paramètre de maille",
    r"parameter de maille",
]

DOI_PATTERNS = [
    r"10\.1016/j\.jpcs\.2026\.113778",
    r"113778",
    r"jpcs",
    r"journal of physics and chemistry of solids",
]


def clear_screen():
    """
    Nettoyage robuste du terminal.
    Evite 'unknown terminal type' si TERM est absent/invalide.
    """
    term = os.environ.get("TERM", "")

    known_terms = {
        "xterm", "xterm-256color", "linux", "screen",
        "screen-256color", "tmux", "tmux-256color",
        "vt100", "vt220", "ansi"
    }

    if term in known_terms:
        os.system("clear")
    else:
        print("\033[2J\033[H", end="")


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def read_cif(path):
    text = path.read_text(errors="replace")
    data = {}

    keys = [
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c",
        "_cell_angle_alpha",
        "_cell_angle_beta",
        "_cell_angle_gamma",
        "_symmetry_space_group_name_H_M",
        "_space_group_name_H_M_alt",
        "_symmetry_Int_Tables_number",
        "_space_group_IT_number",
        "_chemical_formula_sum",
    ]

    for key in keys:
        pattern = rf"^{re.escape(key)}\s+(.+?)\s*$"

        match = re.search(
            pattern,
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        if match:
            data[key] = match.group(1).strip().strip("'\"")

    return text, data


def print_header(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def search_repo():
    print_header("1. RECHERCHE CIBLEE DE PROVENANCE DANS LE REPOSITORY")

    hits = []
    skipped = 0

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        parts = set(path.parts)

        if ".git" in parts:
            continue

        if ".venv" in parts:
            continue

        if "__pycache__" in parts:
            continue

        if path.suffix.lower() not in EXTENSIONS:
            continue

        try:
            size = path.stat().st_size

            if size > 10 * 1024 * 1024:
                skipped += 1
                continue

            text = path.read_text(errors="replace")

        except Exception:
            continue

        target_hit = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in TARGET_PATTERNS
        )

        lattice_hit = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in LATTICE_PATTERNS
        )

        doi_hit = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in DOI_PATTERNS
        )

        if not (target_hit and (lattice_hit or doi_hit)):
            continue

        lines = text.splitlines()
        local = []

        for i, line in enumerate(lines, 1):

            target_here = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in TARGET_PATTERNS
            )

            doi_here = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in DOI_PATTERNS
            )

            if target_here or doi_here:

                lo = max(1, i - 2)
                hi = min(len(lines), i + 2)

                local.append(
                    (
                        i,
                        lo,
                        hi,
                        lines[lo - 1:hi]
                    )
                )

        hits.append((path, local))

    if not hits:

        print("[INFO] Aucun document cible contenant simultanément")
        print("       une référence Ba2TiH6/Sr2TiH6/M2TiH6 et une")
        print("       information de maille/provenance n'a été trouvé.")

    else:

        for path, local in hits:

            print()
            print(f"[HIT] {path.relative_to(ROOT)}")

            for i, lo, hi, block in local[:8]:

                print(
                    f"  --- contexte autour de la ligne {i} ---"
                )

                for n, line in enumerate(block, lo):

                    print(
                        f"  {n:6d}: {line[:240]}"
                    )

    if skipped:

        print()
        print(
            f"[INFO] Fichiers >10 MiB ignorés : {skipped}"
        )


def search_exact_lattice_candidates():

    print_header(
        "2. RECHERCHE DES PARAMETRES DE MAILLE EXPLICITES"
    )

    candidates = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        parts = set(path.parts)

        if ".git" in parts:
            continue

        if ".venv" in parts:
            continue

        if "__pycache__" in parts:
            continue

        if path.suffix.lower() not in EXTENSIONS:
            continue

        try:

            if path.stat().st_size > 10 * 1024 * 1024:
                continue

            text = path.read_text(errors="replace")

        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), 1):

            target = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in TARGET_PATTERNS
            )

            lattice = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in LATTICE_PATTERNS
            )

            if target and lattice:

                candidates.append(
                    (
                        path,
                        lineno,
                        line.strip()
                    )
                )

    if not candidates:

        print(
            "[INFO] Aucun paramètre de maille explicitement associé"
        )
        print(
            "       aux composés cibles dans une même ligne."
        )

        return

    for path, lineno, line in candidates[:200]:

        print(
            f"[{path.relative_to(ROOT)}:{lineno}]"
        )

        print(
            f"  {line[:300]}"
        )

    if len(candidates) > 200:

        print(
            f"[INFO] {len(candidates) - 200} occurrences "
            "supplémentaires masquées."
        )


def audit_cif(name, path):

    print_header(
        f"3. AUDIT DIRECT — {name}"
    )

    if not path.exists():

        print(
            f"[ERROR] CIF absent : {path}"
        )

        return

    text, data = read_cif(path)

    print(f"FILE       : {path}")
    print(f"SIZE       : {path.stat().st_size} bytes")
    print(f"SHA256     : {sha256(path)}")
    print()

    print(
        "FORMULE    :",
        data.get(
            "_chemical_formula_sum",
            "NON DECLAREE"
        )
    )

    print(
        "SPACE GROUP:",
        data.get(
            "_symmetry_space_group_name_H_M",
            data.get(
                "_space_group_name_H_M_alt",
                "NON DECLARE"
            )
        )
    )

    print(
        "SG NUMBER  :",
        data.get(
            "_symmetry_Int_Tables_number",
            data.get(
                "_space_group_IT_number",
                "NON DECLARE"
            )
        )
    )

    print()

    for key in [
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c",
        "_cell_angle_alpha",
        "_cell_angle_beta",
        "_cell_angle_gamma",
    ]:

        print(
            f"{key:30s}: {data.get(key, 'NON DECLARE')}"
        )

    vals = []

    for key in [
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c"
    ]:

        try:

            value = re.sub(
                r"\([^)]*\)",
                "",
                data[key]
            )

            vals.append(float(value))

        except Exception:

            vals.append(None)

    if all(value is not None for value in vals):

        a, b, c = vals

        if (
            abs(a - 1.0) < 1e-8
            and abs(b - 1.0) < 1e-8
            and abs(c - 1.0) < 1e-8
        ):

            print()
            print(
                "[CRITICAL] Maille a=b=c=1.000000 Å."
            )

            print(
                "[CRITICAL] Cette valeur est traitée comme PLACEHOLDER."
            )

            print(
                "[CRITICAL] Elle ne constitue PAS un paramètre physique validé."
            )

        elif min(vals) <= 0:

            print()
            print(
                "[ERROR] Paramètre de maille non physique <= 0."
            )

        else:

            print()
            print(
                "[INFO] Une échelle non-unitaire est présente dans le CIF."
            )

            print(
                "[INFO] Cela ne prouve PAS sa provenance bibliographique."
            )


def provenance_classification():

    print_header(
        "4. CLASSIFICATION DE PROVENANCE"
    )

    print("[A] PUBLISHED / DIRECTLY SOURCED")

    print(
        "    Seulement si une source identifiable fournit explicitement"
    )

    print(
        "    la structure et/ou le paramètre de maille correspondant."
    )

    print()

    print("[B] RECONSTRUCTED")

    print(
        "    Structure reconstruite à partir d'un prototype, symétrie"
    )

    print(
        "    ou coordonnées fractionnaires sans source expérimentale directe."
    )

    print()

    print("[C] PLACEHOLDER SCALE")

    print(
        "    a=b=c=1 Å utilisé comme échelle technique/prototype."
    )

    print()

    print("[D] NOT VALIDATED")

    print(
        "    Aucun paramètre physique documenté ne doit être déduit"
    )

    print(
        "    d'une structure placeholder."
    )

    print()

    print(
        "[RULE] Aucune valeur de a ne sera inventée ou extrapolée."
    )

    print(
        "[RULE] Aucun calcul QE ne doit utiliser ces CIFs à ce stade."
    )


def final_status():

    print_header(
        "5. CONCLUSION M2TiH6.28"
    )

    print(
        "[1] Ba2TiH6 et Sr2TiH6 restent RECONSTRUCTED / NOT PUBLISHED."
    )

    print(
        "[2] a=b=c=1 Å est identifié comme échelle placeholder."
    )

    print(
        "[3] La symétrie Pm-3m #221 peut être conservée comme prototype."
    )

    print(
        "[4] Les coordonnées fractionnaires ne doivent pas être converties"
    )

    print(
        "    en structure DFT physique sans paramètre de maille documenté."
    )

    print(
        "[5] Aucune valeur alternative de a n'est inventée."
    )

    print(
        "[6] Aucun fichier scientifique existant n'est modifié."
    )

    print(
        "[7] Aucun pw.x n'est lancé."
    )

    print()

    print(
        "PROCHAINE ETAPE :"
    )

    print(
        "  établir une provenance bibliographique/cristallographique"
    )

    print(
        "  du paramètre de maille de Ba2TiH6 et/ou Sr2TiH6,"
    )

    print(
        "  ou démontrer explicitement qu'aucune valeur publiée"
    )

    print(
        "  n'est disponible."
    )


def main():

    clear_screen()

    print("=" * 78)
    print(
        "M2TiH6.28 — AUDIT DE PROVENANCE DU PARAMETRE DE MAILLE"
    )
    print("=" * 78)

    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun fichier scientifique modifié")
    print("[INFO] Aucun CIF généré")
    print("[INFO] Aucune valeur de maille inventée")

    for name, path in TARGETS.items():

        audit_cif(
            name,
            path
        )

    search_repo()

    search_exact_lattice_candidates()

    provenance_classification()

    final_status()


if __name__ == "__main__":
    main()
