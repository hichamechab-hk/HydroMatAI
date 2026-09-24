#!/usr/bin/env python3

from pathlib import Path
import re

print("\033c", end="")

print("=" * 78)
print("PHASE 78.65 — AUDIT DES CONTRIBUTIONS ÉLECTRONIQUES À 140/560 Ry")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Analyse de k=4³ → 8³")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print("[INFO] Objectif : identifier l'origine de la non-monotonicité")

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

def last_float(pattern, text):
    vals = re.findall(pattern, text, re.I)
    return float(vals[-1]) if vals else None

def all_float(pattern, text):
    vals = re.findall(pattern, text, re.I)
    return [float(v) for v in vals]

results = []

print()
print("===== 1. INVENTAIRE =====")
print("-" * 78)

for k, path in FILES.items():

    print(f"\n--- k={k}³ ---")
    print(f"FILE = {path}")

    if not path.exists():
        print("[ERROR] Fichier absent")
        continue

    text = path.read_text(errors="replace")

    # Total energy
    energies = all_float(
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
        text
    )

    # Fermi
    fermis = all_float(
        r"the Fermi energy is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",
        text
    )

    # SCF accuracy
    accuracies = all_float(
        r"estimated scf accuracy\s*<\s*"
        r"([0-9.Ee+-]+)\s*Ry",
        text
    )

    # QE decomposition
    one = last_float(
        r"one-electron contribution\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text
    )

    hartree = last_float(
        r"hartree contribution\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text
    )

    xc = last_float(
        r"xc contribution\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text
    )

    ewald = last_float(
        r"ewald contribution\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text
    )

    smearing = last_float(
        r"\(-TS\)\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text
    )

    # Alternative QE notation
    if smearing is None:
        smearing = last_float(
            r"one-electron contribution\s*=\s*"
            r"[-+]?\d+(?:\.\d+)?\s*Ry\s*\n"
            r".*?\(-TS\)\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?)\s*Ry",
            text
        )

    # Number of irreducible k points
    kpoints = None

    m = re.findall(
        r"number of k points\s*=\s*(\d+)",
        text,
        re.I
    )

    if m:
        kpoints = int(m[-1])

    # Number of bands
    bands = None

    m = re.findall(
        r"number of Kohn-Sham states\s*=\s*(\d+)",
        text,
        re.I
    )

    if m:
        bands = int(m[-1])

    # Electrons
    electrons = None

    m = re.findall(
        r"number of electrons\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)",
        text,
        re.I
    )

    if m:
        electrons = float(m[-1])

    # SCF iterations: count "iteration #"
    iterations = len(
        re.findall(
            r"iteration\s*#",
            text,
            re.I
        )
    )

    # JOB DONE
    job_done = "JOB DONE." in text

    # QE warnings
    warnings = []

    for line in text.splitlines():

        low = line.lower()

        if (
            "warning" in low
            or "ecutrho <" in low
            or "not converged" in low
        ):
            warnings.append(line.strip())

    result = {
        "k": k,
        "energy": energies[-1] if energies else None,
        "fermi": fermis[-1] if fermis else None,
        "accuracy": accuracies[-1] if accuracies else None,
        "one": one,
        "hartree": hartree,
        "xc": xc,
        "ewald": ewald,
        "smearing": smearing,
        "kpoints": kpoints,
        "bands": bands,
        "electrons": electrons,
        "iterations": iterations,
        "job_done": job_done,
        "warnings": warnings,
    }

    results.append(result)

    print(f"JOB DONE       : {job_done}")
    print(f"Energy         : {result['energy']}")
    print(f"Fermi          : {result['fermi']}")
    print(f"SCF accuracy   : {result['accuracy']}")
    print(f"Nk irreducible : {result['kpoints']}")
    print(f"Bands          : {result['bands']}")
    print(f"Electrons      : {result['electrons']}")
    print(f"SCF iterations : {result['iterations']}")

    print(f"One-electron   : {result['one']}")
    print(f"Hartree        : {result['hartree']}")
    print(f"XC             : {result['xc']}")
    print(f"Ewald          : {result['ewald']}")
    print(f"(-TS)           : {result['smearing']}")

    if warnings:
        print("Warnings:")
        for w in warnings[-5:]:
            print(f"  {w}")
    else:
        print("Warnings       : aucune")


print()
print("===== 2. TABLEAU DES CONTRIBUTIONS =====")
print("-" * 78)

print(
    f"{'k':>3} | "
    f"{'E total':>15} | "
    f"{'1e':>15} | "
    f"{'Hartree':>15} | "
    f"{'XC':>15} | "
    f"{'-TS':>12}"
)

print("-" * 78)

for r in results:

    def fmt(x, n=10):
        return f"{x:.{n}f}" if x is not None else "N/A"

    print(
        f"{r['k']:>3} | "
        f"{fmt(r['energy']):>15} | "
        f"{fmt(r['one']):>15} | "
        f"{fmt(r['hartree']):>15} | "
        f"{fmt(r['xc']):>15} | "
        f"{fmt(r['smearing'], 8):>12}"
    )


print()
print("===== 3. VARIATIONS SUCCESSIVES =====")
print("-" * 78)

RY_TO_EV = 13.605693009
NAT = 8

for a, b in zip(results[:-1], results[1:]):

    print(f"\n{a['k']}³ → {b['k']}³")

    fields = [
        ("Total", "energy"),
        ("One-electron", "one"),
        ("Hartree", "hartree"),
        ("XC", "xc"),
        ("(-TS)", "smearing"),
    ]

    for label, field in fields:

        va = a[field]
        vb = b[field]

        if va is None or vb is None:
            print(f"  {label:15} : N/A")
            continue

        delta = vb - va

        if field == "energy":
            mev_atom = (
                delta * RY_TO_EV * 1000 / NAT
            )
            print(
                f"  {label:15} : "
                f"{delta:+.10f} Ry "
                f"= {mev_atom:+.6f} meV/at"
            )
        else:
            print(
                f"  {label:15} : "
                f"{delta:+.10f} Ry"
            )


print()
print("===== 4. AMPLITUDE DU TERME DE SMEARING =====")
print("-" * 78)

valid_smearing = [
    r for r in results
    if r["smearing"] is not None
]

if valid_smearing:

    vals = [r["smearing"] for r in valid_smearing]

    smin = min(vals)
    smax = max(vals)

    print(f"(-TS) minimum : {smin:.10f} Ry")
    print(f"(-TS) maximum : {smax:.10f} Ry")

    print(
        f"(-TS) range   : "
        f"{smax - smin:.10f} Ry"
    )

    print(
        f"(-TS) range   : "
        f"{(smax - smin) * RY_TO_EV * 1000:.6f} meV/cell"
    )

    print(
        f"(-TS) range   : "
        f"{(smax - smin) * RY_TO_EV * 1000 / NAT:.6f} meV/atome"
    )

else:
    print("[WARN] Contribution (-TS) non extraite.")


print()
print("===== 5. FERMI ET K-POINTS =====")
print("-" * 78)

for r in results:

    print(
        f"k={r['k']}³ | "
        f"Nk={r['kpoints']} | "
        f"EF={r['fermi']:.6f} eV | "
        f"bands={r['bands']} | "
        f"SCF={r['iterations']}"
    )


print()
print("===== 6. CONTRÔLE DES PARAMÈTRES NUMÉRIQUES =====")
print("-" * 78)

for r in results:

    print(
        f"{r['k']}³ : "
        f"JOB={r['job_done']} | "
        f"Nk={r['kpoints']} | "
        f"bands={r['bands']} | "
        f"electrons={r['electrons']} | "
        f"SCF_acc={r['accuracy']}"
    )


print()
print("===== 7. DIAGNOSTIC =====")
print("-" * 78)

print(
    "[INFO] Le but est de déterminer si la variation énergétique"
)
print(
    "       est principalement associée au terme (-TS), ou aux"
)
print(
    "       contributions électroniques Hartree / XC / one-electron."
)

print()
print("[IMPORTANT]")
print("Cet audit ne lance aucun calcul.")
print("Aucune grille k n'est déclarée convergée.")
print("Aucune interprétation physique définitive n'est faite avant")
print("l'examen des contributions extraites.")

print()
print("=" * 78)
print("PHASE 78.65 TERMINÉE")
print("=" * 78)
