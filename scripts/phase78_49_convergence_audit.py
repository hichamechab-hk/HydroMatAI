#!/usr/bin/env python3

from pathlib import Path
import re
import math

ROOT = Path("/home/hk/HydroMatAI")
WORK = ROOT / "calculations/phase78_48_convergence/TiFeH2"

print("=" * 78)
print("PHASE 78.49 — AUDIT QUANTITATIF DE CONVERGENCE TiFeH2")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

DATA = {
    (60, 2): (-880.83702817, 12.7006),
    (60, 3): (-880.73454370, 13.0638),
    (60, 4): (-880.72278362, 12.9486),
    (80, 2): (-880.84661122, 12.6403),
    (80, 3): (-880.74930446, 13.0615),
    (80, 4): (-880.73747129, 12.9468),
    (100, 2): (-880.84913613, 12.6399),
    (100, 3): (-880.75184042, 13.0611),
    (100, 4): (-880.74001252, 12.9466),
}

NAT = 8
RY_TO_EV = 13.605693009
EV_TO_MEV = 1000.0

print("===== 1. MATRICE DES ÉNERGIES =====")
print()
print(f"{'ecut':>6} {'2x2x2':>16} {'3x3x3':>16} {'4x4x4':>16}")
print("-" * 60)

for ecut in (60, 80, 100):
    vals = [DATA[(ecut, k)][0] for k in (2, 3, 4)]
    print(
        f"{ecut:>6} "
        f"{vals[0]:>16.8f} "
        f"{vals[1]:>16.8f} "
        f"{vals[2]:>16.8f}"
    )

print()
print("===== 2. CONVERGENCE CUTOFF =====")
print()

for k in (2, 3, 4):
    e60 = DATA[(60, k)][0]
    e80 = DATA[(80, k)][0]
    e100 = DATA[(100, k)][0]

    d60_80 = abs(e80 - e60)
    d80_100 = abs(e100 - e80)

    mevatom_60_80 = d60_80 * RY_TO_EV * EV_TO_MEV / NAT
    mevatom_80_100 = d80_100 * RY_TO_EV * EV_TO_MEV / NAT

    print(f"k = {k}x{k}x{k}")
    print(f"  60 -> 80 Ry  : {d60_80:.8f} Ry = {mevatom_60_80:.4f} meV/atom")
    print(f"  80 -> 100 Ry : {d80_100:.8f} Ry = {mevatom_80_100:.4f} meV/atom")

print()
print("===== 3. CONVERGENCE K-POINTS =====")
print()

for ecut in (60, 80, 100):
    e2 = DATA[(ecut, 2)][0]
    e3 = DATA[(ecut, 3)][0]
    e4 = DATA[(ecut, 4)][0]

    d23 = abs(e3 - e2)
    d34 = abs(e4 - e3)

    mevatom_23 = d23 * RY_TO_EV * EV_TO_MEV / NAT
    mevatom_34 = d34 * RY_TO_EV * EV_TO_MEV / NAT

    print(f"ecut = {ecut} Ry")
    print(f"  2x2x2 -> 3x3x3 : {d23:.8f} Ry = {mevatom_23:.3f} meV/atom")
    print(f"  3x3x3 -> 4x4x4 : {d34:.8f} Ry = {mevatom_34:.3f} meV/atom")

print()
print("===== 4. FERMI =====")
print()

for ecut in (60, 80, 100):
    print(
        f"ecut {ecut:3d} : "
        f"2x2x2={DATA[(ecut,2)][1]:.4f} eV | "
        f"3x3x3={DATA[(ecut,3)][1]:.4f} eV | "
        f"4x4x4={DATA[(ecut,4)][1]:.4f} eV"
    )

print()
print("===== 5. CONTRÔLE DES OUTPUTS =====")
print()

outputs = sorted(WORK.glob("*.out"))
print(f"Outputs trouvés : {len(outputs)}")

for out in outputs:
    text = out.read_text(errors="ignore")
    done = "JOB DONE." in text
    energies = re.findall(
        r"!\s+total energy\s+=\s+([-+0-9.]+)\s+Ry",
        text
    )

    print(
        f"{out.name:25s} "
        f"JOB DONE={str(done):5s} "
        f"ENERGY={'OK' if energies else 'MISSING'}"
    )

print()
print("===== 6. INTERPRÉTATION =====")
print()

cutoff_max = 0.0
for k in (2, 3, 4):
    d = abs(DATA[(100, k)][0] - DATA[(80, k)][0])
    cutoff_max = max(cutoff_max, d * RY_TO_EV * EV_TO_MEV / NAT)

kpoint_34 = max(
    abs(DATA[(ecut,4)][0] - DATA[(ecut,3)][0])
    * RY_TO_EV * EV_TO_MEV / NAT
    for ecut in (60, 80, 100)
)

print(f"Variation maximale 80 -> 100 Ry : {cutoff_max:.4f} meV/atom")
print(f"Variation maximale 3x3x3 -> 4x4x4 : {kpoint_34:.3f} meV/atom")
print()

if cutoff_max < 1.0:
    print("[OK] CUTOFF : 100 Ry montre une forte stabilité énergétique.")
else:
    print("[WARN] CUTOFF : convergence encore insuffisante.")

if kpoint_34 > 1.0:
    print("[WARN] K-POINTS : 4x4x4 ne démontre pas encore une convergence à 1 meV/atom.")
    print("[NEXT] Une série 5x5x5 est nécessaire.")
else:
    print("[OK] K-POINTS : 4x4x4 compatible avec le seuil choisi.")

print()
print("=" * 78)
print("PHASE 78.49 TERMINÉE")
print("=" * 78)
