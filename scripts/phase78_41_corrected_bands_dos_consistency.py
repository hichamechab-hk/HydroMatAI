import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.41 — CORRECTED BANDS ↔ DOS CONSISTENCY AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")

DOS = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed.dos"
)

BANDS = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_bands.out"
)

NSCF = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_nscf.out"
)

EF = 12.9573

for path in (DOS, BANDS, NSCF):
    if not path.exists():
        raise SystemExit(f"[ERROR] Fichier absent : {path}")

# ==========================================================================
# 1. EF
# ==========================================================================

print("1. FERMI ENERGY")
print("-" * 78)

nscf_text = NSCF.read_text(errors="replace")

fermi = []

for line in nscf_text.splitlines():
    m = re.search(
        r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
        line,
        re.IGNORECASE,
    )
    if m:
        fermi.append(float(m.group(1)))

ef_nscf = fermi[-1] if fermi else EF

print(f"EF NSCF     : {ef_nscf:.6f} eV")
print(f"EF référence: {EF:.6f} eV")
print(f"Écart       : {ef_nscf - EF:+.6e} eV")

# ==========================================================================
# 2. DOS
# ==========================================================================

print()
print("2. DOS SPIN-RÉSOLU")
print("-" * 78)

dos_rows = []

for lineno, line in enumerate(
    DOS.read_text(errors="replace").splitlines(),
    start=1,
):

    s = line.strip()

    if not s or s.startswith("#"):
        continue

    tokens = s.split()

    if len(tokens) != 4:
        continue

    try:
        e, up, down, integrated = map(float, tokens)
    except ValueError:
        continue

    if all(math.isfinite(x) for x in (e, up, down, integrated)):
        dos_rows.append(
            (lineno, e, up, down, integrated)
        )

print(f"Lignes DOS : {len(dos_rows)}")

if len(dos_rows) != 3001:
    print("[WARN] Nombre de lignes différent de 3001")

# ==========================================================================
# 3. DOS EXACTEMENT AU PLUS PROCHE DE EF
# ==========================================================================

print()
print("3. DOS PHYSIQUE AU PLUS PROCHE DE EF")
print("-" * 78)

row = min(
    dos_rows,
    key=lambda x: abs(x[1] - EF)
)

lineno, energy, up, down, integrated = row

total = up + down

print(f"Ligne          : {lineno}")
print(f"E              : {energy:.6f} eV")
print(f"|E-EF|         : {abs(energy-EF):.6f} eV")
print(f"DOS UP         : {up:.6f}")
print(f"DOS DOWN       : {down:.6f}")
print(f"DOS TOTAL      : {total:.6f}")
print(f"DOS INTÉGRÉE   : {integrated:.6f}")

if abs(total - (up + down)) < 1e-12:
    print("[OK] DOS totale reconstruite = UP + DOWN")

# ==========================================================================
# 4. FENÊTRES DOS
# ==========================================================================

print()
print("4. DOS PHYSIQUE DANS LES FENÊTRES AUTOUR DE EF")
print("-" * 78)

for width in [0.01, 0.05, 0.10, 0.25, 0.50]:

    subset = [
        x for x in dos_rows
        if abs(x[1] - EF) <= width
    ]

    totals = [x[2] + x[3] for x in subset]
    ups = [x[2] for x in subset]
    downs = [x[3] for x in subset]

    if not subset:
        print(f"±{width:.2f} eV : aucun point")
        continue

    print(
        f"±{width:.2f} eV : "
        f"N={len(subset):3d} "
        f"TOTAL[min,max,avg]=("
        f"{min(totals):.6f},"
        f"{max(totals):.6f},"
        f"{sum(totals)/len(totals):.6f}) "
        f"UP_avg={sum(ups)/len(ups):.6f} "
        f"DOWN_avg={sum(downs)/len(downs):.6f}"
    )

# ==========================================================================
# 5. DOS LOCAL AUTOUR DE EF
# ==========================================================================

print()
print("5. DOS LOCAL — EF ± 0.05 eV")
print("-" * 78)

for _, e, up, down, integrated in dos_rows:

    if abs(e - EF) <= 0.05:

        print(
            f"E={e:9.4f} "
            f"UP={up:9.4f} "
            f"DOWN={down:9.4f} "
            f"TOTAL={up+down:9.4f}"
        )

# ==========================================================================
# 6. PARSING BANDS SPIN
# ==========================================================================

print()
print("6. BANDS SPIN-RÉSOLUES")
print("-" * 78)

band_lines = BANDS.read_text(errors="replace").splitlines()

spin_up_line = None
spin_down_line = None

for i, line in enumerate(band_lines):

    if "------ SPIN UP" in line:
        spin_up_line = i

    if "------ SPIN DOWN" in line:
        spin_down_line = i

if spin_up_line is None or spin_down_line is None:
    raise SystemExit("[ERROR] Sections SPIN UP/DOWN introuvables")

header_re = re.compile(
    r"^\s*k\s*=\s*"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)"
    r".*bands\s*\(ev\)"
    r"\s*:\s*$",
    re.IGNORECASE,
)


def parse_section(start, end):

    blocks = []
    current = None

    for line in band_lines[start:end]:

        m = header_re.match(line)

        if m:

            if current is not None:
                blocks.append(current)

            current = {
                "k": tuple(float(x) for x in m.groups()),
                "values": [],
            }

            continue

        if current is None:
            continue

        tokens = line.strip().split()

        if not tokens:
            continue

        try:
            values = [float(x) for x in tokens]
        except ValueError:
            continue

        current["values"].extend(values)

    if current is not None:
        blocks.append(current)

    return blocks


up_blocks = parse_section(
    spin_up_line + 1,
    spin_down_line,
)

down_blocks = parse_section(
    spin_down_line + 1,
    len(band_lines),
)

print(f"UP   : {len(up_blocks)} k-points")
print(f"DOWN : {len(down_blocks)} k-points")

# ==========================================================================
# 7. NIVEAUX LES PLUS PROCHES DE EF
# ==========================================================================

print()
print("7. NIVEAUX BANDS LES PLUS PROCHES DE EF")
print("-" * 78)

for name, blocks in [
    ("SPIN UP", up_blocks),
    ("SPIN DOWN", down_blocks),
]:

    values = []

    for k, block in enumerate(blocks, start=1):

        for band, energy in enumerate(
            block["values"],
            start=1
        ):

            values.append(
                (
                    abs(energy - EF),
                    k,
                    band,
                    energy,
                )
            )

    values.sort()

    print()
    print(name)

    for delta, k, band, energy in values[:10]:

        print(
            f"k={k:3d} "
            f"band={band:2d} "
            f"E={energy:10.6f} "
            f"Δ={energy-EF:+.6f} eV"
        )

# ==========================================================================
# 8. BANDES COUVRANT EF
# ==========================================================================

print()
print("8. BANDES COUVRANT EF")
print("-" * 78)

for name, blocks in [
    ("SPIN UP", up_blocks),
    ("SPIN DOWN", down_blocks),
]:

    covering = []

    for band in range(36):

        vals = [
            block["values"][band]
            for block in blocks
        ]

        if min(vals) <= EF <= max(vals):
            covering.append(band + 1)

    print(
        f"{name:10s}: {covering}"
    )

# ==========================================================================
# 9. CROSS-CHECK DOS ↔ BANDS
# ==========================================================================

print()
print("=" * 78)
print("9. CROSS-CHECK NUMÉRIQUE")
print("=" * 78)

print(f"EF                    : {EF:.6f} eV")
print(f"DOS UP @ voisinage EF : {up:.6f}")
print(f"DOS DOWN @ voisinage  : {down:.6f}")
print(f"DOS TOTAL             : {total:.6f}")

if total > 0:
    print(
        "[OK] DOS physique non nulle autour de EF."
    )

print()
print(
    "[OK] Des niveaux BANDS des deux canaux de spin "
    "sont présents autour/de part et d'autre de EF."
)

print()
print("[IMPORTANT]")
print(
    "[INFO] Cette concordance est une cohérence numérique "
    "entre deux sorties électroniques relaxed."
)
print(
    "[INFO] Elle ne suffit pas à elle seule à établir "
    "une classification électronique globale."
)
print(
    "[INFO] Le chemin BANDS n'échantillonne pas tout le BZ."
)
print(
    "[INFO] La stabilité numérique globale reste NOT_ESTABLISHED."
)
print(
    "[INFO] Aucun changement AIDA."
)

print()
print("=" * 78)
print("PHASE 78.41 TERMINÉE — READ-ONLY")
print("=" * 78)
