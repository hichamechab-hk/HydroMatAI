#!/usr/bin/env python3

from pathlib import Path
import re

print("\033c", end="")

print("=" * 78)
print("PHASE 78.64 — AUDIT FINAL k=4³→8³ À ecutwfc=140 / ecutrho=560 Ry")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Série homogène : ecutwfc=140 Ry / ecutrho=560 Ry")

BASE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_convergence/TiFeH2"
)

FILES = {
    4: BASE / "ecut140_rho560_k444.out",
    5: BASE / "ecut140_rho560_k555.out",
    6: BASE / "ecut140_rho560_k666.out",
    7: BASE / "ecut140_rho560_k777.out",
    8: BASE / "ecut140_rho560_k888_phase78_63.out",
}

RY_TO_EV = 13.605693009
NAT = 8

results = []

print()
print("===== 1. INVENTAIRE =====")
print("-" * 78)

for k, path in FILES.items():

    exists = path.exists()

    print(
        f"k={k}³ | "
        f"{'PRESENT' if exists else 'ABSENT'} | "
        f"{path}"
    )

    if not exists:
        continue

    text = path.read_text(errors="replace")

    energies = re.findall(
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
        text,
        re.I,
    )

    fermis = re.findall(
        r"the Fermi energy is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",
        text,
        re.I,
    )

    accuracies = re.findall(
        r"estimated scf accuracy\s*<\s*"
        r"([0-9.Ee+-]+)\s*Ry",
        text,
        re.I,
    )

    kp = re.findall(
        r"number of k points\s*=\s*(\d+)",
        text,
        re.I,
    )

    results.append({
        "k": k,
        "energy": float(energies[-1]) if energies else None,
        "fermi": float(fermis[-1]) if fermis else None,
        "accuracy": float(accuracies[-1]) if accuracies else None,
        "kpoints": int(kp[-1]) if kp else None,
        "job_done": "JOB DONE." in text,
    })


print()
print("===== 2. VALIDATION QE =====")
print("-" * 78)

for r in results:

    print(
        f"{r['k']}³ | "
        f"JOB DONE={r['job_done']} | "
        f"E={'OK' if r['energy'] is not None else 'ABSENT'} | "
        f"EF={'OK' if r['fermi'] is not None else 'ABSENT'} | "
        f"SCF={'OK' if r['accuracy'] is not None else 'ABSENT'} | "
        f"Nk={r['kpoints'] if r['kpoints'] is not None else '?'}"
    )


print()
print("===== 3. SÉRIE ÉNERGÉTIQUE =====")
print("-" * 78)

print(
    f"{'k':>4} | "
    f"{'E (Ry)':>17} | "
    f"{'ΔE (Ry)':>15} | "
    f"{'ΔE/atome (meV)':>18} | "
    f"{'EF (eV)':>10}"
)

print("-" * 78)

previous = None

for r in results:

    if r["energy"] is None:
        continue

    if previous is None:

        print(
            f"{r['k']:>4} | "
            f"{r['energy']:17.10f} | "
            f"{'REFERENCE':>15} | "
            f"{'---':>18} | "
            f"{r['fermi'] if r['fermi'] is not None else float('nan'):10.6f}"
        )

    else:

        de = r["energy"] - previous["energy"]

        mevatom = (
            de * RY_TO_EV * 1000 / NAT
        )

        print(
            f"{r['k']:>4} | "
            f"{r['energy']:17.10f} | "
            f"{de:+15.10f} | "
            f"{mevatom:+18.6f} | "
            f"{r['fermi'] if r['fermi'] is not None else float('nan'):10.6f}"
        )

    previous = r


print()
print("===== 4. CRITÈRE ≤ 1 meV/ATOME =====")
print("-" * 78)

previous = None

for r in results:

    if r["energy"] is None:
        continue

    if previous is not None:

        de = r["energy"] - previous["energy"]

        mevatom = (
            de * RY_TO_EV * 1000 / NAT
        )

        status = (
            "[OK]"
            if abs(mevatom) <= 1.0
            else "[NON]"
        )

        print(
            f"{previous['k']}³ → {r['k']}³ : "
            f"{mevatom:+.6f} meV/atome "
            f"{status}"
        )

    previous = r


print()
print("===== 5. ÉTENDUE GLOBALE =====")
print("-" * 78)

valid_energy = [
    r for r in results
    if r["energy"] is not None
]

if valid_energy:

    energies = [r["energy"] for r in valid_energy]

    emin = min(energies)
    emax = max(energies)

    rmin = next(
        r for r in valid_energy
        if r["energy"] == emin
    )

    rmax = next(
        r for r in valid_energy
        if r["energy"] == emax
    )

    spread = (
        (emax - emin)
        * RY_TO_EV
        * 1000
        / NAT
    )

    print(
        f"Minimum : {rmin['k']}³ = "
        f"{emin:.10f} Ry"
    )

    print(
        f"Maximum : {rmax['k']}³ = "
        f"{emax:.10f} Ry"
    )

    print(
        f"Étendue : {spread:.6f} meV/atome"
    )


print()
print("===== 6. FERMI =====")
print("-" * 78)

valid_fermi = [
    r for r in results
    if r["fermi"] is not None
]

for r in valid_fermi:
    print(
        f"{r['k']}³ : "
        f"EF = {r['fermi']:.6f} eV"
    )

if valid_fermi:

    efmin = min(r["fermi"] for r in valid_fermi)
    efmax = max(r["fermi"] for r in valid_fermi)

    print()
    print(
        f"EF min = {efmin:.6f} eV"
    )
    print(
        f"EF max = {efmax:.6f} eV"
    )
    print(
        f"EF span = {efmax - efmin:.6f} eV"
    )


print()
print("===== 7. SCF =====")
print("-" * 78)

for r in results:

    if r["accuracy"] is not None:

        print(
            f"{r['k']}³ : "
            f"{r['accuracy']:.3e} Ry"
        )


print()
print("===== 8. CONCLUSION NUMÉRIQUE =====")
print("-" * 78)

deltas = []

previous = None

for r in results:

    if r["energy"] is None:
        continue

    if previous is not None:

        de = (
            (r["energy"] - previous["energy"])
            * RY_TO_EV
            * 1000
            / NAT
        )

        deltas.append(abs(de))

    previous = r

if deltas:

    if all(d <= 1.0 for d in deltas):
        print(
            "[RESULT] Tous les intervalles successifs "
            "satisfont ≤ 1 meV/atome."
        )
    else:
        print(
            "[RESULT] Le critère ≤ 1 meV/atome "
            "N'EST PAS satisfait sur toute la série."
        )

print()
print("[IMPORTANT]")
print("La série est homogène en ecutwfc=140 Ry et ecutrho=560 Ry.")
print("Aucune grille k n'est déclarée convergée uniquement sur")
print("la base de ces cinq points.")
print("Une éventuelle décision 9³ doit être justifiée séparément.")

print()
print("=" * 78)
print("PHASE 78.64 TERMINÉE")
print("=" * 78)
