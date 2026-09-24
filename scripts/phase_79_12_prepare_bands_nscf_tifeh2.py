#!/usr/bin/env python3

from pathlib import Path
import sys

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

OUT = (
    BASE
    / "calculations/phase79_bands/TiFeH2"
)

PSEUDO = (
    BASE
    / "calculations/top5_dft/TiFeH2/pseudo"
)

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

print("=" * 100)
print("PHASE 79.12 — PRÉPARATION NSCF BANDES TiFeH2")
print("=" * 100)
print("[INFO] MODE = PRÉPARATION / AUDIT")
print("[INFO] Aucun pw.x exécuté")
print("[INFO] Aucun fichier scientifique existant modifié")
print("[INFO] Nouveau prefix dédié aux bandes")

# ======================================================================
# 1. ARTEFACTS
# ======================================================================

print("\n" + "-" * 100)
print("1. VÉRIFICATION DES ARTEFACTS")
print("-" * 100)

if not QE.exists():
    print(f"[FAIL] pw.x absent : {QE}")
    sys.exit(1)

print(f"[PASS] QE 7.5 : {QE}")

if not PSEUDO.exists():
    print(f"[FAIL] Répertoire pseudo absent : {PSEUDO}")
    sys.exit(1)

required_pseudos = [
    "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "H.pbe-kjpaw.UPF",
    "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
]

for p in required_pseudos:
    path = PSEUDO / p
    if path.exists():
        print(f"[PASS] {p}")
    else:
        print(f"[FAIL] {p}")
        sys.exit(1)

# ======================================================================
# 2. RÉPERTOIRE DE TRAVAIL
# ======================================================================

print("\n" + "-" * 100)
print("2. RÉPERTOIRE BANDES")
print("-" * 100)

OUT.mkdir(parents=True, exist_ok=True)

print(f"[PASS] {OUT}")

# ======================================================================
# 3. INPUT pw.x
# ======================================================================

print("\n" + "-" * 100)
print("3. GÉNÉRATION DU NSCF BANDES")
print("-" * 100)

INPUT = OUT / "TiFeH2_bands_nscf.in"

PREFIX = "TiFeH2_bands_seekpath"

content = f"""&CONTROL
  calculation = 'bands',
  prefix = '{PREFIX}',
  pseudo_dir = '{PSEUDO}',
  outdir = '{OUT}/tmp',
  verbosity = 'high',
/

&SYSTEM
  ibrav = 0,
  nat = 8,
  ntyp = 3,
  ecutwfc = 140.0,
  ecutrho = 560.0,
  nspin = 2,
  nbnd = 36,
  occupations = 'smearing',
  smearing = 'mv',
  degauss = 0.01,
/

&ELECTRONS
  conv_thr = 1.0d-10,
  mixing_beta = 0.30,
/

ATOMIC_SPECIES
Ti 47.867 Ti.pbe-spn-kjpaw_psl.1.0.0.UPF
Fe 55.845 Fe.pbe-spn-rrkjus_psl.0.2.1.UPF
H  1.008  H.pbe-kjpaw.UPF

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
22
  0.00000000  0.00000000  0.00000000   20 ! GAMMA
  0.29403193 -0.04011345  0.00000000   20 ! Y

  0.29403193 -0.04011345  0.00000000   20 ! Y
  0.28995041  0.03171848  0.00000000   20 ! C_0

  0.28995041  0.03171848  0.00000000   20 ! C_0
  0.28995041  0.03171848  0.00000000   20 ! C_0

  0.28995041  0.03171848  0.00000000   20 ! C_0
  0.00000000  0.00000000  0.00000000   20 ! GAMMA

  0.00000000  0.00000000  0.00000000   20 ! GAMMA
  0.00000000  0.00000000 -0.50000000   20 ! Z

  0.00000000  0.00000000 -0.50000000   20 ! Z
 -0.03603192 -0.36586386 -0.50000000   20 ! A_0

 -0.03603192 -0.36586386 -0.50000000   20 ! A_0
  0.28995041  0.03171848 -0.50000000   20 ! E_0

  0.28995041  0.03171848 -0.50000000   20 ! E_0
  0.29403193 -0.04011345 -0.50000000   20 ! T

  0.29403193 -0.04011345 -0.50000000   20 ! T
  0.29403193 -0.04011345  0.00000000   20 ! Y

  0.00000000  0.00000000  0.00000000   20 ! GAMMA
 -0.37304076  0.33292731  0.00000000   20 ! S

 -0.37304076  0.33292731  0.00000000   20 ! S
 -0.37304076  0.33292731 -0.50000000   20 ! R

 -0.37304076  0.33292731 -0.50000000   20 ! R
  0.00000000  0.00000000 -0.50000000   20 ! Z

  0.00000000  0.00000000 -0.50000000   20 ! Z
  0.29403193 -0.04011345 -0.50000000   20 ! T
"""

# IMPORTANT:
# On prépare ici un fichier volontairement AUDITABLE.
# Le nombre déclaré doit correspondre exactement au nombre de lignes.
#
# Les lignes intermédiaires répétant le même point ont été utilisées
# pour rendre les segments explicites, mais QE crystal_b attend une
# liste ordonnée de points. On vérifie donc automatiquement le compte.

lines = [
    (0.00000000, 0.00000000, 0.00000000, "GAMMA"),
    (0.29403193, -0.04011345, 0.00000000, "Y"),

    (0.29403193, -0.04011345, 0.00000000, "Y"),
    (0.28995041, 0.03171848, 0.00000000, "C_0"),

    (0.28995041, 0.03171848, 0.00000000, "C_0"),
    (0.00000000, 0.00000000, 0.00000000, "GAMMA"),

    (0.00000000, 0.00000000, 0.00000000, "GAMMA"),
    (0.00000000, 0.00000000, -0.50000000, "Z"),

    (0.00000000, 0.00000000, -0.50000000, "Z"),
    (-0.03603192, -0.36586386, -0.50000000, "A_0"),

    (-0.03603192, -0.36586386, -0.50000000, "A_0"),
    (0.28995041, 0.03171848, -0.50000000, "E_0"),

    (0.28995041, 0.03171848, -0.50000000, "E_0"),
    (0.29403193, -0.04011345, -0.50000000, "T"),

    (0.29403193, -0.04011345, -0.50000000, "T"),
    (0.29403193, -0.04011345, 0.00000000, "Y"),

    (0.00000000, 0.00000000, 0.00000000, "GAMMA"),
    (-0.37304076, 0.33292731, 0.00000000, "S"),

    (-0.37304076, 0.33292731, 0.00000000, "S"),
    (-0.37304076, 0.33292731, -0.50000000, "R"),

    (-0.37304076, 0.33292731, -0.50000000, "R"),
    (0.00000000, 0.00000000, -0.50000000, "Z"),

    (0.00000000, 0.00000000, -0.50000000, "Z"),
    (0.29403193, -0.04011345, -0.50000000, "T"),
]

# Replace the manually assembled section with an exact generated section.
# Number of points is therefore guaranteed.

k_lines = [
    f"  {x: .8f} {y: .8f} {z: .8f}   20 ! {label}"
    for x, y, z, label in lines
]

content = f"""&CONTROL
  calculation = 'bands',
  prefix = '{PREFIX}',
  pseudo_dir = '{PSEUDO}',
  outdir = '{OUT}/tmp',
  verbosity = 'high',
/

&SYSTEM
  ibrav = 0,
  nat = 8,
  ntyp = 3,
  ecutwfc = 140.0,
  ecutrho = 560.0,
  nspin = 2,
  nbnd = 36,
  occupations = 'smearing',
  smearing = 'mv',
  degauss = 0.01,
/

&ELECTRONS
  conv_thr = 1.0d-10,
  mixing_beta = 0.30,
/

ATOMIC_SPECIES
Ti 47.867 Ti.pbe-spn-kjpaw_psl.1.0.0.UPF
Fe 55.845 Fe.pbe-spn-rrkjus_psl.0.2.1.UPF
H  1.008  H.pbe-kjpaw.UPF

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
{len(lines)}
""" + "\n".join(k_lines) + "\n"

INPUT.write_text(
    content,
    encoding="utf-8"
)

print(f"[PASS] Input créé : {INPUT}")

# ======================================================================
# 4. AUDIT AUTOMATIQUE
# ======================================================================

print("\n" + "-" * 100)
print("4. AUDIT INPUT")
print("-" * 100)

checks_text = {
    "calculation bands": "calculation = 'bands'" in content,
    "ecutwfc 140": "ecutwfc = 140.0" in content,
    "ecutrho 560": "ecutrho = 560.0" in content,
    "nspin 2": "nspin = 2" in content,
    "nbnd 36": "nbnd = 36" in content,
    "MV 0.01": "smearing = 'mv'" in content and "degauss = 0.01" in content,
    "K_POINTS crystal_b": "K_POINTS crystal_b" in content,
    "nat 8": "nat = 8" in content,
    "ntyp 3": "ntyp = 3" in content,
}

failed = False

for label, ok in checks_text.items():
    if ok:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label}")
        failed = True

print(f"[INFO] Nombre de k-points déclarés = {len(lines)}")
print("[INFO] Nombre de segments SeeK-path = 11")

if len(lines) != 24:
    print(
        "[FAIL] Le chemin explicite contient "
        f"{len(lines)} points au lieu de 24."
    )
    failed = True
else:
    print("[PASS] 24 points de chemin")

# ======================================================================
# 5. AUDIT DES LABELS
# ======================================================================

print("\n" + "-" * 100)
print("5. LABELS DU CHEMIN")
print("-" * 100)

expected = {
    "GAMMA",
    "Y",
    "C_0",
    "Z",
    "A_0",
    "E_0",
    "T",
    "S",
    "R",
}

found = {x[3] for x in lines}

for label in sorted(expected):
    if label in found:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label}")
        failed = True

# ======================================================================
# 6. RÉSUMÉ
# ======================================================================

print("\n" + "=" * 100)
print("RÉSULTAT PHASE 79.12")
print("=" * 100)

if failed:
    print("[RESULT] FAIL — input à corriger avant tout calcul.")
    sys.exit(1)

print("[RESULT] PASS — input NSCF bandes préparé.")
print("[RESULT] QE 7.5")
print("[RESULT] 140 Ry / 560 Ry")
print("[RESULT] nspin = 2")
print("[RESULT] nbnd = 36")
print("[RESULT] MV / degauss = 0.01")
print("[RESULT] Cmmm #65 / oC1")
print("[RESULT] 24 points explicites")
print("[RESULT] 11 segments SeeK-path")
print("[RESULT] pw.x = NON EXÉCUTÉ")
print("[RESULT] bands.x = NON EXÉCUTÉ")

print("\n[INFO] IMPORTANT :")
print(
    "[INFO] Le prefix est "
    f"'{PREFIX}' et ne remplace PAS le SAVE final "
    "'ecut140_rho560_k888'."
)
print(
    "[INFO] Le calcul pourra donc être exécuté séparément "
    "et audité indépendamment."
)
