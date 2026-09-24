#!/usr/bin/env python3

import re
from pathlib import Path

print("\033c", end="")

print("=" * 78)
print("PHASE 78.66 — AUDIT c_bands / CONVERGENCE DES VALEURS PROPRES")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Structure identique")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print("[INFO] Analyse : k=4³ → 8³")
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

results = []


def floats(pattern, text):
    return [
        float(x)
        for x in re.findall(pattern, text, re.I)
    ]


print("===== 1. INVENTAIRE DES SORTIES =====")
print("-" * 78)

for k, path in FILES.items():

    print(f"\nk = {k}³")
    print(f"FILE = {path}")

    if not path.exists():
        print("[ERROR] Fichier absent")
        continue

    text = path.read_text(errors="replace")

    energy = floats(
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
        text
    )

    fermi = floats(
        r"the Fermi energy is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",
        text
    )

    accuracy = floats(
        r"estimated scf accuracy\s*<\s*"
        r"([0-9.Ee+-]+)\s*Ry",
        text
    )

    cbands_lines = []

    for line in text.splitlines():

        if "c_bands:" in line.lower():
            cbands_lines.append(line.strip())

    # Extraction du nombre d'eigenvalues non converged
    cbands_counts = []

    for line in cbands_lines:

        m = re.search(
            r"c_bands:\s*(\d+)\s+eigenvalues\s+not\s+converged",
            line,
            re.I
        )

        if m:
            cbands_counts.append(int(m.group(1)))

    # Iterations SCF
    scf_iterations = re.findall(
        r"iteration\s*#\s*(\d+)",
        text,
        re.I
    )

    scf_numbers = [int(x) for x in scf_iterations]

    # K points
    nk = re.findall(
        r"number of k points\s*=\s*(\d+)",
        text,
        re.I
    )

    # Bands
    bands = re.findall(
        r"number of Kohn-Sham states\s*=\s*(\d+)",
        text,
        re.I
    )

    # Occupation / smearing
    smearing = re.findall(
        r"the Fermi-Dirac smearing is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*Ry",
        text,
        re.I
    )

    mv_width = re.findall(
        r"Gaussian broadening.*?([-+]?\d+(?:\.\d+)?)\s*Ry",
        text,
        re.I
    )

    # Recherche générale de "not converged"
    not_converged_lines = [
        line.strip()
        for line in text.splitlines()
        if "not converged" in line.lower()
    ]

    # JOB DONE
    job_done = "JOB DONE." in text

    r = {
        "k": k,
        "energy": energy[-1] if energy else None,
        "fermi": fermi[-1] if fermi else None,
        "accuracy": accuracy[-1] if accuracy else None,
        "cbands": cbands_counts,
        "cbands_total": sum(cbands_counts),
        "cbands_events": len(cbands_counts),
        "scf": scf_numbers,
        "nk": int(nk[-1]) if nk else None,
        "bands": int(bands[-1]) if bands else None,
        "smearing": smearing[-1] if smearing else None,
        "mv_width": mv_width[-1] if mv_width else None,
        "not_converged": not_converged_lines,
        "job_done": job_done,
    }

    results.append(r)

    print(f"JOB DONE              : {job_done}")
    print(f"Energy                : {r['energy']}")
    print(f"Fermi                 : {r['fermi']}")
    print(f"SCF accuracy          : {r['accuracy']}")
    print(f"SCF iterations        : {len(r['scf'])}")

    if r["scf"]:
        print(f"Dernière itération    : {r['scf'][-1]}")

    print(f"Nk irréductibles      : {r['nk']}")
    print(f"Bandes                : {r['bands']}")

    print(
        f"Événements c_bands    : "
        f"{r['cbands_events']}"
    )

    print(
        f"Eigenvalues non conv. : "
        f"{r['cbands_total']}"
    )

    if r["cbands"]:
        print(
            f"Répartition           : "
            f"{r['cbands']}"
        )

    if r["not_converged"]:
        print("Lignes concernées :")
        for line in r["not_converged"]:
            print(f"  {line}")


print()
print("===== 2. SYNTHÈSE c_bands =====")
print("-" * 78)

print(
    f"{'k':>3} | "
    f"{'Nk':>4} | "
    f"{'SCF':>4} | "
    f"{'évén.':>6} | "
    f"{'eig. NC':>7} | "
    f"{'E (Ry)':>16} | "
    f"{'EF (eV)':>10}"
)

print("-" * 78)

for r in results:

    print(
        f"{r['k']:>3} | "
        f"{str(r['nk']):>4} | "
        f"{len(r['scf']):>4} | "
        f"{r['cbands_events']:>6} | "
        f"{r['cbands_total']:>7} | "
        f"{r['energy']:>16.10f} | "
        f"{r['fermi']:>10.4f}"
    )


print()
print("===== 3. RAPPORT c_bands PAR ITÉRATION =====")
print("-" * 78)

for r in results:

    print(f"\nk = {r['k']}³")

    if not r["cbands"]:
        print("  Aucun message c_bands détecté.")
        continue

    print(
        "  Nombre d'eigenvalues non convergées "
        "par événement :"
    )

    for i, n in enumerate(r["cbands"], start=1):
        print(
            f"    événement {i:02d} : {n}"
        )


print()
print("===== 4. CORRÉLATION c_bands / ÉNERGIE =====")
print("-" * 78)

if len(results) >= 2:

    RY_TO_EV = 13.605693009
    NAT = 8

    for a, b in zip(results[:-1], results[1:]):

        de = b["energy"] - a["energy"]

        mev_atom = (
            de * RY_TO_EV * 1000 / NAT
        )

        dc = (
            b["cbands_total"]
            - a["cbands_total"]
        )

        print(
            f"{a['k']}³ → {b['k']}³ : "
            f"ΔE = {mev_atom:+.6f} meV/at | "
            f"Δ(c_bands) = {dc:+d}"
        )


print()
print("===== 5. CONTRÔLE DE LA CONVERGENCE SCF =====")
print("-" * 78)

for r in results:

    print(
        f"k={r['k']}³ | "
        f"SCF acc={r['accuracy']:.2e} Ry | "
        f"itérations={len(r['scf'])} | "
        f"JOB DONE={r['job_done']}"
    )


print()
print("===== 6. INTERPRÉTATION AUTOMATIQUE PRUDENTE =====")
print("-" * 78)

total_cbands = sum(
    r["cbands_total"] for r in results
)

if total_cbands > 0:

    print(
        f"[RESULT] {total_cbands} événements "
        f"c_bands détectés sur les 5 calculs."
    )

    print(
        "[INFO] Les messages c_bands indiquent que certaines "
        "valeurs propres n'ont pas atteint le critère interne "
        "de diagonalisation à certaines étapes."
    )

    print(
        "[INFO] Leur présence ne signifie pas automatiquement "
        "que le calcul SCF final est invalide."
    )

else:

    print(
        "[RESULT] Aucun événement c_bands détecté."
    )


print()
print("===== 7. CONCLUSION =====")
print("-" * 78)

print(
    "[INFO] Cet audit ne permet pas à lui seul de déclarer "
    "une grille k convergée."
)

print(
    "[INFO] La convergence énergétique doit rester basée "
    "sur des comparaisons homogènes entre grilles."
)

print(
    "[INFO] Les messages c_bands seront confrontés aux "
    "variations d'énergie et au comportement de EF."
)

print()
print("=" * 78)
print("PHASE 78.66 TERMINÉE")
print("=" * 78)
