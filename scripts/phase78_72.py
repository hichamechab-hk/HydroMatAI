#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

print("\033c")

print("=" * 78)
print("PHASE 78.72 — AUDIT MÉTALLIQUE EF / SMearing / ÉNERGIE")
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

RY_TO_EV = 13.605693
RY_TO_MEV = RY_TO_EV * 1000.0


def read_text(path):
    return path.read_text(errors="replace")


def find_float(pattern, text):
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None


def find_int(pattern, text):
    m = re.search(pattern, text, re.I)
    return int(m.group(1)) if m else None


def all_floats(pattern, text):
    return [float(x) for x in re.findall(pattern, text, re.I)]


records = {}

# ======================================================================
# 1. INVENTAIRE
# ======================================================================

print("===== 1. INVENTAIRE =====")
print("-" * 78)

for n, path in FILES.items():
    print(
        f"{n}³ : {'OK' if path.exists() else 'ABSENT'} "
        f"{path.name}"
    )

print()

# ======================================================================
# 2. EXTRACTION PHYSIQUE
# ======================================================================

print("===== 2. EXTRACTION DES GRANDEURS PHYSIQUES =====")
print("-" * 78)

for n, path in FILES.items():

    if not path.exists():
        continue

    text = read_text(path)

    energy = find_float(
        r"!\s+total energy\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    ef = find_float(
        r"the Fermi energy is\s+([-\d.Ee+]+)\s+ev",
        text
    )

    minus_ts = find_float(
        r"smearing contrib\.\s+\(-TS\)\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    internal = find_float(
        r"one-electron contribution\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    nk = find_int(
        r"number of k points\s*=\s*(\d+)",
        text
    )

    scf_accuracy = find_float(
        r"estimated scf accuracy\s*<\s*([-\d.Ee+]+)\s+Ry",
        text
    )

    if scf_accuracy is None:
        scf_accuracy = find_float(
            r"estimated scf accuracy\s*=\s*([-\d.Ee+]+)\s+Ry",
            text
        )

    scf_iterations = len(
        re.findall(
            r"^\s*iteration\s+#?\s*\d+",
            text,
            re.I | re.M
        )
    )

    c_bands_events = len(
        re.findall(
            r"c_bands:\s+\d+\s+eigenvalues\s+not\s+converged",
            text,
            re.I
        )
    )

    c_bands_eigs = sum(
        int(x)
        for x in re.findall(
            r"c_bands:\s+(\d+)\s+eigenvalues\s+not\s+converged",
            text,
            re.I
        )
    )

    occupations = re.findall(
        r"occupations\s*=\s*['\"]?([^,'\"\n]+)",
        text,
        re.I
    )

    smearing = re.findall(
        r"smearing\s*=\s*['\"]?([^,'\"\n]+)",
        text,
        re.I
    )

    degauss = find_float(
        r"degauss\s*=\s*([-\d.Ee+]+)",
        text
    )

    records[n] = {
        "energy": energy,
        "ef": ef,
        "minus_ts": minus_ts,
        "internal": internal,
        "nk": nk,
        "scf_accuracy": scf_accuracy,
        "scf_iterations": scf_iterations,
        "c_bands_events": c_bands_events,
        "c_bands_eigs": c_bands_eigs,
        "occupations": occupations[0].strip() if occupations else None,
        "smearing": smearing[0].strip() if smearing else None,
        "degauss": degauss,
    }

    print(f"--- {n}³ ---")
    print(f"E totale          : {energy} Ry")
    print(f"EF                : {ef} eV")
    print(f"(-TS)             : {minus_ts} Ry")
    print(f"Nk                : {nk}")
    print(f"SCF accuracy      : {scf_accuracy} Ry")
    print(f"SCF iterations    : {scf_iterations}")
    print(f"c_bands events    : {c_bands_events}")
    print(f"c_bands eigenvals : {c_bands_eigs}")
    print(f"occupations       : {records[n]['occupations']}")
    print(f"smearing          : {records[n]['smearing']}")
    print(f"degauss           : {degauss} Ry")
    print()

# ======================================================================
# 3. (-TS) EN meV/ATOM
# ======================================================================

print("===== 3. CONTRIBUTION (-TS) =====")
print("-" * 78)

for n in sorted(records):

    ts = records[n]["minus_ts"]

    if ts is None:
        continue

    mevatom = ts * RY_TO_MEV / 8.0

    print(
        f"{n}³ : (-TS) = {ts:+.8f} Ry"
        f" = {mevatom:+.6f} meV/at"
    )

print()

# ======================================================================
# 4. ENERGIE INTERNE / FREE ENERGY
# ======================================================================

print("===== 4. ÉNERGIE ET SMearing =====")
print("-" * 78)

for n in sorted(records):

    E = records[n]["energy"]
    TS = records[n]["minus_ts"]

    if E is None:
        continue

    print(f"{n}³ : E totale = {E:.10f} Ry")

    if TS is not None:
        F = E - TS
        U = E + TS

        print(f"      E - (-TS) = {F:.10f} Ry")
        print(f"      E + (-TS) = {U:.10f} Ry")

print()

# ======================================================================
# 5. EF / ÉNERGIE
# ======================================================================

print("===== 5. CORRÉLATION EF / ÉNERGIE =====")
print("-" * 78)

values = []

for n in sorted(records):

    E = records[n]["energy"]
    EF = records[n]["ef"]

    if E is not None and EF is not None:
        values.append((n, E, EF))

for i in range(1, len(values)):

    n0, E0, EF0 = values[i - 1]
    n1, E1, EF1 = values[i]

    dE = (E1 - E0) * RY_TO_MEV / 8.0
    dEF = EF1 - EF0

    print(
        f"{n0}³ → {n1}³ : "
        f"ΔE = {dE:+.6f} meV/at ; "
        f"ΔEF = {dEF:+.6f} eV"
    )

print()

# ======================================================================
# 6. CORRÉLATION (-TS) / ÉNERGIE
# ======================================================================

print("===== 6. CORRÉLATION (-TS) / ÉNERGIE =====")
print("-" * 78)

for i in range(1, len(values)):

    n0, E0, EF0 = values[i - 1]
    n1, E1, EF1 = values[i]

    ts0 = records[n0]["minus_ts"]
    ts1 = records[n1]["minus_ts"]

    if ts0 is None or ts1 is None:
        continue

    dE = (E1 - E0) * RY_TO_MEV / 8.0
    dTS = (ts1 - ts0) * RY_TO_MEV / 8.0

    print(
        f"{n0}³ → {n1}³ : "
        f"ΔE = {dE:+.6f} meV/at ; "
        f"Δ(-TS) = {dTS:+.6f} meV/at"
    )

print()

# ======================================================================
# 7. SCF / c_bands
# ======================================================================

print("===== 7. SCF / c_bands =====")
print("-" * 78)

for n in sorted(records):

    r = records[n]

    print(
        f"{n}³ : "
        f"SCF={r['scf_iterations']} ; "
        f"c_bands={r['c_bands_events']} événements / "
        f"{r['c_bands_eigs']} eigenvalues"
    )

print()

# ======================================================================
# 8. TABLEAU SYNTHÉTIQUE
# ======================================================================

print("===== 8. TABLEAU SYNTHÉTIQUE =====")
print("-" * 78)

print(
    f"{'k':>3} "
    f"{'Nk':>5} "
    f"{'E(Ry)':>15} "
    f"{'EF(eV)':>10} "
    f"{'(-TS) Ry':>12} "
    f"{'(-TS) meV/at':>15} "
    f"{'SCF':>5} "
    f"{'c_bands':>8}"
)

for n in sorted(records):

    r = records[n]

    ts_mev = (
        r["minus_ts"] * RY_TO_MEV / 8.0
        if r["minus_ts"] is not None
        else None
    )

    print(
        f"{n:>3} "
        f"{r['nk']:>5} "
        f"{r['energy']:>15.10f} "
        f"{r['ef']:>10.4f} "
        f"{r['minus_ts']:>12.8f} "
        f"{ts_mev:>15.6f} "
        f"{r['scf_iterations']:>5} "
        f"{r['c_bands_eigs']:>8}"
    )

print()

# ======================================================================
# 9. DIAGNOSTIC
# ======================================================================

print("===== 9. DIAGNOSTIC FINAL =====")
print("-" * 78)

print(
    "[INFO] Cette phase mesure l'effet du smearing et de EF "
    "sur la série déjà calculée."
)

print(
    "[INFO] (-TS) est converti en meV/at pour comparaison directe "
    "avec les variations d'énergie."
)

print(
    "[INFO] Les variations de EF sont rapportées séparément."
)

print(
    "[INFO] Les événements c_bands sont diagnostiqués mais "
    "ne constituent pas à eux seuls un échec SCF."
)

print(
    "[INFO] Aucun calcul supplémentaire n'a été lancé."
)

print()
print("=" * 78)
print("PHASE 78.72 TERMINÉE")
print("=" * 78)
