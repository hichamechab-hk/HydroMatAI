#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?"

HEADER_RE = re.compile(
    r"^\s*k\s*=.*bands\s*\(ev\)\s*:\s*$",
    re.IGNORECASE
)

EF_RE = re.compile(
    rf"the Fermi energy is\s+({FLOAT})\s+ev",
    re.IGNORECASE
)

NUMERIC_RE = re.compile(r"^[\s+\-0-9.eEdD]+$")


def fnum(x):
    return float(x.replace("D", "E").replace("d", "e"))


def extract_k(header):
    """
    Extraction des trois coordonnées directement depuis
    la partie située avant 'bands (ev):'.

    On utilise les nombres présents dans l'en-tête,
    sans jamais scanner les lignes d'énergie.
    """
    text = re.sub(
        r"\s*bands\s*\(ev\)\s*:\s*$",
        "",
        header,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^\s*k\s*=\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Format normal QE :
    # k = 0.0000 0.0000 0.4954 bands (ev):
    vals = re.findall(FLOAT, text)

    if len(vals) >= 3:
        try:
            return tuple(fnum(v) for v in vals[:3])
        except ValueError:
            return None

    return None


def parse_file(path):
    lines = path.read_text(errors="replace").splitlines()

    ef = None

    for line in lines:
        m = EF_RE.search(line)
        if m:
            ef = fnum(m.group(1))

    records = []
    spin = None

    for i, line in enumerate(lines):

        if re.search(r"SPIN\s+UP", line, re.IGNORECASE):
            spin = "UP"

        elif re.search(r"SPIN\s+DOWN", line, re.IGNORECASE):
            spin = "DOWN"

        if not HEADER_RE.match(line):
            continue

        k = extract_k(line)

        j = i + 1

        while j < len(lines) and not lines[j].strip():
            j += 1

        values = []

        while j < len(lines):

            s = lines[j].strip()

            if not s:
                break

            if not NUMERIC_RE.match(s):
                break

            nums = re.findall(FLOAT, s)

            if not nums:
                break

            values.extend(fnum(x) for x in nums)
            j += 1

        if len(values) != 36:
            continue

        for band, energy in enumerate(values, start=1):
            records.append(
                {
                    "spin": spin,
                    "band": band,
                    "energy": energy,
                    "k": k,
                    "header_line": i + 1,
                }
            )

    return lines, ef, records


def nearest_states(records, ef):

    below = None
    above = None

    for r in records:

        if r["energy"] <= ef:
            if below is None or r["energy"] > below["energy"]:
                below = r

        if r["energy"] >= ef:
            if above is None or r["energy"] < above["energy"]:
                above = r

    return below, above


def print_state(label, state, ef):

    print(label)

    if state is None:
        print("  [WARN] Aucun état")
        return

    print(f"  Spin       : {state['spin']}")
    print(f"  Bande      : {state['band']}")
    print(f"  Energie    : {state['energy']:.6f} eV")
    print(f"  ΔEF        : {state['energy'] - ef:+.6f} eV")
    print(f"  Header     : ligne {state['header_line']}")

    if state["k"] is None:
        print("  k-point    : NON PARSÉ")
    else:
        x, y, z = state["k"]
        print(f"  k-point    : ({x:+.4f}, {y:+.4f}, {z:+.4f})")


print("=" * 78)
print("PHASE 78.89 — VALIDATION INDÉPENDANTE DU PARSEUR")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

results = {}

for mesh, path in FILES.items():

    print("=" * 78)
    print(f"PHASE 78.89 — {mesh}³")
    print("=" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    lines, ef, records = parse_file(path)

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(lines)}")

    if ef is None:
        print("[ERROR] EF introuvable")
        continue

    expected_blocks = 60 if mesh == 4 else 78
    expected_states = expected_blocks * 36

    up = [r for r in records if r["spin"] == "UP"]
    down = [r for r in records if r["spin"] == "DOWN"]

    print(f"[OK] EF = {ef:.6f} eV")
    print()
    print("[VALIDATION]")
    print(f"  Etats attendus : {expected_states}")
    print(f"  Etats extraits : {len(records)}")
    print(f"  UP             : {len(up)}")
    print(f"  DOWN           : {len(down)}")

    if len(records) == expected_states:
        print("  [PASS] Extraction complète")
    else:
        print("  [FAIL] Extraction incomplète")

    missing_k = sum(r["k"] is None for r in records)

    print()
    print("[K-POINTS]")
    print(f"  Coordonnées non parsées : {missing_k}/{len(records)}")

    if missing_k == 0:
        print("  [PASS] Coordonnées k complètes")
    else:
        print("  [WARN] Coordonnées k incomplètes")

    below, above = nearest_states(records, ef)

    print()
    print("-" * 78)
    print("ÉTAT LE PLUS PROCHE SOUS EF")
    print("-" * 78)
    print_state("[BELOW EF]", below, ef)

    print()
    print("-" * 78)
    print("ÉTAT LE PLUS PROCHE AU-DESSUS DE EF")
    print("-" * 78)
    print_state("[ABOVE EF]", above, ef)

    if below is not None and above is not None:

        separation = above["energy"] - below["energy"]

        print()
        print("-" * 78)
        print("SÉPARATION LOCALE")
        print("-" * 78)
        print(f"  Δ local = {separation:.6f} eV")
        print(f"  Δ local = {separation * 1000:.3f} meV")

    # Quelques k-points uniques pour contrôle visuel.
    print()
    print("[ÉCHANTILLON K-POINTS]")

    seen = set()

    for r in records:

        key = (r["spin"], r["header_line"])

        if key in seen:
            continue

        seen.add(key)

        if r["k"] is not None:
            print(
                f"  {r['spin']:4s} "
                f"ligne {r['header_line']:4d} : "
                f"k=({r['k'][0]:+.4f}, "
                f"{r['k'][1]:+.4f}, "
                f"{r['k'][2]:+.4f})"
            )

        if len(seen) >= 5:
            break

    results[mesh] = {
        "ef": ef,
        "below": below,
        "above": above,
    }


print()
print("=" * 78)
print("PHASE 78.89 — COMPARAISON")
print("=" * 78)

for mesh in (4, 5):

    if mesh not in results:
        continue

    r = results[mesh]

    print(f"{mesh}³ : EF = {r['ef']:.6f} eV")

    if r["below"]:
        b = r["below"]
        print(
            f"  BELOW = {b['energy']:.6f} eV | "
            f"{b['spin']} | band {b['band']} | k={b['k']}"
        )

    if r["above"]:
        a = r["above"]
        print(
            f"  ABOVE = {a['energy']:.6f} eV | "
            f"{a['spin']} | band {a['band']} | k={a['k']}"
        )

if 4 in results and 5 in results:

    dEF = results[5]["ef"] - results[4]["ef"]

    print()
    print(f"ΔEF (5³ - 4³) = {dEF:+.6f} eV")

print()
print("=" * 78)
print("PHASE 78.89 — FIN")
print("=" * 78)
print("[INFO] Validation du parsing uniquement.")
print("[INFO] Aucun gap global déduit.")
print("[PASS] READ-ONLY")
print("=" * 78)
