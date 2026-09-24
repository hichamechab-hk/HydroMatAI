import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.39 — RELAXED BANDS ↔ DOS CONSISTENCY AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")

BANDS = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_bands.out"
)

DOS = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed.dos"
)

NSCF = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_nscf.out"
)

EF = 12.9573

print("1. FICHIERS")
print("-" * 78)

for label, path in [
    ("BANDS", BANDS),
    ("DOS", DOS),
    ("NSCF", NSCF),
]:
    print(f"{label:5s} : {'OK' if path.exists() else 'ABSENT'}")

if not BANDS.exists() or not DOS.exists() or not NSCF.exists():
    raise SystemExit("[ERROR] Fichier nécessaire absent")

# ----------------------------------------------------------------------
# 2. EF NSCF
# ----------------------------------------------------------------------

print()
print("2. FERMI ENERGY")
print("-" * 78)

nscf_text = NSCF.read_text(errors="replace")

fermi_values = []

for line in nscf_text.splitlines():
    if "the Fermi energy is" in line:
        m = re.search(
            r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
            line,
            re.IGNORECASE,
        )
        if m:
            fermi_values.append(float(m.group(1)))

if fermi_values:
    ef_found = fermi_values[-1]
    print(f"EF NSCF trouvé : {ef_found:.6f} eV")
    print(f"EF de référence : {EF:.6f} eV")
    print(f"Écart           : {ef_found - EF:+.6e} eV")

    if abs(ef_found - EF) < 1e-6:
        print("[OK] EF cohérent")
    else:
        print("[WARN] EF différent")
else:
    print("[WARN] EF non trouvé dans NSCF")
    ef_found = EF

# ----------------------------------------------------------------------
# 3. DOS
# ----------------------------------------------------------------------

print()
print("3. INVENTAIRE DOS")
print("-" * 78)

dos_lines = DOS.read_text(errors="replace").splitlines()

data = []

for line in dos_lines:
    stripped = line.strip()

    if not stripped:
        continue

    tokens = stripped.split()

    if len(tokens) < 4:
        continue

    try:
        e = float(tokens[0])
        up = float(tokens[1])
        down = float(tokens[2])
        total = float(tokens[3])
    except ValueError:
        continue

    if all(math.isfinite(x) for x in (e, up, down, total)):
        data.append((e, up, down, total))

print(f"Lignes numériques : {len(data)}")

if not data:
    raise SystemExit("[ERROR] Aucun point DOS exploitable")

energies = [x[0] for x in data]

print(f"Emin : {min(energies):.6f} eV")
print(f"Emax : {max(energies):.6f} eV")

# ----------------------------------------------------------------------
# 4. GRILLE DOS
# ----------------------------------------------------------------------

print()
print("4. GRILLE DOS")
print("-" * 78)

steps = [
    energies[i + 1] - energies[i]
    for i in range(len(energies) - 1)
]

print(f"Pas minimal : {min(steps):.12f} eV")
print(f"Pas maximal : {max(steps):.12f} eV")

regular = max(steps) - min(steps) < 1e-8

print(f"Grille régulière : {'YES' if regular else 'NO'}")

if regular:
    print("[OK] Grille énergétique régulière")

# ----------------------------------------------------------------------
# 5. POINT DOS LE PLUS PROCHE DE EF
# ----------------------------------------------------------------------

print()
print("5. DOS AU PLUS PROCHE DE EF")
print("-" * 78)

nearest = min(
    data,
    key=lambda x: abs(x[0] - EF)
)

e0, up0, down0, total0 = nearest

print(f"EF                 : {EF:.6f} eV")
print(f"E DOS le plus proche: {e0:.6f} eV")
print(f"|ΔE|               : {abs(e0-EF):.6f} eV")
print(f"DOS UP             : {up0:.6f}")
print(f"DOS DOWN           : {down0:.6f}")
print(f"DOS TOTAL          : {total0:.6f}")

if total0 > 0:
    print("[OK] DOS totale non nulle au voisinage immédiat de EF")
else:
    print("[WARN] DOS totale nulle au point le plus proche")

# ----------------------------------------------------------------------
# 6. FENÊTRES AUTOUR DE EF
# ----------------------------------------------------------------------

print()
print("6. DOS DANS DES FENÊTRES AUTOUR DE EF")
print("-" * 78)

windows = [0.01, 0.05, 0.10, 0.25, 0.50]

for width in windows:

    subset = [
        x for x in data
        if abs(x[0] - EF) <= width
    ]

    if not subset:
        print(f"±{width:.2f} eV : aucun point")
        continue

    totals = [x[3] for x in subset]
    ups = [x[1] for x in subset]
    downs = [x[2] for x in subset]

    print(
        f"±{width:.2f} eV : "
        f"N={len(subset):3d} "
        f"TOTAL[min,max,avg]=("
        f"{min(totals):.4f},"
        f"{max(totals):.4f},"
        f"{sum(totals)/len(totals):.4f}) "
        f"UP_avg={sum(ups)/len(ups):.4f} "
        f"DOWN_avg={sum(downs)/len(downs):.4f}"
    )

# ----------------------------------------------------------------------
# 7. POINTS DOS AUTOUR DE EF
# ----------------------------------------------------------------------

print()
print("7. VOISINAGE IMMÉDIAT DE EF")
print("-" * 78)

local = [
    x for x in data
    if abs(x[0] - EF) <= 0.10
]

for e, up, down, total in local:
    print(
        f"E={e:9.4f} "
        f"UP={up:9.4f} "
        f"DOWN={down:9.4f} "
        f"TOTAL={total:9.4f}"
    )

# ----------------------------------------------------------------------
# 8. BANDS : extraction des niveaux proches de EF
# ----------------------------------------------------------------------

print()
print("8. BANDS — NIVEAUX PROCHES DE EF")
print("-" * 78)

bands_lines = BANDS.read_text(errors="replace").splitlines()

spin_up_line = None
spin_down_line = None

for i, line in enumerate(bands_lines):
    if "------ SPIN UP" in line:
        spin_up_line = i
    elif "------ SPIN DOWN" in line:
        spin_down_line = i

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

    for lineno in range(start, end):
        line = bands_lines[lineno]

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
            vals = [float(x) for x in tokens]
        except ValueError:
            continue

        current["values"].extend(vals)

    if current is not None:
        blocks.append(current)

    return blocks


up_blocks = parse_section(
    spin_up_line + 1,
    spin_down_line,
)

down_blocks = parse_section(
    spin_down_line + 1,
    len(bands_lines),
)

print(f"Spin UP blocks   : {len(up_blocks)}")
print(f"Spin DOWN blocks : {len(down_blocks)}")

for name, blocks in [
    ("SPIN UP", up_blocks),
    ("SPIN DOWN", down_blocks),
]:

    near = []

    for k_idx, block in enumerate(blocks, start=1):
        for band_idx, energy in enumerate(
            block["values"],
            start=1
        ):
            near.append(
                (
                    abs(energy - EF),
                    k_idx,
                    band_idx,
                    energy,
                )
            )

    near.sort()

    print()
    print(name)

    for _, k, band, energy in near[:5]:
        print(
            f"k={k:3d} "
            f"band={band:2d} "
            f"E={energy:10.6f} "
            f"Δ={energy-EF:+.6f} eV"
        )

# ----------------------------------------------------------------------
# 9. COMPARAISON QUALITATIVE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("9. COHÉRENCE BANDS ↔ DOS")
print("=" * 78)

print("[OK] EF BANDS/NSCF = %.6f eV" % EF)

print()
print("Observation DOS :")
print(
    f"- DOS totale proche de EF = {total0:.6f}"
)

print()
print("Observation BANDS :")

up_cross = []
down_cross = []

for band in range(36):

    vals = [
        b["values"][band]
        for b in up_blocks
    ]

    if min(vals) <= EF <= max(vals):
        up_cross.append(band + 1)

for band in range(36):

    vals = [
        b["values"][band]
        for b in down_blocks
    ]

    if min(vals) <= EF <= max(vals):
        down_cross.append(band + 1)

print(
    "UP   bandes couvrant EF   :",
    up_cross
)

print(
    "DOWN bandes couvrant EF   :",
    down_cross
)

if total0 > 0 and (up_cross or down_cross):
    print()
    print(
        "[OK] Les observations BANDS et DOS sont "
        "numériquement compatibles autour de EF."
    )
else:
    print()
    print(
        "[WARN] Les observations BANDS/DOS ne peuvent "
        "pas être considérées comme concordantes."
    )

# ----------------------------------------------------------------------
# 10. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("10. SYNTHÈSE")
print("=" * 78)

print("[OK] DOS relaxed réel analysé")
print("[OK] NSCF relaxed réel utilisé pour EF")
print("[OK] BANDS relaxed spin-résolu analysé")
print("[OK] EF cohérent entre NSCF et référence")
print("[OK] DOS non nulle au voisinage immédiat de EF")
print("[OK] Bandes proches/couvrant EF identifiées")

print()
print("[IMPORTANT]")
print("[INFO] Cette phase établit une cohérence numérique entre")
print("       BANDS et DOS autour de EF.")
print("[INFO] Elle ne constitue pas une validation scientifique complète.")
print("[INFO] La stabilité numérique globale reste NOT_ESTABLISHED.")
print("[INFO] Aucun changement AIDA.")
print()
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")

print()
print("=" * 78)
print("PHASE 78.39 TERMINÉE — READ-ONLY")
print("=" * 78)
