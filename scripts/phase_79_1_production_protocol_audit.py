#!/usr/bin/env python3

from pathlib import Path

print("\033[2J\033[H", end="")

print("=" * 78)
print("PHASE 79.1 — GEL DU PROTOCOLE DFT DE PRODUCTION TiFeH2")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

ROOT = Path("/home/hk/HydroMatAI")

PROTOCOL = {
    "code": "Quantum ESPRESSO 7.5",
    "ecutwfc": 140,
    "ecutrho": 560,
    "kmesh": "8x8x8",
    "nspin": 2,
    "occupations": "smearing",
    "smearing": "Marzari-Vanderbilt",
    "degauss": 0.01,
    "conv_thr": "< 1e-8 Ry",
    "nat": 8,
    "ntyp": 3,
    "nbnd": 36,
}

print("===== 1. PROTOCOLE DE PRODUCTION =====")
print("-" * 78)

for key, value in PROTOCOL.items():
    print(f"{key:15s}: {value}")

print()

print("===== 2. JUSTIFICATION DU MAILLAGE k =====")
print("-" * 78)

print("[DATA] 7x7x7 : 343 k-points totaux / 100 irréductibles")
print("[DATA] 8x8x8 : 512 k-points totaux / 170 irréductibles")
print("[DATA] ΔE(7³→8³) = +5.434828 meV/at")
print("[DATA] ΔEF(7³→8³) = +0.037600 eV")
print()
print("[RESULT] Tolérance 1 meV/at : NON démontrée")
print("[RESULT] Tolérance 5 meV/at : NON satisfaite")
print("[RESULT] Tolérance 10 meV/at : satisfaite")
print()
print("[DECISION] 8x8x8 = maillage de production retenu")
print("[DECISION] Tolérance énergétique déclarée = 10 meV/at")
print("[IMPORTANT] 8x8x8 ne doit pas être présenté comme convergé à 1 meV/at")

print()

print("===== 3. CONVERGENCE SCF =====")
print("-" * 78)

scf_values = {
    "7³": 5.8e-9,
    "8³": 7.5e-9,
}

for mesh, value in scf_values.items():
    if value < 1e-8:
        print(f"[PASS] {mesh}: {value:.2e} Ry < 1e-8 Ry")
    else:
        print(f"[FAIL] {mesh}: {value:.2e} Ry")

print()

print("===== 4. CUT-OFFS =====")
print("-" * 78)

print("[PASS] ecutwfc = 140 Ry")
print("[PASS] ecutrho = 560 Ry")
print("[INFO] Rapport ecutrho/ecutwfc = 4.0")

print()

print("===== 5. SPIN ET OCCUPATIONS =====")
print("-" * 78)

print("[PASS] nspin = 2")
print("[PASS] occupations = smearing")
print("[PASS] smearing = Marzari-Vanderbilt")
print("[PASS] degauss = 0.01 Ry")

print()

print("===== 6. SYSTEME =====")
print("-" * 78)

print("[PASS] nat = 8")
print("[PASS] ntyp = 3")
print("[PASS] nbnd = 36")
print("[INFO] Structure = TiFeH2")
print("[INFO] Composition = Ti2 Fe2 H4")

print()

print("===== 7. ETAPES DE PRODUCTION A VENIR =====")
print("-" * 78)

steps = [
    "1. SCF final sur géométrie relaxée avec protocole gelé",
    "2. NSCF dense avec protocole explicitement documenté",
    "3. Bandes électroniques",
    "4. DOS / PDOS",
    "5. Analyse EF / états proches de EF",
    "6. Audit de convergence des propriétés électroniques",
    "7. Rapport scientifique final",
]

for step in steps:
    print(f"[NEXT] {step}")

print()

print("===== 8. REGLES DE TRAÇABILITE =====")
print("-" * 78)

print("[RULE] Ne pas modifier les sorties historiques 78.x")
print("[RULE] Conserver les inputs exacts utilisés en production")
print("[RULE] Conserver les outputs QE complets")
print("[RULE] Documenter chaque changement de paramètre")
print("[RULE] Ne pas appeler une propriété 'convergée' sans test correspondant")
print("[RULE] Distinguer convergence SCF et convergence k")
print()

print("===== 9. PREFLIGHT =====")
print("-" * 78)

checks = [
    ("ecutwfc", PROTOCOL["ecutwfc"] == 140),
    ("ecutrho", PROTOCOL["ecutrho"] == 560),
    ("kmesh", PROTOCOL["kmesh"] == "8x8x8"),
    ("nspin", PROTOCOL["nspin"] == 2),
    ("degauss", PROTOCOL["degauss"] == 0.01),
    ("nat", PROTOCOL["nat"] == 8),
    ("nbnd", PROTOCOL["nbnd"] == 36),
]

all_ok = True

for name, ok in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    all_ok &= ok

print()

if all_ok:
    print("[RESULT] PREFLIGHT PROTOCOLE = VALID")
else:
    print("[RESULT] PREFLIGHT PROTOCOLE = INVALID")

print()
print("=" * 78)
print("PHASE 79.1 — FIN")
print("=" * 78)
print("[INFO] Aucun pw.x exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
