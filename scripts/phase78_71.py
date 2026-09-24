#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

print("\033c")

print("=" * 78)
print("PHASE 78.71 — RECONSTRUCTION DES GRILLES K + AUDIT Γ / PAIR-IMPAIR")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] Cible : TiFeH2 / 140 Ry / 560 Ry / k=4→8")
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


def read_text(path):
    return path.read_text(errors="replace")


def first_float(pattern, text):
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def first_int(pattern, text):
    m = re.search(pattern, text, re.I)
    return int(m.group(1)) if m else None


records = {}

# ======================================================================
# 1. INVENTAIRE
# ======================================================================

print("===== 1. INVENTAIRE DES SORTIES =====")
print("-" * 78)

for n, path in FILES.items():
    status = "OK" if path.exists() else "ABSENT"
    print(f"{n}³ : {status}  {path.name}")

print()

# ======================================================================
# 2. EXTRACTION
# ======================================================================

print("===== 2. EXTRACTION DES PARAMÈTRES QE =====")
print("-" * 78)

for n, path in FILES.items():

    if not path.exists():
        continue

    text = read_text(path)

    nk = first_int(
        r"number of k points\s*=\s*(\d+)",
        text
    )

    energy = first_float(
        r"!\s+total energy\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    ef = first_float(
        r"the Fermi energy is\s+([-\d.Ee+]+)\s+ev",
        text
    )

    sym = first_int(
        r"(\d+)\s+Sym\. Ops\.,\s+with inversion,\s+found",
        text
    )

    smearing = first_float(
        r"smearing,\s*width \(Ry\)=\s*([-\d.Ee+]+)",
        text
    )

    records[n] = {
        "nk": nk,
        "energy": energy,
        "ef": ef,
        "sym": sym,
        "smearing": smearing,
    }

    print(f"--- {n}x{n}x{n} ---")
    print(f"Nk irréductibles : {nk}")
    print(f"E totale         : {energy} Ry")
    print(f"EF               : {ef} eV")
    print(f"Symétries        : {sym}")
    print(f"Smearing         : {smearing} Ry")
    print()

# ======================================================================
# 3. GRILLE COMPLETE THEORIQUE
# ======================================================================

print("===== 3. RECONSTRUCTION DE LA GRILLE =====")
print("-" * 78)

print(
    f"{'grille':>8}"
    f"{'N total':>10}"
    f"{'N irr.':>10}"
    f"{'ratio':>10}"
    f"{'parité':>10}"
    f"{'Γ':>10}"
)

for n in sorted(records):

    nk = records[n]["nk"]
    ntotal = n ** 3

    ratio = ntotal / nk if nk else float("nan")

    parity = "PAIRE" if n % 2 == 0 else "IMPAIRE"

    # Pour K_POINTS automatic avec shift 0 0 0 :
    # grille impaire -> Gamma présent
    # grille paire -> Gamma absent
    gamma = "OUI" if n % 2 else "NON"

    print(
        f"{n}³"
        f"{ntotal:>10}"
        f"{nk:>10}"
        f"{ratio:>10.3f}"
        f"{parity:>10}"
        f"{gamma:>10}"
    )

print()

# ======================================================================
# 4. PAIR / IMPAIR
# ======================================================================

print("===== 4. AUDIT PAIR / IMPAIR / Γ =====")
print("-" * 78)

for n in sorted(records):

    if n % 2 == 0:
        print(
            f"{n}³ : PAIRE → Γ NON attendu avec "
            f"une grille automatique non décalée"
        )
    else:
        print(
            f"{n}³ : IMPAIRE → Γ attendu avec "
            f"une grille automatique non décalée"
        )

print()

# ======================================================================
# 5. REDUCTION PAR SYMETRIE
# ======================================================================

print("===== 5. RÉDUCTION PAR SYMÉTRIE =====")
print("-" * 78)

for n in sorted(records):

    nk = records[n]["nk"]
    ntotal = n ** 3
    sym = records[n]["sym"]

    if nk:
        fraction = 100.0 * nk / ntotal
        ratio = ntotal / nk
    else:
        fraction = 0.0
        ratio = 0.0

    print(f"--- {n}³ ---")
    print(f"Grille complète : {ntotal} points")
    print(f"Nk irréductibles: {nk}")
    print(f"Fraction        : {fraction:.3f} %")
    print(f"Facteur         : {ratio:.4f}")
    print(f"Symétries QE    : {sym}")
    print()

# ======================================================================
# 6. ENERGIES
# ======================================================================

print("===== 6. ÉNERGIES ET DELTAS =====")
print("-" * 78)

previous = None

for n in sorted(records):

    energy = records[n]["energy"]

    if energy is None:
        continue

    print(f"{n}³ : E = {energy:.10f} Ry")

    if previous is not None:

        pn, pe = previous

        delta_ry = energy - pe

        delta_mev_atom = (
            delta_ry * 13.605693 * 1000.0 / 8.0
        )

        print(
            f"      ΔE {pn}³→{n}³ = "
            f"{delta_mev_atom:+.6f} meV/at"
        )

    previous = (n, energy)

print()

# ======================================================================
# 7. FERMI
# ======================================================================

print("===== 7. NIVEAUX DE FERMI =====")
print("-" * 78)

efs = []

for n in sorted(records):

    ef = records[n]["ef"]

    if ef is not None:
        efs.append(ef)
        print(f"{n}³ : EF = {ef:.6f} eV")

if efs:

    print()
    print(f"EF min  = {min(efs):.6f} eV")
    print(f"EF max  = {max(efs):.6f} eV")
    print(f"EF span = {max(efs) - min(efs):.6f} eV")

print()

# ======================================================================
# 8. TEST DE MONOTONICITE
# ======================================================================

print("===== 8. TEST DE MONOTONICITÉ =====")
print("-" * 78)

values = [
    (n, records[n]["energy"])
    for n in sorted(records)
    if records[n]["energy"] is not None
]

non_monotonic = False

for i in range(1, len(values)):

    n0, e0 = values[i - 1]
    n1, e1 = values[i]

    delta = e1 - e0

    if delta > 0:
        non_monotonic = True
        print(
            f"[NON-MONOTONE] {n0}³ → {n1}³ : "
            f"ΔE = {delta:+.10f} Ry"
        )
    else:
        print(
            f"[DESCENTE] {n0}³ → {n1}³ : "
            f"ΔE = {delta:+.10f} Ry"
        )

print()

# ======================================================================
# 9. DIAGNOSTIC
# ======================================================================

print("===== 9. DIAGNOSTIC FINAL =====")
print("-" * 78)

print(
    "[INFO] Les cinq calculs utilisent des grilles n×n×n "
    "et la même symétrie QE."
)

print(
    "[INFO] QE détecte 4 opérations de symétrie avec inversion "
    "pour chaque calcul."
)

print(
    "[INFO] La parité de n modifie la présence attendue de Γ "
    "dans une grille non décalée."
)

print(
    "[INFO] La réduction Nk total → Nk irréductible n'est "
    "pas simplement égale à 1/4."
)

if non_monotonic:
    print(
        "[WARN] La série énergétique reste NON MONOTONE."
    )

print(
    "[INFO] Cette phase ne déclare PAS la convergence "
    "en k-points."
)

print(
    "[INFO] Aucun calcul QE supplémentaire n'a été lancé."
)

print()
print("=" * 78)
print("PHASE 78.71 TERMINÉE")
print("=" * 78)
