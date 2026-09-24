#!/usr/bin/env python3

from pathlib import Path
import sys
import re
import numpy as np

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF = BASE / "calculations/top5_dft/TiFeH2/TiFeH2.cif"

print("=" * 96)
print("PHASE 79.09 — CHEMIN BZ HAUTE SYMÉTRIE TiFeH2")
print("=" * 96)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun dos.x")
print("[INFO] Aucun fichier scientifique modifié")

# ======================================================================
# 1. DEPENDANCES
# ======================================================================

print("\n" + "-" * 96)
print("1. DÉPENDANCES")
print("-" * 96)

try:
    import spglib
    import seekpath
except ImportError as exc:
    print(f"[FAIL] Dépendance manquante : {exc}")
    sys.exit(1)

print(f"[PASS] spglib  = {spglib.__version__}")
print(f"[PASS] seekpath = {seekpath.__version__}")

# ======================================================================
# 2. LECTURE CIF
# ======================================================================

print("\n" + "-" * 96)
print("2. LECTURE STRUCTURE CIF")
print("-" * 96)

if not CIF.exists():
    print(f"[FAIL] CIF absent : {CIF}")
    sys.exit(1)

lines = CIF.read_text(
    encoding="utf-8",
    errors="replace"
).splitlines()

def cif_float(value):
    value = value.strip()
    value = re.sub(r"\([^)]*\)", "", value)
    return float(value)

def get_value(tag):
    pattern = re.compile(
        rf"^\s*{re.escape(tag)}\s+(\S+)",
        re.IGNORECASE
    )

    for line in lines:
        m = pattern.match(line)
        if m:
            try:
                return cif_float(m.group(1))
            except ValueError:
                pass

    return None

a = get_value("_cell_length_a")
b = get_value("_cell_length_b")
c = get_value("_cell_length_c")
alpha = get_value("_cell_angle_alpha")
beta = get_value("_cell_angle_beta")
gamma = get_value("_cell_angle_gamma")

if None in (a, b, c, alpha, beta, gamma):
    print("[FAIL] Paramètres de maille incomplets")
    sys.exit(1)

print(f"[INFO] a     = {a:.10f} Å")
print(f"[INFO] b     = {b:.10f} Å")
print(f"[INFO] c     = {c:.10f} Å")
print(f"[INFO] alpha = {alpha:.10f}°")
print(f"[INFO] beta  = {beta:.10f}°")
print(f"[INFO] gamma = {gamma:.10f}°")

# ======================================================================
# 3. EXTRACTION ATOMIQUE
# ======================================================================

print("\n" + "-" * 96)
print("3. EXTRACTION ATOMIQUE")
print("-" * 96)

loop_start = None
tags = []
data_start = None

for i, line in enumerate(lines):

    if line.strip().lower() != "loop_":
        continue

    candidate = []
    j = i + 1

    while j < len(lines):

        s = lines[j].strip()

        if s.startswith("_"):
            candidate.append(s.split()[0])
            j += 1
        else:
            break

    low = [x.lower() for x in candidate]

    if (
        "_atom_site_fract_x" in low
        and "_atom_site_fract_y" in low
        and "_atom_site_fract_z" in low
    ):
        loop_start = i
        tags = candidate
        data_start = j
        break

if loop_start is None:
    print("[FAIL] Loop atomique introuvable")
    sys.exit(1)

def find_tag(*names):
    lower = {
        tag.lower(): idx
        for idx, tag in enumerate(tags)
    }

    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]

    return None

i_type = find_tag("_atom_site_type_symbol")
i_label = find_tag("_atom_site_label")
i_x = find_tag("_atom_site_fract_x")
i_y = find_tag("_atom_site_fract_y")
i_z = find_tag("_atom_site_fract_z")

if i_x is None or i_y is None or i_z is None:
    print("[FAIL] Coordonnées fractionnaires absentes")
    sys.exit(1)

atoms = []

for j in range(data_start, len(lines)):

    s = lines[j].strip()

    if not s:
        continue

    if s.startswith("#"):
        continue

    if s.lower() == "loop_" or s.startswith("_"):
        break

    parts = s.split()

    if len(parts) < len(tags):
        continue

    try:
        species = (
            parts[i_type]
            if i_type is not None
            else parts[i_label]
        )

        x = cif_float(parts[i_x])
        y = cif_float(parts[i_y])
        z = cif_float(parts[i_z])

        species = re.sub(r"[^A-Za-z]", "", species)

        atoms.append((species, x, y, z))

    except (ValueError, IndexError):
        continue

if not atoms:
    print("[FAIL] Aucun atome extrait")
    sys.exit(1)

print(f"[PASS] {len(atoms)} atomes extraits")

for i, atom in enumerate(atoms, 1):
    print(
        f"       {i:02d} {atom[0]:2s} "
        f"{atom[1]: .8f} "
        f"{atom[2]: .8f} "
        f"{atom[3]: .8f}"
    )

# ======================================================================
# 4. MAILLE
# ======================================================================

print("\n" + "-" * 96)
print("4. CONSTRUCTION DE LA MAILLE")
print("-" * 96)

ar = np.radians(alpha)
br = np.radians(beta)
gr = np.radians(gamma)

avec = np.array([a, 0.0, 0.0])

bvec = np.array([
    b * np.cos(gr),
    b * np.sin(gr),
    0.0
])

cx = c * np.cos(br)
cy = c * (
    np.cos(ar) -
    np.cos(br) * np.cos(gr)
) / np.sin(gr)

cz = np.sqrt(
    c**2 - cx**2 - cy**2
)

cvec = np.array([
    cx,
    cy,
    cz
])

lattice = np.array([
    avec,
    bvec,
    cvec
])

positions = np.array([
    [x, y, z]
    for _, x, y, z in atoms
])

species_map = {}
numbers = []

for species, _, _, _ in atoms:

    if species not in species_map:
        species_map[species] = len(species_map) + 1

    numbers.append(species_map[species])

numbers = np.array(numbers, dtype=int)

print("[INFO] Maille directe utilisée par SeeK-path :")

for vec in lattice:
    print(
        "       "
        + " ".join(f"{v: .10f}" for v in vec)
    )

print(
    f"[INFO] Volume = "
    f"{abs(np.linalg.det(lattice)):.10f} Å³"
)

# ======================================================================
# 5. SPGLIB AVANT SEEKPATH
# ======================================================================

print("\n" + "-" * 96)
print("5. CONTRÔLE SPGLIB")
print("-" * 96)

cell = (
    lattice,
    positions,
    numbers
)

dataset = spglib.get_symmetry_dataset(
    cell,
    symprec=1e-5
)

if dataset is None:
    print("[FAIL] SPGLIB ne détecte pas la symétrie")
    sys.exit(1)

print(
    f"[PASS] Groupe spatial = "
    f"{dataset['international']} "
    f"(#{dataset['number']})"
)

print(
    f"[INFO] Point group = "
    f"{dataset['pointgroup']}"
)

# ======================================================================
# 6. SEEK-PATH
# ======================================================================

print("\n" + "-" * 96)
print("6. STANDARDISATION SEEK-PATH")
print("-" * 96)

try:

    result = seekpath.get_path(
        cell,
        symprec=1e-5,
        angle_tolerance=-1.0,
        threshold=1e-7
    )

except Exception as exc:

    print(f"[FAIL] SeeK-path : {exc}")
    sys.exit(1)

print(
    f"[PASS] Structure standardisée obtenue"
)

print(
    f"[INFO] Groupe international SeeK-path : "
    f"{result.get('bravais_lattice')}"
)

print(
    f"[INFO] Groupe spatial : "
    f"{result.get('spacegroup_international')} "
    f"(#{result.get('spacegroup_number')})"
)

print(
    f"[INFO] Type de réseau : "
    f"{result.get('bravais_lattice')}"
)

print(
    f"[INFO] Type de maille primitive : "
    f"{result.get('bravais_lattice_extended')}"
)

# ======================================================================
# 7. POINTS HAUTE SYMETRIE
# ======================================================================

print("\n" + "-" * 96)
print("7. POINTS HAUTE SYMÉTRIE")
print("-" * 96)

point_coords = result["point_coords"]

for label, coord in point_coords.items():

    print(
        f"[POINT] {label:6s} "
        f"({coord[0]: .8f}, "
        f"{coord[1]: .8f}, "
        f"{coord[2]: .8f})"
    )

# ======================================================================
# 8. CHEMIN OFFICIEL
# ======================================================================

print("\n" + "-" * 96)
print("8. CHEMIN BZ SEEК-PATH")
print("-" * 96)

path = result["path"]

print(
    f"[INFO] Nombre de segments = {len(path)}"
)

for i, segment in enumerate(path, 1):

    start, end = segment

    print(
        f"[SEGMENT {i:02d}] "
        f"{start} → {end}"
    )

# ======================================================================
# 9. VÉRIFICATION DES LABELS PROVISOIRES
# ======================================================================

print("\n" + "-" * 96)
print("9. COMPARAISON AVEC LES LABELS PROVISOIRES")
print("-" * 96)

provisional = {
    "G": (0.0, 0.0, 0.0),
    "X": (0.5, 0.0, 0.0),
    "Y": (0.0, 0.5, 0.0),
    "Z": (0.0, 0.0, 0.5),
    "L": (0.5, 0.5, 0.0),
    "M": (0.5, 0.0, 0.5),
    "N": (0.0, 0.5, 0.5),
    "R": (0.5, 0.5, 0.5),
}

for label, coord in provisional.items():

    if label in point_coords:

        official = np.array(
            point_coords[label]
        )

        delta = np.linalg.norm(
            official -
            np.array(coord)
        )

        if delta < 1e-6:
            status = "COHÉRENT"
        else:
            status = "DIFFÉRENT"

        print(
            f"[INFO] {label:2s} : "
            f"{status} "
            f"(écart={delta:.8f})"
        )

    else:

        print(
            f"[INFO] {label:2s} : "
            f"pas de label SeeK-path correspondant"
        )

# ======================================================================
# 10. CELLULES STANDARDISÉES
# ======================================================================

print("\n" + "-" * 96)
print("10. CELLULE STANDARDISÉE")
print("-" * 96)

for name in [
    "primitive_lattice",
    "conv_lattice"
]:

    if name not in result:
        continue

    print(f"[INFO] {name} :")

    arr = np.array(result[name])

    for vec in arr:
        print(
            "       "
            + " ".join(
                f"{v: .10f}"
                for v in vec
            )
        )

# ======================================================================
# 11. RÉSULTAT
# ======================================================================

print("\n" + "=" * 96)
print("RÉSULTAT PHASE 79.09")
print("=" * 96)

print(
    f"[RESULT] Symétrie : "
    f"{result.get('spacegroup_international')} "
    f"(#{result.get('spacegroup_number')})"
)

print(
    f"[RESULT] Réseau : "
    f"{result.get('bravais_lattice_extended')}"
)

print(
    f"[RESULT] Points haute symétrie : "
    f"{len(point_coords)}"
)

print(
    f"[RESULT] Segments BZ : "
    f"{len(path)}"
)

print(
    "[RESULT] CHEMIN BZ OFFICIEL SEEК-PATH EXTRAIT"
)

print("[INFO] Aucun calcul QE exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
print(
    "[INFO] Ne pas lancer bands.x avant validation "
    "du chemin et de la convention de cellule."
)
