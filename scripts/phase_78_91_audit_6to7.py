#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    6: {
        "out": BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
        "in":  BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.in",
    },
    7: {
        "out": BASE / "calculations/phase78_55_convergence/TiFeH2/ecut140_k777.out",
        "in":  BASE / "calculations/phase78_55_convergence/TiFeH2/ecut140_k777.in",
    },
}

def find(pattern, text, flags=re.I | re.M):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def finds(pattern, text, flags=re.I | re.M):
    return re.findall(pattern, text, flags)

def read_input(path):
    return path.read_text(errors="replace") if path.exists() else ""

def read_output(path):
    return path.read_text(errors="replace") if path.exists() else ""

def parse(inp, out):
    text = inp + "\n" + out
    d = {}

    patterns = {
        "ecutwfc": r"ecutwfc\s*=\s*([0-9.eEdD+-]+)",
        "ecutrho": r"ecutrho\s*=\s*([0-9.eEdD+-]+)",
        "nat": r"\bnat\s*=\s*(\d+)",
        "ntyp": r"\bntyp\s*=\s*(\d+)",
        "nbnd": r"\bnbnd\s*=\s*(\d+)",
        "nspin": r"\bnspin\s*=\s*(\d+)",
        "degauss": r"degauss\s*=\s*([0-9.eEdD+-]+)",
        "conv_thr": r"conv_thr\s*=\s*([0-9.eEdD+-]+)",
        "mixing_beta": r"mixing_beta\s*=\s*([0-9.eEdD+-]+)",
    }

    for key, pattern in patterns.items():
        vals = finds(pattern, text)
        d[key] = vals[-1] if vals else None

    d["occupations"] = find(
        r"occupations\s*=\s*['\"]?([^,'\"\s]+)", text
    )
    d["smearing"] = find(
        r"smearing\s*=\s*['\"]?([^,'\"\s]+)", text
    )

    d["energy"] = (
        finds(r"!\s+total energy\s*=\s*([-+0-9.eEdD]+)\s+Ry", out)[-1]
        if finds(r"!\s+total energy\s*=\s*([-+0-9.eEdD]+)\s+Ry", out)
        else None
    )

    ef = finds(r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev", out)
    d["ef"] = ef[-1] if ef else None

    ne = finds(r"number of electrons\s*=\s*([-+0-9.eEdD]+)", out)
    d["electrons"] = ne[-1] if ne else None

    ks = finds(r"number of Kohn-Sham states\s*=\s*(\d+)", out)
    d["ks"] = ks[-1] if ks else None

    d["ts"] = find(r"\(-TS\)\s*=\s*([-+0-9.eEdD]+)", out)

    pseudo = re.findall(
        r"^\s*([A-Za-z][A-Za-z0-9_]*)\s+\d+(?:\.\d+)?\s+(\S+\.UPF)\s*$",
        inp,
        re.M
    )
    d["pseudos"] = pseudo

    d["cbands"] = len(re.findall(r"c_bands:", out, re.I))
    d["warnings"] = len(re.findall(r"\bWARNING\b", out, re.I))
    d["errors"] = len(re.findall(r"\bERROR\b", out, re.I))
    d["job_done"] = "JOB DONE" in out

    return d

def fnum(x):
    if x is None:
        return None
    return float(x.replace("D", "E").replace("d", "e"))

print("=" * 78)
print("PHASE 78.91 — AUDIT DE CONTINUITÉ 6³ → 7³")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

DATA = {}

for k in (6, 7):
    inp_path = FILES[k]["in"]
    out_path = FILES[k]["out"]

    print("-" * 78)
    print(f"MAILLAGE {k}³")
    print("-" * 78)
    print(f"[INFO] INPUT  : {inp_path}")
    print(f"[INFO] OUTPUT : {out_path}")

    if not inp_path.exists():
        print("[ERROR] INPUT absent")
        continue

    if not out_path.exists():
        print("[ERROR] OUTPUT absent")
        continue

    inp = read_input(inp_path)
    out = read_output(out_path)

    d = parse(inp, out)
    DATA[k] = d

    print()
    print("[PARAMÈTRES]")

    for key in (
        "ecutwfc",
        "ecutrho",
        "nat",
        "ntyp",
        "nbnd",
        "nspin",
        "occupations",
        "smearing",
        "degauss",
        "conv_thr",
        "mixing_beta",
    ):
        print(f"  {key:14s}: {d[key]}")

    print()
    print("[SYSTÈME]")
    print(f"  électrons     : {d['electrons']}")
    print(f"  KS states     : {d['ks']}")

    print()
    print("[PSEUDOS]")
    for species, pseudo in d["pseudos"]:
        print(f"  {species:4s}: {pseudo}")

    print()
    print("[RÉSULTATS]")
    print(f"  E             : {d['energy']} Ry")
    print(f"  EF            : {d['ef']} eV")
    print(f"  (-TS)         : {d['ts']} Ry")

    print()
    print("[DIAGNOSTIC]")
    print(f"  c_bands       : {d['cbands']}")
    print(f"  WARNING       : {d['warnings']}")
    print(f"  ERROR         : {d['errors']}")
    print(f"  JOB DONE      : {d['job_done']}")

print()
print("=" * 78)
print("COMPARAISON 6³ ↔ 7³")
print("=" * 78)

if 6 in DATA and 7 in DATA:

    A = DATA[6]
    B = DATA[7]

    keys = (
        "ecutwfc",
        "ecutrho",
        "nat",
        "ntyp",
        "nbnd",
        "nspin",
        "occupations",
        "smearing",
        "degauss",
        "conv_thr",
        "mixing_beta",
        "electrons",
        "ks",
    )

    for key in keys:
        if A[key] == B[key]:
            print(f"[PASS] {key:14s}: {A[key]}")
        else:
            print(f"[DIFF] {key:14s}: 6³={A[key]} | 7³={B[key]}")

    print()
    print("[PSEUDOPOTENTIELS]")

    if A["pseudos"] == B["pseudos"]:
        print("[PASS] Identiques")
    else:
        print("[DIFF] Différents")
        print("  6³:", A["pseudos"])
        print("  7³:", B["pseudos"])

    print()
    print("[ÉNERGIE]")

    e6 = fnum(A["energy"])
    e7 = fnum(B["energy"])

    de_ry = e7 - e6
    de_mev = de_ry * 13.605693009 * 1000.0 / 8.0

    print(f"  E(6³) = {e6:.10f} Ry")
    print(f"  E(7³) = {e7:.10f} Ry")
    print(f"  ΔE    = {de_ry:+.10f} Ry")
    print(f"  ΔE/at = {de_mev:+.6f} meV/at")

    print()
    print("[FERMI]")

    ef6 = fnum(A["ef"])
    ef7 = fnum(B["ef"])

    print(f"  EF(6³) = {ef6:.6f} eV")
    print(f"  EF(7³) = {ef7:.6f} eV")
    print(f"  ΔEF    = {ef7 - ef6:+.6f} eV")

    print()
    print("[VERDICT]")

    differences = []

    for key in keys:
        if A[key] != B[key]:
            differences.append(key)

    if A["pseudos"] != B["pseudos"]:
        differences.append("pseudopotentiels")

    if differences:
        print("[WARN] Différences détectées :")
        for x in differences:
            print(f"  - {x}")
    else:
        print("[PASS] Aucun paramètre physique/computationnel comparé ne diffère.")

    print()
    print("[INFO] Le saut 6³ → 7³ de "
          f"{abs(de_mev):.6f} meV/at doit donc être interprété "
          "à partir des différences effectivement détectées ci-dessus.")

else:
    print("[ERROR] Impossible de comparer 6³ et 7³.")

print()
print("=" * 78)
print("PHASE 78.91 — FIN")
print("=" * 78)
print("[PASS] AUDIT READ-ONLY TERMINÉ")
print("=" * 78)
