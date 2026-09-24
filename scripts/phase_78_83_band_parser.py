#!/usr/bin/env python3

import sys
import re
from pathlib import Path

# ============================================================
# Nettoyage terminal sans dépendre de TERM
# ============================================================
sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

EXPECTED = {
    4: 30,
    5: 39,
}

NBND = 36

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


def is_float(token):
    return re.fullmatch(FLOAT, token, re.I) is not None


def parse_numeric_line(line):
    """
    Retourne les valeurs numériques d'une ligne uniquement
    si tous les tokens sont des flottants.
    """
    tokens = line.strip().split()

    if not tokens:
        return None

    if not all(is_float(x) for x in tokens):
        return None

    return [fnum(x) for x in tokens]


def find_headers(lines, start, end):

    headers = []

    for i in range(start, end):

        m = K_RE.search(lines[i])

        if m:

            headers.append({
                "line": i,
                "k": (
                    fnum(m.group(1)),
                    fnum(m.group(2)),
                    fnum(m.group(3)),
                ),
            })

    return headers


def extract_block(lines, header_index, next_header_index):
    """
    Extraction stricte.

    Après le header k=..., on recherche les lignes numériques.
    On arrête dès que NBND=36 eigenvalues ont été récupérées.

    IMPORTANT :
    on ne traverse jamais le prochain header.
    """

    values = []

    # Fenêtre maximale volontairement raisonnable.
    # Les blocs QE observés ici sont courts.
    max_line = min(
        next_header_index,
        header_index + 12,
    )

    for i in range(header_index + 1, max_line):

        # Ne jamais franchir un nouveau header.
        if K_RE.search(lines[i]):
            break

        vals = parse_numeric_line(lines[i])

        if vals is None:
            continue

        # Ajouter uniquement ce qui est nécessaire.
        remaining = NBND - len(values)

        values.extend(vals[:remaining])

        if len(values) == NBND:
            break

    return values


def parse_spin(lines, start, end, spin):

    headers = find_headers(
        lines,
        start,
        end,
    )

    blocks = []

    for n, header in enumerate(headers):

        if n + 1 < len(headers):
            next_header = headers[n + 1]["line"]
        else:
            next_header = end

        values = extract_block(
            lines,
            header["line"],
            next_header,
        )

        blocks.append({
            "number": n + 1,
            "spin": spin,
            "line": header["line"] + 1,
            "k": header["k"],
            "values": values,
        })

    return blocks


def validate(blocks):

    good = []
    bad = []

    for block in blocks:

        if len(block["values"]) == NBND:
            good.append(block)
        else:
            bad.append(block)

    return good, bad


def states_from(blocks):

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
    print(f"PHASE 78.83 — {grid}³")
    print("=" * 78)

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(lines)}")
    print(f"[INFO] Octets  : {path.stat().st_size}")

    # ------------------------------------------------------------
    # EF
    # ------------------------------------------------------------

    ef_matches = []

    for i, line in enumerate(lines):

        m = FERMI_RE.search(line)

        if m:
            ef_matches.append(
                (i, fnum(m.group(1)))
            )

    if not ef_matches:
        print("[ERROR] EF introuvable.")
        return

    ef_line, ef = ef_matches[-1]

    print(
        f"[OK] EF = {ef:.6f} eV "
        f"(L{ef_line + 1})"
    )

    # ------------------------------------------------------------
    # SPINS
    # ------------------------------------------------------------

    up_positions = [
        i for i, line in enumerate(lines)
        if UP_RE.search(line)
    ]

    down_positions = [
        i for i, line in enumerate(lines)
        if DOWN_RE.search(line)
    ]

    if not up_positions or not down_positions:
        print("[ERROR] Sections SPIN absentes.")
        return

    up = up_positions[-1]
    down = down_positions[-1]

    print()
    print("[1] SECTIONS")
    print(f"SPIN UP   : L{up + 1}")
    print(f"SPIN DOWN : L{down + 1}")
    print(f"FERMI     : L{ef_line + 1}")

    # ------------------------------------------------------------
    # HEADERS
    # ------------------------------------------------------------

    up_blocks = parse_spin(
        lines,
        up + 1,
        down,
        "UP",
    )

    down_blocks = parse_spin(
        lines,
        down + 1,
        ef_line,
        "DOWN",
    )

    expected = EXPECTED[grid]

    print()
    print("[2] HEADERS")

    print(
        f"UP   : {len(up_blocks)} / {expected}"
    )

    print(
        f"DOWN : {len(down_blocks)} / {expected}"
    )

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    up_good, up_bad = validate(up_blocks)
    down_good, down_bad = validate(down_blocks)

    print()
    print("[3] VALIDATION DES 36 EIGENVALUES")

    print(
        f"UP   : {len(up_good)} blocs valides"
    )

    print(
        f"DOWN : {len(down_good)} blocs valides"
    )

    if up_bad:

        print()
        print("[WARN] BLOCS UP INCOMPLETS")

        for b in up_bad:
            print(
                f"  bloc {b['number']:2d} "
                f"L{b['line']:4d} "
                f"n={len(b['values']):2d} "
                f"k={b['k']}"
            )

    if down_bad:

        print()
        print("[WARN] BLOCS DOWN INCOMPLETS")

        for b in down_bad:
            print(
                f"  bloc {b['number']:2d} "
                f"L{b['line']:4d} "
                f"n={len(b['values']):2d} "
                f"k={b['k']}"
            )

    # ------------------------------------------------------------
    # COMPLETUDE
    # ------------------------------------------------------------

    complete = (
        len(up_blocks) == expected
        and len(down_blocks) == expected
        and not up_bad
        and not down_bad
    )

    if not complete:

        print()
        print("[RESULT]")
        print(
            "[WARN] EXTRACTION COMPLETE NON VALIDEE."
        )

        print(
            "[INFO] Aucun résultat électronique global "
            "ne sera interprété."
        )

        return

    # ------------------------------------------------------------
    # ETATS
    # ------------------------------------------------------------

    up_states = states_from(up_good)
    down_states = states_from(down_good)

    states = up_states + down_states

    expected_states = (
        expected * NBND * 2
    )

    print()
    print("[4] COMPTAGE")

    print(
        f"UP    = {len(up_states)}"
    )

    print(
        f"DOWN  = {len(down_states)}"
    )

    print(
        f"TOTAL = {len(states)} / {expected_states}"
    )

    if len(states) != expected_states:
        print(
            "[ERROR] Comptage électronique incohérent."
        )
        return

    # ------------------------------------------------------------
    # AUTOUR DE EF
    # ------------------------------------------------------------

    below = sorted(
        [
            s for s in states
            if s["energy"] < ef
        ],
        key=lambda s: ef - s["energy"],
    )

    above = sorted(
        [
            s for s in states
            if s["energy"] > ef
        ],
        key=lambda s: s["energy"] - ef,
    )

    print()
    print("[5] PLUS PROCHES SOUS EF")
    print("-" * 78)

    for s in below[:5]:
        show_state(s, ef)

    print()
    print("[6] PLUS PROCHES AU-DESSUS DE EF")
    print("-" * 78)

    for s in above[:5]:
        show_state(s, ef)

    b = below[0]
    a = above[0]

    db = ef - b["energy"]
    da = a["energy"] - ef

    print()
    print("[7] RESULTAT")
    print("-" * 78)

    print(
        f"EF = {ef:.6f} eV"
    )

    print(
        f"MAX BELOW EF = {b['energy']:.6f} eV"
    )

    print(
        f"MIN ABOVE EF = {a['energy']:.6f} eV"
    )

    print(
        f"Δbelow = {db:.6f} eV"
    )

    print(
        f"Δabove = {da:.6f} eV"
    )

    print(
        f"SEPARATION LOCALE = {db + da:.6f} eV"
    )

    print()
    print(
        "[INFO] La séparation locale autour de EF "
        "n'est pas assimilée à un band gap."
    )

    print(
        f"[RESULT] {grid}³ : EXTRACTION COMPLETE VALIDEE."
    )


def main():

    print("=" * 78)
    print("PHASE 78.83 — BAND PARSER v3")
    print("=" * 78)
    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun recalcul")
    print("[INFO] Aucun fichier scientifique modifié")

    for grid in (4, 5):

        path = FILES[grid]

        if not path.exists():
            print()
            print(
                f"[ERROR] Fichier {grid}³ absent : {path}"
            )
            continue

        analyse(
            grid,
            path,
        )

    print()
    print("=" * 78)
    print("PHASE 78.83 — FIN")
    print("=" * 78)


if __name__ == "__main__":
    main()
