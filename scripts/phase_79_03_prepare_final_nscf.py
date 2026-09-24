#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

SAVE = BASE / "calculations/top5_dft/TiFeH2/tmp_scf/ecut140_rho560_k888.save"
ELECTRONIC = BASE / "calculations/top5_dft/TiFeH2/electronic"

print("=" * 88)
print("PHASE 79.03 — PRÉPARATION NSCF FINAL TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

# ----------------------------------------------------------------------
# 1. SAVE
# ----------------------------------------------------------------------

print("-" * 88)
print("1. .SAVE FINAL")
print("-" * 88)

print(f"[INFO] {SAVE}")

if not SAVE.is_dir():
    print("[FAIL] .save absent")
    raise SystemExit(1)

schema = SAVE / "data-file-schema.xml"
charge = SAVE / "charge-density.dat"

print(f"[PASS] Répertoire .save")
print(f"[PASS] data-file-schema.xml = {schema.exists()}")
print(f"[PASS] charge-density.dat  = {charge.exists()}")

# ----------------------------------------------------------------------
# 2. XML — extraire uniquement les informations d'identité utiles
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("2. IDENTITÉ DU CALCUL DANS data-file-schema.xml")
print("-" * 88)

xml = schema.read_text(errors="ignore")

for label, patterns in {
    "prefix": [
        r'prefix="([^"]+)"',
        r'<prefix>(.*?)</prefix>',
    ],
    "atomic species": [
        r'<atomic_species[^>]*>',
    ],
    "cell": [
        r'<cell[^>]*>',
    ],
}.items():

    found = None

    for pat in patterns:
        m = re.search(pat, xml, re.I | re.S)
        if m:
            found = m.group(1) if m.lastindex else m.group(0)
            break

    print(f"[INFO] {label:<18} = {found if found else '?'}")

# ----------------------------------------------------------------------
# 3. Anciens inputs : uniquement pour comparaison
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("3. ANCIEN TiFeH2_nscf.in")
print("-" * 88)

old = ELECTRONIC / "TiFeH2_nscf.in"

if not old.exists():
    print("[INFO] Aucun ancien NSCF input")
else:
    text = old.read_text(errors="ignore")

    for name, pat in [
        ("prefix", r'\bprefix\s*=\s*[\'"]([^\'"]+)'),
        ("outdir", r'\boutdir\s*=\s*[\'"]([^\'"]+)'),
        ("pseudo_dir", r'\bpseudo_dir\s*=\s*[\'"]([^\'"]+)'),
        ("ecutwfc", r'\becutwfc\s*=\s*([0-9.]+)'),
        ("ecutrho", r'\becutrho\s*=\s*([0-9.]+)'),
        ("nbnd", r'\bnbnd\s*=\s*(\d+)'),
        ("nspin", r'\bnspin\s*=\s*(\d+)'),
        ("degauss", r'\bdegauss\s*=\s*([0-9.]+)'),
    ]:
        m = re.search(pat, text, re.I)
        print(f"[INFO] {name:<12} = {m.group(1) if m else '?'}")

# ----------------------------------------------------------------------
# 4. SAVE directories voisines
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("4. INVENTAIRE DES .SAVE TiFeH2")
print("-" * 88)

parent = SAVE.parent

for p in sorted(parent.glob("*.save")):
    marker = " <-- FINAL 140/560/8³" if p == SAVE else ""
    print(f"[SAVE] {p.name}{marker}")

# ----------------------------------------------------------------------
# 5. PROTOCOLE CIBLE
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("5. PROTOCOLE NSCF CIBLE")
print("-" * 88)

print("[INFO] Parent SCF        = ecut140_rho560_k888.save")
print("[INFO] ecutwfc           = 140 Ry")
print("[INFO] ecutrho           = 560 Ry")
print("[INFO] nspin             = 2")
print("[INFO] nbnd              = 36")
print("[INFO] occupations       = smearing")
print("[INFO] smearing           = mv")
print("[INFO] degauss            = 0.01 Ry")
print("[INFO] électrons          = 60")
print("[INFO] états KS           = 36")

# ----------------------------------------------------------------------
# 6. DÉCISION
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("DÉCISION PHASE 79.03")
print("=" * 88)

if schema.exists() and charge.exists():
    print("[RESULT] PASS — .save final exploitable pour NSCF.")
    print("[RESULT] Aucun ancien résultat électronique n'est validé comme final.")
    print("[RESULT] Prochaine étape : créer un NSCF propre sur CE .save.")
else:
    print("[RESULT] FAIL — .save incomplet.")

print("=" * 88)
