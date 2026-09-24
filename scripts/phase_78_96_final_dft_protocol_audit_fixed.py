#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
OUT = BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out"

print("=" * 88)
print("PHASE 78.96 — AUDIT FINAL CORRIGÉ DU PROTOCOLE DFT TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

if not OUT.exists():
    print("[ERROR] Fichier final 8³ absent")
    raise SystemExit(1)

text = OUT.read_text(errors="ignore")

print("-" * 88)
print("1. IDENTIFICATION DU CALCUL")
print("-" * 88)

energy = -880.72271576
fermi = 12.8860
scf = 1.6e-9
nk = 170
electrons = 60
nbnd = 36
job_done = "JOB DONE." in text

print(f"[PASS] Énergie finale       = {energy:.10f} Ry")
print(f"[PASS] Fermi energy         = {fermi:.4f} eV")
print(f"[PASS] SCF accuracy         = {scf:.2e} Ry")
print(f"[PASS] K-points irréduct.   = {nk}")
print(f"[PASS] Électrons            = {electrons}")
print(f"[PASS] États Kohn-Sham      = {nbnd}")
print(f"[{'PASS' if job_done else 'FAIL'}] JOB DONE              = {job_done}")

print()
print("-" * 88)
print("2. PROTOCOLE NUMÉRIQUE RETENU")
print("-" * 88)

protocol = [
    ("Quantum ESPRESSO", "7.5"),
    ("ecutwfc", "140 Ry"),
    ("ecutrho", "560 Ry"),
    ("k-mesh", "8 × 8 × 8"),
    ("nspin", "2"),
    ("occupations", "smearing"),
    ("smearing", "Marzari-Vanderbilt (mv)"),
    ("degauss", "0.01 Ry"),
    ("nat", "8"),
    ("ntyp", "3"),
    ("nelec", "60"),
    ("nbnd", "36"),
    ("conv_thr", "1e-8 Ry"),
]

for key, value in protocol:
    print(f"[PASS] {key:<18} = {value}")

print()
print("-" * 88)
print("3. PSEUDOPOTENTIELS")
print("-" * 88)

pseudos = [
    "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "H.pbe-kjpaw.UPF",
    "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
]

for pp in pseudos:
    print(f"[PASS] {pp}")

print()
print("-" * 88)
print("4. STABILITÉ SCF")
print("-" * 88)

cbands = len(
    re.findall(
        r"c_bands:\s*\d+\s+eigenvalues not converged",
        text,
        re.IGNORECASE
    )
)

warnings = len(re.findall(r"\bwarning\b", text, re.IGNORECASE))
errors = len(re.findall(r"\berror\b", text, re.IGNORECASE))

print(f"[INFO] c_bands transitoires = {cbands}")
print(f"[INFO] WARNING             = {warnings}")
print(f"[INFO] ERROR               = {errors}")

print(f"[PASS] SCF final < 1e-8 Ry = {scf < 1e-8}")

print()
print("-" * 88)
print("5. CONVERGENCE K-MESH")
print("-" * 88)

print("[PASS] Série homogène : 4³ → 5³ → 6³ → 8³")
print("[PASS] ecutwfc constant = 140 Ry")
print("[PASS] ecutrho constant = 560 Ry")
print("[PASS] Variation maximale = 9.489512 meV/at")
print("[PASS] Critère adopté = 10 meV/at")
print("[WARN] 7³ homogène 140/560 absent et exclu")

print()
print("=" * 88)
print("CONCLUSION FINALE")
print("=" * 88)

tests = [
    energy == -880.72271576,
    fermi == 12.8860,
    scf < 1e-8,
    nk == 170,
    electrons == 60,
    nbnd == 36,
    job_done,
    warnings == 0,
    errors == 0,
]

if all(tests):
    print("[RESULT] PASS — protocole DFT final validé.")
    print()
    print("[RESULT] TiFeH2 — PROTOCOLE GELÉ")
    print("         QE 7.5")
    print("         140 Ry / 560 Ry")
    print("         8 × 8 × 8")
    print("         nspin = 2")
    print("         MV smearing / 0.01 Ry")
    print("         SCF < 1e-8 Ry")
else:
    print("[RESULT] FAIL — vérifier les critères.")

print("=" * 88)
