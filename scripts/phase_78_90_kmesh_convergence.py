#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
    6: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
    7: BASE / "calculations/phase78_55_convergence/TiFeH2/ecut140_k777.out",
    8: BASE / "calculations/phase78_53_convergence/TiFeH2/ecut140_k888.out",
}

NK_TOTAL = {4: 64, 5: 125, 6: 216, 7: 343, 8: 512}
NK_IRR = {4: 30, 5: 39, 6: 80, 7: 100, 8: 170}

def parse(path):
    text = path.read_text(errors="replace")

    m = re.findall(
        r"!\s+total energy\s*=\s*([-+0-9.eEdD]+)\s+Ry",
        text,
        re.I
    )
    energy = float(m[-1].replace("D", "E").replace("d", "e")) if m else None

    m = re.findall(
        r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev",
        text,
        re.I
    )
    ef = float(m[-1].replace("D", "E").replace("d", "e")) if m else None

    m = re.findall(
        r"\(-TS\)\s*=\s*([-+0-9.eEdD]+)\s*Ry",
        text,
        re.I
    )
    ts = float(m[-1].replace("D", "E").replace("d", "e")) if m else None

    cbands = len(re.findall(r"c_bands:", text, re.I))
    job_done = "JOB DONE" in text

    return energy, ef, ts, cbands, job_done


print("=" * 78)
print("PHASE 78.90 — CONVERGENCE DU MAILLAGE K")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print()

R = {}

for k in (4, 5, 6, 7, 8):

    path = FILES[k]

    print("-" * 78)
    print(f"{k}³")
    print("-" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    energy, ef, ts, cbands, done = parse(path)

    R[k] = {
        "energy": energy,
        "ef": ef,
        "ts": ts,
        "cbands": cbands,
        "done": done,
    }

    print(f"[INFO] Fichier : {path}")

    if energy is not None:
        print(f"[RESULT] E       = {energy:.10f} Ry")
    else:
        print("[ERROR] Energie introuvable")

    if ef is not None:
        print(f"[RESULT] EF      = {ef:.6f} eV")
    else:
        print("[WARN] EF introuvable")

    if ts is not None:
        print(f"[RESULT] (-TS)   = {ts:.8f} Ry")
    else:
        print("[WARN] (-TS) introuvable")

    print(f"[INFO] Nk total = {NK_TOTAL[k]}")
    print(f"[INFO] Nk irr   = {NK_IRR[k]}")
    print(f"[INFO] c_bands  = {cbands}")

    if done:
        print("[PASS] JOB DONE")
    else:
        print("[WARN] JOB DONE absent")

print()
print("=" * 78)
print("TABLEAU CONSOLIDÉ")
print("=" * 78)

print(
    f"{'k':>3} {'Nk':>5} {'Nirr':>6} "
    f"{'E(Ry)':>16} {'ΔE/at(meV)':>15} {'EF(eV)':>11}"
)

print("-" * 78)

reference = R[4]["energy"] if 4 in R else None

for k in (4, 5, 6, 7, 8):

    if k not in R:
        continue

    e = R[k]["energy"]
    ef = R[k]["ef"]

    if reference is not None and e is not None:
        de = (e - reference) * 13.605693009 * 1000 / 8
    else:
        de = None

    de_txt = f"{de:+.6f}" if de is not None else "N/A"
    e_txt = f"{e:.10f}" if e is not None else "N/A"
    ef_txt = f"{ef:.6f}" if ef is not None else "N/A"

    print(
        f"{k:>3} "
        f"{NK_TOTAL[k]:>5} "
        f"{NK_IRR[k]:>6} "
        f"{e_txt:>16} "
        f"{de_txt:>15} "
        f"{ef_txt:>11}"
    )

print()
print("=" * 78)
print("VARIATIONS SUCCESSIVES")
print("=" * 78)

for a, b in ((4, 5), (5, 6), (6, 7), (7, 8)):

    if a not in R or b not in R:
        continue

    de = (
        (R[b]["energy"] - R[a]["energy"])
        * 13.605693009
        * 1000 / 8
    )

    d_ef = R[b]["ef"] - R[a]["ef"]

    print(
        f"{a}³ → {b}³ : "
        f"ΔE/at = {de:+.6f} meV/at | "
        f"ΔEF = {d_ef:+.6f} eV"
    )

print()
print("=" * 78)
print("RANGE GLOBAL")
print("=" * 78)

energies = [R[k]["energy"] for k in R if R[k]["energy"] is not None]
efs = [R[k]["ef"] for k in R if R[k]["ef"] is not None]

if energies:
    rng = (
        (max(energies) - min(energies))
        * 13.605693009 * 1000 / 8
    )
    print(f"[RESULT] Plage énergie = {rng:.6f} meV/at")

if efs:
    print(
        f"[RESULT] Plage EF = "
        f"{max(efs) - min(efs):.6f} eV"
    )

print()
print("=" * 78)
print("TESTS DE TOLÉRANCE")
print("=" * 78)

successive = []

for a, b in ((4, 5), (5, 6), (6, 7), (7, 8)):

    if a in R and b in R:
        d = abs(
            (R[b]["energy"] - R[a]["energy"])
            * 13.605693009 * 1000 / 8
        )
        successive.append(d)

for tol in (10.0, 5.0, 2.0, 1.0):

    ok = all(x <= tol for x in successive)

    print(
        f"[{'PASS' if ok else 'FAIL'}] "
        f"Tolérance ≤ {tol:.1f} meV/at"
    )

print()
print("=" * 78)
print("PHASE 78.90 — CONCLUSION")
print("=" * 78)

if successive:

    print(
        "[INFO] Variations successives : "
        + ", ".join(f"{x:.6f}" for x in successive)
        + " meV/at."
    )

    if all(x <= 1.0 for x in successive):
        print("[PASS] 1 meV/at")
    else:
        print("[INFO] 1 meV/at non démontré")

    if all(x <= 5.0 for x in successive):
        print("[PASS] 5 meV/at")
    else:
        print("[INFO] 5 meV/at non démontré")

    if all(x <= 10.0 for x in successive):
        print("[PASS] 10 meV/at")
    else:
        print("[INFO] 10 meV/at non démontré")

print()
print("[PASS] PHASE 78.90 TERMINÉE — READ-ONLY")
print("=" * 78)
