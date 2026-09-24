import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.36 — RELAXED BANDS / EXACT PARSER")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")
BANDS = BASE / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_bands.out"
NSCF = BASE / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_nscf.out"

EF = 12.9573
EXPECTED_K = 141
EXPECTED_BANDS = 36

if not BANDS.exists():
    raise SystemExit(f"[ERROR] Fichier absent : {BANDS}")

text = BANDS.read_text(errors="replace")
lines = text.splitlines()

# ----------------------------------------------------------------------
# 1. Détection EXCLUSIVE des vrais blocs :
#    "k = ... bands (ev):"
# ----------------------------------------------------------------------

k_header = re.compile(
    r"^\s*k\s*=\s*"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)"
    r".*bands\s*\(ev\)"
    r"\s*:\s*$",
    re.IGNORECASE,
)

blocks = []
current = None

for i, line in enumerate(lines, start=1):

    m = k_header.match(line)

    if m:
        if current is not None:
            blocks.append(current)

        current = {
            "line": i,
            "k": tuple(float(x) for x in m.groups()),
            "values": [],
        }
        continue

    if current is None:
        continue

    # Fin du bloc si on atteint une nouvelle structure importante
    if "End of band structure calculation" in line:
        break

    # Extraire uniquement les nombres de lignes numériques
    stripped = line.strip()

    if not stripped:
        continue

    # Les lignes de bandes contiennent uniquement des flottants
    tokens = stripped.split()

    try:
        vals = [float(x) for x in tokens]
    except ValueError:
        continue

    if vals:
        current["values"].extend(vals)

if current is not None:
    blocks.append(current)

print("1. PARSING EXACT")
print("-" * 78)
print(f"Blocs 'k = ... bands (ev)' détectés : {len(blocks)}")
print(f"k-points attendus                  : {EXPECTED_K}")

if len(blocks) == EXPECTED_K:
    print("[OK] Nombre exact de k-points")
else:
    print("[WARN] Nombre de k-points inattendu")

counts = [len(b["values"]) for b in blocks]

print(f"Nombre de bandes par bloc           : {sorted(set(counts))}")

bad_counts = [
    (idx + 1, c)
    for idx, c in enumerate(counts)
    if c != EXPECTED_BANDS
]

if not bad_counts:
    print(f"[OK] {EXPECTED_BANDS} bandes pour chaque k-point")
else:
    print(f"[WARN] Blocs avec nombre de bandes incorrect : {len(bad_counts)}")
    for x in bad_counts[:10]:
        print(f"  k={x[0]} : {x[1]} valeurs")

total = sum(counts)

print(f"Valeurs totales extraites              : {total}")
print(f"Valeurs attendues                      : {EXPECTED_K * EXPECTED_BANDS}")

if total == EXPECTED_K * EXPECTED_BANDS:
    print("[OK] Structure numérique exacte 141 × 36")
else:
    print("[WARN] Structure numérique différente")

# ----------------------------------------------------------------------
# 2. Contrôle valeurs
# ----------------------------------------------------------------------

print()
print("2. CONTRÔLE NUMÉRIQUE")
print("-" * 78)

all_values = [
    v
    for block in blocks
    for v in block["values"]
]

finite = all(math.isfinite(v) for v in all_values)

print(f"Toutes les valeurs sont finies : {'YES' if finite else 'NO'}")

# ----------------------------------------------------------------------
# 3. Analyse bande par bande
# ----------------------------------------------------------------------

if len(blocks) != EXPECTED_K or any(c != EXPECTED_BANDS for c in counts):
    print()
    print("[STOP] Structure insuffisante pour l'analyse bande par bande.")
    print("[INFO] Corriger uniquement le parsing avant toute interprétation.")
    raise SystemExit(0)

print()
print("3. ANALYSE BANDE PAR BANDE AUTOUR DE EF")
print("-" * 78)
print(f"EF NSCF relaxed : {EF:.4f} eV")

band_stats = []

for band_idx in range(EXPECTED_BANDS):

    vals = [blocks[k]["values"][band_idx] for k in range(EXPECTED_K)]

    below = [v for v in vals if v <= EF]
    above = [v for v in vals if v >= EF]

    min_e = min(vals)
    max_e = max(vals)

    closest = min(vals, key=lambda x: abs(x - EF))

    crosses = min_e <= EF <= max_e

    band_stats.append({
        "band": band_idx + 1,
        "min": min_e,
        "max": max_e,
        "closest": closest,
        "delta": closest - EF,
        "crosses": crosses,
    })

    print(
        f"band={band_idx+1:2d} "
        f"min={min_e:10.4f} "
        f"max={max_e:10.4f} "
        f"closest={closest:10.4f} "
        f"delta={closest-EF:+10.4f} "
        f"crosses_EF={'YES' if crosses else 'NO'}"
    )

# ----------------------------------------------------------------------
# 4. Bandes traversant EF
# ----------------------------------------------------------------------

crossing_bands = [
    x for x in band_stats
    if x["crosses"]
]

print()
print("4. BANDES DONT LA PLAGE COUVRE EF")
print("-" * 78)

if crossing_bands:
    print(f"Nombre de bandes concernées : {len(crossing_bands)}")

    for x in crossing_bands:
        print(
            f"band={x['band']:2d} "
            f"min={x['min']:10.4f} eV "
            f"max={x['max']:10.4f} eV"
        )
else:
    print("[INFO] Aucune bande ne couvre EF sur le chemin BANDS.")

# ----------------------------------------------------------------------
# 5. Points les plus proches de EF
# ----------------------------------------------------------------------

print()
print("5. NIVEAUX LES PLUS PROCHES DE EF")
print("-" * 78)

near = []

for k_idx, block in enumerate(blocks, start=1):
    for band_idx, energy in enumerate(block["values"], start=1):
        near.append({
            "k": k_idx,
            "band": band_idx,
            "energy": energy,
            "delta": energy - EF,
            "kcoord": block["k"],
        })

near.sort(key=lambda x: abs(x["delta"]))

print("10 niveaux les plus proches :")

for x in near[:10]:
    print(
        f"k={x['k']:3d} "
        f"band={x['band']:2d} "
        f"E={x['energy']:10.6f} eV "
        f"Δ={x['delta']:+10.6f} eV "
        f"k=({x['kcoord'][0]:.6f},"
        f"{x['kcoord'][1]:.6f},"
        f"{x['kcoord'][2]:.6f})"
    )

# ----------------------------------------------------------------------
# 6. Vérification du NSCF EF
# ----------------------------------------------------------------------

print()
print("6. REFERENCE EF")
print("-" * 78)

if NSCF.exists():
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
        print(f"EF trouvé dans NSCF : {fermi_values[-1]:.6f} eV")
        print(f"EF utilisé            : {EF:.6f} eV")
        print(
            f"Écart                 : "
            f"{fermi_values[-1] - EF:+.6f} eV"
        )
    else:
        print("[WARN] EF non retrouvé automatiquement dans NSCF")
else:
    print("[WARN] NSCF absent")

# ----------------------------------------------------------------------
# 7. Synthèse
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

if len(blocks) == EXPECTED_K and total == EXPECTED_K * EXPECTED_BANDS:
    print("[OK] BANDS = 141 k-points × 36 bandes")
else:
    print("[WARN] Structure BANDS non conforme")

print("[OK] Parsing limité aux vrais blocs 'k = ... bands (ev)'")
print("[OK] Toutes les énergies sont finies")

if crossing_bands:
    print(
        f"[INFO] {len(crossing_bands)} bande(s) couvre(nt) "
        f"EF sur le chemin BANDS."
    )
else:
    print("[INFO] Aucune bande ne couvre EF sur ce chemin.")

print()
print("[IMPORTANT]")
print("[INFO] Le chemin BANDS n'est pas une grille complète de la zone")
print("       de Brillouin.")
print("[INFO] Une bande couvrant EF sur ce chemin est une observation")
print("       numérique sur ce chemin, pas à elle seule une classification")
print("       globale métal/isolant.")
print("[INFO] Le DOS relaxed constitue une information complémentaire.")
print()
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.36 TERMINÉE — READ-ONLY")
print("=" * 78)
