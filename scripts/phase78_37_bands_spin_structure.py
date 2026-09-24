import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.37 — RELAXED BANDS / SPIN STRUCTURE DIAGNOSTIC")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")
FILE = BASE / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_bands.out"

EXPECTED_K = 141
EXPECTED_BANDS = 36

text = FILE.read_text(errors="replace")
lines = text.splitlines()

header_re = re.compile(
    r"^\s*k\s*=\s*"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)"
    r".*bands\s*\(ev\)"
    r"\s*:\s*$",
    re.IGNORECASE,
)

blocks = []
current = None

for lineno, line in enumerate(lines, start=1):

    m = header_re.match(line)

    if m:
        if current is not None:
            blocks.append(current)

        current = {
            "line": lineno,
            "k": tuple(float(x) for x in m.groups()),
            "values": [],
        }
        continue

    if current is None:
        continue

    if "End of band structure calculation" in line:
        break

    tokens = line.strip().split()

    if not tokens:
        continue

    try:
        vals = [float(x) for x in tokens]
    except ValueError:
        continue

    current["values"].extend(vals)

if current is not None:
    blocks.append(current)

print("1. INVENTAIRE DES BLOCS")
print("-" * 78)
print(f"Nombre total de blocs : {len(blocks)}")
print(f"Nombre attendu par branche : {EXPECTED_K}")

counts = [len(b["values"]) for b in blocks]

print(f"Bandes par bloc : {sorted(set(counts))}")

# ----------------------------------------------------------------------
# Coordonnées uniques
# ----------------------------------------------------------------------

print()
print("2. COORDONNÉES K")
print("-" * 78)

coords = [b["k"] for b in blocks]

unique = []
for c in coords:
    if not any(
        all(abs(c[i] - u[i]) < 1e-10 for i in range(3))
        for u in unique
    ):
        unique.append(c)

print(f"Blocs totaux       : {len(coords)}")
print(f"Coordonnées uniques : {len(unique)}")

if len(unique) == EXPECTED_K:
    print("[OK] Exactement 141 coordonnées k uniques")
else:
    print("[WARN] Nombre inattendu de coordonnées uniques")

# ----------------------------------------------------------------------
# Comparaison blocs espacés de 141
# ----------------------------------------------------------------------

print()
print("3. TEST DE DUPLICATION PAR BRANCHES")
print("-" * 78)

if len(blocks) == 2 * EXPECTED_K:

    same_coords = 0
    max_coord_delta = 0.0

    for i in range(EXPECTED_K):
        a = blocks[i]["k"]
        b = blocks[i + EXPECTED_K]["k"]

        delta = max(abs(a[j] - b[j]) for j in range(3))
        max_coord_delta = max(max_coord_delta, delta)

        if delta < 1e-10:
            same_coords += 1

    print(f"Comparaison bloc i avec bloc i+141")
    print(f"Coordonnées identiques : {same_coords}/{EXPECTED_K}")
    print(f"Écart maximal coordonnée : {max_coord_delta:.3e}")

    if same_coords == EXPECTED_K:
        print("[OK] Les 282 blocs utilisent les mêmes 141 k-points")
        print("[INFO] Deux branches sont présentes sur le même chemin k.")
    else:
        print("[WARN] Les deux groupes ne sont pas coordonnés identiquement.")

# ----------------------------------------------------------------------
# Comparaison des énergies
# ----------------------------------------------------------------------

print()
print("4. COMPARAISON ÉNERGÉTIQUE DES DEUX GROUPES")
print("-" * 78)

if len(blocks) == 2 * EXPECTED_K and all(c == EXPECTED_BANDS for c in counts):

    differences = []

    for i in range(EXPECTED_K):
        a = blocks[i]["values"]
        b = blocks[i + EXPECTED_K]["values"]

        d = max(abs(x - y) for x, y in zip(a, b))
        differences.append(d)

    print(f"Différence max entre groupes : {max(differences):.8f} eV")
    print(f"Différence min entre groupes : {min(differences):.8f} eV")
    print(f"Différence moyenne          : {sum(differences)/len(differences):.8f} eV")

    identical = sum(d < 1e-10 for d in differences)

    print(f"Blocs pratiquement identiques : {identical}/{EXPECTED_K}")

    if identical == EXPECTED_K:
        print("[INFO] Les deux groupes sont numériquement identiques.")
    else:
        print("[INFO] Les deux groupes contiennent des valeurs différentes.")
        print("[IMPORTANT] Cela peut correspondre à deux composantes de spin.")

# ----------------------------------------------------------------------
# Premier et dernier blocs
# ----------------------------------------------------------------------

print()
print("5. EXEMPLES DE BLOCS")
print("-" * 78)

for idx in [0, 1, 2, 138, 139, 140, 141, 142, 143,
            278, 279, 280, 281]:

    if idx >= len(blocks):
        continue

    b = blocks[idx]

    print()
    print(
        f"bloc={idx+1:3d} "
        f"ligne={b['line']:4d} "
        f"k=({b['k'][0]:.6f}, {b['k'][1]:.6f}, {b['k'][2]:.6f})"
    )

    print(
        "  premières énergies :",
        " ".join(f"{x:.4f}" for x in b["values"][:8])
    )

    print(
        "  dernières énergies  :",
        " ".join(f"{x:.4f}" for x in b["values"][-8:])
    )

# ----------------------------------------------------------------------
# Recherche éventuelle d'indicateurs spin
# ----------------------------------------------------------------------

print()
print("6. INDICATEURS SPIN DANS LE FICHIER")
print("-" * 78)

patterns = [
    r"spin",
    r"up",
    r"down",
    r"spin-up",
    r"spin-down",
]

for p in patterns:
    found = [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if re.search(p, line, re.IGNORECASE)
    ]

    print(f"{p:12s} : {len(found)} occurrence(s)")

    for item in found[:5]:
        print(f"  ligne {item[0]} : {item[1][:120]}")

# ----------------------------------------------------------------------
# Synthèse
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

if len(blocks) == 282 and len(unique) == 141:
    print("[OK] 282 blocs correspondant à 141 coordonnées k uniques.")
    print("[INFO] La duplication est structurée et doit être interprétée")
    print("       avant toute analyse EF.")

if len(blocks) == 2 * EXPECTED_K:
    print("[OK] Le fichier est compatible avec deux groupes de 141 blocs.")

print()
print("[IMPORTANT]")
print("[INFO] Aucune énergie n'est supprimée ou recalculée.")
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.37 TERMINÉE — READ-ONLY")
print("=" * 78)
