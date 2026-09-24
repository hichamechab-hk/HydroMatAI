import os
os.system("clear")

from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")

BANDS = (
    ROOT
    / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
      "TiFeH2_relaxed_bands.out"
)

print("=" * 78)
print("PHASE 78.34 — RELAXED BANDS NUMERICAL AUDIT")
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
# 1. JOB STATUS
# ----------------------------------------------------------------------

print("1. ÉTAT DU CALCUL")
print("-" * 78)

job_done = bool(re.search(r"\bJOB DONE\b", text, re.I))

errors = re.findall(
    r"(?:Error in routine|ERROR:|fatal error|stopping|cannot open)",
    text,
    re.I,
)

c_bands = len(
    re.findall(r"c_bands:", text, re.I)
)

print("JOB DONE      :", "YES" if job_done else "NO")
print("Error markers :", len(errors))
print("c_bands       :", c_bands)


# ----------------------------------------------------------------------
# 2. DIMENSIONS
# ----------------------------------------------------------------------

print()
print("2. DIMENSIONS")
print("-" * 78)

for pattern, label in [
    (r"number of k points\s*=\s*(\d+)", "k-points"),
    (r"number of Kohn-Sham states\s*=\s*(\d+)", "KS states"),
    (r"number of bands\s*=\s*(\d+)", "bands"),
]:

    matches = re.findall(pattern, text, re.I)

    if matches:
        print(label, ":", matches[-1])
    else:
        print(label, ": non trouvé")


# ----------------------------------------------------------------------
# 3. FERMI
# ----------------------------------------------------------------------

print()
print("3. NIVEAU DE FERMI")
print("-" * 78)

fermi_patterns = [
    r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
    r"Fermi energy\s*[:=]\s*([-+0-9.EeDd]+)",
]

fermi_values = []

for pattern in fermi_patterns:
    fermi_values.extend(re.findall(pattern, text, re.I))

if fermi_values:
    print("Valeur(s) détectée(s) :")
    for value in fermi_values[-5:]:
        print(" ", value, "eV")
else:
    print("Fermi non trouvé dans le fichier BANDS.")


# ----------------------------------------------------------------------
# 4. BLOCS DE BANDES
# ----------------------------------------------------------------------

print()
print("4. STRUCTURE DES BLOCS DE BANDES")
print("-" * 78)

markers = []

for i, line in enumerate(lines, 1):

    if re.search(r"End of band structure calculation", line, re.I):
        markers.append((i, "END_BANDS"))

    if re.search(r"Writing eigenvalues", line, re.I):
        markers.append((i, "EIGENVALUES"))

    if re.search(r"bands", line, re.I) and "number" in line.lower():
        markers.append((i, "BANDS_HEADER"))

for item in markers:
    print(f"{item[0]:6d} : {item[1]}")


# ----------------------------------------------------------------------
# 5. K-POINT BLOCKS
# ----------------------------------------------------------------------

print()
print("5. K-POINTS")
print("-" * 78)

kpt_lines = []

for i, line in enumerate(lines, 1):

    if re.search(r"k\s*=\s*", line, re.I):
        kpt_lines.append((i, line.strip()))

print("Nombre de lignes k= détectées :", len(kpt_lines))

for i, line in kpt_lines[:5]:
    print(f"{i:6d}: {line}")

if len(kpt_lines) > 5:
    print("...")
    for i, line in kpt_lines[-5:]:
        print(f"{i:6d}: {line}")


# ----------------------------------------------------------------------
# 6. EXTRACTION DES VALEURS D'ÉNERGIE
# ----------------------------------------------------------------------

print()
print("6. ÉNERGIES DES BANDES — INVENTAIRE")
print("-" * 78)

energy_lines = []

for i, line in enumerate(lines, 1):

    stripped = line.strip()

    if not stripped:
        continue

    parts = stripped.split()

    if len(parts) < 2:
        continue

    try:
        values = [
            float(x.replace("D", "E"))
            for x in parts
        ]
    except ValueError:
        continue

    # On garde uniquement les lignes ayant plusieurs valeurs numériques.
    if len(values) >= 4:
        energy_lines.append((i, values))

print("Lignes numériques multi-valeurs :", len(energy_lines))

if energy_lines:

    print()
    print("Premières lignes candidates :")

    for i, values in energy_lines[:5]:
        print(f"{i:6d}:", values[:10])

    print()
    print("Dernières lignes candidates :")

    for i, values in energy_lines[-5:]:
        print(f"{i:6d}:", values[:10])


# ----------------------------------------------------------------------
# 7. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

print("[OK] Sortie BANDS relaxée inspectée.")
print("[OK] État de terminaison inspecté.")
print("[OK] Dimensions inspectées.")
print("[OK] K-points inspectés.")
print("[OK] Blocs énergétiques inspectés.")
print()
print("[INFO] Les éventuels c_bands restent des avertissements numériques.")
print("[INFO] Aucun jugement scientifique global n'est déduit ici.")
print("[INFO] Aucun calcul QE.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] AIDA inchangé.")

print()
print("=" * 78)
print("PHASE 78.34 TERMINÉE — READ-ONLY")
print("=" * 78)
