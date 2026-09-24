#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
OUT = BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out"
IN_CANDIDATES = [
    BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in",
    BASE / "calculations/phase78_63_convergence/TiFeH2/ecut140_rho560_k888.in",
]

print("=" * 88)
print("PHASE 78.95 — AUDIT FINAL DU PROTOCOLE DFT TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

if not OUT.exists():
    print("[ERROR] Sortie 8³ 140/560 introuvable")
    raise SystemExit(1)

text = OUT.read_text(errors="ignore")

def find(pattern, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def check(label, value, expected=None):
    if expected is None:
        print(f"[INFO] {label:<28} = {value}")
    else:
        ok = value == expected
        print(f"[{'PASS' if ok else 'FAIL'}] {label:<28} = {value}")

print("-" * 88)
print("1. CALCUL FINAL 8³")
print("-" * 88)

energy = find(r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry")
fermi = find(r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev")
scf = find(r"estimated scf accuracy\s*<\s*([-+0-9.Ee]+)\s+Ry")
nk = find(r"number of k points=\s*(\d+)")
job = "JOB DONE." in text

check("Énergie finale (Ry)", energy)
check("Fermi energy (eV)", fermi)
check("SCF accuracy (Ry)", scf)
check("K-points irréductibles", nk)
check("JOB DONE", job, True)

print()
print("-" * 88)
print("2. PARAMÈTRES PHYSIQUES")
print("-" * 88)

for label, pattern, expected in [
    ("ecutwfc", r"ecutwfc\s*=\s*([0-9.]+)", "140"),
    ("ecutrho", r"ecutrho\s*=\s*([0-9.]+)", "560"),
    ("nat", r"\bnat\s*=\s*(\d+)", "8"),
    ("ntyp", r"\bntyp\s*=\s*(\d+)", "3"),
    ("nspin", r"\bnspin\s*=\s*(\d+)", "2"),
    ("degauss", r"degauss\s*=\s*([0-9.]+)", "0.01"),
    ("nbnd", r"\bnbnd\s*=\s*(\d+)", "36"),
]:
    v = find(pattern)
    if v is None:
        print(f"[WARN] {label:<28} = non extrait")
    else:
        check(label, v, expected)

print()
print("-" * 88)
print("3. OCCUPATIONS / SMEARING")
print("-" * 88)

for term in ["occupations = 'smearing'", "smearing = 'mv'"]:
    ok = term.lower() in text.lower()
    print(f"[{'PASS' if ok else 'WARN'}] {term}")

print()
print("-" * 88)
print("4. ÉLECTRONS / ÉTATS")
print("-" * 88)

electrons = find(r"number of electrons\s*=\s*([0-9.]+)")
ks = find(r"number of Kohn-Sham states\s*=\s*(\d+)")

check("Électrons", electrons, "60.0000")
check("États Kohn-Sham", ks, "36")

print()
print("-" * 88)
print("5. PSEUDOPOTENTIELS")
print("-" * 88)

required_pp = [
    "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "H.pbe-kjpaw.UPF",
    "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
]

for pp in required_pp:
    ok = pp in text
    print(f"[{'PASS' if ok else 'FAIL'}] {pp}")

print()
print("-" * 88)
print("6. STABILITÉ NUMÉRIQUE")
print("-" * 88)

cbands = len(re.findall(r"c_bands:\s*\d+\s+eigenvalues not converged", text))
warnings = len(re.findall(r"warning", text, re.I))
errors = len(re.findall(r"\berror\b", text, re.I))

print(f"[INFO] Événements c_bands      = {cbands}")
print(f"[INFO] Occurrences WARNING     = {warnings}")
print(f"[INFO] Occurrences ERROR       = {errors}")

if scf:
    scf_value = float(scf)
    print(f"[{'PASS' if scf_value < 1e-8 else 'FAIL'}] SCF < 1e-8 Ry")

print()
print("-" * 88)
print("7. PROTOCOLE FINAL RETENU")
print("-" * 88)

protocol = [
    ("Code", "Quantum ESPRESSO 7.5"),
    ("ecutwfc", "140 Ry"),
    ("ecutrho", "560 Ry"),
    ("k-mesh", "8 × 8 × 8"),
    ("Spin", "nspin = 2"),
    ("Occupations", "Marzari-Vanderbilt smearing"),
    ("degauss", "0.01 Ry"),
    ("nat", "8"),
    ("ntyp", "3"),
    ("nbnd", "36"),
    ("SCF threshold", "< 1e-8 Ry"),
]

for k, v in protocol:
    print(f"[INFO] {k:<18} : {v}")

print()
print("=" * 88)
print("CONCLUSION")
print("=" * 88)

critical = [
    energy is not None,
    fermi is not None,
    scf is not None and float(scf) < 1e-8,
    nk == "170",
    job,
    electrons is not None,
    ks == "36",
]

if all(critical):
    print("[RESULT] PASS — calcul final 8³/140/560 exploitable.")
else:
    print("[RESULT] FAIL — vérifier les paramètres critiques.")

print()
print("[INFO] Énergie finale attendue : -880.72271576 Ry")
print("[INFO] EF attendu              : 12.8860 eV")
print("[INFO] k-points irréductibles  : 170")
print()
print("[WARN] La convergence k-mesh reste documentée avec")
print("       4³ → 5³ → 6³ → 8³ ; le 7³ homogène 140/560")
print("       n'est pas disponible et reste exclu.")
print()
print("[RESULT] PROTOCOLE À UTILISER POUR LA SUITE :")
print("         140 Ry / 560 Ry / 8×8×8 / nspin=2 / MV 0.01")
print("=" * 88)
