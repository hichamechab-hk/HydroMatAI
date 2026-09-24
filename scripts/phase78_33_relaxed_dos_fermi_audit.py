import os
os.system("clear")

from pathlib import Path
import math

ROOT = Path("/home/hk/HydroMatAI")

DOS = (
    ROOT
    / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
      "TiFeH2_relaxed.dos"
)

EF = 12.9573
WINDOW = 0.50


print("=" * 78)
print("PHASE 78.33 — RELAXED DOS / FERMI AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


# ----------------------------------------------------------------------
# 1. LECTURE
# ----------------------------------------------------------------------

if not DOS.exists():
    print("[ERROR] Fichier DOS absent :", DOS)
    raise SystemExit(1)

rows = []

for line in DOS.read_text(errors="replace").splitlines():

    line = line.strip()

    if not line:
        continue

    parts = line.split()

    try:
        values = [float(x.replace("D", "E")) for x in parts]
    except ValueError:
        continue

    if len(values) >= 3:
        rows.append(values)


print("1. DONNÉES")
print("-" * 78)
print("Fichier :", DOS)
print("Lignes numériques :", len(rows))

if not rows:
    print("[ERROR] Aucune donnée numérique.")
    raise SystemExit(1)


# ----------------------------------------------------------------------
# 2. IDENTIFICATION DES COLONNES
# ----------------------------------------------------------------------

print()
print("2. STRUCTURE DES DONNÉES")
print("-" * 78)

print("Première ligne numérique :", rows[0])
print("Dernière ligne numérique :", rows[-1])

print()
print("Convention attendue :")
print("  colonne 1 = Energy")
print("  colonne 2 = DOS up")
print("  colonne 3 = DOS down")
print("  colonne 4 = Integrated DOS")


# ----------------------------------------------------------------------
# 3. POINT LE PLUS PROCHE DE EF
# ----------------------------------------------------------------------

nearest = min(
    rows,
    key=lambda r: abs(r[0] - EF)
)

idx = rows.index(nearest)

print()
print("3. POINT LE PLUS PROCHE DE EF")
print("-" * 78)

print("EF NSCF :", EF, "eV")
print("E DOS   :", nearest[0], "eV")
print("|ΔE|    :", abs(nearest[0] - EF), "eV")

up = nearest[1]
down = nearest[2]
total = up + down

print("DOS up    :", up)
print("DOS down  :", down)
print("DOS total :", total)


# ----------------------------------------------------------------------
# 4. VOISINAGE IMMÉDIAT
# ----------------------------------------------------------------------

print()
print("4. VOISINAGE DE EF")
print("-" * 78)

start = max(0, idx - 5)
end = min(len(rows), idx + 6)

print(
    f"{'E (eV)':>12} "
    f"{'DOS up':>15} "
    f"{'DOS down':>15} "
    f"{'DOS total':>15}"
)

for r in rows[start:end]:

    total_r = r[1] + r[2]

    print(
        f"{r[0]:12.5f} "
        f"{r[1]:15.8f} "
        f"{r[2]:15.8f} "
        f"{total_r:15.8f}"
    )


# ----------------------------------------------------------------------
# 5. FENÊTRE ±0.5 eV
# ----------------------------------------------------------------------

window_rows = [
    r for r in rows
    if abs(r[0] - EF) <= WINDOW
]

print()
print("5. FENÊTRE AUTOUR DE EF")
print("-" * 78)

print(
    "Fenêtre :",
    EF - WINDOW,
    "→",
    EF + WINDOW,
    "eV"
)

print("Points :", len(window_rows))

if window_rows:

    totals = [r[1] + r[2] for r in window_rows]

    print("DOS total min :", min(totals))
    print("DOS total max :", max(totals))
    print("DOS total moy :", sum(totals) / len(totals))

    min_row = min(
        window_rows,
        key=lambda r: r[1] + r[2]
    )

    max_row = max(
        window_rows,
        key=lambda r: r[1] + r[2]
    )

    print()
    print("Minimum :")
    print("  E =", min_row[0], "eV")
    print("  DOS =", min_row[1] + min_row[2])

    print()
    print("Maximum :")
    print("  E =", max_row[0], "eV")
    print("  DOS =", max_row[1] + max_row[2])


# ----------------------------------------------------------------------
# 6. TEST DE NULLITÉ LOCALE
# ----------------------------------------------------------------------

print()
print("6. TEST DE NULLITÉ LOCALE")
print("-" * 78)

threshold = 1e-8

zero_like = [
    r for r in window_rows
    if abs(r[1] + r[2]) <= threshold
]

print("Seuil numérique :", threshold)
print("Points DOS ≈ 0 :", len(zero_like))
print("Points fenêtre :", len(window_rows))

if zero_like:
    print(
        "[INFO] Des points présentent un DOS numériquement nul "
        "dans la fenêtre."
    )
else:
    print(
        "[INFO] Aucun point de la fenêtre ne présente "
        "un DOS numériquement nul au seuil choisi."
    )


# ----------------------------------------------------------------------
# 7. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

print("[OK] DOS relaxé lu directement.")
print("[OK] Niveau de Fermi comparé au maillage DOS.")
print("[OK] Voisinage de EF inspecté.")
print("[OK] Fenêtre ±0.5 eV inspectée.")
print()
print("[INFO] Cette phase caractérise le DOS numérique.")
print("[INFO] Elle ne constitue pas à elle seule une validation")
print("       scientifique complète.")
print()
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.33 TERMINÉE — READ-ONLY")
print("=" * 78)
