#!/usr/bin/env python3

from pathlib import Path
import re

# ==============================================================================
# PHASE 78.81 — FULL BAND BLOCK PARSER
# ==============================================================================
# MODE = READ-ONLY
# Aucun pw.x
# Aucun recalcul
# Aucun fichier scientifique modifié
#
# Objectif :
#   - récupérer TOUS les blocs "bands (ev)"
#   - 4³ : 30 UP + 30 DOWN
#   - 5³ : 39 UP + 39 DOWN
#   - 36 eigenvalues exactement par bloc
#   - extraction stricte autour de EF
# ==============================================================================

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

EXPECTED_BLOCKS = {
    4: 30,
    5: 39,
}

EXPECTED_BANDS = 36

FLOAT_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"

FERMI_RE = re.compile(
    rf"the\s+Fermi\s+energy\s+is\s+({FLOAT_RE})\s*eV",
    re.I,
)

K_RE = re.compile(
    rf"^\s*k\s*=\s*"
    rf"({FLOAT_RE})\s+"
    rf"({FLOAT_RE})\s+"
    rf"({FLOAT_RE})"
    rf".*?bands\s*\(ev\)\s*:",
    re.I,
)

SPIN_UP_RE = re.compile(
    r"^\s*-+\s*SPIN\s+UP\s*-+\s*$",
    re.I,
)

SPIN_DOWN_RE = re.compile(
    r"^\s*-+\s*SPIN\s+DOWN\s*-+\s*$",
    re.I,
)


def to_float(value):
    return float(value.replace("D", "E").replace("d", "e"))


def numeric_line(line):
    """
    Retourne les nombres de la ligne si TOUS les tokens sont numériques.
    """
    tokens = line.strip().split()

    if not tokens:
        return []

    result = []

    for token in tokens:
        if not re.fullmatch(FLOAT_RE, token, re.I):
            return None

        result.append(to_float(token))

    return result


def find_marker(lines, regex):
    for i, line in enumerate(lines):
        if regex.search(line):
            return i
    return None


def find_all_k_headers(lines, start, end):
    """
    Repère tous les headers k = ... bands(ev).
    """
    result = []

    for i in range(start, end):
        match = K_RE.search(lines[i])

        if match:
            result.append(
                (
                    i,
                    (
                        to_float(match.group(1)),
                        to_float(match.group(2)),
                        to_float(match.group(3)),
                    ),
                )
            )

    return result


def extract_36_values(lines, start, end):
    """
    À partir du header d'un bloc, cherche les 36 premières valeurs
    numériques rencontrées avant le prochain header k.

    Aucun while non borné.
    """
    values = []

    maximum_lines = min(end, start + 20)

    for i in range(start + 1, maximum_lines):

        if K_RE.search(lines[i]):
            break

        vals = numeric_line(lines[i])

        if vals is None:
            continue

        values.extend(vals)

        if len(values) >= EXPECTED_BANDS:
            return values[:EXPECTED_BANDS]

    return values


def parse_section(lines, start, end, spin):
    headers = find_all_k_headers(
        lines,
        start,
        end,
    )

    blocks = []

    for header_line, kcoords in headers:

        values = extract_36_values(
            lines,
            header_line,
            end,
        )

        blocks.append(
            {
                "spin": spin,
                "line": header_line + 1,
                "k": kcoords,
                "values": values,
            }
        )

    return blocks


def make_states(blocks):
    states = []
    invalid = []

    for number, block in enumerate(blocks, 1):

        if len(block["values"]) != EXPECTED_BANDS:

            invalid.append(
                {
                    "number": number,
                    "line": block["line"],
                    "count": len(block["values"]),
                    "k": block["k"],
                }
            )

            continue

        for band, energy in enumerate(
            block["values"],
            start=1,
        ):

            states.append(
                {
                    "energy": energy,
                    "band": band,
                    "spin": block["spin"],
                    "k": block["k"],
                    "line": block["line"],
                }
            )

    return states, invalid


def nearest(states, ef):

    below = [
        x for x in states
        if x["energy"] < ef
    ]

    above = [
        x for x in states
        if x["energy"] > ef
    ]

    below.sort(
        key=lambda x: ef - x["energy"]
    )

    above.sort(
        key=lambda x: x["energy"] - ef
    )

    return below, above


def print_state(state, ef):

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
    print(f"PHASE 78.81 — {grid}³")
    print("=" * 78)

    if not path.exists():
        print("[WARN] Fichier absent.")
        return

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(lines)}")
    print(f"[INFO] Octets  : {path.stat().st_size}")

    # ------------------------------------------------------------------
    # EF
    # ------------------------------------------------------------------

    ef = None

    for line in lines:
        match = FERMI_RE.search(line)

        if match:
            ef = to_float(match.group(1))

    if ef is None:
        print("[ERROR] EF introuvable.")
        return

    print(f"[OK] EF = {ef:.6f} eV")

    # ------------------------------------------------------------------
    # SPIN markers
    # ------------------------------------------------------------------

    up = find_marker(
        lines,
        SPIN_UP_RE,
    )

    down = find_marker(
        lines,
        SPIN_DOWN_RE,
    )

    print()
    print("[1] SECTIONS SPIN")

    print(
        f"SPIN UP   : "
        f"{'L' + str(up + 1) if up is not None else 'ABSENT'}"
    )

    print(
        f"SPIN DOWN : "
        f"{'L' + str(down + 1) if down is not None else 'ABSENT'}"
    )

    if up is None or down is None:
        print("[ERROR] Sections spin introuvables.")
        return

    if down <= up:
        print("[ERROR] Ordre des sections invalide.")
        return

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    up_blocks = parse_section(
        lines,
        up + 1,
        down,
        "UP",
    )

    # Le dernier Fermi est utilisé uniquement comme limite.
    fermi_lines = [
        i for i, line in enumerate(lines)
        if FERMI_RE.search(line)
    ]

    if fermi_lines:
        down_end = fermi_lines[-1]
    else:
        down_end = len(lines)

    down_blocks = parse_section(
        lines,
        down + 1,
        down_end,
        "DOWN",
    )

    expected = EXPECTED_BLOCKS[grid]

    print()
    print("[2] NOMBRE DE BLOCS")

    print(
        f"UP   : {len(up_blocks)} / {expected}"
    )

    print(
        f"DOWN : {len(down_blocks)} / {expected}"
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    up_states, up_invalid = make_states(
        up_blocks
    )

    down_states, down_invalid = make_states(
        down_blocks
    )

    print()
    print("[3] VALIDATION DES BLOCS")

    if len(up_blocks) == expected:
        print(
            f"[OK] UP : {expected} blocs détectés."
        )
    else:
        print(
            f"[WARN] UP : attendu {expected}, "
            f"trouvé {len(up_blocks)}."
        )

    if len(down_blocks) == expected:
        print(
            f"[OK] DOWN : {expected} blocs détectés."
        )
    else:
        print(
            f"[WARN] DOWN : attendu {expected}, "
            f"trouvé {len(down_blocks)}."
        )

    if not up_invalid:
        print(
            "[OK] UP : 36 eigenvalues dans chaque bloc."
        )
    else:
        print(
            f"[WARN] UP : {len(up_invalid)} bloc(s) "
            f"avec nombre incorrect."
        )

    if not down_invalid:
        print(
            "[OK] DOWN : 36 eigenvalues dans chaque bloc."
        )
    else:
        print(
            f"[WARN] DOWN : {len(down_invalid)} bloc(s) "
            f"avec nombre incorrect."
        )

    if up_invalid:
        print()
        print("[DETAIL] BLOCS UP INVALIDES")

        for x in up_invalid:
            print(
                f"  bloc={x['number']:2d} "
                f"L{x['line']:4d} "
                f"n={x['count']:2d} "
                f"k={x['k']}"
            )

    if down_invalid:
        print()
        print("[DETAIL] BLOCS DOWN INVALIDES")

        for x in down_invalid:
            print(
                f"  bloc={x['number']:2d} "
                f"L{x['line']:4d} "
                f"n={x['count']:2d} "
                f"k={x['k']}"
            )

    # ------------------------------------------------------------------
    # Analyse uniquement si TOUS les blocs sont valides
    # ------------------------------------------------------------------

    complete = (
        len(up_blocks) == expected
        and len(down_blocks) == expected
        and not up_invalid
        and not down_invalid
    )

    if not complete:

        print()
        print("[RESULT]")
        print(
            "[WARN] Extraction électronique NON DECLAREE COMPLETE."
        )
        print(
            "[INFO] Aucun résultat de bord de bande global "
            "ne sera publié."
        )
        return

    states = up_states + down_states

    below, above = nearest(
        states,
        ef,
    )

    print()
    print("[4] 5 ETATS LES PLUS PROCHES SOUS EF")
    print("-" * 78)

    for state in below[:5]:
        print_state(
            state,
            ef,
        )

    print()
    print("[5] 5 ETATS LES PLUS PROCHES AU-DESSUS DE EF")
    print("-" * 78)

    for state in above[:5]:
        print_state(
            state,
            ef,
        )

    if not below or not above:
        print("[WARN] Impossible de déterminer les deux côtés de EF.")
        return

    b = below[0]
    a = above[0]

    d_below = ef - b["energy"]
    d_above = a["energy"] - ef

    print()
    print("[6] RESULTAT GLOBAL")
    print("-" * 78)

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
        f"{d_below:.6f} eV"
    )

    print(
        f"DISTANCE_ABOVE_EF = "
        f"{d_above:.6f} eV"
    )

    print(
        f"TWO_SIDED_SEPARATION = "
        f"{d_below + d_above:.6f} eV"
    )

    print()
    print(
        "[INFO] Ceci est une séparation spectrale locale autour de EF."
    )

    print(
        "[INFO] Ce résultat n'est PAS déclaré comme band gap."
    )

    print(
        "[INFO] Occupations = smearing ; degauss = 0.01 Ry."
    )

    print()
    print(
        f"[RESULT] {grid}³ : ANALYSE COMPLETE."
    )


def main():

    print("=" * 78)
    print("PHASE 78.81 — FULL BAND BLOCK PARSER")
    print("=" * 78)
    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun recalcul")
    print("[INFO] Aucun fichier scientifique modifié")
    print()

    for grid in (4, 5):
        analyse(
            grid,
            FILES[grid],
        )

    print()
    print("=" * 78)
    print("PHASE 78.81 — FIN")
    print("=" * 78)
    print("[RESULT] Aucun calcul DFT exécuté.")
    print("[RESULT] Aucun fichier scientifique modifié.")


if __name__ == "__main__":
    main()
