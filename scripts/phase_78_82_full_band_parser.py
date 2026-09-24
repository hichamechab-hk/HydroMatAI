#!/usr/bin/env python3

import sys
import re
from pathlib import Path

# Nettoyage terminal sans dépendre de TERM
sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

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

FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"

K_RE = re.compile(
    rf"^\s*k\s*=\s*"
    rf"({FLOAT})\s+"
    rf"({FLOAT})\s+"
    rf"({FLOAT}).*?bands\s*\(ev\)\s*:",
    re.I,
)

FERMI_RE = re.compile(
    rf"the\s+Fermi\s+energy\s+is\s+({FLOAT})\s*eV",
    re.I,
)

UP_RE = re.compile(
    r"^\s*-+\s*SPIN\s+UP\s*-+\s*$",
    re.I,
)

DOWN_RE = re.compile(
    r"^\s*-+\s*SPIN\s+DOWN\s*-+\s*$",
    re.I,
)


def fnum(x):
    return float(x.replace("D", "E").replace("d", "e"))


def numeric_values(line):
    """
    Retourne les nombres si la ligne est exclusivement numérique.
    """
    tokens = line.strip().split()

    if not tokens:
        return []

    vals = []

    for token in tokens:
        if not re.fullmatch(FLOAT, token, re.I):
            return None

        vals.append(fnum(token))

    return vals


def find_all_headers(lines, start, end):
    result = []

    for i in range(start, end):
        m = K_RE.search(lines[i])

        if m:
            result.append({
                "line": i,
                "k": (
                    fnum(m.group(1)),
                    fnum(m.group(2)),
                    fnum(m.group(3)),
                ),
            })

    return result


def extract_block(lines, header_line, next_header_line):
    """
    Analyse exclusivement la zone :

        header courant
        ...
        juste avant header suivant

    Aucun nombre provenant du bloc suivant ne peut être capturé.
    """

    values = []

    for i in range(header_line + 1, next_header_line):

        vals = numeric_values(lines[i])

        if vals is None:
            continue

        values.extend(vals)

    return values


def parse_blocks(lines, headers, spin):
    blocks = []

    for idx, header in enumerate(headers):

        start = header["line"]

        if idx + 1 < len(headers):
            end = headers[idx + 1]["line"]
        else:
            end = len(lines)

        values = extract_block(
            lines,
            start,
            end,
        )

        blocks.append({
            "spin": spin,
            "line": start + 1,
            "k": header["k"],
            "values": values,
        })

    return blocks


def validate_blocks(blocks):
    valid = []
    invalid = []

    for i, block in enumerate(blocks, 1):

        n = len(block["values"])

        if n == EXPECTED_BANDS:
            valid.append(block)
        else:
            invalid.append({
                "number": i,
                "line": block["line"],
                "count": n,
                "k": block["k"],
            })

    return valid, invalid


def make_states(blocks):
    states = []

    for block in blocks:

        for band, energy in enumerate(
            block["values"],
            start=1,
        ):
            states.append({
                "energy": energy,
                "band": band,
                "spin": block["spin"],
                "k": block["k"],
                "line": block["line"],
            })

    return states


def nearest(states, ef):

    below = [
        s for s in states
        if s["energy"] < ef
    ]

    above = [
        s for s in states
        if s["energy"] > ef
    ]

    below.sort(
        key=lambda s: ef - s["energy"]
    )

    above.sort(
        key=lambda s: s["energy"] - ef
    )

    return below, above


def show_state(s, ef):

    print(
        f"  E={s['energy']:10.6f} eV   "
        f"dEF={s['energy'] - ef:+10.6f} eV   "
        f"{s['spin']:4s}   "
        f"band={s['band']:2d}   "
        f"k=("
        f"{s['k'][0]: .4f}, "
        f"{s['k'][1]: .4f}, "
        f"{s['k'][2]: .4f})   "
        f"L{s['line']}"
    )


def analyse(grid, path):

    print()
    print("=" * 78)
    print(f"PHASE 78.82 — {grid}³")
    print("=" * 78)

    if not path.exists():
        print("[ERROR] Fichier absent.")
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

    ef_values = []

    for line in lines:
        m = FERMI_RE.search(line)

        if m:
            ef_values.append(
                fnum(m.group(1))
            )

    if not ef_values:
        print("[ERROR] EF introuvable.")
        return

    ef = ef_values[-1]

    print(f"[OK] EF = {ef:.6f} eV")

    # ------------------------------------------------------------------
    # Spin sections
    # ------------------------------------------------------------------

    up_lines = [
        i for i, line in enumerate(lines)
        if UP_RE.search(line)
    ]

    down_lines = [
        i for i, line in enumerate(lines)
        if DOWN_RE.search(line)
    ]

    if not up_lines or not down_lines:
        print("[ERROR] Sections SPIN absentes.")
        return

    up = up_lines[-1]
    down = down_lines[-1]

    print()
    print("[1] SECTIONS SPIN")
    print(f"SPIN UP   : L{up + 1}")
    print(f"SPIN DOWN : L{down + 1}")

    # ------------------------------------------------------------------
    # Tous les headers K
    # ------------------------------------------------------------------

    up_headers = find_all_headers(
        lines,
        up + 1,
        down,
    )

    down_end = len(lines)

    # On arrête avant le Fermi final
    fermi_line = None

    for i in range(down + 1, len(lines)):
        if FERMI_RE.search(lines[i]):
            fermi_line = i
            break

    if fermi_line is not None:
        down_end = fermi_line

    down_headers = find_all_headers(
        lines,
        down + 1,
        down_end,
    )

    expected = EXPECTED_BLOCKS[grid]

    print()
    print("[2] HEADERS `bands (ev)`")

    print(
        f"UP   : {len(up_headers)} / {expected}"
    )

    print(
        f"DOWN : {len(down_headers)} / {expected}"
    )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    up_blocks = parse_blocks(
        lines,
        up_headers,
        "UP",
    )

    down_blocks = parse_blocks(
        lines,
        down_headers,
        "DOWN",
    )

    up_valid, up_invalid = validate_blocks(
        up_blocks
    )

    down_valid, down_invalid = validate_blocks(
        down_blocks
    )

    print()
    print("[3] VALIDATION DES BLOCS")

    if not up_invalid:
        print(
            f"[OK] UP   : {len(up_valid)} blocs × "
            f"{EXPECTED_BANDS} eigenvalues"
        )
    else:
        print(
            f"[WARN] UP : {len(up_invalid)} bloc(s) invalides"
        )

    if not down_invalid:
        print(
            f"[OK] DOWN : {len(down_valid)} blocs × "
            f"{EXPECTED_BANDS} eigenvalues"
        )
    else:
        print(
            f"[WARN] DOWN : {len(down_invalid)} bloc(s) invalides"
        )

    # ------------------------------------------------------------------
    # Détails éventuels
    # ------------------------------------------------------------------

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
    # Vérification globale
    # ------------------------------------------------------------------

    complete = (
        len(up_headers) == expected
        and len(down_headers) == expected
        and not up_invalid
        and not down_invalid
    )

    if not complete:

        print()
        print("[RESULT]")
        print(
            "[WARN] Extraction intégrale NON VALIDEE."
        )
        print(
            "[INFO] Aucun bord électronique global "
            "ne sera interprété."
        )
        return

    # ------------------------------------------------------------------
    # Etats
    # ------------------------------------------------------------------

    up_states = make_states(
        up_valid
    )

    down_states = make_states(
        down_valid
    )

    states = up_states + down_states

    expected_states = (
        expected
        * EXPECTED_BANDS
        * 2
    )

    print()
    print("[4] COMPTAGE DES ETATS")

    print(
        f"UP   : {len(up_states)}"
    )

    print(
        f"DOWN : {len(down_states)}"
    )

    print(
        f"TOTAL : {len(states)} / "
        f"{expected_states}"
    )

    if len(states) != expected_states:
        print(
            "[ERROR] Nombre total d'états incohérent."
        )
        return

    # ------------------------------------------------------------------
    # EF
    # ------------------------------------------------------------------

    below, above = nearest(
        states,
        ef,
    )

    print()
    print("[5] 5 ETATS LES PLUS PROCHES SOUS EF")
    print("-" * 78)

    for state in below[:5]:
        show_state(
            state,
            ef,
        )

    print()
    print("[6] 5 ETATS LES PLUS PROCHES AU-DESSUS DE EF")
    print("-" * 78)

    for state in above[:5]:
        show_state(
            state,
            ef,
        )

    # ------------------------------------------------------------------
    # Résultat
    # ------------------------------------------------------------------

    b = below[0]
    a = above[0]

    d_below = ef - b["energy"]
    d_above = a["energy"] - ef

    print()
    print("[7] RESULTAT ELECTRONIQUE")
    print("-" * 78)

    print(
        f"EF = {ef:.6f} eV"
    )

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
        f"TWO_SIDED_LOCAL_SEPARATION = "
        f"{d_below + d_above:.6f} eV"
    )

    print()
    print(
        "[INFO] Cette quantité est une séparation locale "
        "des états autour de EF."
    )

    print(
        "[INFO] Elle n'est PAS interprétée comme un band gap."
    )

    print(
        "[INFO] Occupations = smearing / MV / degauss = 0.01 Ry."
    )

    print()
    print(
        f"[RESULT] {grid}³ : EXTRACTION INTEGRALE VALIDEE."
    )


def main():

    print("=" * 78)
    print("PHASE 78.82 — FULL BAND BLOCK PARSER v2")
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
    print("PHASE 78.82 — FIN")
    print("=" * 78)


if __name__ == "__main__":
    main()
