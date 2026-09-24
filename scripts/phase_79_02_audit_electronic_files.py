#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
DIR = BASE / "calculations/top5_dft/TiFeH2/electronic"

print("=" * 88)
print("PHASE 79.02 — AUDIT NSCF / BANDS / DOS TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun dos.x")
print("[INFO] Aucun fichier modifié")
print()

FILES = [
    DIR / "TiFeH2_nscf.in",
    DIR / "TiFeH2_nscf.out",
    DIR / "TiFeH2_bands.in",
    DIR / "TiFeH2_bands.out",
    DIR / "TiFeH2_dos.in",
    DIR / "TiFeH2_dos.out",
    DIR / "TiFeH2.dos",
    DIR / "CRASH",
]

def read(p):
    return p.read_text(errors="ignore") if p.exists() else ""

def extract(text, pattern):
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1) if m else None

def show_file(p):
    print("-" * 88)
    print(f"[FILE] {p}")

    if not p.exists():
        print("[WARN] ABSENT")
        return ""

    text = read(p)
    print(f"[INFO] Taille = {p.stat().st_size} octets")
    print(f"[INFO] Lignes = {len(text.splitlines())}")
    return text

texts = {}

for p in FILES:
    texts[p.name] = show_file(p)

# ----------------------------------------------------------------------
# NSCF INPUT
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("1. TiFeH2_nscf.in")
print("=" * 88)

t = texts["TiFeH2_nscf.in"]

if t:
    patterns = [
        ("prefix", r"prefix\s*=\s*['\"]([^'\"]+)"),
        ("outdir", r"outdir\s*=\s*['\"]([^'\"]+)"),
        ("pseudo_dir", r"pseudo_dir\s*=\s*['\"]([^'\"]+)"),
        ("ecutwfc", r"ecutwfc\s*=\s*([0-9.]+)"),
        ("ecutrho", r"ecutrho\s*=\s*([0-9.]+)"),
        ("nbnd", r"nbnd\s*=\s*(\d+)"),
        ("nspin", r"nspin\s*=\s*(\d+)"),
        ("degauss", r"degauss\s*=\s*([0-9.]+)"),
        ("conv_thr", r"conv_thr\s*=\s*([0-9.Ee+-]+)"),
    ]

    for name, pat in patterns:
        v = extract(t, pat)
        print(f"[INFO] {name:<12} = {v if v else '?'}")

    if re.search(r"K_POINTS\s+automatic", t, re.I):
        print("[INFO] K_POINTS automatic détecté")

    if re.search(r"K_POINTS\s+crystal", t, re.I):
        print("[INFO] K_POINTS crystal détecté")

# ----------------------------------------------------------------------
# NSCF OUTPUT
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("2. TiFeH2_nscf.out")
print("=" * 88)

t = texts["TiFeH2_nscf.out"]

if t:
    for name, pat in [
        ("energy",
         r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry"),
        ("fermi",
         r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev"),
        ("nbnd",
         r"number of Kohn-Sham states\s*=\s*(\d+)"),
        ("electrons",
         r"number of electrons\s*=\s*([-+0-9.Ee]+)"),
        ("nk",
         r"number of k points=\s*(\d+)"),
    ]:
        v = extract(t, pat)
        print(f"[INFO] {name:<12} = {v if v else '?'}")

    print(f"[INFO] JOB DONE = {'JOB DONE.' in t}")

# ----------------------------------------------------------------------
# BANDS INPUT / OUTPUT
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("3. BANDS")
print("=" * 88)

for name in ["TiFeH2_bands.in", "TiFeH2_bands.out"]:
    t = texts[name]

    if not t:
        continue

    print(f"[INFO] {name}")

    for label, pat in [
        ("prefix",
         r"prefix\s*=\s*['\"]([^'\"]+)"),
        ("outdir",
         r"outdir\s*=\s*['\"]([^'\"]+)"),
        ("filband",
         r"filband\s*=\s*['\"]([^'\"]+)"),
        ("JOB DONE",
         r"JOB DONE\."),
        ("ERROR",
         r"\berror\b"),
    ]:
        if label == "JOB DONE":
            print(f"[INFO] JOB DONE = {bool(re.search(pat, t, re.I))}")
        elif label == "ERROR":
            print(f"[INFO] ERROR = {len(re.findall(pat, t, re.I))}")
        else:
            print(f"[INFO] {label:<12} = {extract(t, pat) or '?'}")

# ----------------------------------------------------------------------
# DOS INPUT / OUTPUT
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("4. DOS")
print("=" * 88)

for name in ["TiFeH2_dos.in", "TiFeH2_dos.out"]:
    t = texts[name]

    if not t:
        continue

    print(f"[INFO] {name}")

    for label, pat in [
        ("prefix",
         r"prefix\s*=\s*['\"]([^'\"]+)"),
        ("outdir",
         r"outdir\s*=\s*['\"]([^'\"]+)"),
        ("fildos",
         r"fildos\s*=\s*['\"]([^'\"]+)"),
        ("JOB DONE",
         r"JOB DONE\."),
        ("ERROR",
         r"\berror\b"),
    ]:
        if label == "JOB DONE":
            print(f"[INFO] JOB DONE = {bool(re.search(pat, t, re.I))}")
        elif label == "ERROR":
            print(f"[INFO] ERROR = {len(re.findall(pat, t, re.I))}")
        else:
            print(f"[INFO] {label:<12} = {extract(t, pat) or '?'}")

# ----------------------------------------------------------------------
# CRASH
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("5. CRASH")
print("=" * 88)

crash = texts["CRASH"]

if crash:
    print("[WARN] Fichier CRASH présent")
    print("[INFO] Contenu :")
    print(crash[:3000])
else:
    print("[PASS] Aucun fichier CRASH")

# ----------------------------------------------------------------------
# DECISION
# ----------------------------------------------------------------------

print()
print("=" * 88)
print("DÉCISION PHASE 79.02")
print("=" * 88)

print("[INFO] Les anciens NSCF/BANDS/DOS ne seront pas considérés")
print("       comme résultats finaux avant vérification du parent SCF.")
print()
print("[INFO] Référence finale obligatoire :")
print("       ecutwfc = 140 Ry")
print("       ecutrho = 560 Ry")
print("       k = 8 × 8 × 8")
print("       nspin = 2")
print("       nbnd = 36")
print("       EF = 12.8860 eV")
print()
print("[RESULT] Aucun calcul exécuté.")
print("=" * 88)
