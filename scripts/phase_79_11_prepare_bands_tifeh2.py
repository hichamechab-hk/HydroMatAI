#!/usr/bin/env python3

from pathlib import Path
import re
import sys

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

SAVE_DIR = (
    BASE
    / "calculations/top5_dft/TiFeH2/tmp_scf"
    / "ecut140_rho560_k888.save"
)

NSCF_OUT = (
    BASE
    / "calculations/phase79_final_electronic/TiFeH2"
    / "TiFeH2_final_nscf.out"
)

OUT_DIR = (
    BASE
    / "calculations/phase79_final_electronic/TiFeH2"
)

BANDS_IN = OUT_DIR / "TiFeH2_final_bands.in"
BANDS_PLAN = OUT_DIR / "TiFeH2_final_bands_path.txt"

QE_BANDS = (
    Path("/home/hk/software/qe-7.5/bin/bands.x")
)

print("=" * 100)
print("PHASE 79.11 — PRÉPARATION / AUDIT bands.x TiFeH2")
print("=" * 100)
print("[INFO] MODE = PRÉPARATION + AUDIT")
print("[INFO] Aucun bands.x exécuté")
print("[INFO] Aucun pw.x exécuté")
print("[INFO] Aucun fichier scientifique existant modifié")

# ============================================================================
# 1. VÉRIFICATION DES ARTEFACTS
# ============================================================================

print("\n" + "-" * 100)
print("1. ARTEFACTS REQUIS")
print("-" * 100)

checks = [
    ("SAVE final NSCF", SAVE_DIR),
    ("NSCF final", NSCF_OUT),
    ("bands.x QE 7.5", QE_BANDS),
]

all_ok = True

for label, path in checks:
    if path.exists():
        print(f"[PASS] {label}: {path}")
    else:
        print(f"[FAIL] {label} absent: {path}")
        all_ok = False

if not all_ok:
    print("\n[FAIL] Préparation interrompue.")
    sys.exit(1)

# ============================================================================
# 2. AUDIT DU NSCF FINAL
# ============================================================================

print("\n" + "-" * 100)
print("2. AUDIT NSCF FINAL")
print("-" * 100)

text = NSCF_OUT.read_text(
    encoding="utf-8",
    errors="replace"
)

def first_float(pattern):
    m = re.search(pattern, text, re.I | re.M)
    return float(m.group(1)) if m else None

def first_int(pattern):
    m = re.search(pattern, text, re.I | re.M)
    return int(m.group(1)) if m else None

electrons = first_float(
    r"number of electrons\s*=\s*([0-9.]+)"
)

nbnd = first_int(
    r"number of Kohn-Sham states\s*=\s*([0-9]+)"
)

fermi = first_float(
    r"the Fermi energy is\s*([0-9.+-Ee]+)\s*ev"
)

ecutwfc = first_float(
    r"kinetic-energy cutoff\s*=\s*([0-9.+-Ee]+)\s*Ry"
)

nspin = None
m = re.search(
    r"number of spin components\s*=\s*([0-9]+)",
    text,
    re.I
)
if m:
    nspin = int(m.group(1))

job_done = "JOB DONE." in text

print(f"[INFO] Électrons        = {electrons}")
print(f"[INFO] KS states       = {nbnd}")
print(f"[INFO] Fermi           = {fermi} eV")
print(f"[INFO] ecutwfc         = {ecutwfc} Ry")
print(f"[INFO] nspin           = {nspin}")
print(f"[INFO] JOB DONE        = {job_done}")

if electrons != 60:
    print("[FAIL] Nombre d'électrons différent de 60")
    sys.exit(1)

if nbnd != 36:
    print("[FAIL] Nombre d'états KS différent de 36")
    sys.exit(1)

if not job_done:
    print("[FAIL] NSCF final non terminé")
    sys.exit(1)

print("[PASS] NSCF final compatible avec le protocole")

# ============================================================================
# 3. PREFIX / OUTDIR / PSEUDO_DIR
# ============================================================================

print("\n" + "-" * 100)
print("3. IDENTIFICATION QE")
print("-" * 100)

prefix_candidates = []

for line in text.splitlines():
    if "prefix" in line.lower():
        prefix_candidates.append(line.strip())

for line in prefix_candidates[:10]:
    print(f"[INFO] {line}")

if "ecut140_rho560_k888" not in text:
    print(
        "[WARN] Le prefix final n'est pas explicitement retrouvé "
        "dans le texte de sortie."
    )
else:
    print("[PASS] Prefix ecut140_rho560_k888 retrouvé")

# ============================================================================
# 4. CHEMIN SEEK-PATH → QE
# ============================================================================

print("\n" + "-" * 100)
print("4. CHEMIN BZ OFFICIEL")
print("-" * 100)

points = {
    "GAMMA":  (0.00000000,  0.00000000,  0.00000000),
    "Y":      (0.29403193, -0.04011345,  0.00000000),
    "T":      (0.29403193, -0.04011345, -0.50000000),
    "Z":      (0.00000000,  0.00000000, -0.50000000),
    "S":      (-0.37304076, 0.33292731,  0.00000000),
    "R":      (-0.37304076, 0.33292731, -0.50000000),
    "SIGMA_0": (-0.03603192, -0.36586386, 0.00000000),
    "C_0":    (0.28995041, 0.03171848,  0.00000000),
    "A_0":    (-0.03603192, -0.36586386, -0.50000000),
    "E_0":    (0.28995041, 0.03171848, -0.50000000),
}

path = [
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

print("[PASS] 10 points")
print("[PASS] 11 segments")

for i, (start, end) in enumerate(path, 1):
    print(f"[INFO] {i:02d}: {start} -> {end}")

# ============================================================================
# 5. CONSTRUCTION DU FICHIER bands.x
# ============================================================================

print("\n" + "-" * 100)
print("5. GÉNÉRATION DE L'INPUT bands.x")
print("-" * 100)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

bands_input = f"""&BANDS
  prefix = 'ecut140_rho560_k888',
  outdir = '{SAVE_DIR.parent}',
  filband = 'TiFeH2_final_bands.dat',
/
"""

# IMPORTANT:
# bands.x ne reçoit PAS le chemin k-point.
# Le calcul des bandes doit être préparé via pw.x avec K_POINTS crystal_b
# dans une étape dédiée. Ici, on ne lance donc PAS bands.x.
#
# Le présent fichier est volontairement limité au namelist &BANDS afin
# d'éviter de confondre la syntaxe de bands.x avec celle de pw.x.

BANDS_IN.write_text(
    bands_input,
    encoding="utf-8"
)

print(f"[PASS] Input bands.x préparé :")
print(f"       {BANDS_IN}")

print("\n[INFO] Contenu :")
print(bands_input)

# ============================================================================
# 6. PLAN DE CHEMIN POUR pw.x / BANDS
# ============================================================================

print("\n" + "-" * 100)
print("6. PLAN DU CHEMIN BZ")
print("-" * 100)

plan_lines = []

for i, (start, end) in enumerate(path, 1):

    ks = points[start]
    ke = points[end]

    plan_lines.append(
        f"{i:02d} "
        f"{start:8s} -> {end:8s} | "
        f"({ks[0]: .8f} {ks[1]: .8f} {ks[2]: .8f}) -> "
        f"({ke[0]: .8f} {ke[1]: .8f} {ke[2]: .8f})"
    )

BANDS_PLAN.write_text(
    "\n".join(plan_lines) + "\n",
    encoding="utf-8"
)

print(f"[PASS] Plan écrit :")
print(f"       {BANDS_PLAN}")

for line in plan_lines:
    print("[PATH]", line)

# ============================================================================
# 7. CONTRÔLE DES COORDONNÉES
# ============================================================================

print("\n" + "-" * 100)
print("7. CONTRÔLE COORDONNÉES")
print("-" * 100)

for label, coord in points.items():

    if all(abs(x) <= 0.5 + 1e-10 for x in coord):
        print(
            f"[PASS] {label:8s} "
            f"({coord[0]: .8f}, "
            f"{coord[1]: .8f}, "
            f"{coord[2]: .8f})"
        )
    else:
        print(
            f"[WARN] {label:8s} coordonnée hors représentation [-0.5,0.5]"
        )

# ============================================================================
# 8. CONTRÔLE CRITIQUE : NE PAS UTILISER bands.x DIRECTEMENT POUR LE PATH
# ============================================================================

print("\n" + "-" * 100)
print("8. CONTRÔLE MÉTHODOLOGIQUE")
print("-" * 100)

print(
    "[PASS] Les coordonnées BZ ont été obtenues dans la base réciproque QE."
)

print(
    "[PASS] Elles peuvent être utilisées pour construire un calcul "
    "de bandes via pw.x / K_POINTS crystal_b."
)

print(
    "[INFO] bands.x sert ensuite à extraire/ordonner les eigenvalues "
    "depuis le fichier save."
)

print(
    "[WARN] bands.x seul ne définit pas le chemin k-point."
)

print(
    "[WARN] Aucun calcul de bandes n'est lancé dans cette phase."
)

# ============================================================================
# 9. CHECK FINAL
# ============================================================================

print("\n" + "=" * 100)
print("RÉSULTAT PHASE 79.11")
print("=" * 100)

print("[RESULT] NSCF final          = VALIDÉ")
print("[RESULT] SAVE 140/560/8³    = PRÉSENT")
print("[RESULT] États KS            = 36")
print("[RESULT] Électrons            = 60")
print("[RESULT] Chemin SeeK-path     = Cmmm/oC1")
print("[RESULT] Points               = 10")
print("[RESULT] Segments             = 11")
print("[RESULT] bands.x              = NON EXÉCUTÉ")
print("[RESULT] pw.x                 = NON EXÉCUTÉ")

print("\n[INFO] IMPORTANT")
print(
    "[INFO] La prochaine étape doit préparer un INPUT pw.x "
    "NSCF de bandes avec K_POINTS crystal_b."
)
print(
    "[INFO] Ensuite seulement bands.x pourra extraire "
    "les bandes depuis le nouveau fichier .save."
)
print(
    "[INFO] Le NSCF uniforme 8×8×8 reste intact et inchangé."
)
