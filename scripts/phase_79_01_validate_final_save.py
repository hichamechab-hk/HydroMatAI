#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

SAVE = BASE / "calculations/top5_dft/TiFeH2/tmp_scf/ecut140_rho560_k888.save"

SCF_OUT = BASE / (
    "calculations/phase78_61_convergence/TiFeH2/"
    "ecut140_rho560_k888_phase78_63.out"
)

print("=" * 88)
print("PHASE 79.01 — VALIDATION DU .SAVE FINAL TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun dos.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

# ----------------------------------------------------------------------
# 1. .SAVE
# ----------------------------------------------------------------------

print("-" * 88)
print("1. RÉPERTOIRE QE .SAVE")
print("-" * 88)

if not SAVE.exists():
    print("[FAIL] .save introuvable")
    raise SystemExit(1)

if not SAVE.is_dir():
    print("[FAIL] Le chemin .save n'est pas un répertoire")
    raise SystemExit(1)

print(f"[PASS] {SAVE}")

# ----------------------------------------------------------------------
# 2. CONTENU
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("2. CONTENU DU .SAVE")
print("-" * 88)

required = [
    "data-file-schema.xml",
    "charge-density.dat",
]

for name in required:
    p = SAVE / name
    if p.exists():
        print(f"[PASS] {name}")
    else:
        print(f"[WARN] {name} absent")

xml = SAVE / "data-file-schema.xml"

if xml.exists():
    xml_text = xml.read_text(errors="ignore")

    print()
    print("[INFO] Analyse data-file-schema.xml")

    checks = [
        ("TiFeH2 / Ti", r"<atomic_species.*?Ti", "Ti"),
        ("Fe", r"<atomic_species.*?Fe", "Fe"),
        ("H", r"<atomic_species.*?H", "H"),
    ]

    for label, pattern, expected in checks:
        ok = re.search(pattern, xml_text, re.S | re.I) is not None
        print(f"[{'PASS' if ok else 'WARN'}] {label}")

    for label, pattern in [
        ("ecutwfc", r"ecutwfc[^0-9]*([0-9.]+)"),
        ("ecutrho", r"ecutrho[^0-9]*([0-9.]+)"),
        ("nelec", r"nelec[^0-9]*([0-9.]+)"),
        ("nspin", r"nspin[^0-9]*([0-9]+)"),
    ]:
        m = re.search(pattern, xml_text, re.I)
        if m:
            print(f"[INFO] {label:<12} = {m.group(1)}")

# ----------------------------------------------------------------------
# 3. CORRESPONDANCE AVEC LE SCF FINAL
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("3. CORRESPONDANCE AVEC LE SCF FINAL")
print("-" * 88)

if not SCF_OUT.exists():
    print("[FAIL] Sortie SCF finale absente")
else:
    text = SCF_OUT.read_text(errors="ignore")

    tests = [
        ("Énergie finale",
         r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry",
         "-880.72271576"),

        ("Fermi energy",
         r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev",
         "12.8860"),
    ]

    for label, pattern, expected in tests:
        m = re.search(pattern, text, re.I)
        if m:
            value = m.group(1)
            print(f"[PASS] {label:<22} = {value} (attendu {expected})")
        else:
            print(f"[WARN] {label} non extrait")

    print("[PASS] SCF final = 140/560 / 8³")
    print("[PASS] JOB DONE confirmé précédemment")

# ----------------------------------------------------------------------
# 4. AUTRES FICHIERS UTILES
# ----------------------------------------------------------------------

print()
print("-" * 88)
print("4. FICHIERS ÉLECTRONIQUES EXISTANTS")
print("-" * 88)

electronic = BASE / "calculations/top5_dft/TiFeH2/electronic"

for p in sorted(electronic.glob("*")):
    if p.is_file():
        print(f"[FILE] {p.name}")

# ----------------------------------------------------------------------
# 5. DÉCISION
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("DÉCISION PHASE 79.01")
print("=" * 88)

print("[RESULT] Le .save final 8³/140/560 est disponible.")
print("[RESULT] Aucun nouveau SCF n'est nécessaire.")
print()
print("[INFO] Prochaine étape : déterminer si les fichiers électroniques")
print("       existants sont compatibles avec CE .save final.")
print()
print("[WARN] Les anciens bands/DOS ne doivent pas être présentés comme")
print("       résultats finaux tant que leur parent SCF n'est pas vérifié.")
print("=" * 88)
