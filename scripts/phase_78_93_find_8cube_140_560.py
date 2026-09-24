#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

print("=" * 78)
print("PHASE 78.93 — LOCALISATION DU 8³ HOMOGÈNE 140/560")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier modifié")
print()

patterns = [
    "*k888*.out",
    "*k888*.OUT",
    "*888*.out",
]

found = []

for pattern in patterns:
    for p in BASE.glob(f"calculations/**/{pattern}"):
        if p not in found:
            found.append(p)

for p in sorted(found):

    text = p.read_text(errors="replace")

    ecutwfc = re.findall(
        r"ecutwfc\s*=\s*([0-9.eEdD+-]+)", text, re.I
    )
    ecutrho = re.findall(
        r"ecutrho\s*=\s*([0-9.eEdD+-]+)", text, re.I
    )

    energies = re.findall(
        r"!\s+total energy\s*=\s*([-+0-9.eEdD]+)\s+Ry",
        text,
        re.I
    )

    ef = re.findall(
        r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev",
        text,
        re.I
    )

    job = "JOB DONE" in text

    ew = ecutwfc[-1] if ecutwfc else "?"
    er = ecutrho[-1] if ecutrho else "?"
    en = energies[-1] if energies else "?"
    fe = ef[-1] if ef else "?"

    print("-" * 78)
    print(f"[FILE] {p}")
    print(f"[INFO] ecutwfc = {ew}")
    print(f"[INFO] ecutrho = {er}")
    print(f"[INFO] E       = {en} Ry")
    print(f"[INFO] EF      = {fe} eV")
    print(f"[INFO] JOB DONE = {job}")

    if ew.startswith("140") and er.startswith("560"):
        print("[PASS] CANDIDAT 8³ À 140/560")
    else:
        print("[INFO] Non homogène 140/560")

print()
print("=" * 78)
print("RÉSULTAT")
print("=" * 78)
print("[INFO] Le fichier 8³ doit être identifié avec ecutwfc=140 et ecutrho=560.")
print("[INFO] Aucun fallback 140/240 n'est accepté.")
print("=" * 78)
