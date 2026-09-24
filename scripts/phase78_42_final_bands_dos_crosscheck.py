import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.42 — FINAL BANDS ↔ DOS CROSS-CHECK")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")

DOS = BASE / (
    "calculations/top5_dft/TiFeH2/electronic_relaxed/"
    "TiFeH2_relaxed.dos"
)

BANDS = BASE / (
    "calculations/top5_dft/TiFeH2/electronic_relaxed/"
    "TiFeH2_relaxed_bands.out"
)

NSCF = BASE / (
    "calculations/top5_dft/TiFeH2/electronic_relaxed/"
    "TiFeH2_relaxed_nscf.out"
)

EF = 12.9573

# ==========================================================================
# 1. FILES
# ==========================================================================

print("1. FICHIERS")
print("-" * 78)

for name, path in [
    ("DOS", DOS),
    ("BANDS", BANDS),
    ("NSCF", NSCF),
]:
    print(f"{name:5s} : {'OK' if path.exists() else 'ABSENT'}")

if not all(p.exists() for p in [DOS, BANDS, NSCF]):
    raise SystemExit("[ERROR] Fichier requis absent")

# ==========================================================================
# 2. EF
# ==========================================================================

print()
print("2. FERMI ENERGY")
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

ef_nscf = fermi[-1] if fermi else None

print(f"EF référence : {EF:.6f} eV")

if ef_nscf is not None:
    print(f"EF NSCF      : {ef_nscf:.6f} eV")
    print(f"Écart        : {ef_nscf - EF:+.6e} eV")

# ==========================================================================
# 3. DOS
# ==========================================================================

print()
print("3. DOS SPIN-RÉSOLU")
print("-" * 78)

rows = []

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
        energy, dos_up, dos_down, integrated = map(float, tokens)
    except ValueError:
        continue

    if all(
        math.isfinite(x)
        for x in [energy, dos_up, dos_down, integrated]
    ):
        rows.append(
            {
                "line": lineno,
                "energy": energy,
                "up": dos_up,
                "down": dos_down,
                "integrated": integrated,
            }
        )

print(f"Lignes DOS : {len(rows)}")

# ==========================================================================
# 4. REFERENCE DOS POINT
# ==========================================================================

print()
print("4. POINT DOS DE RÉFÉRENCE")
print("-" * 78)

ref = min(
    rows,
    key=lambda r: abs(r["energy"] - EF)
)

ref_e = ref["energy"]
ref_up = ref["up"]
ref_down = ref["down"]
ref_total = ref_up + ref_down
ref_integrated = ref["integrated"]

print(f"Ligne       : {ref['line']}")
print(f"E           : {ref_e:.6f} eV")
print(f"|E-EF|      : {abs(ref_e-EF):.6f} eV")
print(f"DOS UP      : {ref_up:.6f}")
print(f"DOS DOWN    : {ref_down:.6f}")
print(f"DOS TOTAL   : {ref_total:.6f}")
print(f"Int DOS     : {ref_integrated:.6f}")

print()
print(
    f"[CHECK] {ref_up:.6f} + {ref_down:.6f} "
    f"= {ref_total:.6f}"
)

# ==========================================================================
# 5. DOS WINDOW
# ==========================================================================

print()
print("5. DOS PHYSIQUE AUTOUR DE EF")
print("-" * 78)

for width in [0.01, 0.05, 0.10, 0.25, 0.50]:

    subset = [
        r for r in rows
        if abs(r["energy"] - EF) <= width
    ]

    totals = [
        r["up"] + r["down"]
        for r in subset
    ]

    if not subset:
        continue

    print(
        f"±{width:.2f} eV : "
        f"N={len(subset):3d} "
        f"TOTAL[min,max,avg]=("
        f"{min(totals):.6f},"
        f"{max(totals):.6f},"
        f"{sum(totals)/len(totals):.6f})"
    )

# ==========================================================================
# 6. BANDS
# ==========================================================================

print()
print("6. BANDS SPIN-RÉSOLUES")
print("-" * 78)

band_lines = BANDS.read_text(errors="replace").splitlines()

spin_up_start = None
spin_down_start = None

for i, line in enumerate(band_lines):

    if "------ SPIN UP" in line:
        spin_up_start = i

    if "------ SPIN DOWN" in line:
        spin_down_start = i

if spin_up_start is None or spin_down_start is None:
    raise SystemExit("[ERROR] Sections spin introuvables")

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

        match = header_re.match(line)

        if match:

            if current is not None:
                blocks.append(current)

            current = {
                "k": tuple(float(x) for x in match.groups()),
                "values": [],
            }

            continue

        if current is None:
            continue

        tokens = line.strip().split()

        if not tokens:
            continue

        try:
            vals = [float(x) for x in tokens]
        except ValueError:
            continue

        current["values"].extend(vals)

    if current is not None:
        blocks.append(current)

    return blocks


up_blocks = parse_section(
    spin_up_start + 1,
    spin_down_start,
)

down_blocks = parse_section(
    spin_down_start + 1,
    len(band_lines),
)

print(f"UP   : {len(up_blocks)} k-points")
print(f"DOWN : {len(down_blocks)} k-points")

# ==========================================================================
# 7. CLOSEST BAND LEVELS
# ==========================================================================

print()
print("7. NIVEAUX BANDS LES PLUS PROCHES DE EF")
print("-" * 78)

for label, blocks in [
    ("SPIN UP", up_blocks),
    ("SPIN DOWN", down_blocks),
]:

    candidates = []

    for k_index, block in enumerate(blocks, start=1):

        for band_index, energy in enumerate(
            block["values"],
            start=1,
        ):

            candidates.append(
                (
                    abs(energy - EF),
                    k_index,
                    band_index,
                    energy,
                )
            )

    candidates.sort()

    print()
    print(label)

    for delta, k, band, energy in candidates[:5]:

        print(
            f"k={k:3d} "
            f"band={band:2d} "
            f"E={energy:10.6f} "
            f"Δ={energy-EF:+.6f} eV"
        )

# ==========================================================================
# 8. BANDS COVERING EF
# ==========================================================================

print()
print("8. BANDES COUVRANT EF")
print("-" * 78)

covering = {}

for label, blocks in [
    ("UP", up_blocks),
    ("DOWN", down_blocks),
]:

    bands = []

    for band in range(36):

        values = [
            block["values"][band]
            for block in blocks
        ]

        if min(values) <= EF <= max(values):
            bands.append(band + 1)

    covering[label] = bands

    print(f"{label:4s} : {bands}")

# ==========================================================================
# 9. FINAL CROSS-CHECK
# ==========================================================================

print()
print("=" * 78)
print("9. CROSS-CHECK FINAL")
print("=" * 78)

print(f"EF                       = {EF:.6f} eV")
print(f"E DOS le plus proche     = {ref_e:.6f} eV")
print(f"DOS UP                   = {ref_up:.6f}")
print(f"DOS DOWN                 = {ref_down:.6f}")
print(f"DOS TOTAL = UP + DOWN    = {ref_total:.6f}")
print(f"DOS intégrée             = {ref_integrated:.6f}")

print()

if ref_total > 0:
    print("[OK] DOS physique non nulle au voisinage de EF")
else:
    print("[WARN] DOS physique nulle au voisinage de EF")

if covering["UP"] and covering["DOWN"]:
    print(
        "[OK] Les deux canaux de spin présentent "
        "des bandes couvrant EF sur le chemin BANDS."
    )
else:
    print("[WARN] Un canal de spin ne couvre pas EF")

print()
print("[IMPORTANT]")
print(
    "[INFO] La colonne Int dos n'est PAS utilisée comme DOS totale."
)
print(
    "[INFO] La DOS totale est explicitement reconstruite "
    "par DOS UP + DOS DOWN."
)
print(
    "[INFO] Le chemin BANDS ne représente pas tout le BZ."
)
print(
    "[INFO] Aucun classement métal/isolant n'est effectué."
)
print(
    "[INFO] Stabilité numérique globale : NOT_ESTABLISHED."
)
print(
    "[INFO] AIDA inchangé."
)
print(
    "[INFO] Aucun calcul QE."
)
print(
    "[INFO] Aucun fichier modifié."
)

print()
print("=" * 78)
print("PHASE 78.42 TERMINÉE — READ-ONLY")
print("=" * 78)
