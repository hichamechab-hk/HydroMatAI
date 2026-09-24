#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

print("\033c")

print("=" * 78)
print("PHASE 78.73 — AUDIT FINAL INPUT / SCF / FREE-ENERGY")
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
    4: {
        "in": BASE / "ecut140_rho560_k444.in",
        "out": BASE / "ecut140_rho560_k444.out",
    },
    5: {
        "in": BASE / "ecut140_rho560_k555.in",
        "out": BASE / "ecut140_rho560_k555.out",
    },
    6: {
        "in": BASE / "ecut140_rho560_k666.in",
        "out": BASE / "ecut140_rho560_k666.out",
    },
    7: {
        "in": BASE / "ecut140_rho560_k777.in",
        "out": BASE / "ecut140_rho560_k777.out",
    },
    8: {
        "in": None,
        "out": BASE / "ecut140_rho560_k888_phase78_63.out",
    },
}

RY_TO_MEV = 13605.693
RY_TO_EV = 13.605693


def read(path):
    if path is None or not path.exists():
        return None
    return path.read_text(errors="replace")


def float_search(pattern, text):
    if not text:
        return None
    m = re.search(pattern, text, re.I | re.M)
    return float(m.group(1)) if m else None


def int_search(pattern, text):
    if not text:
        return None
    m = re.search(pattern, text, re.I | re.M)
    return int(m.group(1)) if m else None


def last_float(pattern, text):
    if not text:
        return None
    matches = re.findall(pattern, text, re.I | re.M)
    return float(matches[-1]) if matches else None


records = {}

# ======================================================================
# 1. INVENTAIRE
# ======================================================================

print("===== 1. INVENTAIRE =====")
print("-" * 78)

for n, paths in FILES.items():

    inp = paths["in"]
    out = paths["out"]

    print(
        f"{n}³ : "
        f"IN={'OK' if inp and inp.exists() else 'ABSENT'} ; "
        f"OUT={'OK' if out.exists() else 'ABSENT'}"
    )

print()

# ======================================================================
# 2. EXTRACTION INPUTS
# ======================================================================

print("===== 2. PARAMÈTRES DES INPUTS =====")
print("-" * 78)

for n, paths in FILES.items():

    text = read(paths["in"])

    if text is None:
        print(f"--- {n}³ ---")
        print("[INFO] Input absent — analyse limitée à OUT")
        print()
        continue

    ecutwfc = float_search(
        r"ecutwfc\s*=\s*([0-9.Ee+-]+)",
        text
    )

    ecutrho = float_search(
        r"ecutrho\s*=\s*([0-9.Ee+-]+)",
        text
    )

    degauss = float_search(
        r"degauss\s*=\s*([0-9.Ee+-]+)",
        text
    )

    nspin = int_search(
        r"nspin\s*=\s*(\d+)",
        text
    )

    nat = int_search(
        r"nat\s*=\s*(\d+)",
        text
    )

    ntyp = int_search(
        r"ntyp\s*=\s*(\d+)",
        text
    )

    occupations = re.findall(
        r"occupations\s*=\s*['\"]([^'\"]+)['\"]",
        text,
        re.I
    )

    smearing = re.findall(
        r"smearing\s*=\s*['\"]([^'\"]+)['\"]",
        text,
        re.I
    )

    kp = re.search(
        r"K_POINTS\s+automatic\s*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+"
        r"(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.I
    )

    print(f"--- {n}³ ---")
    print(f"ecutwfc    = {ecutwfc}")
    print(f"ecutrho    = {ecutrho}")
    print(f"ratio rho/wfc = {ecutrho/ecutwfc if ecutwfc else None}")
    print(f"occupations = {occupations[0] if occupations else None}")
    print(f"smearing    = {smearing[0] if smearing else None}")
    print(f"degauss     = {degauss}")
    print(f"nspin       = {nspin}")
    print(f"nat         = {nat}")
    print(f"ntyp        = {ntyp}")

    if kp:
        print(
            "K_POINTS    = "
            f"{kp.group(1)} {kp.group(2)} {kp.group(3)} "
            f"{kp.group(4)} {kp.group(5)} {kp.group(6)}"
        )
    else:
        print("K_POINTS    = NON EXTRAIT")

    print()

# ======================================================================
# 3. EXTRACTION SORTIES QE
# ======================================================================

print("===== 3. SORTIES QE =====")
print("-" * 78)

for n, paths in FILES.items():

    text = read(paths["out"])

    if text is None:
        continue

    energy = last_float(
        r"!\s+total energy\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    ef = last_float(
        r"the Fermi energy is\s+([-\d.Ee+]+)\s+ev",
        text
    )

    ts = last_float(
        r"smearing contrib\.\s+\(-TS\)\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    internal = last_float(
        r"one-electron contribution\s+=\s+([-\d.Ee+]+)\s+Ry",
        text
    )

    nk = int_search(
        r"number of k points\s*=\s*(\d+)",
        text
    )

    electrons = last_float(
        r"number of electrons\s*=\s*([-\d.Ee+]+)",
        text
    )

    bands = int_search(
        r"number of Kohn-Sham states\s*=\s*(\d+)",
        text
    )

    # Cherche uniquement les vraies lignes "estimated scf accuracy"
    scf_values = re.findall(
        r"estimated scf accuracy\s*<\s*([0-9.Ee+-]+)\s*Ry",
        text,
        re.I
    )

    scf_accuracy = (
        float(scf_values[-1])
        if scf_values
        else None
    )

    iterations = [
        int(x)
        for x in re.findall(
            r"^\s*iteration\s+#?\s*(\d+)",
            text,
            re.I | re.M
        )
    ]

    # c_bands scientifiques uniquement
    cb = re.findall(
        r"c_bands:\s+(\d+)\s+eigenvalues\s+not\s+converged",
        text,
        re.I
    )

    cb = [int(x) for x in cb]

    records[n] = {
        "energy": energy,
        "ef": ef,
        "ts": ts,
        "internal": internal,
        "nk": nk,
        "electrons": electrons,
        "bands": bands,
        "scf": scf_accuracy,
        "iterations": max(iterations) if iterations else None,
        "cb_events": len(cb),
        "cb_eigs": sum(cb),
        "job_done": "JOB DONE" in text,
    }

    print(f"--- {n}³ ---")
    print(f"E totale       = {energy} Ry")
    print(f"EF             = {ef} eV")
    print(f"(-TS)          = {ts} Ry")
    print(f"Nk             = {nk}")
    print(f"électrons      = {electrons}")
    print(f"KS states      = {bands}")
    print(f"SCF accuracy   = {scf_accuracy} Ry")
    print(f"SCF iterations = {max(iterations) if iterations else None}")
    print(f"c_bands        = {len(cb)} événements / {sum(cb)} eigenvalues")
    print(f"JOB DONE       = {records[n]['job_done']}")
    print()

# ======================================================================
# 4. (-TS) EN meV/AT
# ======================================================================

print("===== 4. (-TS) EN meV/ATOM =====")
print("-" * 78)

for n in sorted(records):

    ts = records[n]["ts"]

    if ts is None:
        continue

    mevat = ts * RY_TO_MEV / 8.0

    print(
        f"{n}³ : {ts:+.8f} Ry = "
        f"{mevat:+.6f} meV/at"
    )

print()

# ======================================================================
# 5. E, FREE ENERGY ET INTERNAL ENERGY
# ======================================================================

print("===== 5. E / E-(-TS) / E+(-TS) =====")
print("-" * 78)

for n in sorted(records):

    E = records[n]["energy"]
    TS = records[n]["ts"]

    if E is None or TS is None:
        continue

    print(f"{n}³ :")
    print(f"  E             = {E:.10f} Ry")
    print(f"  E - (-TS)     = {E-TS:.10f} Ry")
    print(f"  E + (-TS)     = {E+TS:.10f} Ry")
    print()

# ======================================================================
# 6. VALIDATION SCF
# ======================================================================

print("===== 6. VALIDATION SCF =====")
print("-" * 78)

for n in sorted(records):

    r = records[n]

    print(
        f"{n}³ : "
        f"SCF_accuracy={r['scf']} Ry ; "
        f"iterations={r['iterations']} ; "
        f"JOB_DONE={r['job_done']}"
    )

print()

# ======================================================================
# 7. DIAGNOSTIC
# ======================================================================

print("===== 7. DIAGNOSTIC FINAL =====")
print("-" * 78)

print(
    "[INFO] Les paramètres électroniques sont lus depuis les INPUTS "
    "lorsqu'ils sont disponibles."
)

print(
    "[INFO] La vraie SCF accuracy est recherchée uniquement dans "
    "les lignes QE 'estimated scf accuracy'."
)

print(
    "[INFO] Les valeurs précédemment obtenues de l'ordre de 1–2 Ry "
    "étaient un artefact du parser Phase 78.72."
)

print(
    "[INFO] (-TS) reste insuffisant pour expliquer seul les "
    "oscillations de plusieurs meV/at."
)

print(
    "[INFO] Aucun calcul supplémentaire n'a été lancé."
)

print()
print("=" * 78)
print("PHASE 78.73 TERMINÉE")
print("=" * 78)
