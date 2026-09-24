import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.40 — EXACT DOS COLUMN / SPIN AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")

DOS = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed.dos"
)

NSCF = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_nscf.out"
)

EF = 12.9573

if not DOS.exists():
    raise SystemExit(f"[ERROR] DOS absent : {DOS}")

text = DOS.read_text(errors="replace")
lines = text.splitlines()

# ----------------------------------------------------------------------
# 1. HEADER EXACT
# ----------------------------------------------------------------------

print("1. HEADER DU FICHIER DOS")
print("-" * 78)

for i, line in enumerate(lines[:20], start=1):
    print(f"{i:4d}: {line}")

# ----------------------------------------------------------------------
# 2. ANALYSE DES LIGNES DE HEADER
# ----------------------------------------------------------------------

print()
print("2. INTERPRÉTATION DU HEADER")
print("-" * 78)

headers = [
    (i + 1, line)
    for i, line in enumerate(lines[:20])
    if line.lstrip().startswith("#")
]

if headers:
    print(f"Lignes header détectées : {len(headers)}")
    for lineno, line in headers:
        print(f"ligne {lineno}: {line}")
else:
    print("[WARN] Aucun header '#' détecté")

# ----------------------------------------------------------------------
# 3. INVENTAIRE DU NOMBRE DE COLONNES
# ----------------------------------------------------------------------

print()
print("3. STRUCTURE DES DONNÉES")
print("-" * 78)

numeric_rows = []

for lineno, line in enumerate(lines, start=1):

    stripped = line.strip()

    if not stripped or stripped.startswith("#"):
        continue

    tokens = stripped.split()

    try:
        vals = [float(x) for x in tokens]
    except ValueError:
        continue

    if vals:
        numeric_rows.append((lineno, vals))

if not numeric_rows:
    raise SystemExit("[ERROR] Aucune ligne numérique")

column_counts = sorted(set(len(v) for _, v in numeric_rows))

print(f"Lignes numériques : {len(numeric_rows)}")
print(f"Nombres de colonnes observés : {column_counts}")

for lineno, vals in numeric_rows[:3]:
    print(f"ligne {lineno}: {len(vals)} colonnes")
    print(vals)

# ----------------------------------------------------------------------
# 4. POINT DOS LE PLUS PROCHE DE EF
# ----------------------------------------------------------------------

print()
print("4. LIGNE DOS LA PLUS PROCHE DE EF")
print("-" * 78)

nearest_lineno, nearest = min(
    numeric_rows,
    key=lambda x: abs(x[1][0] - EF)
)

print(f"EF = {EF:.6f} eV")
print(f"Ligne = {nearest_lineno}")
print(f"E = {nearest[0]:.6f} eV")
print(f"Nombre de colonnes = {len(nearest)}")

for i, value in enumerate(nearest, start=1):
    print(f"colonne {i:2d} : {value:.9f}")

# ----------------------------------------------------------------------
# 5. TEST DOS UP + DOS DOWN
# ----------------------------------------------------------------------

print()
print("5. TEST DOS UP + DOS DOWN")
print("-" * 78)

if len(nearest) >= 3:

    e = nearest[0]
    c2 = nearest[1]
    c3 = nearest[2]

    print(f"E             = {e:.6f}")
    print(f"colonne 2     = {c2:.6f}")
    print(f"colonne 3     = {c3:.6f}")
    print(f"col2 + col3   = {c2 + c3:.6f}")

    if len(nearest) >= 4:
        print(f"colonne 4     = {nearest[3]:.6f}")

    if abs((c2 + c3) - nearest[3]) < 1e-6:
        print("[OK] Colonne 4 = somme colonne 2 + colonne 3")
    else:
        print(
            "[INFO] Colonne 4 != somme des deux premières DOS spin."
        )
        print(
            "[IMPORTANT] La colonne 4 ne doit pas être appelée "
            "automatiquement DOS totale."
        )

# ----------------------------------------------------------------------
# 6. ANALYSE DES VARIATIONS DES COLONNES
# ----------------------------------------------------------------------

print()
print("6. COMPORTEMENT DES COLONNES")
print("-" * 78)

ncols = max(column_counts)

for col in range(ncols):

    vals = [
        row[col]
        for _, row in numeric_rows
        if len(row) > col
    ]

    if not vals:
        continue

    print(
        f"colonne {col+1:2d} : "
        f"min={min(vals):.6f} "
        f"max={max(vals):.6f} "
        f"moy={sum(vals)/len(vals):.6f}"
    )

# ----------------------------------------------------------------------
# 7. EF NSCF
# ----------------------------------------------------------------------

print()
print("7. FERMI ENERGY NSCF")
print("-" * 78)

if NSCF.exists():

    nscf_text = NSCF.read_text(errors="replace")

    fermi = []

    for line in nscf_text.splitlines():

        m = re.search(
            r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
            line,
            re.IGNORECASE,
        )

        if m:
            fermi.append(float(m.group(1)))

    if fermi:
        print(f"EF NSCF : {fermi[-1]:.6f} eV")
        print(f"EF audit: {EF:.6f} eV")
        print(f"Écart   : {fermi[-1] - EF:+.6e} eV")

# ----------------------------------------------------------------------
# 8. VOISINAGE EXACT DE EF
# ----------------------------------------------------------------------

print()
print("8. DOS AUTOUR DE EF — COLONNES BRUTES")
print("-" * 78)

for lineno, row in numeric_rows:

    if abs(row[0] - EF) <= 0.05:

        print(
            f"ligne={lineno:5d} "
            + " ".join(
                f"C{i+1}={v:10.6f}"
                for i, v in enumerate(row)
            )
        )

# ----------------------------------------------------------------------
# 9. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("9. SYNTHÈSE")
print("=" * 78)

print("[OK] Fichier DOS réel inspecté.")
print("[OK] Header et nombre de colonnes déterminés.")
print("[OK] EF NSCF utilisé comme référence.")

print()
print("[IMPORTANT]")
print(
    "[INFO] Ne pas appeler la colonne 4 'DOS totale' "
    "avant identification exacte du format QE."
)
print(
    "[INFO] Pour un calcul spin-polarisé, la DOS physique totale "
    "sera vérifiée explicitement à partir des colonnes UP/DOWN."
)
print(
    "[INFO] Aucun calcul QE."
)
print(
    "[INFO] Aucun fichier modifié."
)
print(
    "[INFO] AIDA inchangé."
)

print()
print("=" * 78)
print("PHASE 78.40 TERMINÉE — READ-ONLY")
print("=" * 78)
