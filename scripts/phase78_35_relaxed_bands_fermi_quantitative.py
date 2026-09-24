import os
os.system("clear")

from pathlib import Path
import re
import math

ROOT = Path("/home/hk/HydroMatAI")

BANDS = (
    ROOT
    / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
      "TiFeH2_relaxed_bands.out"
)

EF = 12.9573
EXPECTED_KPOINTS = 141
EXPECTED_BANDS = 36


print("=" * 78)
print("PHASE 78.35 — RELAXED BANDS / FERMI QUANTITATIVE AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


if not BANDS.exists():
    print("[ERROR] Fichier absent :", BANDS)
    raise SystemExit(1)

text = BANDS.read_text(errors="replace")
lines = text.splitlines()


# ----------------------------------------------------------------------
# 1. LOCATE BAND BLOCKS
# ----------------------------------------------------------------------

blocks = []

i = 0

while i < len(lines):

    line = lines[i]

    match = re.search(
        r"^\s*k\s*=\s*"
        r"([-+0-9.EeDd]+)\s+"
        r"([-+0-9.EeDd]+)\s+"
        r"([-+0-9.EeDd]+)"
        r".*bands\s*\(ev\)",
        line,
        re.I,
    )

    if not match:
        i += 1
        continue

    kx = float(match.group(1).replace("D", "E"))
    ky = float(match.group(2).replace("D", "E"))
    kz = float(match.group(3).replace("D", "E"))

    values = []

    j = i + 1

    while j < len(lines):

        current = lines[j].strip()

        if re.search(r"^\s*k\s*=", current, re.I):
            break

        if re.search(r"End of band structure calculation", current, re.I):
            break

        if current:

            parts = current.split()

            try:
                nums = [
                    float(x.replace("D", "E"))
                    for x in parts
                ]
            except ValueError:
                nums = []

            if nums:
                values.extend(nums)

        j += 1

    if values:
        blocks.append({
            "k": (kx, ky, kz),
            "values": values,
        })

    i = j


# ----------------------------------------------------------------------
# 2. STRUCTURAL VALIDATION
# ----------------------------------------------------------------------

print("1. STRUCTURE EXTRAITE")
print("-" * 78)

print("Blocs k-point détectés :", len(blocks))
print("k-points attendus      :", EXPECTED_KPOINTS)

if len(blocks) == EXPECTED_KPOINTS:
    print("[OK] Nombre de k-points cohérent")
else:
    print("[WARN] Nombre de k-points différent de l'attendu")


band_counts = [len(b["values"]) for b in blocks]

if band_counts:
    unique_counts = sorted(set(band_counts))

    print("Nombre de bandes par bloc :", unique_counts)

    if unique_counts == [EXPECTED_BANDS]:
        print("[OK] 36 bandes extraites pour chaque k-point")
    else:
        print("[WARN] Nombre de bandes variable ou inattendu")

total_values = sum(band_counts)

print("Valeurs totales extraites :", total_values)
print(
    "Valeurs attendues         :",
    EXPECTED_KPOINTS * EXPECTED_BANDS,
)

if total_values == EXPECTED_KPOINTS * EXPECTED_BANDS:
    print("[OK] Nombre total de valeurs cohérent")
else:
    print("[WARN] Nombre total de valeurs différent")


# ----------------------------------------------------------------------
# 3. VALIDATE NUMERICAL CONTENT
# ----------------------------------------------------------------------

print()
print("2. CONTRÔLE NUMÉRIQUE")
print("-" * 78)

finite = all(
    math.isfinite(v)
    for b in blocks
    for v in b["values"]
)

print("Toutes les valeurs sont finies :", "YES" if finite else "NO")


# ----------------------------------------------------------------------
# 4. ALL VALUES RELATIVE TO EF
# ----------------------------------------------------------------------

below = []
above = []

for ik, block in enumerate(blocks, start=1):

    for ib, energy in enumerate(block["values"], start=1):

        delta = energy - EF

        record = {
            "k_index": ik,
            "band": ib,
            "k": block["k"],
            "energy": energy,
            "delta": delta,
        }

        if energy <= EF:
            below.append(record)

        if energy >= EF:
            above.append(record)


print()
print("3. RÉPARTITION PAR RAPPORT À EF")
print("-" * 78)

print("EF NSCF :", EF, "eV")
print("Valeurs <= EF :", len(below))
print("Valeurs >= EF :", len(above))


# ----------------------------------------------------------------------
# 5. CLOSEST BELOW / ABOVE
# ----------------------------------------------------------------------

print()
print("4. BANDES LES PLUS PROCHES DE EF")
print("-" * 78)

closest_below = sorted(
    below,
    key=lambda x: abs(x["delta"])
)

closest_above = sorted(
    above,
    key=lambda x: abs(x["delta"])
)

print()
print("PLUS PROCHE SOUS EF")

for r in closest_below[:10]:

    print(
        f"k={r['k_index']:3d} "
        f"band={r['band']:2d} "
        f"E={r['energy']:12.6f} eV "
        f"Δ={r['delta']:+12.6f} eV "
        f"k=({r['k'][0]:.6f}, "
        f"{r['k'][1]:.6f}, "
        f"{r['k'][2]:.6f})"
    )


print()
print("PLUS PROCHE AU-DESSUS DE EF")

for r in closest_above[:10]:

    print(
        f"k={r['k_index']:3d} "
        f"band={r['band']:2d} "
        f"E={r['energy']:12.6f} eV "
        f"Δ={r['delta']:+12.6f} eV "
        f"k=({r['k'][0]:.6f}, "
        f"{r['k'][1]:.6f}, "
        f"{r['k'][2]:.6f})"
    )


# ----------------------------------------------------------------------
# 6. GLOBAL BAND SEPARATION AROUND EF
# ----------------------------------------------------------------------

print()
print("5. SÉPARATION NUMÉRIQUE AUTOUR DE EF")
print("-" * 78)

if closest_below and closest_above:

    ev = closest_below[0]
    ec = closest_above[0]

    separation = ec["energy"] - ev["energy"]

    print("Dernière énergie <= EF :", ev["energy"], "eV")
    print("Première énergie >= EF :", ec["energy"], "eV")
    print("Séparation numérique    :", separation, "eV")

    print()
    print(
        "Sous EF :",
        ev["energy"],
        "à k-index",
        ev["k_index"],
        "band",
        ev["band"],
    )

    print(
        "Au-dessus EF :",
        ec["energy"],
        "à k-index",
        ec["k_index"],
        "band",
        ec["band"],
    )

else:
    print("[WARN] Données insuffisantes")


# ----------------------------------------------------------------------
# 7. SEARCH FOR BANDS STRADDLING EF
# ----------------------------------------------------------------------

print()
print("6. RECHERCHE DE FRANCHISSEMENT LOCAL DE EF")
print("-" * 78)

crossings = []

for ik, block in enumerate(blocks, start=1):

    vals = sorted(block["values"])

    for a, b in zip(vals, vals[1:]):

        if a <= EF <= b and a != b:

            crossings.append({
                "k_index": ik,
                "a": a,
                "b": b,
                "width": b - a,
                "k": block["k"],
            })

            break

print("k-points présentant des niveaux encadrant EF :", len(crossings))

for r in crossings[:20]:

    print(
        f"k={r['k_index']:3d} "
        f"{r['a']:12.6f} <= EF <= {r['b']:12.6f} "
        f"Δ={r['width']:.6f} eV"
    )

if len(crossings) > 20:
    print("...")


# ----------------------------------------------------------------------
# 8. SUMMARY
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

if (
    len(blocks) == EXPECTED_KPOINTS
    and all(x == EXPECTED_BANDS for x in band_counts)
):
    print("[OK] 141 k-points × 36 bandes correctement extraits.")
else:
    print("[WARN] Structure différente de 141 × 36.")

if finite:
    print("[OK] Toutes les énergies sont numériques et finies.")
else:
    print("[WARN] Valeurs non finies détectées.")

print()
print("[INFO] EF utilisé :", EF, "eV")
print("[INFO] EF provient du NSCF relaxed.")
print("[INFO] Cette phase mesure la position des bandes par rapport à EF.")
print("[INFO] Elle ne transforme pas automatiquement le résultat en")
print("       classification métal/isolant/semi-conducteur.")
print()
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.35 TERMINÉE — READ-ONLY")
print("=" * 78)
