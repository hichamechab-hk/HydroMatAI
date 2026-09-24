#!/usr/bin/env python3

from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")

DIRS = [
    ROOT / "calculations/phase78_48_convergence/TiFeH2",
    ROOT / "calculations/phase78_50_convergence/TiFeH2",
]

print("=" * 78)
print("PHASE 78.51 — AUDIT STRUCTUREL DES INPUTS DE CONVERGENCE TiFeH2")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

def extract(text, pattern, default="NOT_FOUND"):
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1).strip() if m else default

for directory in DIRS:
    print("=" * 78)
    print(f"DIRECTORY : {directory}")
    print("=" * 78)

    inputs = sorted(directory.glob("*.in"))

    if not inputs:
        print("[WARN] Aucun input")
        continue

    for inp in inputs:
        text = inp.read_text(errors="ignore")

        ecut = extract(
            text,
            r"^\s*ecutwfc\s*=\s*([0-9.+\-eEdD]+)"
        )

        degauss = extract(
            text,
            r"^\s*degauss\s*=\s*([0-9.+\-eEdD]+)"
        )

        occupations = extract(
            text,
            r"^\s*occupations\s*=\s*['\"]([^'\"]+)['\"]"
        )

        smearing = extract(
            text,
            r"^\s*smearing\s*=\s*['\"]([^'\"]+)['\"]"
        )

        nspin = extract(
            text,
            r"^\s*nspin\s*=\s*([0-9]+)"
        )

        prefix = extract(
            text,
            r"^\s*prefix\s*=\s*['\"]([^'\"]+)['\"]"
        )

        kmatch = re.search(
            r"K_POINTS\s+automatic\s*\n\s*"
            r"([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+"
            r"([0-9]+)\s+([0-9]+)\s+([0-9]+)",
            text,
            re.I
        )

        kpoints = (
            f"{kmatch.group(1)}x{kmatch.group(2)}x{kmatch.group(3)}"
            if kmatch else "NOT_FOUND"
        )

        pseudo_dir = extract(
            text,
            r"^\s*pseudo_dir\s*=\s*['\"]([^'\"]+)['\"]"
        )

        print(f"\n{inp.name}")
        print(f"  ecutwfc    = {ecut}")
        print(f"  kpoints    = {kpoints}")
        print(f"  degauss    = {degauss}")
        print(f"  occupations= {occupations}")
        print(f"  smearing   = {smearing}")
        print(f"  nspin      = {nspin}")
        print(f"  prefix     = {prefix}")
        print(f"  pseudo_dir = {pseudo_dir}")

print()
print("=" * 78)
print("PHASE 78.51 TERMINÉE")
print("=" * 78)
