#!/usr/bin/env python3

import os
import re
from pathlib import Path

print("\033[2J\033[H", end="")

print("=" * 78)
print("PHASE 79.0B — AUDIT CIBLE DU MAILLAGE 7³ ↔ 8³")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

ROOT = Path("/home/hk/HydroMatAI")

TARGETS = {
    "7³": [
        ROOT / "calculations/top5_dft/TiFeH2/ecut140_rho560_k777_phase78_55.out",
        ROOT / "calculations/top5_dft/TiFeH2/ecut140_rho560_k777_phase78_55.out",
    ],
    "8³": [
        ROOT / "calculations/top5_dft/TiFeH2/ecut140_rho560_k888_phase78_63.out",
        ROOT / "calculations/top5_dft/TiFeH2/ecut140_rho560_k888_phase78_63.out",
    ],
}


def find_existing(candidates, mesh):
    for p in candidates:
        if p.exists():
            return p

    patterns = {
        "7³": ["*k777*.out", "*k777*.txt"],
        "8³": ["*k888*.out", "*k888*.txt"],
    }

    found = []
    for pattern in patterns[mesh]:
        found.extend(ROOT.rglob(pattern))

    if found:
        return sorted(found)[0]

    return None


def read_output(path):
    text = path.read_text(errors="replace")

    result = {
        "energy": None,
        "fermi": None,
        "scf": None,
        "smearing": None,
        "nat": None,
        "nbnd": None,
        "ecutwfc": None,
        "ecutrho": None,
        "nspin": None,
        "nk": None,
        "cbands": 0,
        "iterations": None,
        "job_done": "JOB DONE" in text,
        "warnings": [],
        "lines": len(text.splitlines()),
        "bytes": path.stat().st_size,
    }

    patterns = {
        "energy": [
            r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry",
        ],
        "fermi": [
            r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev",
            r"the Fermi energy is\s+([-+0-9.Ee]+)\s+eV",
        ],
        "scf": [
            r"estimated scf accuracy\s+<\s*([-+0-9.Ee]+)\s+Ry",
        ],
        "smearing": [
            r"\(-TS\)\s*=\s*([-+0-9.Ee]+)\s+Ry",
        ],
        "nat": [
            r"\bnat\s*=\s*(\d+)",
        ],
        "nbnd": [
            r"\bnbnd\s*=\s*(\d+)",
        ],
        "ecutwfc": [
            r"\becutwfc\s*=\s*([-+0-9.Ee]+)",
        ],
        "ecutrho": [
            r"\becutrho\s*=\s*([-+0-9.Ee]+)",
        ],
        "nspin": [
            r"\bnspin\s*=\s*(\d+)",
        ],
    }

    for key, plist in patterns.items():
        for pat in plist:
            matches = re.findall(pat, text, flags=re.I)
            if matches:
                try:
                    result[key] = float(matches[-1])
                    if key in ("nat", "nbnd", "nspin"):
                        result[key] = int(result[key])
                except ValueError:
                    pass
                break

    nk_matches = re.findall(
        r"number of k points\s*=\s*(\d+)", text, flags=re.I
    )
    if nk_matches:
        result["nk"] = int(nk_matches[-1])

    result["cbands"] = len(
        re.findall(r"c_bands:\s+\d+\s+eigenvalues", text, flags=re.I)
    )

    iter_matches = re.findall(
        r"iteration\s*#\s*(\d+)", text, flags=re.I
    )
    if iter_matches:
        result["iterations"] = int(iter_matches[-1])

    for line in text.splitlines():
        low = line.lower()
        if "warning" in low or "error" in low:
            result["warnings"].append(line.strip())

    return result


print("===== 1. LOCALISATION DES SORTIES =====")
print("-" * 78)

files = {}

for mesh in ("7³", "8³"):
    path = find_existing(TARGETS[mesh], mesh)

    if path is None:
        print(f"[ERROR] Sortie {mesh} introuvable")
    else:
        files[mesh] = path
        print(f"[OK] {mesh} : {path}")

print()

if len(files) != 2:
    print("[ERROR] Les deux sorties 7³ et 8³ sont nécessaires.")
    print("[INFO] Aucun calcul lancé.")
    raise SystemExit(1)


print("===== 2. EXTRACTION DES PARAMETRES =====")
print("-" * 78)

data = {}

for mesh, path in files.items():
    data[mesh] = read_output(path)

    d = data[mesh]

    print()
    print(f"--- {mesh} ---")
    print(f"fichier       : {path}")
    print(f"lignes        : {d['lines']}")
    print(f"octets        : {d['bytes']}")
    print(f"energy        : {d['energy']} Ry")
    print(f"Fermi         : {d['fermi']} eV")
    print(f"SCF accuracy  : {d['scf']} Ry")
    print(f"(-TS)         : {d['smearing']} Ry")
    print(f"ecutwfc       : {d['ecutwfc']} Ry")
    print(f"ecutrho       : {d['ecutrho']} Ry")
    print(f"nat           : {d['nat']}")
    print(f"nbnd          : {d['nbnd']}")
    print(f"nspin         : {d['nspin']}")
    print(f"k-points irr. : {d['nk']}")
    print(f"c_bands       : {d['cbands']}")
    print(f"iterations    : {d['iterations']}")
    print(f"JOB DONE      : {'YES' if d['job_done'] else 'NO'}")

print()


print("===== 3. COMPARAISON 7³ ↔ 8³ =====")
print("-" * 78)

d7 = data["7³"]
d8 = data["8³"]

if d7["energy"] is not None and d8["energy"] is not None:
    de_cell = d8["energy"] - d7["energy"]
    de_atom = de_cell / 8.0
    print(f"ΔE(8³-7³) cellule : {de_cell:+.10f} Ry")
    print(f"ΔE(8³-7³) / atom  : {de_atom * 13605.693:.6f} meV/at")
else:
    print("[WARN] Énergie absente pour une des deux sorties.")

if d7["fermi"] is not None and d8["fermi"] is not None:
    dfermi = d8["fermi"] - d7["fermi"]
    print(f"ΔEF(8³-7³)        : {dfermi:+.6f} eV")

if d7["smearing"] is not None and d8["smearing"] is not None:
    dts = d8["smearing"] - d7["smearing"]
    print(f"Δ(-TS)             : {dts:+.10f} Ry")
    print(f"Δ(-TS) / atom      : {dts * 13605.693 / 8.0:+.6f} meV/at")

print()


print("===== 4. VERIFICATION DE L'HOMOGENEITE NUMERIQUE =====")
print("-" * 78)

checks = [
    ("ecutwfc", d7["ecutwfc"], d8["ecutwfc"]),
    ("ecutrho", d7["ecutrho"], d8["ecutrho"]),
    ("nat", d7["nat"], d8["nat"]),
    ("nbnd", d7["nbnd"], d8["nbnd"]),
    ("nspin", d7["nspin"], d8["nspin"]),
]

for name, a, b in checks:
    if a == b:
        print(f"[OK]   {name:8s}: {a}")
    else:
        print(f"[WARN] {name:8s}: 7³={a} / 8³={b}")

print()


print("===== 5. CONVERGENCE SCF =====")
print("-" * 78)

for mesh in ("7³", "8³"):
    scf = data[mesh]["scf"]

    if scf is None:
        print(f"[WARN] {mesh}: précision SCF non extraite")
    elif scf < 1e-8:
        print(f"[OK]   {mesh}: SCF < 1e-8 Ry ({scf:.3e} Ry)")
    else:
        print(f"[WARN] {mesh}: SCF = {scf:.3e} Ry")

print()


print("===== 6. c_bands =====")
print("-" * 78)

for mesh in ("7³", "8³"):
    print(f"{mesh}: {data[mesh]['cbands']} événement(s) c_bands")

print()


print("===== 7. STATUT DES CALCULS =====")
print("-" * 78)

for mesh in ("7³", "8³"):
    if data[mesh]["job_done"]:
        print(f"[OK]   {mesh}: JOB DONE")
    else:
        print(f"[WARN] {mesh}: JOB DONE absent")

print()


print("===== 8. AVERTISSEMENTS BRUTS =====")
print("-" * 78)

for mesh in ("7³", "8³"):
    print(f"--- {mesh} ---")
    if data[mesh]["warnings"]:
        for w in data[mesh]["warnings"]:
            print(w)
    else:
        print("[OK] Aucun WARNING/ERROR textuel détecté")

print()


print("=" * 78)
print("PHASE 79.0B — FIN")
print("=" * 78)
print("[INFO] Audit terminé en lecture seule.")
print("[INFO] Aucun pw.x exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
