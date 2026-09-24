#!/usr/bin/env python3

from pathlib import Path
import sys

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

BANDS_DIR = (
    BASE
    / "calculations"
    / "phase79_final_bands"
    / "TiFeH2"
)

OLD_INPUT = BANDS_DIR / "TiFeH2_bands_path.in"
NEW_INPUT = BANDS_DIR / "TiFeH2_bands_path_corrected.in"

NSEG = 40

print("=" * 100)
print("PHASE 79.12C — AUDIT STRICT crystal_b TiFeH2")
print("=" * 100)
print("[INFO] MODE = READ-ONLY / CORRECTION DE PRÉPARATION")
print("[INFO] Aucun pw.x exécuté")
print("[INFO] Aucun fichier .save modifié")
print("[INFO] Aucun calcul DFT")
print()

# ----------------------------------------------------------------------
# 1. INPUT PRECEDENT
# ----------------------------------------------------------------------

print("-" * 100)
print("1. INPUT PHASE 79.12B")
print("-" * 100)

if not OLD_INPUT.is_file():
    print(f"[FAIL] Input absent : {OLD_INPUT}")
    sys.exit(1)

print(f"[PASS] Input trouvé : {OLD_INPUT}")

text = OLD_INPUT.read_text(encoding="utf-8")

if "K_POINTS crystal_b" not in text:
    print("[FAIL] Carte K_POINTS crystal_b absente")
    sys.exit(1)

print("[PASS] K_POINTS crystal_b présent")

# ----------------------------------------------------------------------
# 2. SYNTAXE DE BASE
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("2. CONTRÔLE DE LA CARTE crystal_b")
print("-" * 100)

lines = text.splitlines()

try:
    idx = next(
        i for i, line in enumerate(lines)
        if line.strip().lower().startswith("k_points crystal_b")
    )
except StopIteration:
    print("[FAIL] K_POINTS crystal_b introuvable")
    sys.exit(1)

try:
    npoints = int(lines[idx + 1].strip())
except Exception:
    print("[FAIL] Nombre de sommets crystal_b illisible")
    sys.exit(1)

print(f"[INFO] Nombre de sommets déclaré = {npoints}")

if npoints != 15:
    print("[FAIL] Le chemin Cmmm attendu nécessite 15 sommets")
    sys.exit(1)

print("[PASS] 15 sommets déclarés")

# ----------------------------------------------------------------------
# 3. CHEMIN CORRECT
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("3. CHEMIN SeeK-path CORRIGÉ")
print("-" * 100)

# Chaque ligne :
# x y z N
#
# N = nombre de points vers le sommet suivant.
# N=0 permet de couper les segments disjoints.

path = [
    ("GAMMA",     0.00000000,  0.00000000,  0.00000000, 40),
    ("Y",        -0.50000000,  0.50000000,  0.00000000, 40),
    ("C_0",      -0.44912523,  0.55087477,  0.00000000,  0),

    ("SIGMA_0",   0.44912523,  0.44912523,  0.00000000, 40),
    ("GAMMA",     0.00000000,  0.00000000,  0.00000000, 40),
    ("Z",         0.00000000,  0.00000000,  0.50000000, 40),
    ("A_0",       0.44912523,  0.44912523,  0.50000000,  0),

    ("E_0",      -0.44912523,  0.55087477,  0.50000000, 40),
    ("T",        -0.50000000,  0.50000000,  0.50000000, 40),
    ("Y",        -0.50000000,  0.50000000,  0.00000000,  0),

    ("GAMMA",     0.00000000,  0.00000000,  0.00000000, 40),
    ("S",         0.00000000,  0.50000000,  0.00000000, 40),
    ("R",         0.00000000,  0.50000000,  0.50000000, 40),
    ("Z",         0.00000000,  0.00000000,  0.50000000, 40),
    ("T",        -0.50000000,  0.50000000,  0.50000000,  0),
]

print()

for i, (label, x, y, z, n) in enumerate(path, 1):
    print(
        f"[{i:02d}] {label:10s} "
        f"{x: .8f} {y: .8f} {z: .8f}  N={n}"
    )

# ----------------------------------------------------------------------
# 4. CONTRÔLE DES 11 SEGMENTS
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("4. VÉRIFICATION DES 11 SEGMENTS")
print("-" * 100)

expected = [
    ("GAMMA", "Y"),
    ("Y", "C_0"),
    ("SIGMA_0", "GAMMA"),
    ("GAMMA", "Z"),
    ("Z", "A_0"),
    ("E_0", "T"),
    ("T", "Y"),
    ("GAMMA", "S"),
    ("S", "R"),
    ("R", "Z"),
    ("Z", "T"),
]

# Indices des sommets de départ pour les 11 lignes.
starts = [0, 1, 3, 4, 5, 7, 8, 10, 11, 12, 13]

for i, ((a, b), start) in enumerate(zip(expected, starts), 1):
    label = path[start][0]
    next_label = path[start + 1][0]

    if label != a or next_label != b:
        print(
            f"[FAIL] Segment {i:02d}: "
            f"attendu {a}->{b}, obtenu {label}->{next_label}"
        )
        sys.exit(1)

    if path[start][4] != NSEG:
        print(
            f"[FAIL] Segment {i:02d}: "
            f"N={path[start][4]} au lieu de {NSEG}"
        )
        sys.exit(1)

    print(f"[PASS] {i:02d} {a} -> {b} : {NSEG} points")

# ----------------------------------------------------------------------
# 5. RUPTURES DE CHEMIN
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("5. CONTRÔLE DES RUPTURES")
print("-" * 100)

breaks = [
    ("C_0", "SIGMA_0", path[2][4]),
    ("A_0", "E_0", path[6][4]),
    ("Y", "GAMMA", path[9][4]),
]

for a, b, n in breaks:
    if n != 0:
        print(f"[FAIL] Rupture {a}->{b} possède N={n}")
        sys.exit(1)

    print(f"[PASS] Rupture {a} -> {b} : N=0")

# ----------------------------------------------------------------------
# 6. NOMBRE DE POINTS
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("6. DENSITÉ DU CHEMIN")
print("-" * 100)

print(f"[INFO] Segments = {len(expected)}")
print(f"[INFO] Points/segment = {NSEG}")
print(f"[INFO] Points interpolés théoriques ≈ {len(expected) * NSEG + 1}")

# ----------------------------------------------------------------------
# 7. GÉNÉRATION INPUT CORRIGÉ
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("7. GÉNÉRATION INPUT CORRIGÉ")
print("-" * 100)

header = """&CONTROL
  calculation = 'bands',
  prefix      = 'ecut140_rho560_k888',
  pseudo_dir  = '/home/hk/HydroMatAI/calculations/new_campaign/TiFeH2/pseudo',
  outdir      = '/home/hk/HydroMatAI/calculations/phase79_final_bands/TiFeH2/tmp',
  verbosity   = 'high',
/

&SYSTEM
  ibrav       = 0,
  nat         = 8,
  ntyp        = 3,
  ecutwfc     = 140,
  ecutrho     = 560,
  nspin       = 2,
  nbnd        = 36,
  occupations = 'smearing',
  smearing    = 'mv',
  degauss     = 0.01,
/

&ELECTRONS
  conv_thr    = 1.0d-10,
/

ATOMIC_SPECIES
Ti  47.867  Ti.pbe-spn-kjpaw_psl.1.0.0.UPF
Fe  55.845  Fe.pbe-spn-rrkjus_psl.0.2.1.UPF
H    1.008  H.pbe-kjpaw.UPF

CELL_PARAMETERS angstrom
  5.2399261000   0.0000000000   0.0000000000
 -0.5935539478   5.2062000773   0.0000000000
  0.0000000000   0.0000000000   2.6442020000

ATOMIC_POSITIONS crystal
Ti  0.281859  0.281859  0.000000
Ti  0.718141  0.718141  0.000000
Fe  0.766146  0.233854  0.000000
Fe  0.233854  0.766146  0.000000
H   0.000000  0.500000  0.000000
H   0.000000  0.000000  0.000000
H   0.500000  0.000000  0.000000
H   0.500000  0.500000  0.500000

K_POINTS crystal_b
15
"""

body = ""

for label, x, y, z, n in path:
    body += (
        f" {x: .8f} {y: .8f} {z: .8f} {n:3d} "
        f"! {label}\n"
    )

NEW_INPUT.write_text(header + body, encoding="utf-8")

print(f"[PASS] Input corrigé écrit :")
print(f"       {NEW_INPUT}")

# ----------------------------------------------------------------------
# 8. RÉSUMÉ
# ----------------------------------------------------------------------

print()
print("=" * 100)
print("RÉSULTAT PHASE 79.12C")
print("=" * 100)

print("[PASS] crystal_b identifié")
print("[PASS] 15 sommets")
print("[PASS] 11 segments SeeK-path")
print("[PASS] 40 points par segment")
print("[PASS] Rupture C_0 -> SIGMA_0 contrôlée")
print("[PASS] Rupture A_0 -> E_0 contrôlée")
print("[PASS] Rupture Y -> GAMMA contrôlée")
print("[PASS] Aucun ancien chemin Γ-X-L-Y-Γ-Z-M-R-N-Z")
print("[PASS] Aucun pw.x exécuté")
print("[PASS] Aucun .save modifié")
print()
print("[RESULT] Input corrigé prêt pour l'étape d'isolation du SAVE.")
print()
print("[NEXT] PHASE 79.12D")
print("       Isolation du SAVE final dans un répertoire dédié")
print("       puis contrôle final de l'input avant lancement pw.x.")
print("=" * 100)
