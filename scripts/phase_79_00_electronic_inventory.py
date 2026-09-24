#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CALC = BASE / "calculations"

print("=" * 88)
print("PHASE 79.00 — INVENTAIRE STRUCTURE ÉLECTRONIQUE TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

# ----------------------------------------------------------------------
# 1. SORTIE SCF FINALE
# ----------------------------------------------------------------------

print("-" * 88)
print("1. SORTIE SCF FINALE 140/560 — 8³")
print("-" * 88)

scf_candidates = [
    CALC / "phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out",
    CALC / "phase78_63_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out",
]

scf_out = None

for p in scf_candidates:
    if p.exists():
        scf_out = p
        break

if scf_out is None:
    print("[WARN] Sortie SCF finale non trouvée dans les chemins connus.")
else:
    print(f"[PASS] SCF final trouvé : {scf_out}")

    text = scf_out.read_text(errors="ignore")

    m = re.search(
        r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry",
        text
    )
    print(
        f"[INFO] E = {m.group(1)} Ry"
        if m else "[WARN] Énergie non extraite"
    )

    m = re.search(
        r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev",
        text,
        re.I
    )
    print(
        f"[INFO] EF = {m.group(1)} eV"
        if m else "[WARN] EF non extrait"
    )

    print(f"[INFO] JOB DONE = {'JOB DONE.' in text}")

# ----------------------------------------------------------------------
# 2. INVENTAIRE NSCF / BANDS / DOS EXISTANTS
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("2. INVENTAIRE DES CALCULS ÉLECTRONIQUES EXISTANTS")
print("-" * 88)

patterns = [
    "**/*nscf*.in",
    "**/*nscf*.out",
    "**/*bands*.in",
    "**/*bands*.out",
    "**/*dos*.in",
    "**/*dos*.out",
    "**/*projwfc*.in",
    "**/*projwfc*.out",
]

found = []

for pattern in patterns:
    for p in CALC.glob(pattern):
        if p.is_file() and p not in found:
            found.append(p)

if not found:
    print("[INFO] Aucun calcul NSCF/BANDS/DOS nouveau détecté.")
else:
    for p in sorted(found):
        print(f"[FILE] {p}")

# ----------------------------------------------------------------------
# 3. FICHIERS DE CHARGE QE
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("3. INVENTAIRE DES DONNÉES QE RÉUTILISABLES")
print("-" * 88)

charge_patterns = [
    "**/charge-density.dat",
    "**/charge-density.hdf5",
    "**/*.save",
]

charge_found = []

for pattern in charge_patterns:
    for p in CALC.glob(pattern):
        if p.exists() and p not in charge_found:
            charge_found.append(p)

# Limitation volontaire : seulement affichage, aucun accès/modification.
if not charge_found:
    print("[WARN] Aucune charge-density / répertoire .save trouvé sous calculations/")
else:
    for p in sorted(charge_found):
        if p.is_dir():
            print(f"[DIR ] {p}")
        else:
            print(f"[FILE] {p}")

# ----------------------------------------------------------------------
# 4. STRUCTURE
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("4. STRUCTURE TiFeH2")
print("-" * 88)

cif_candidates = [
    CALC / "top5_dft/TiFeH2/TiFeH2.cif",
]

for cif in cif_candidates:
    if cif.exists():
        print(f"[PASS] CIF trouvé : {cif}")
        text = cif.read_text(errors="ignore")
        atoms = len(re.findall(r"^\s*(Ti|Fe|H)\s+", text, re.MULTILINE))
        print(f"[INFO] Entrées atomiques détectées = {atoms}")
    else:
        print(f"[WARN] CIF absent : {cif}")

# ----------------------------------------------------------------------
# 5. PROTOCOLE GELÉ
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("5. PROTOCOLE ÉLECTRONIQUE GELÉ")
print("-" * 88)

for k, v in [
    ("QE", "7.5"),
    ("ecutwfc", "140 Ry"),
    ("ecutrho", "560 Ry"),
    ("k-mesh SCF", "8 × 8 × 8"),
    ("nspin", "2"),
    ("occupations", "smearing"),
    ("smearing", "mv"),
    ("degauss", "0.01 Ry"),
    ("nat", "8"),
    ("ntyp", "3"),
    ("nelec", "60"),
    ("nbnd", "36"),
]:
    print(f"[PASS] {k:<18} = {v}")

print()
print("=" * 88)
print("DÉCISION")
print("=" * 88)

if scf_out is not None:
    print("[RESULT] SCF final identifié.")
else:
    print("[RESULT] SCF final à localiser avant NSCF.")

if charge_found:
    print("[RESULT] Données QE réutilisables détectées.")
    print("[INFO] Une Phase 79 NSCF/BANDS/DOS peut être préparée.")
else:
    print("[WARN] Aucune donnée .save détectée.")
    print("[INFO] Ne pas supposer que le NSCF peut réutiliser automatiquement")
    print("       le SCF historique.")

print()
print("[INFO] Cette phase n'exécute volontairement aucun calcul.")
print("=" * 88)
