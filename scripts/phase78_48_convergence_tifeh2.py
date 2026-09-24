#!/usr/bin/env python3

from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/top5_dft/TiFeH2"
WORK = ROOT / "calculations/phase78_48_convergence/TiFeH2"
QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

REFERENCE = BASE / "TiFeH2_scf_run.in"

CUTOFFS = [60, 80, 100]
KPOINTS = [(2, 2, 2), (3, 3, 3), (4, 4, 4)]

print("=" * 78)
print("PHASE 78.48 — CONVERGENCE DFT TiFeH2")
print("=" * 78)
print("[INFO] Calculs DFT réels")
print("[INFO] Les fichiers scientifiques existants ne sont pas modifiés")
print()

if not QE.exists():
    print(f"[ERROR] pw.x introuvable : {QE}")
    sys.exit(1)

if not REFERENCE.exists():
    print(f"[ERROR] Input de référence introuvable : {REFERENCE}")
    sys.exit(1)

WORK.mkdir(parents=True, exist_ok=True)

template = REFERENCE.read_text()

def replace_or_fail(text, pattern, replacement, label):
    new = re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if new == text:
        raise RuntimeError(f"Impossible de remplacer {label}")
    return new

def make_input(ecut, kx, ky, kz):
    text = template

    text = replace_or_fail(
        text,
        r"^\s*ecutwfc\s*=\s*[-+0-9.eE]+\s*,?",
        f"    ecutwfc = {ecut},",
        "ecutwfc",
    )

    text = replace_or_fail(
        text,
        r"^\s*K_POINTS\s+automatic\s*\n\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+",
        f"K_POINTS automatic\n {kx} {ky} {kz} 0 0 0",
        "K_POINTS",
    )

    # Isoler chaque calcul
    text = re.sub(
        r"prefix\s*=\s*['\"][^'\"]+['\"]",
        "prefix = 'TiFeH2_conv'",
        text,
        count=1,
        flags=re.IGNORECASE,
    )

    return text

jobs = []

# 5 nouveaux calculs : le 60/2x2x2 existe déjà
for ecut in CUTOFFS:
    for kx, ky, kz in KPOINTS:
        if ecut == 60 and (kx, ky, kz) == (2, 2, 2):
            continue

        name = f"ecut{ecut}_k{kx}{ky}{kz}"
        inp = WORK / f"{name}.in"
        out = WORK / f"{name}.out"

        inp.write_text(make_input(ecut, kx, ky, kz))
        jobs.append((name, inp, out))

print("===== CALCULS PRÉVUS =====")
print(f"Calculs nouveaux : {len(jobs)}")
for name, _, _ in jobs:
    print(f"  - {name}")
print()

for name, inp, out in jobs:
    print("-" * 78)
    print(f"[RUN] {name}")
    print(f"[IN ] {inp}")
    print(f"[OUT] {out}")

    with out.open("w") as fout:
        result = subprocess.run(
            [str(QE), "-in", str(inp)],
            stdout=fout,
            stderr=subprocess.STDOUT,
            cwd=str(WORK),
        )

    if result.returncode != 0:
        print(f"[ERROR] pw.x return code = {result.returncode}")
        continue

    data = out.read_text(errors="ignore")
    done = "JOB DONE." in data

    energies = re.findall(
        r"!\s+total energy\s+=\s+([-+0-9.]+)\s+Ry",
        data
    )

    fermis = re.findall(
        r"the Fermi energy is\s+([-+0-9.]+)\s+ev",
        data,
        flags=re.IGNORECASE,
    )

    print(f"[RESULT] JOB DONE = {done}")

    if energies:
        print(f"[RESULT] Energy finale = {energies[-1]} Ry")
    else:
        print("[WARN] Énergie finale non détectée")

    if fermis:
        print(f"[RESULT] Fermi = {fermis[-1]} eV")
    else:
        print("[WARN] Fermi non détecté")

print()
print("=" * 78)
print("PHASE 78.48 TERMINÉE")
print("=" * 78)
print(f"[INFO] Résultats : {WORK}")
