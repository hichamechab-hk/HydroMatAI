#!/usr/bin/env python3

from pathlib import Path
import re
import sys

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

PSEUDO_DIR = (
    BASE
    / "calculations"
    / "new_campaign"
    / "TiFeH2"
    / "pseudo"
)

SOURCE_SAVE = (
    BASE
    / "calculations"
    / "top5_dft"
    / "TiFeH2"
    / "tmp_scf"
    / "ecut140_rho560_k888.save"
)

OUT_DIR = (
    BASE
    / "calculations"
    / "phase79_final_bands"
    / "TiFeH2"
)

INPUT_FILE = OUT_DIR / "TiFeH2_bands_path.in"
PLAN_FILE = OUT_DIR / "TiFeH2_bands_path_plan.txt"

PREFIX = "ecut140_rho560_k888"

# ----------------------------------------------------------------------
# PROTOCOLE FINAL
# ----------------------------------------------------------------------

ECUTWFC = 140
ECUTRHO = 560
NBND = 36
NSPIN = 2
DEGAUSS = 0.01

# Nombre de points d'interpolation par segment.
# Phase de préparation seulement : aucun calcul ici.
NSEG = 40

# ----------------------------------------------------------------------
# CHEMIN SeeK-path OFFICIEL — Cmmm #65 / oC1
# ----------------------------------------------------------------------

PATH = [
    ("GAMMA",     0.00000000,  0.00000000,  0.00000000),
    ("Y",         -0.50000000,  0.50000000,  0.00000000),
    ("C_0",       -0.44912523,  0.55087477,  0.00000000),
    ("SIGMA_0",    0.44912523,  0.44912523,  0.00000000),
    ("GAMMA",      0.00000000,  0.00000000,  0.00000000),
    ("Z",          0.00000000,  0.00000000,  0.50000000),
    ("A_0",        0.44912523,  0.44912523,  0.50000000),
    ("E_0",       -0.44912523,  0.55087477,  0.50000000),
    ("T",         -0.50000000,  0.50000000,  0.50000000),
    ("Y",         -0.50000000,  0.50000000,  0.00000000),
    ("GAMMA",      0.00000000,  0.00000000,  0.00000000),
    ("S",          0.00000000,  0.50000000,  0.00000000),
    ("R",          0.00000000,  0.50000000,  0.50000000),
    ("Z",          0.00000000,  0.00000000,  0.50000000),
    ("T",         -0.50000000,  0.50000000,  0.50000000),
]

# Segments SeeK-path :
SEGMENTS = [
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

# ----------------------------------------------------------------------
# AUDIT INITIAL
# ----------------------------------------------------------------------

print("=" * 100)
print("PHASE 79.12B — PRÉPARATION BANDES TiFeH2")
print("=" * 100)
print("[INFO] MODE = PRÉPARATION / AUDIT")
print("[INFO] Aucun pw.x exécuté")
print("[INFO] Aucun fichier scientifique existant modifié")
print("[INFO] Aucun .save existant modifié")
print("[INFO] Protocole final = 140 Ry / 560 Ry / 8x8x8 / nspin=2 / nbnd=36")
print("[INFO] Structure = TiFeH2 finale Cmmm #65")
print("[INFO] Chemin = SeeK-path Cmmm / oC1")
print()

# ----------------------------------------------------------------------
# 1. QE
# ----------------------------------------------------------------------

print("-" * 100)
print("1. QE")
print("-" * 100)

if QE.is_file() and QE.stat().st_mode & 0o111:
    print(f"[PASS] QE 7.5 : {QE}")
else:
    print(f"[FAIL] QE introuvable ou non exécutable : {QE}")
    sys.exit(1)

# ----------------------------------------------------------------------
# 2. PSEUDOS
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("2. PSEUDOPOTENTIELS")
print("-" * 100)

pseudo_targets = [
    "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "H.pbe-kjpaw.UPF",
    "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
]

if not PSEUDO_DIR.is_dir():
    print(f"[FAIL] Répertoire pseudo absent : {PSEUDO_DIR}")
    sys.exit(1)

print(f"[PASS] Répertoire pseudo : {PSEUDO_DIR}")

for name in pseudo_targets:
    p = PSEUDO_DIR / name
    if p.is_file():
        print(f"[PASS] {name} ({p.stat().st_size} octets)")
    else:
        print(f"[FAIL] {name} absent")
        sys.exit(1)

# ----------------------------------------------------------------------
# 3. SAVE SOURCE
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("3. SAVE SOURCE — PROTOCOLE FINAL")
print("-" * 100)

if not SOURCE_SAVE.is_dir():
    print(f"[FAIL] SAVE final absent : {SOURCE_SAVE}")
    sys.exit(1)

print(f"[PASS] SAVE final trouvé : {SOURCE_SAVE}")

required_save = [
    "data-file-schema.xml",
]

for name in required_save:
    p = SOURCE_SAVE / name
    if p.is_file():
        print(f"[PASS] SAVE contient : {name}")
    else:
        print(f"[WARN] Élément absent : {name}")

# ----------------------------------------------------------------------
# 4. CHEMIN SeeK-path
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("4. CHEMIN SeeK-path")
print("-" * 100)

print("[INFO] Space group = Cmmm #65")
print("[INFO] Bravais = oC1")
print("[INFO] Segments officiels :")
for i, (a, b) in enumerate(SEGMENTS, 1):
    print(f"  [{i:02d}] {a:10s} -> {b}")

if len(SEGMENTS) != 11:
    print("[FAIL] Nombre de segments différent de 11")
    sys.exit(1)

print("[PASS] 11 segments SeeK-path détectés")

# ----------------------------------------------------------------------
# 5. VÉRIFICATION DES COORDONNÉES
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("5. COORDONNÉES FRACTIONNELLES SeeK-path")
print("-" * 100)

for label, x, y, z in PATH:
    print(
        f"[K] {label:10s} "
        f"{x: .8f} {y: .8f} {z: .8f}"
    )

# ----------------------------------------------------------------------
# 6. CONTRÔLE DES SEGMENTS
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("6. CONTRÔLE DES SEGMENTS")
print("-" * 100)

# Coordonnées par label.
coords = {}
for label, x, y, z in PATH:
    coords.setdefault(label, (x, y, z))

# Vérification de cohérence.
for i, (a, b) in enumerate(SEGMENTS, 1):
    if a not in coords:
        print(f"[FAIL] Point initial absent : {a}")
        sys.exit(1)

    if b not in coords:
        print(f"[FAIL] Point final absent : {b}")
        sys.exit(1)

    print(f"[PASS] Segment {i:02d} : {a} -> {b}")

# ----------------------------------------------------------------------
# 7. CALCUL DU NOMBRE DE POINTS
# ----------------------------------------------------------------------

print()
print("-" * 100)
print("7. DENSITÉ DU CHEMIN")
print("-" * 100)

print(f"[INFO] Interpolation par segment = {NSEG}")
print(f"[INFO] Nombre de segments = {len(SEGMENTS)}")
print(f"[INFO] Ordre de grandeur du chemin = ~{len(SEGMENTS) * NSEG + 1} points")
print("[INFO] Aucun calcul lancé dans cette phase.")

# ----------------------------------------------------------------------
# 8. CRÉATION DU RÉPERTOIRE DE PRÉPARATION
# ----------------------------------------------------------------------

OUT_DIR.mkdir(parents=True, exist_ok=True)

print()
print("-" * 100)
print("8. RÉPERTOIRE DE PRÉPARATION")
print("-" * 100)

print(f"[PASS] Répertoire : {OUT_DIR}")

# ----------------------------------------------------------------------
# 9. GÉNÉRATION DU PLAN
# ----------------------------------------------------------------------

plan = []

plan.append("=" * 90)
plan.append("TiFeH2 — PLAN BANDES DFT")
plan.append("=" * 90)
plan.append("")
plan.append("STATUT : PREPARATION ONLY")
plan.append("Aucun calcul pw.x lancé par cette phase.")
plan.append("")
plan.append("PROTOCOLE")
plan.append("--------------------")
plan.append("QE              : 7.5")
plan.append("ecutwfc         : 140 Ry")
plan.append("ecutrho         : 560 Ry")
plan.append("nbnd            : 36")
plan.append("nspin           : 2")
plan.append("degauss         : 0.01 Ry")
plan.append("prefix          : ecut140_rho560_k888")
plan.append("")
plan.append("SAVE SOURCE")
plan.append("--------------------")
plan.append(str(SOURCE_SAVE))
plan.append("")
plan.append("PSEUDO DIR")
plan.append("--------------------")
plan.append(str(PSEUDO_DIR))
plan.append("")
plan.append("SYMMETRIE")
plan.append("--------------------")
plan.append("Space group     : Cmmm #65")
plan.append("Bravais         : oC1")
plan.append("")
plan.append("CHEMIN SeeK-path")
plan.append("--------------------")

for i, (a, b) in enumerate(SEGMENTS, 1):
    plan.append(f"{i:02d}. {a} -> {b}")

plan.append("")
plan.append(f"Points / segment : {NSEG}")
plan.append("")
plan.append("ATTENTION")
plan.append("--------------------")
plan.append("Le SAVE final 8x8x8 n'est pas modifié par cette phase.")
plan.append("Une future phase de calcul devra travailler dans un espace")
plan.append("dédié aux bandes et ne devra pas écraser le SAVE SCF final.")
plan.append("")
plan.append("Le chemin historique Γ-X-L-Y-Γ-Z-M-R-N-Z n'est PAS utilisé.")
plan.append("")

PLAN_FILE.write_text("\n".join(plan) + "\n", encoding="utf-8")

print(f"[PASS] Plan écrit : {PLAN_FILE}")

# ----------------------------------------------------------------------
# 10. GÉNÉRATION INPUT — PRÉPARATION UNIQUEMENT
# ----------------------------------------------------------------------

# NOTE :
# La syntaxe crystal_b est préparée ici sous forme de sommets.
# Le calcul effectif sera lancé dans une phase dédiée après audit
# de la syntaxe QE 7.5 et isolation du SAVE source.

input_text = f"""&CONTROL
  calculation = 'bands',
  prefix      = '{PREFIX}',
  pseudo_dir  = '{PSEUDO_DIR}',
  outdir      = '{OUT_DIR / "tmp"}',
  verbosity   = 'high',
/

&SYSTEM
  ibrav       = 0,
  nat         = 8,
  ntyp        = 3,
  ecutwfc     = {ECUTWFC},
  ecutrho     = {ECUTRHO},
  nspin       = {NSPIN},
  nbnd        = {NBND},
  occupations = 'smearing',
  smearing    = 'mv',
  degauss     = {DEGAUSS},
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
  0.00000000  0.00000000  0.00000000  {NSEG} ! GAMMA
 -0.50000000  0.50000000  0.00000000  {NSEG} ! Y
 -0.44912523  0.55087477  0.00000000  0       ! C_0
  0.44912523  0.44912523  0.00000000  {NSEG} ! SIGMA_0
  0.00000000  0.00000000  0.00000000  {NSEG} ! GAMMA
  0.00000000  0.00000000  0.50000000  {NSEG} ! Z
  0.44912523  0.44912523  0.50000000  0       ! A_0
 -0.44912523  0.55087477  0.50000000  {NSEG} ! E_0
 -0.50000000  0.50000000  0.50000000  {NSEG} ! T
 -0.50000000  0.50000000  0.00000000  {NSEG} ! Y
  0.00000000  0.00000000  0.00000000  {NSEG} ! GAMMA
  0.00000000  0.50000000  0.00000000  {NSEG} ! S
  0.00000000  0.50000000  0.50000000  {NSEG} ! R
  0.00000000  0.00000000  0.50000000  {NSEG} ! Z
 -0.50000000  0.50000000  0.50000000  0       ! T
"""

INPUT_FILE.write_text(input_text, encoding="utf-8")

print(f"[PASS] Input de préparation écrit : {INPUT_FILE}")

# ----------------------------------------------------------------------
# 11. RÉSUMÉ
# ----------------------------------------------------------------------

print()
print("=" * 100)
print("RÉSULTAT PHASE 79.12B")
print("=" * 100)

print("[PASS] QE 7.5 localisé")
print("[PASS] 3 pseudopotentiels exacts localisés")
print("[PASS] SAVE final 140/560/8x8x8 localisé")
print("[PASS] Cmmm #65 / oC1 confirmé par le protocole précédent")
print("[PASS] Chemin SeeK-path à 11 segments intégré")
print("[PASS] Ancien chemin Γ-X-L-Y-Γ-Z-M-R-N-Z exclu")
print("[PASS] Aucun pw.x exécuté")
print("[PASS] Aucun SAVE scientifique modifié")
print()
print(f"[RESULT] INPUT : {INPUT_FILE}")
print(f"[RESULT] PLAN  : {PLAN_FILE}")
print()
print("[NEXT] Phase 79.12C = AUDIT STRICT DE LA SYNTAXE crystal_b")
print("[NEXT] puis isolation du SAVE avant le vrai calcul de bandes.")
print("=" * 100)
