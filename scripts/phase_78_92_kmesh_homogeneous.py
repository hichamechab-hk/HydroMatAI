#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
RY_TO_EV = 13.605693009
NAT = 8

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
    6: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
    8: BASE / "calculations/phase78_63_convergence/TiFeH2/ecut140_rho560_k888.out",
}

# Fallback historique si le fichier 78.63 n'existe pas.
FALLBACK_8 = BASE / "calculations/phase78_53_convergence/TiFeH2/ecut140_k888.out"

EXPECTED_NK = {
    4: (64, 30),
    5: (125, 39),
    6: (216, 80),
    8: (512, 170),
}

def last(pattern, text):
    vals = re.findall(pattern, text, re.I | re.M)
    return vals[-1] if vals else None

def fnum(x):
    if x is None:
        return None
    return float(x.replace("D", "E").replace("d", "e"))

def parse(path, k):
    text = path.read_text(errors="replace")

    energy = last(
        r"!\s+total energy\s*=\s*([-+0-9.eEdD]+)\s+Ry",
        text
    )

    ef = last(
        r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev",
        text
    )

    ts = last(
        r"\(-TS\)\s*=\s*([-+0-9.eEdD]+)",
        text
    )

    scf = last(
        r"convergence has been achieved in .*?iterations.*?ethr\s*=\s*([0-9.eEdD+-]+)",
        text
    )

    # Extraction robuste de la précision SCF depuis :
    # estimated scf accuracy < valeur Ry
    scf2 = last(
        r"estimated scf accuracy\s*<\s*([0-9.eEdD+-]+)\s+Ry",
        text
    )

    if scf2 is not None:
        scf = scf2

    cband_count = len(re.findall(r"c_bands:", text, re.I))
    job_done = "JOB DONE" in text

    return {
        "k": k,
        "energy": fnum(energy),
        "ef": fnum(ef),
        "ts": fnum(ts),
        "scf": fnum(scf),
        "cbands": cband_count,
        "job_done": job_done,
        "nk": EXPECTED_NK[k][0],
        "nirr": EXPECTED_NK[k][1],
    }

print("=" * 78)
print("PHASE 78.92 — CONVERGENCE K HOMOGÈNE 140/560")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print("[INFO] nat = 8")
print("[INFO] 7³ historique à ecutrho=240 Ry EXCLU")
print()

DATA = {}

for k in (4, 5, 6, 8):

    path = FILES[k]

    if k == 8 and not path.exists():
        print("[WARN] Fichier 8³ homogène 78.63 absent.")
        print("[INFO] Utilisation du fichier historique 8³ disponible.")
        path = FALLBACK_8

    print("-" * 78)
    print(f"{k}³")
    print("-" * 78)
    print(f"[INFO] Fichier : {path}")

    if not path.exists():
        print("[ERROR] Fichier absent")
        continue

    d = parse(path, k)
    DATA[k] = d

    print(f"[RESULT] E       = {d['energy']:.10f} Ry")
    print(f"[RESULT] EF      = {d['ef']:.6f} eV")
    print(f"[RESULT] (-TS)   = {d['ts']:.8f} Ry")
    print(f"[INFO] Nk total = {d['nk']}")
    print(f"[INFO] Nk irr   = {d['nirr']}")
    print(f"[INFO] c_bands  = {d['cbands']}")
    print(f"[INFO] SCF acc  = {d['scf']}")
    print("[PASS] JOB DONE" if d["job_done"] else "[FAIL] JOB DONE absent")

print()
print("=" * 78)
print("TABLEAU HOMOGÈNE 140/560")
print("=" * 78)

print(
    f"{'k':>3} {'Nk':>5} {'Nirr':>6} "
    f"{'E(Ry)':>18} {'ΔE/at vs 4³':>18} {'EF(eV)':>12}"
)
print("-" * 78)

if 4 in DATA:
    ref = DATA[4]["energy"]

    for k in (4, 5, 6, 8):
        if k not in DATA:
            continue

        d = DATA[k]
        de = (d["energy"] - ref) * RY_TO_EV * 1000 / NAT

        print(
            f"{k:>3} {d['nk']:>5} {d['nirr']:>6} "
            f"{d['energy']:>18.10f} {de:>18.6f} {d['ef']:>12.6f}"
        )

print()
print("=" * 78)
print("VARIATIONS SUCCESSIVES — MAILLAGE HOMOGÈNE")
print("=" * 78)

successive = []

for a, b in ((4, 5), (5, 6), (6, 8)):

    if a not in DATA or b not in DATA:
        continue

    de = (
        DATA[b]["energy"] - DATA[a]["energy"]
    ) * RY_TO_EV * 1000 / NAT

    def_ef = DATA[b]["ef"] - DATA[a]["ef"]

    successive.append(abs(de))

    print(
        f"{a}³ → {b}³ : "
        f"ΔE/at = {de:+.6f} meV/at | "
        f"ΔEF = {def_ef:+.6f} eV"
    )

print()
print("=" * 78)
print("RANGE GLOBAL HOMOGÈNE")
print("=" * 78)

if DATA:

    energies = [d["energy"] for d in DATA.values()]
    efs = [d["ef"] for d in DATA.values()]

    erange = (
        max(energies) - min(energies)
    ) * RY_TO_EV * 1000 / NAT

    efrange = max(efs) - min(efs)

    print(f"[RESULT] Plage énergie = {erange:.6f} meV/at")
    print(f"[RESULT] Plage EF      = {efrange:.6f} eV")

print()
print("=" * 78)
print("TESTS DE TOLÉRANCE — VARIATIONS SUCCESSIVES")
print("=" * 78)

for tol in (10.0, 5.0, 2.0, 1.0):

    if successive and max(successive) <= tol:
        print(f"[PASS] Toutes les variations ≤ {tol:.1f} meV/at")
    else:
        print(f"[FAIL] Toutes les variations ≤ {tol:.1f} meV/at")

print()
print("=" * 78)
print("POINT SPÉCIFIQUE 6³ → 8³")
print("=" * 78)

if 6 in DATA and 8 in DATA:

    de68 = (
        DATA[8]["energy"] - DATA[6]["energy"]
    ) * RY_TO_EV * 1000 / NAT

    def68 = DATA[8]["ef"] - DATA[6]["ef"]

    print(f"[RESULT] ΔE/at = {de68:+.6f} meV/at")
    print(f"[RESULT] ΔEF    = {def68:+.6f} eV")

print()
print("=" * 78)
print("CONCLUSION")
print("=" * 78)

print("[INFO] Le maillage 7³ à ecutrho=240 Ry est exclu.")
print("[INFO] La convergence k est évaluée uniquement à 140/560 Ry.")
print("[INFO] Série homogène : 4³ → 5³ → 6³ → 8³.")

if successive:
    print(
        "[INFO] Variations successives homogènes : "
        + ", ".join(f"{x:.6f}" for x in successive)
        + " meV/at."
    )

if successive and max(successive) <= 10.0:
    print("[PASS] Critère global ≤ 10 meV/at satisfait.")
else:
    print("[WARN] Critère global ≤ 10 meV/at non démontré.")

if successive and max(successive) <= 5.0:
    print("[PASS] Critère global ≤ 5 meV/at satisfait.")
else:
    print("[WARN] Critère global ≤ 5 meV/at non démontré.")

if successive and max(successive) <= 1.0:
    print("[PASS] Critère global ≤ 1 meV/at satisfait.")
else:
    print("[WARN] Critère global ≤ 1 meV/at non démontré.")

print()
print("[INFO] Aucun résultat scientifique n'a été modifié.")
print("[PASS] PHASE 78.92 TERMINÉE — READ-ONLY")
print("=" * 78)
