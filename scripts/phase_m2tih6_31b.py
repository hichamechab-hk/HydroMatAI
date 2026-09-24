#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

print("=" * 78)
print("M2TiH6.31B — RECHERCHE DU TABLEAU 1 / PARAMETRES PUBLIES")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun calcul QE")
print("[INFO] Aucun fichier modifié")
print()

# ----------------------------------------------------------------------
# 1. INVENTAIRE DES DOCUMENTS POTENTIELS
# ----------------------------------------------------------------------

print("===== 1. DOCUMENTS POTENTIELLEMENT PERTINENTS =====")
print()

extensions = {
    ".pdf",
    ".txt",
    ".html",
    ".htm",
    ".csv",
    ".cif",
}

keywords = [
    "113778",
    "karafi",
    "Ba2TiH6",
    "Sr2TiH6",
    "M2TiH6",
    "Table 1",
    "Table 1.",
    "Table I",
]

files = []

for p in BASE.rglob("*"):
    if not p.is_file():
        continue

    if p.suffix.lower() not in extensions:
        continue

    name = p.name.lower()

    if any(k.lower() in name for k in keywords):
        files.append(p)

files = sorted(set(files))

if not files:
    print("[INFO] Aucun document pertinent trouvé par son nom.")
else:
    for p in files:
        print(f"[FOUND] {p}")

print()

# ----------------------------------------------------------------------
# 2. RECHERCHE TEXTUELLE
# ----------------------------------------------------------------------

print("===== 2. RECHERCHE TEXTUELLE DES PARAMETRES =====")
print()

patterns = [
    r"Ba2TiH6",
    r"Sr2TiH6",
    r"113778",
    r"Table\s*1",
    r"Table\s*I",
    r"lattice\s+parameter",
    r"lattice\s+constant",
    r"cell\s+parameter",
    r"space\s+group",
    r"Pm-?3m",
    r"Pm\s*-?\s*3\s*m",
]

text_files = []

for p in BASE.rglob("*"):
    if not p.is_file():
        continue

    if p.suffix.lower() not in {".txt", ".html", ".htm", ".csv", ".cif"}:
        continue

    text_files.append(p)

matches = 0

for p in sorted(set(text_files)):
    try:
        txt = p.read_text(errors="ignore")
    except Exception:
        continue

    low = txt.lower()

    local_hits = []

    for pattern in patterns:
        try:
            if re.search(pattern, txt, re.IGNORECASE):
                local_hits.append(pattern)
        except re.error:
            pass

    if local_hits:
        matches += 1
        print(f"[MATCH] {p}")
        print("        " + ", ".join(local_hits))

print()

# ----------------------------------------------------------------------
# 3. EXTRACTION DE VALEURS DE MAILLE SI PRESENTES
# ----------------------------------------------------------------------

print("===== 3. VALEURS DE MAILLE DETECTEES =====")
print()

lattice_patterns = [
    r"(?:a|lattice\s+parameter)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:Å|A|angstrom)?",
    r"a\s*=\s*([0-9]+(?:\.[0-9]+)?)",
    r"lattice\s+constant\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
]

found_values = []

for p in sorted(set(text_files)):
    try:
        txt = p.read_text(errors="ignore")
    except Exception:
        continue

    for pattern in lattice_patterns:
        for m in re.finditer(pattern, txt, re.IGNORECASE):
            value = m.group(1)

            # éliminer les valeurs manifestement non pertinentes
            try:
                x = float(value)
            except ValueError:
                continue

            if 2.0 <= x <= 20.0:
                found_values.append((p, value, m.group(0)))

for p, value, expression in found_values:
    print(f"[CELL] {p}")
    print(f"       {expression}")
    print(f"       a_candidate = {value} A")
    print()

if not found_values:
    print("[INFO] Aucune valeur de maille exploitable trouvée localement.")

print()

# ----------------------------------------------------------------------
# 4. CONTROLE DES RECONSTRUCTIONS
# ----------------------------------------------------------------------

print("===== 4. CONTROLE DES CIF RECONSTRUITS =====")
print()

reconstructed = [
    BASE / "reports/m2tih6_reconstructed/Ba2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
    BASE / "reports/m2tih6_reconstructed/Sr2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
]

for cif in reconstructed:
    print(f"[CHECK] {cif}")

    if not cif.exists():
        print("        [MISSING]")
        continue

    txt = cif.read_text(errors="ignore")

    for key in [
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c",
        "_cell_angle_alpha",
        "_cell_angle_beta",
        "_cell_angle_gamma",
        "_symmetry_space_group_name_h-m",
    ]:
        m = re.search(
            rf"^{re.escape(key)}\s+(.+)$",
            txt,
            re.MULTILINE | re.IGNORECASE,
        )

        if m:
            print(f"        {key} = {m.group(1).strip()}")

    print()

# ----------------------------------------------------------------------
# 5. DECISION
# ----------------------------------------------------------------------

print("===== 5. DECISION M2TiH6.31B =====")
print()

if found_values:
    print("[INFO] Des valeurs candidates ont été trouvées.")
    print("[NEXT] Elles doivent être vérifiées contre le Tableau 1.")
else:
    print("[BLOCK] Aucun paramètre publié numériquement disponible localement.")
    print("[NEXT] Fournir le PDF/article avec le Tableau 1 pour extraction exacte.")

print()
print("[SAFETY] Aucun pw.x lancé.")
print("[SAFETY] Aucun CIF modifié.")
print("[SAFETY] Les structures a=b=c=1 A restent INVALIDES pour le DFT.")

print()
print("=" * 78)
print("M2TiH6.31B — FIN")
print("=" * 78)
