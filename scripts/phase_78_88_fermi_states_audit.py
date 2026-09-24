#!/usr/bin/env python3

import re
from pathlib import Path

# Nettoyage terminal sans dépendre de TERM
print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

HEADER_RE = re.compile(
    r"^\s*k\s*=.*bands\s*\(ev\)\s*:\s*$",
    re.IGNORECASE
)

NUMBER_RE = re.compile(
    r"^[\s+\-0-9.eEdD]+$"
)

FLOAT_RE = re.compile(
    r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?"
)


def parse_float(text):
    return float(text.replace("D", "E").replace("d", "e"))


def parse_file(path):
    lines = path.read_text(errors="replace").splitlines()

    ef = None

    for line in lines:
        m = re.search(r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev", line, re.I)
        if m:
            ef = parse_float(m.group(1))

    blocks = []
    current_spin = None

    for i, line in enumerate(lines):
        s = line.strip()

        if re.search(r"------\s*SPIN\s+UP", line, re.I):
            current_spin = "UP"
            continue

        if re.search(r"------\s*SPIN\s+DOWN", line, re.I):
            current_spin = "DOWN"
            continue

        if not HEADER_RE.match(line):
            continue

        header_line = i + 1
        header = line.strip()

        # Coordonnées k-point.
        coord_text = None
        mcoord = re.search(r"k\s*=\s*(.*?)\s+bands\s*\(ev\)", line, re.I)
        if mcoord:
            coord_text = mcoord.group(1).strip()

        # Extraction robuste des coordonnées, y compris lorsque QE
        # supprime certains espaces autour des signes négatifs.
        coords = None
        if coord_text:
            nums = FLOAT_RE.findall(coord_text)
            if len(nums) >= 3:
                try:
                    coords = tuple(parse_float(x) for x in nums[-3:])
                except ValueError:
                    coords = None

        # Après le header : ignorer les lignes vides initiales,
        # puis collecter les lignes numériques jusqu'à la ligne vide.
        j = i + 1

        while j < len(lines) and not lines[j].strip():
            j += 1

        numeric_lines = []

        while j < len(lines):
            t = lines[j].strip()

            if not t:
                break

            if not NUMBER_RE.match(t):
                break

            vals = FLOAT_RE.findall(t)

            if not vals:
                break

            numeric_lines.append((j + 1, vals))
            j += 1

        values = []

        for _, vals in numeric_lines:
            for v in vals:
                try:
                    values.append(parse_float(v))
                except ValueError:
                    pass

        valid = (
            len(numeric_lines) == 5
            and len(values) == 36
        )

        if valid:
            for band_index, energy in enumerate(values, start=1):
                blocks.append({
                    "spin": current_spin,
                    "band": band_index,
                    "energy": energy,
                    "k": coords,
                    "line": header_line,
                })

    return lines, ef, blocks


def nearest_states(blocks, ef):
    below = None
    above = None

    for b in blocks:
        e = b["energy"]

        if e <= ef:
            if below is None or e > below["energy"]:
                below = b

        if e >= ef:
            if above is None or e < above["energy"]:
                above = b

    return below, above


def fmt_state(label, state, ef):
    if state is None:
        print(f"[WARN] {label} : aucun état trouvé")
        return

    de = state["energy"] - ef

    print(f"{label}")
    print(f"  Spin       : {state['spin']}")
    print(f"  Bande      : {state['band']}")
    print(f"  Energie    : {state['energy']:.6f} eV")
    print(f"  ΔEF        : {de:+.6f} eV")
    print(f"  |ΔEF|      : {abs(de):.6f} eV")
    print(f"  Ligne header : {state['line']}")

    if state["k"] is not None:
        print(
            "  k-point    : "
            f"({state['k'][0]:+.4f}, "
            f"{state['k'][1]:+.4f}, "
            f"{state['k'][2]:+.4f})"
        )
    else:
        print("  k-point    : non parsé")


print("=" * 78)
print("PHASE 78.88 — AUDIT QUANTITATIF DES ÉTATS PROCHES DE EF")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

results = {}

for mesh, path in FILES.items():

    print("=" * 78)
    print(f"PHASE 78.88 — {mesh}³")
    print("=" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    lines, ef, blocks = parse_file(path)

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(lines)}")

    if ef is None:
        print("[ERROR] EF introuvable")
        continue

    print(f"[OK] EF = {ef:.6f} eV")

    up = [b for b in blocks if b["spin"] == "UP"]
    down = [b for b in blocks if b["spin"] == "DOWN"]

    print()
    print(f"[INFO] États UP extraits   : {len(up)}")
    print(f"[INFO] États DOWN extraits : {len(down)}")
    print(f"[INFO] États totaux        : {len(blocks)}")

    below, above = nearest_states(blocks, ef)

    print()
    print("-" * 78)
    print("ÉTAT LE PLUS PROCHE SOUS EF")
    print("-" * 78)
    fmt_state("[BELOW EF]", below, ef)

    print()
    print("-" * 78)
    print("ÉTAT LE PLUS PROCHE AU-DESSUS DE EF")
    print("-" * 78)
    fmt_state("[ABOVE EF]", above, ef)

    separation = None

    if below is not None and above is not None:
        separation = above["energy"] - below["energy"]

        print()
        print("-" * 78)
        print("SÉPARATION LOCALE AUTOUR DE EF")
        print("-" * 78)
        print(f"EF                  : {ef:.6f} eV")
        print(f"Below               : {below['energy']:.6f} eV")
        print(f"Above               : {above['energy']:.6f} eV")
        print(f"Δ local             : {separation:.6f} eV")
        print(f"Δ local             : {separation * 1000:.3f} meV")

    results[mesh] = {
        "ef": ef,
        "below": below,
        "above": above,
        "separation": separation,
    }


print()
print("=" * 78)
print("PHASE 78.88 — COMPARAISON 4³ / 5³")
print("=" * 78)

for mesh in (4, 5):
    if mesh not in results:
        continue

    r = results[mesh]

    print()
    print(f"{mesh}³")
    print(f"  EF = {r['ef']:.6f} eV")

    if r["below"]:
        print(
            f"  Below = {r['below']['energy']:.6f} eV "
            f"({r['below']['spin']}, band {r['below']['band']})"
        )

    if r["above"]:
        print(
            f"  Above = {r['above']['energy']:.6f} eV "
            f"({r['above']['spin']}, band {r['above']['band']})"
        )

    if r["separation"] is not None:
        print(
            f"  Séparation locale = "
            f"{r['separation']:.6f} eV "
            f"({r['separation'] * 1000:.3f} meV)"
        )

if 4 in results and 5 in results:

    ef_delta = results[5]["ef"] - results[4]["ef"]

    print()
    print("-" * 78)
    print("VARIATION EF")
    print("-" * 78)
    print(f"EF(4³) : {results[4]['ef']:.6f} eV")
    print(f"EF(5³) : {results[5]['ef']:.6f} eV")
    print(f"ΔEF    : {ef_delta:+.6f} eV")

print()
print("=" * 78)
print("PHASE 78.88 — INTERPRÉTATION")
print("=" * 78)
print("[INFO] Cet audit recherche uniquement les états les plus proches de EF.")
print("[INFO] La séparation locale n'est PAS un gap électronique global.")
print("[INFO] Aucun classement métallique/semiconducteur n'est produit.")
print("[INFO] Une conclusion globale nécessite une analyse complète de la")
print("       dispersion des bandes sur l'ensemble des k-points.")
print()
print("[PASS] AUDIT TERMINÉ — MODE READ-ONLY")
print("=" * 78)
