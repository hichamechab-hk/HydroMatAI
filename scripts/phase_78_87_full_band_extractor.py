#!/usr/bin/env python3

import sys
import re
from pathlib import Path

sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

HEADER_RE = re.compile(
    r"k\s*=.*bands\s*\(ev\)",
    re.IGNORECASE
)

FERMI_RE = re.compile(
    r"the\s+Fermi\s+energy\s+is\s+"
    r"([+-]?\d+(?:\.\d+)?)\s+ev",
    re.IGNORECASE
)

FLOAT_RE = re.compile(
    r"^[\s]*"
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[EeDd][+-]?\d+)?"
    r"(?:\s+"
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[EeDd][+-]?\d+)?)*"
    r"[\s]*$"
)

def to_float(x):
    return float(x.replace("D", "E").replace("d", "e"))

def numeric_values(line):
    if not FLOAT_RE.match(line):
        return None

    parts = line.split()

    try:
        return [to_float(x) for x in parts]
    except ValueError:
        return None

def extract_blocks(lines, headers, spin):

    blocks = []

    for header_idx in headers:

        j = header_idx + 1

        # Sauter les lignes vides avant le premier bloc numérique
        while j < len(lines) and not lines[j].strip():
            j += 1

        values = []
        numeric_started = False

        while j < len(lines):

            line = lines[j]

            if not line.strip():

                if numeric_started:
                    break

                j += 1
                continue

            vals = numeric_values(line)

            if vals is None:
                break

            numeric_started = True
            values.extend(vals)

            j += 1

        blocks.append({
            "header_line": header_idx + 1,
            "header": lines[header_idx].strip(),
            "spin": spin,
            "values": values,
        })

    return blocks

print("=" * 78)
print("PHASE 78.87 — FULL BAND EIGENVALUE EXTRACTION")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")

for grid, path in FILES.items():

    print()
    print("=" * 78)
    print(f"PHASE 78.87 — {grid}³")
    print("=" * 78)

    lines = path.read_text(errors="replace").splitlines()

    # Sections
    up = None
    down = None
    fermi = None
    ef = None

    for i, line in enumerate(lines):

        if "------ SPIN UP" in line:
            up = i

        elif "------ SPIN DOWN" in line:
            down = i

        m = FERMI_RE.search(line)

        if m:
            fermi = i
            ef = to_float(m.group(1))

    if up is None or down is None or fermi is None:
        print("[ERROR] Sections QE introuvables.")
        continue

    # Headers
    up_headers = [
        i for i in range(up + 1, down)
        if HEADER_RE.search(lines[i])
    ]

    down_headers = [
        i for i in range(down + 1, fermi)
        if HEADER_RE.search(lines[i])
    ]

    up_blocks = extract_blocks(lines, up_headers, "UP")
    down_blocks = extract_blocks(lines, down_headers, "DOWN")

    all_blocks = up_blocks + down_blocks

    expected_k = 30 if grid == 4 else 39
    expected_blocks = expected_k * 2
    expected_states = expected_blocks * 36

    print(f"[INFO] EF = {ef:.6f} eV")
    print()

    print("[1] HEADERS")
    print(f"UP   : {len(up_headers)} / {expected_k}")
    print(f"DOWN : {len(down_headers)} / {expected_k}")

    print()
    print("[2] VALIDATION DES BLOCS")

    invalid = []

    for block in all_blocks:

        n = len(block["values"])

        if n != 36:
            invalid.append(
                (
                    block["spin"],
                    block["header_line"],
                    n
                )
            )

    valid_up = sum(
        len(b["values"]) == 36
        for b in up_blocks
    )

    valid_down = sum(
        len(b["values"]) == 36
        for b in down_blocks
    )

    print(
        f"UP   : {valid_up} / {len(up_blocks)} blocs de 36"
    )

    print(
        f"DOWN : {valid_down} / {len(down_blocks)} blocs de 36"
    )

    if invalid:

        print()
        print("[WARN] BLOCS INVALIDES")

        for spin, line, n in invalid:
            print(
                f"  {spin} L{line}: "
                f"{n} eigenvalues"
            )

    print()
    print("[3] COMPTAGE GLOBAL")

    total_blocks = len(all_blocks)
    total_states = sum(
        len(b["values"])
        for b in all_blocks
    )

    print(f"Blocs attendus        : {expected_blocks}")
    print(f"Blocs obtenus         : {total_blocks}")
    print(f"Eigenvalues attendues : {expected_states}")
    print(f"Eigenvalues extraites : {total_states}")

    complete = (
        len(up_headers) == expected_k
        and len(down_headers) == expected_k
        and len(all_blocks) == expected_blocks
        and not invalid
        and total_states == expected_states
    )

    print()

    if not complete:

        print("[RESULT]")
        print("[WARN] EXTRACTION COMPLETE NON VALIDEE.")
        print("[INFO] Aucun bord électronique global ne sera interprété.")
        continue

    print("[OK] EXTRACTION COMPLETE VALIDEE.")

    # ---------------------------------------------------------------
    # Recherche des états les plus proches de EF
    # ---------------------------------------------------------------

    states = []

    for block in all_blocks:

        for band_index, energy in enumerate(
            block["values"], start=1
        ):

            delta = energy - ef

            states.append({
                "energy": energy,
                "delta": delta,
                "abs_delta": abs(delta),
                "spin": block["spin"],
                "band": band_index,
                "header_line": block["header_line"],
                "header": block["header"],
            })

    below = [
        s for s in states
        if s["energy"] <= ef
    ]

    above = [
        s for s in states
        if s["energy"] >= ef
    ]

    if not below or not above:
        print("[WARN] États des deux côtés de EF absents.")
        continue

    nearest_below = max(
        below,
        key=lambda x: x["energy"]
    )

    nearest_above = min(
        above,
        key=lambda x: x["energy"]
    )

    separation = (
        nearest_above["energy"]
        - nearest_below["energy"]
    )

    print()
    print("[4] ÉTATS LES PLUS PROCHES DE EF")
    print()
    print("Sous EF :")
    print(
        f"  E       = {nearest_below['energy']:.6f} eV"
    )
    print(
        f"  ΔEF     = {nearest_below['delta']:+.6f} eV"
    )
    print(
        f"  spin    = {nearest_below['spin']}"
    )
    print(
        f"  bande   = {nearest_below['band']}"
    )
    print(
        f"  header  = L{nearest_below['header_line']}"
    )

    print()
    print("Au-dessus EF :")
    print(
        f"  E       = {nearest_above['energy']:.6f} eV"
    )
    print(
        f"  ΔEF     = {nearest_above['delta']:+.6f} eV"
    )
    print(
        f"  spin    = {nearest_above['spin']}"
    )
    print(
        f"  bande   = {nearest_above['band']}"
    )
    print(
        f"  header  = L{nearest_above['header_line']}"
    )

    print()
    print(
        f"[RESULT] Séparation locale autour de EF = "
        f"{separation:.6f} eV"
    )

    # ---------------------------------------------------------------
    # Résumé spin
    # ---------------------------------------------------------------

    print()
    print("[5] RÉSUMÉ PAR SPIN")

    for spin in ("UP", "DOWN"):

        subset = [
            s for s in states
            if s["spin"] == spin
        ]

        b = [
            s for s in subset
            if s["energy"] <= ef
        ]

        a = [
            s for s in subset
            if s["energy"] >= ef
        ]

        print()
        print(f"{spin}:")

        if b:
            sb = max(b, key=lambda x: x["energy"])
            print(
                f"  sous EF : "
                f"{sb['energy']:.6f} eV "
                f"(Δ={sb['delta']:+.6f})"
            )

        if a:
            sa = min(a, key=lambda x: x["energy"])
            print(
                f"  au-dessus : "
                f"{sa['energy']:.6f} eV "
                f"(Δ={sa['delta']:+.6f})"
            )

print()
print("=" * 78)
print("PHASE 78.87 — FIN")
print("=" * 78)
