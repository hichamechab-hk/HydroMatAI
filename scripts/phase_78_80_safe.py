#!/usr/bin/env python3

from pathlib import Path
import re

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
    6: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
    7: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k777.out",
    8: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out",
}

EXPECTED_BLOCKS = {
    4: 30,
    5: 39,
}

EXPECTED_BANDS = 36

FERMI_RE = re.compile(
    r"the\s+Fermi\s+energy\s+is\s+([+-]?[0-9]+(?:\.[0-9]+)?)\s*eV",
    re.I,
)

K_RE = re.compile(
    r"^\s*k\s*=\s*"
    r"([+-]?[0-9]+(?:\.[0-9]+)?)\s+"
    r"([+-]?[0-9]+(?:\.[0-9]+)?)\s+"
    r"([+-]?[0-9]+(?:\.[0-9]+)?)"
    r".*bands\s*\(ev\)",
    re.I,
)


def numeric_values(line):
    s = line.strip()

    if not s:
        return None

    values = []

    for token in s.split():
        try:
            values.append(float(token.replace("D", "E").replace("d", "e")))
        except ValueError:
            return None

    return values


def find_marker(lines, text):
    for i, line in enumerate(lines):
        if text.lower() in line.lower() and "----" in line:
            return i
    return None


def find_fermi(lines):
    value = None

    for line in lines:
        match = FERMI_RE.search(line)
        if match:
            value = float(match.group(1))

    return value


def parse_blocks(lines, start, end, spin):
    blocks = []

    i = start
    safety = 0
    maximum = max(1000, (end - start) * 2)

    while i < end:

        safety += 1

        if safety > maximum:
            print(f"[ERROR] Garde-fou atteint pour SPIN {spin}.")
            break

        match = K_RE.search(lines[i])

        if match is None:
            i += 1
            continue

        kx = float(match.group(1))
        ky = float(match.group(2))
        kz = float(match.group(3))

        values = []
        j = i + 1
        local = 0

        while j < end and local < 12:

            local += 1
            line = lines[j]

            if not line.strip():
                j += 1
                continue

            if K_RE.search(line):
                break

            vals = numeric_values(line)

            if vals is None:
                break

            values.extend(vals)

            if len(values) >= EXPECTED_BANDS:
                break

            j += 1

        blocks.append({
            "spin": spin,
            "k": (kx, ky, kz),
            "values": values,
            "line": i + 1,
        })

        i = max(i + 1, j)

    return blocks


def make_states(blocks):
    states = []
    invalid = []

    for number, block in enumerate(blocks, 1):

        if len(block["values"]) != EXPECTED_BANDS:
            invalid.append((
                number,
                block["line"],
                len(block["values"]),
                block["k"],
            ))
            continue

        for band, energy in enumerate(block["values"], 1):
            states.append({
                "energy": energy,
                "band": band,
                "spin": block["spin"],
                "k": block["k"],
                "line": block["line"],
            })

    return states, invalid


def nearest(states, ef):

    below = [x for x in states if x["energy"] < ef]
    above = [x for x in states if x["energy"] > ef]

    below.sort(key=lambda x: ef - x["energy"])
    above.sort(key=lambda x: x["energy"] - ef)

    return below, above


def show_state(state, ef):

    print(
        f"  E={state['energy']:10.6f} eV  "
        f"dEF={state['energy'] - ef:+10.6f} eV  "
        f"{state['spin']:4s}  "
        f"band={state['band']:2d}  "
        f"k=({state['k'][0]: .4f}, "
        f"{state['k'][1]: .4f}, "
        f"{state['k'][2]: .4f})  "
        f"L{state['line']}"
    )


def analyse(grid, path):

    print()
    print("=" * 78)
    print(f"PHASE 78.80 SAFE — {grid}³")
    print("=" * 78)

    if not path.exists():
        print("[WARN] Fichier absent.")
        return

    print(f"[INFO] Fichier : {path}")

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    print(f"[INFO] Lignes : {len(lines)}")
    print(f"[INFO] Octets : {path.stat().st_size}")

    ef = find_fermi(lines)

    if ef is None:
        print("[WARN] EF introuvable.")
    else:
        print(f"[OK] EF = {ef:.6f} eV")

    if grid not in EXPECTED_BLOCKS:

        print()
        print("[RESULT]")
        print("[INFO] Aucun bloc final SPIN UP/DOWN exploitable.")
        print("[INFO] Les eigenvalues finales ne sont pas imprimées")
        print("[INFO] dans cette sortie SCF.")
        return

    up = find_marker(lines, "SPIN UP")
    down = find_marker(lines, "SPIN DOWN")

    print()
    print("[1] MARQUEURS SPIN")

    print(
        f"SPIN UP   : "
        f"{'L' + str(up + 1) if up is not None else 'ABSENT'}"
    )

    print(
        f"SPIN DOWN : "
        f"{'L' + str(down + 1) if down is not None else 'ABSENT'}"
    )

    if up is None or down is None:
        print("[WARN] Sections SPIN incomplètes.")
        return

    if down <= up:
        print("[WARN] Ordre des sections SPIN incorrect.")
        return

    up_blocks = parse_blocks(
        lines,
        up + 1,
        down,
        "UP",
    )

    fermi_positions = [
        i for i, line in enumerate(lines)
        if FERMI_RE.search(line)
    ]

    down_end = (
        fermi_positions[-1]
        if fermi_positions
        else len(lines)
    )

    down_blocks = parse_blocks(
        lines,
        down + 1,
        down_end,
        "DOWN",
    )

    expected = EXPECTED_BLOCKS[grid]

    print()
    print("[2] BLOCS")

    print(f"UP   : {len(up_blocks)} / {expected}")
    print(f"DOWN : {len(down_blocks)} / {expected}")

    up_states, up_bad = make_states(up_blocks)
    down_states, down_bad = make_states(down_blocks)

    print()
    print("[3] VALIDATION DES 36 EIGENVALUES")

    print(f"UP   états valides   : {len(up_states)}")
    print(f"DOWN états valides   : {len(down_states)}")

    print(
        "[OK] Tous les blocs UP = 36 états."
        if not up_bad
        else f"[WARN] Blocs UP invalides : {len(up_bad)}"
    )

    print(
        "[OK] Tous les blocs DOWN = 36 états."
        if not down_bad
        else f"[WARN] Blocs DOWN invalides : {len(down_bad)}"
    )

    if ef is None:
        return

    states = up_states + down_states

    if not states:
        print("[WARN] Aucun état exploitable.")
        return

    below, above = nearest(states, ef)

    print()
    print("[4] ETATS LES PLUS PROCHES SOUS EF")
    print("-" * 78)

    for state in below[:5]:
        show_state(state, ef)

    print()
    print("[5] ETATS LES PLUS PROCHES AU-DESSUS DE EF")
    print("-" * 78)

    for state in above[:5]:
        show_state(state, ef)

    print()
    print("[6] RESUME GLOBAL")
    print("-" * 78)

    if below and above:

        b = below[0]
        a = above[0]

        d1 = ef - b["energy"]
        d2 = a["energy"] - ef

        print(
            f"MAX_EIGENVALUE_BELOW_EF = "
            f"{b['energy']:.6f} eV"
        )

        print(
            f"MIN_EIGENVALUE_ABOVE_EF = "
            f"{a['energy']:.6f} eV"
        )

        print(
            f"DISTANCE_BELOW_EF = "
            f"{d1:.6f} eV"
        )

        print(
            f"DISTANCE_ABOVE_EF = "
            f"{d2:.6f} eV"
        )

        print(
            f"TWO_SIDED_SEPARATION = "
            f"{d1 + d2:.6f} eV"
        )

        print()
        print(
            "[INFO] Indicateur spectral autour de EF."
        )
        print(
            "[INFO] PAS de déclaration automatique de band gap."
        )
        print(
            "[INFO] Occupations = smearing, degauss = 0.01 Ry."
        )

    print()
    print(f"[RESULT] {grid}³ terminé.")


def main():

    print("=" * 78)
    print("PHASE 78.80 SAFE — EXTRACTION ELECTRONIQUE")
    print("=" * 78)
    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun recalcul")
    print("[INFO] Aucun fichier scientifique modifié")
    print()

    for grid in (4, 5, 6, 7, 8):
        analyse(grid, FILES[grid])

    print()
    print("=" * 78)
    print("PHASE 78.80 SAFE — FIN")
    print("=" * 78)


if __name__ == "__main__":
    main()
