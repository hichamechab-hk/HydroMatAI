#!/usr/bin/env python3

import re
from pathlib import Path

print("\033c", end="")

print("=" * 78)
print("PHASE 78.67 — CHRONOLOGIE c_bands / SCF FINAL")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Objectif : localiser précisément les c_bands")
print("[INFO] et déterminer s'ils persistent lors de la convergence finale")
print()

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


def parse_file(k, path):

    text = path.read_text(errors="replace")
    lines = text.splitlines()

    iterations = []
    current_iteration = None

    for i, line in enumerate(lines):

        m = re.search(
            r"iteration\s*#\s*(\d+)",
            line,
            re.I
        )

        if m:
            current_iteration = int(m.group(1))
            iterations.append({
                "iteration": current_iteration,
                "cbands": [],
                "accuracy": None,
                "energy": None,
            })

        if "c_bands:" in line.lower():

            m = re.search(
                r"c_bands:\s*(\d+)\s+eigenvalues\s+not\s+converged",
                line,
                re.I
            )

            n = int(m.group(1)) if m else None

            if iterations:
                iterations[-1]["cbands"].append(n)

        if iterations:

            m = re.search(
                r"estimated scf accuracy\s*<\s*"
                r"([0-9.Ee+-]+)\s*Ry",
                line,
                re.I
            )

            if m:
                iterations[-1]["accuracy"] = float(m.group(1))

            m = re.search(
                r"total energy\s*=\s*"
                r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
                line,
                re.I
            )

            if m:
                iterations[-1]["energy"] = float(m.group(1))

    # Énergie finale
    energies = re.findall(
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
        text,
        re.I
    )

    energy_final = float(energies[-1]) if energies else None

    # Accuracy finale
    accuracies = re.findall(
        r"estimated scf accuracy\s*<\s*"
        r"([0-9.Ee+-]+)\s*Ry",
        text,
        re.I
    )

    accuracy_final = (
        float(accuracies[-1])
        if accuracies else None
    )

    return {
        "k": k,
        "iterations": iterations,
        "energy": energy_final,
        "accuracy": accuracy_final,
        "job_done": "JOB DONE." in text,
    }


results = []

print("===== 1. ANALYSE DES FICHIERS =====")
print("-" * 78)

for k, path in FILES.items():

    print()
    print(f"k = {k}³")
    print(f"FILE = {path}")

    if not path.exists():
        print("[ERROR] Fichier absent")
        continue

    r = parse_file(k, path)
    results.append(r)

    print(f"JOB DONE       : {r['job_done']}")
    print(f"SCF iterations : {len(r['iterations'])}")
    print(f"E finale       : {r['energy']}")
    print(f"SCF accuracy   : {r['accuracy']}")

    print()
    print("Chronologie :")

    for it in r["iterations"]:

        ncb = sum(
            x for x in it["cbands"]
            if x is not None
        )

        print(
            f"  iter {it['iteration']:>3} | "
            f"c_bands={ncb:>2} | "
            f"accuracy={it['accuracy']} | "
            f"E={it['energy']}"
        )


print()
print("===== 2. c_bands À LA DERNIÈRE ITÉRATION =====")
print("-" * 78)

for r in results:

    if not r["iterations"]:
        print(f"k={r['k']}³ : aucune itération détectée")
        continue

    last = r["iterations"][-1]

    ncb = sum(
        x for x in last["cbands"]
        if x is not None
    )

    print(
        f"k={r['k']}³ | "
        f"dernière itération={last['iteration']} | "
        f"c_bands dernière itération={ncb} | "
        f"accuracy={last['accuracy']}"
    )


print()
print("===== 3. c_bands TRANSITOIRES VS FINAUX =====")
print("-" * 78)

for r in results:

    total = 0
    final = 0
    events = 0

    for it in r["iterations"]:

        n = sum(
            x for x in it["cbands"]
            if x is not None
        )

        total += n

        if n > 0:
            events += 1

    if r["iterations"]:

        last = r["iterations"][-1]

        final = sum(
            x for x in last["cbands"]
            if x is not None
        )

    print(
        f"k={r['k']}³ | "
        f"total={total} | "
        f"événements={events} | "
        f"final={final} | "
        f"transitoire={total-final}"
    )


print()
print("===== 4. DERNIÈRES ITÉRATIONS =====")
print("-" * 78)

for r in results:

    print()
    print(f"k={r['k']}³")

    for it in r["iterations"][-5:]:

        ncb = sum(
            x for x in it["cbands"]
            if x is not None
        )

        print(
            f"  iter {it['iteration']:>3} | "
            f"c_bands={ncb} | "
            f"accuracy={it['accuracy']}"
        )


print()
print("===== 5. CONTRÔLE FINAL =====")
print("-" * 78)

for r in results:

    if not r["iterations"]:
        continue

    last = r["iterations"][-1]

    ncb = sum(
        x for x in last["cbands"]
        if x is not None
    )

    if ncb == 0:
        status = "AUCUN c_bands À LA DERNIÈRE ITÉRATION"
    else:
        status = "c_bands PRÉSENT À LA DERNIÈRE ITÉRATION"

    print(
        f"k={r['k']}³ : {status}"
    )


print()
print("=" * 78)
print("PHASE 78.67 TERMINÉE")
print("=" * 78)
