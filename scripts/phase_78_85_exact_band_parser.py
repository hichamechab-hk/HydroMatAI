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

K_RE = re.compile(
    r"^\s*k\s*=\s*"
    r"([+-]?\d+(?:\.\d+)?)\s+"
    r"([+-]?\d+(?:\.\d+)?)\s+"
    r"([+-]?\d+(?:\.\d+)?)"
    r".*bands\s*\(ev\)"
)

NUM_RE = re.compile(
    r"^\s*"
    r"([+-]?\d+(?:\.\d+)?(?:[EeDd][+-]?\d+)?)"
    r"(?:\s+([+-]?\d+(?:\.\d+)?(?:[EeDd][+-]?\d+)?))*"
    r"\s*$"
)

FERMI_RE = re.compile(
    r"the Fermi energy is\s+([+-]?\d+(?:\.\d+)?)\s+ev",
    re.I
)

def ffloat(x):
    return float(x.replace("D", "E").replace("d", "e"))

def parse_numeric_line(line):
    s = line.strip()
    if not s:
        return []

    parts = s.split()

    vals = []
    for p in parts:
        try:
            vals.append(ffloat(p))
        except ValueError:
            return []

    return vals

def parse_file(path):

    lines = path.read_text(errors="replace").splitlines()

    # ------------------------------------------------------------------
    # Localisation des sections
    # ------------------------------------------------------------------

    up_line = None
    down_line = None
    fermi_line = None
    ef = None

    for i, line in enumerate(lines):

        if "------ SPIN UP" in line:
            up_line = i

        elif "------ SPIN DOWN" in line:
            down_line = i

        m = FERMI_RE.search(line)
        if m:
            fermi_line = i
            ef = ffloat(m.group(1))

    if up_line is None or down_line is None:
        raise RuntimeError("Sections SPIN UP/DOWN introuvables")

    if fermi_line is None:
        raise RuntimeError("Fermi energy introuvable")

    # ------------------------------------------------------------------
    # Extraction des headers
    # ------------------------------------------------------------------

    up_headers = []
    down_headers = []

    for i in range(up_line + 1, down_line):
        if K_RE.search(lines[i]):
            up_headers.append(i)

    for i in range(down_line + 1, fermi_line):
        if K_RE.search(lines[i]):
            down_headers.append(i)

    # ------------------------------------------------------------------
    # Parse EXACT de chaque bloc
    #
    # QE écrit exactement :
    #
    # header
    #
    # 8 valeurs
    # 8 valeurs
    # 8 valeurs
    # 8 valeurs
    # 4 valeurs
    #
    # = 36 eigenvalues
    # ------------------------------------------------------------------

    def parse_block(header_idx, next_header_idx):

        header = lines[header_idx]

        m = K_RE.search(header)
        if not m:
            return None

        kpoint = tuple(ffloat(x) for x in m.groups())

        values = []

        # On limite volontairement la recherche à la zone
        # située entre ce header et le prochain header.
        end = next_header_idx if next_header_idx is not None else fermi_line

        for j in range(header_idx + 1, end):

            vals = parse_numeric_line(lines[j])

            if vals:
                values.extend(vals)

                if len(values) >= 36:
                    break

        return {
            "line": header_idx + 1,
            "k": kpoint,
            "values": values,
        }

    def parse_section(headers):

        blocks = []

        for n, h in enumerate(headers):

            next_h = headers[n + 1] if n + 1 < len(headers) else None

            block = parse_block(h, next_h)

            blocks.append(block)

        return blocks

    up_blocks = parse_section(up_headers)
    down_blocks = parse_section(down_headers)

    # ------------------------------------------------------------------
    # Validation stricte
    # ------------------------------------------------------------------

    def validate(blocks):

        valid = []
        invalid = []

        for idx, block in enumerate(blocks, start=1):

            n = len(block["values"])

            if n == 36:
                valid.append(block)
            else:
                invalid.append((idx, block["line"], n, block["k"]))

        return valid, invalid

    up_valid, up_invalid = validate(up_blocks)
    down_valid, down_invalid = validate(down_blocks)

    # ------------------------------------------------------------------
    # Etats globaux
    # ------------------------------------------------------------------

    states = []

    for spin, blocks in [
        ("UP", up_valid),
        ("DOWN", down_valid),
    ]:
        for ib, block in enumerate(blocks, start=1):
            for band, energy in enumerate(block["values"], start=1):
                states.append({
                    "spin": spin,
                    "block": ib,
                    "band": band,
                    "energy": energy,
                    "k": block["k"],
                    "line": block["line"],
                })

    below = [s for s in states if s["energy"] <= ef]
    above = [s for s in states if s["energy"] > ef]

    below.sort(key=lambda s: ef - s["energy"])
    above.sort(key=lambda s: s["energy"] - ef)

    return {
        "lines": len(lines),
        "bytes": path.stat().st_size,
        "ef": ef,
        "fermi_line": fermi_line + 1,
        "up_line": up_line + 1,
        "down_line": down_line + 1,
        "up_headers": up_headers,
        "down_headers": down_headers,
        "up_valid": up_valid,
        "down_valid": down_valid,
        "up_invalid": up_invalid,
        "down_invalid": down_invalid,
        "states": states,
        "below": below,
        "above": above,
    }


def print_state(label, state, ef):

    d = state["energy"] - ef

    print(
        f"{label:<14} "
        f"{state['energy']:10.6f} eV   "
        f"ΔEF={d:+.6f} eV   "
        f"spin={state['spin']:<4} "
        f"band={state['band']:2d}   "
        f"k=({state['k'][0]:.4f}, "
        f"{state['k'][1]:.4f}, "
        f"{state['k'][2]:.4f})   "
        f"L{state['line']}"
    )


print("=" * 78)
print("PHASE 78.85 — EXACT FULL BAND PARSER")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

for grid, path in FILES.items():

    print("=" * 78)
    print(f"PHASE 78.85 — {grid}³")
    print("=" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {path.read_text(errors='replace').count(chr(10)) + 1}")
    print(f"[INFO] Octets  : {path.stat().st_size}")

    try:
        r = parse_file(path)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        continue

    print(f"[OK] EF = {r['ef']:.6f} eV (L{r['fermi_line']})")
    print()

    print("[1] SECTIONS")
    print(f"SPIN UP   : L{r['up_line']}")
    print(f"SPIN DOWN : L{r['down_line']}")
    print(f"FERMI     : L{r['fermi_line']}")
    print()

    print("[2] HEADERS `bands (ev)`")
    print(
        f"UP   : {len(r['up_headers'])} / "
        f"{30 if grid == 4 else 39}"
    )
    print(
        f"DOWN : {len(r['down_headers'])} / "
        f"{30 if grid == 4 else 39}"
    )
    print()

    print("[3] VALIDATION EXACTE DES BLOCS")
    print(
        f"UP   : {len(r['up_valid'])} / "
        f"{len(r['up_headers'])} blocs valides"
    )
    print(
        f"DOWN : {len(r['down_valid'])} / "
        f"{len(r['down_headers'])} blocs valides"
    )

    if r["up_invalid"]:
        print()
        print("[WARN] BLOCS UP INVALIDES")
        for item in r["up_invalid"]:
            print(
                f"  bloc={item[0]:2d} "
                f"L{item[1]:4d} "
                f"n={item[2]:2d} "
                f"k={item[3]}"
            )

    if r["down_invalid"]:
        print()
        print("[WARN] BLOCS DOWN INVALIDES")
        for item in r["down_invalid"]:
            print(
                f"  bloc={item[0]:2d} "
                f"L{item[1]:4d} "
                f"n={item[2]:2d} "
                f"k={item[3]}"
            )

    expected_blocks = 60 if grid == 4 else 78
    expected_states = expected_blocks * 36

    print()
    print("[4] COMPTAGE GLOBAL")

    print(f"Blocs attendus       : {expected_blocks}")
    print(
        f"Blocs obtenus        : "
        f"{len(r['up_valid']) + len(r['down_valid'])}"
    )

    print(f"Eigenvalues attendues : {expected_states}")
    print(f"Eigenvalues extraites : {len(r['states'])}")

    complete = (
        len(r["up_invalid"]) == 0
        and len(r["down_invalid"]) == 0
        and len(r["up_valid"]) + len(r["down_valid"]) == expected_blocks
        and len(r["states"]) == expected_states
    )

    print()

    if not complete:
        print("[RESULT]")
        print("[WARN] EXTRACTION COMPLETE NON VALIDEE.")
        print("[INFO] Aucun bord électronique global ne sera interprété.")
        print()
        continue

    print("[OK] EXTRACTION COMPLETE VALIDEE.")
    print("[OK] Tous les blocs contiennent exactement 36 eigenvalues.")
    print()

    print("[5] ETATS LES PLUS PROCHES DE EF")

    if r["below"]:
        print()
        print("Plus proches SOUS EF :")
        for i, state in enumerate(r["below"][:10], start=1):
            print_state(f"{i:2d}.", state, r["ef"])

    if r["above"]:
        print()
        print("Plus proches AU-DESSUS EF :")
        for i, state in enumerate(r["above"][:10], start=1):
            print_state(f"{i:2d}.", state, r["ef"])

    if r["below"] and r["above"]:

        lower = r["below"][0]
        upper = r["above"][0]

        lower_dist = r["ef"] - lower["energy"]
        upper_dist = upper["energy"] - r["ef"]

        print()
        print("[6] DIAGNOSTIC DE PROXIMITE A EF")
        print(f"EF                  = {r['ef']:.6f} eV")
        print(f"Etat inférieur      = {lower['energy']:.6f} eV")
        print(f"Distance inférieure = {lower_dist:.6f} eV")
        print(f"Etat supérieur      = {upper['energy']:.6f} eV")
        print(f"Distance supérieure = {upper_dist:.6f} eV")
        print(
            f"Séparation locale   = "
            f"{lower_dist + upper_dist:.6f} eV"
        )

    print()
    print("[IMPORTANT]")
    print("[INFO] Ces valeurs sont des eigenvalues issues d'un calcul")
    print("[INFO] occupations='smearing', smearing='mv', degauss=0.01.")
    print("[INFO] Elles décrivent la proximité des états autour de EF.")
    print("[INFO] Aucun 'band gap' ne sera déclaré à partir de cette seule")
    print("[INFO] analyse sans protocole électronique complémentaire.")

print()
print("=" * 78)
print("PHASE 78.85 — FIN")
print("=" * 78)
