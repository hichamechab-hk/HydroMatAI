import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.38 — RELAXED BANDS / SPIN-RESOLVED EF AUDIT")
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

NSCF = (
    BASE
    / "calculations/top5_dft/TiFeH2/electronic_relaxed"
    / "TiFeH2_relaxed_nscf.out"
)

EF = 12.9573
EXPECTED_K = 141
EXPECTED_BANDS = 36

if not BANDS.exists():
    raise SystemExit(f"[ERROR] BANDS absent : {BANDS}")

text = BANDS.read_text(errors="replace")
lines = text.splitlines()

# ----------------------------------------------------------------------
# 1. Localisation des sections SPIN UP / SPIN DOWN
# ----------------------------------------------------------------------

spin_up_line = None
spin_down_line = None

for i, line in enumerate(lines):
    if "------ SPIN UP" in line:
        spin_up_line = i
    elif "------ SPIN DOWN" in line:
        spin_down_line = i

print("1. SECTIONS SPIN")
print("-" * 78)

print(f"SPIN UP   : ligne {spin_up_line + 1 if spin_up_line is not None else 'ABSENT'}")
print(f"SPIN DOWN : ligne {spin_down_line + 1 if spin_down_line is not None else 'ABSENT'}")

if spin_up_line is None or spin_down_line is None:
    raise SystemExit("[ERROR] Sections SPIN UP / SPIN DOWN introuvables")

if spin_down_line <= spin_up_line:
    raise SystemExit("[ERROR] Ordre des sections incohérent")

print("[OK] Deux sections spin explicites détectées")

# ----------------------------------------------------------------------
# 2. Parser une section
# ----------------------------------------------------------------------

header_re = re.compile(
    r"^\s*k\s*=\s*"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)"
    r".*bands\s*\(ev\)"
    r"\s*:\s*$",
    re.IGNORECASE,
)


def parse_section(section_lines):

    blocks = []
    current = None

    for lineno, line in section_lines:

        m = header_re.match(line)

        if m:
            if current is not None:
                blocks.append(current)

            current = {
                "line": lineno,
                "k": tuple(float(x) for x in m.groups()),
                "values": [],
            }
            continue

        if current is None:
            continue

        stripped = line.strip()

        if not stripped:
            continue

        # Ne pas traverser une nouvelle section
        if "------ SPIN" in line:
            break

        tokens = stripped.split()

        try:
            vals = [float(x) for x in tokens]
        except ValueError:
            continue

        if vals:
            current["values"].extend(vals)

    if current is not None:
        blocks.append(current)

    return blocks


up_lines = [
    (i + 1, lines[i])
    for i in range(spin_up_line + 1, spin_down_line)
]

down_lines = [
    (i + 1, lines[i])
    for i in range(spin_down_line + 1, len(lines))
]

up = parse_section(up_lines)
down = parse_section(down_lines)

# ----------------------------------------------------------------------
# 3. Validation structure
# ----------------------------------------------------------------------

print()
print("2. STRUCTURE PAR SPIN")
print("-" * 78)

for name, blocks in [("SPIN UP", up), ("SPIN DOWN", down)]:

    counts = [len(b["values"]) for b in blocks]

    print()
    print(name)
    print(f"  k-points : {len(blocks)} / {EXPECTED_K}")
    print(f"  bandes   : {sorted(set(counts))}")

    if (
        len(blocks) == EXPECTED_K
        and all(c == EXPECTED_BANDS for c in counts)
    ):
        print("  [OK] 141 × 36")
    else:
        print("  [WARN] structure inattendue")

# ----------------------------------------------------------------------
# 4. Contrôle coordonnées
# ----------------------------------------------------------------------

print()
print("3. COORDONNÉES")
print("-" * 78)

if len(up) == EXPECTED_K and len(down) == EXPECTED_K:

    max_delta = 0.0
    same = 0

    for a, b in zip(up, down):

        delta = max(
            abs(a["k"][j] - b["k"][j])
            for j in range(3)
        )

        max_delta = max(max_delta, delta)

        if delta < 1e-10:
            same += 1

    print(f"Coordonnées identiques UP/DOWN : {same}/{EXPECTED_K}")
    print(f"Écart maximal                  : {max_delta:.3e}")

    if same == EXPECTED_K:
        print("[OK] Même chemin k pour les deux spins")
    else:
        print("[WARN] Chemins k différents")

# ----------------------------------------------------------------------
# 5. Analyse quantitative d'un spin
# ----------------------------------------------------------------------

def analyze_spin(name, blocks):

    print()
    print("=" * 78)
    print(name)
    print("=" * 78)

    all_values = [
        v
        for block in blocks
        for v in block["values"]
    ]

    finite = all(math.isfinite(v) for v in all_values)

    print()
    print("A. CONTRÔLE")
    print("-" * 78)
    print(f"Valeurs totales : {len(all_values)}")
    print(f"Valeurs finies  : {'YES' if finite else 'NO'}")

    # --------------------------------------------------------------
    # Global closest levels
    # --------------------------------------------------------------

    near = []

    for k_idx, block in enumerate(blocks, start=1):

        for band_idx, energy in enumerate(
            block["values"],
            start=1
        ):

            near.append({
                "k": k_idx,
                "band": band_idx,
                "energy": energy,
                "delta": energy - EF,
                "kcoord": block["k"],
            })

    near.sort(key=lambda x: abs(x["delta"]))

    print()
    print("B. NIVEAUX LES PLUS PROCHES DE EF")
    print("-" * 78)

    for x in near[:10]:

        print(
            f"k={x['k']:3d} "
            f"band={x['band']:2d} "
            f"E={x['energy']:10.6f} eV "
            f"Δ={x['delta']:+10.6f} eV "
            f"k=("
            f"{x['kcoord'][0]:.6f},"
            f"{x['kcoord'][1]:.6f},"
            f"{x['kcoord'][2]:.6f})"
        )

    # --------------------------------------------------------------
    # Per-band min/max and EF coverage
    # --------------------------------------------------------------

    print()
    print("C. ANALYSE DES 36 BANDES")
    print("-" * 78)

    crossing_bands = []

    for band_idx in range(EXPECTED_BANDS):

        vals = [
            block["values"][band_idx]
            for block in blocks
        ]

        min_e = min(vals)
        max_e = max(vals)

        closest = min(
            vals,
            key=lambda x: abs(x - EF)
        )

        crosses = min_e <= EF <= max_e

        if crosses:
            crossing_bands.append(band_idx + 1)

        print(
            f"band={band_idx+1:2d} "
            f"min={min_e:10.5f} "
            f"max={max_e:10.5f} "
            f"closest={closest:10.5f} "
            f"Δ={closest-EF:+9.5f} "
            f"covers_EF={'YES' if crosses else 'NO'}"
        )

    print()
    print("D. BANDES COUVRANT EF")
    print("-" * 78)

    if crossing_bands:
        print(
            "[INFO] Bandes couvrant EF :",
            ", ".join(str(x) for x in crossing_bands)
        )
    else:
        print("[INFO] Aucune bande ne couvre EF sur ce chemin")

    # --------------------------------------------------------------
    # Crossings entre k successifs
    # --------------------------------------------------------------

    print()
    print("E. FRANCHISSEMENTS ENTRE K-POINTS")
    print("-" * 78)

    crossings = []

    for band_idx in range(EXPECTED_BANDS):

        vals = [
            block["values"][band_idx]
            for block in blocks
        ]

        for i in range(len(vals) - 1):

            e1 = vals[i]
            e2 = vals[i + 1]

            if (
                (e1 < EF and e2 > EF)
                or
                (e1 > EF and e2 < EF)
                or
                e1 == EF
                or
                e2 == EF
            ):

                crossings.append(
                    (
                        band_idx + 1,
                        i + 1,
                        e1,
                        e2,
                    )
                )

    print(f"Franchissements détectés : {len(crossings)}")

    for band, k, e1, e2 in crossings[:20]:

        print(
            f"band={band:2d} "
            f"k={k:3d}->{k+1:3d} "
            f"E1={e1:10.6f} "
            f"E2={e2:10.6f}"
        )

    return {
        "near": near,
        "crossing_bands": crossing_bands,
        "crossings": crossings,
    }


# ----------------------------------------------------------------------
# 6. Analyse UP / DOWN
# ----------------------------------------------------------------------

up_result = analyze_spin("SPIN UP", up)
down_result = analyze_spin("SPIN DOWN", down)

# ----------------------------------------------------------------------
# 7. Comparaison UP / DOWN
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("4. COMPARAISON SPIN UP / SPIN DOWN")
print("=" * 78)

if (
    len(up) == EXPECTED_K
    and len(down) == EXPECTED_K
):

    print(
        "Bandes couvrant EF — UP   :",
        up_result["crossing_bands"] or "aucune"
    )

    print(
        "Bandes couvrant EF — DOWN :",
        down_result["crossing_bands"] or "aucune"
    )

    print(
        "Franchissements EF — UP   :",
        len(up_result["crossings"])
    )

    print(
        "Franchissements EF — DOWN :",
        len(down_result["crossings"])
    )

# ----------------------------------------------------------------------
# 8. EF NSCF
# ----------------------------------------------------------------------

print()
print("5. REFERENCE EF")
print("-" * 78)

if NSCF.exists():

    nscf_text = NSCF.read_text(errors="replace")

    fermi_values = []

    for line in nscf_text.splitlines():

        if "the Fermi energy is" in line:

            m = re.search(
                r"the Fermi energy is\s+"
                r"([-+0-9.eE]+)\s+ev",
                line,
                re.IGNORECASE,
            )

            if m:
                fermi_values.append(float(m.group(1)))

    if fermi_values:

        print(
            f"EF NSCF trouvé : "
            f"{fermi_values[-1]:.6f} eV"
        )

        print(
            f"EF utilisé     : "
            f"{EF:.6f} eV"
        )

        print(
            f"Écart          : "
            f"{fermi_values[-1] - EF:+.6f} eV"
        )

    else:
        print("[WARN] EF non trouvé automatiquement")

# ----------------------------------------------------------------------
# 9. Synthèse
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("6. SYNTHÈSE")
print("=" * 78)

if (
    len(up) == EXPECTED_K
    and len(down) == EXPECTED_K
    and all(len(x["values"]) == EXPECTED_BANDS for x in up)
    and all(len(x["values"]) == EXPECTED_BANDS for x in down)
):
    print("[OK] Structure exacte :")
    print("     SPIN UP   = 141 × 36")
    print("     SPIN DOWN = 141 × 36")
else:
    print("[WARN] Structure spin incomplète")

print()
print("[INFO] EF utilisé :", EF, "eV")
print("[INFO] EF provenant du NSCF relaxed.")
print()
print("[IMPORTANT]")
print("[INFO] L'analyse est limitée au chemin BANDS.")
print("[INFO] Elle ne constitue pas à elle seule une classification")
print("       globale métal/isolant/semi-conducteur.")
print("[INFO] Le DOS relaxed doit rester interprété séparément.")
print()
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.38 TERMINÉE — READ-ONLY")
print("=" * 78)
