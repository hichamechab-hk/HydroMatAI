#!/usr/bin/env python3

from pathlib import Path
import sys
import re
import numpy as np

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF = BASE / "calculations/top5_dft/TiFeH2/TiFeH2.cif"

print("=" * 100)
print("PHASE 79.10 — MAPPING SEEK-PATH → CELLULE QE TiFeH2")
print("=" * 100)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun dos.x")
print("[INFO] Aucun fichier scientifique modifié")

# ======================================================================
# 1. DEPENDANCES
# ======================================================================

print("\n" + "-" * 100)
print("1. DÉPENDANCES")
print("-" * 100)

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

print("\n" + "-" * 100)
print("2. LECTURE DU CIF QE")
print("-" * 100)

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
# 3. ATOMES
# ======================================================================

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

atoms = []

for j in range(data_start, len(lines)):

    s = lines[j].strip()

    if not s or s.startswith("#"):
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

        species = re.sub(
            r"[^A-Za-z]",
            "",
            species
        )

        atoms.append(
            (species, x, y, z)
        )

    except (ValueError, IndexError):
        continue

if len(atoms) != 8:
    print(
        f"[FAIL] Nombre d'atomes extrait = "
        f"{len(atoms)} ; attendu = 8"
    )
    sys.exit(1)

print("[PASS] 8 atomes extraits")

# ======================================================================
# 4. CELLULE DIRECTE QE
# ======================================================================

print("\n" + "-" * 100)
print("3. CELLULE DIRECTE QE")
print("-" * 100)

ar = np.radians(alpha)
br = np.radians(beta)
gr = np.radians(gamma)

A = np.array([
    a, 0.0, 0.0
])

B = np.array([
    b * np.cos(gr),
    b * np.sin(gr),
    0.0
])

C = np.array([
    c * np.cos(br),
    c * (
        np.cos(ar)
        - np.cos(br) * np.cos(gr)
    ) / np.sin(gr),
    np.sqrt(
        c**2
        - (c * np.cos(br))**2
        - (
            c * (
                np.cos(ar)
                - np.cos(br) * np.cos(gr)
            ) / np.sin(gr)
        )**2
    )
])

qe_lattice = np.array([A, B, C])

print("[INFO] CELL_PARAMETERS QE :")

for v in qe_lattice:
    print(
        "       "
        + " ".join(
            f"{x: .10f}"
            for x in v
        )
    )

print(
    f"[INFO] Volume = "
    f"{abs(np.linalg.det(qe_lattice)):.10f} Å³"
)

# ======================================================================
# 5. CONSTRUCTION CELL + SEEKPATH
# ======================================================================

print("\n" + "-" * 100)
print("4. CELLULE SPGLIB / SEEK-PATH")
print("-" * 100)

species_map = {}
numbers = []

for species, _, _, _ in atoms:

    if species not in species_map:
        species_map[species] = len(species_map) + 1

    numbers.append(species_map[species])

positions = np.array([
    [x, y, z]
    for _, x, y, z in atoms
])

numbers = np.array(numbers, dtype=int)

cell = (
    qe_lattice,
    positions,
    numbers
)

dataset = spglib.get_symmetry_dataset(
    cell,
    symprec=1e-5
)

if dataset is None:
    print("[FAIL] SPGLIB : symétrie introuvable")
    sys.exit(1)

print(
    f"[PASS] SPGLIB = "
    f"{dataset['international']} "
    f"(#{dataset['number']})"
)

seek = seekpath.get_path(
    cell,
    symprec=1e-5,
    angle_tolerance=-1.0,
    threshold=1e-7
)

print(
    f"[PASS] SeeK-path = "
    f"{seek['spacegroup_international']} "
    f"(#{seek['spacegroup_number']})"
)

print(
    f"[INFO] Réseau = "
    f"{seek['bravais_lattice_extended']}"
)

# ======================================================================
# 6. MATRICES DE CONVERSION
# ======================================================================

print("\n" + "-" * 100)
print("5. MATRICES DE CONVERSION")
print("-" * 100)

primitive = np.array(
    seek["primitive_lattice"],
    dtype=float
)

conventional = np.array(
    seek["conv_lattice"],
    dtype=float
)

print("[INFO] Primitive SeeK-path :")

for v in primitive:
    print(
        "       "
        + " ".join(
            f"{x: .10f}"
            for x in v
        )
    )

print("[INFO] Conventionnelle SeeK-path :")

for v in conventional:
    print(
        "       "
        + " ".join(
            f"{x: .10f}"
            for x in v
        )
    )

# ----------------------------------------------------------------------
# Convention utilisée ici :
#
# Les vecteurs sont rangés en lignes.
#
# Pour un vecteur réciproque exprimé en coordonnées fractionnaires
# dans la base réciproque primitive SeeK-path :
#
#       k_cart = k_prim @ B_prim
#
# On cherche q_QE tel que :
#
#       q_QE @ B_QE = k_cart
#
# donc :
#
#       q_QE = k_prim @ B_prim @ inv(B_QE)
#
# ----------------------------------------------------------------------

# Reciprocal matrices WITHOUT 2*pi, sufficient for fractional mapping.
# Rows = reciprocal vectors.

Bprim_recip = 2.0 * np.pi * np.linalg.inv(primitive)
Bqe_recip = 2.0 * np.pi * np.linalg.inv(qe_lattice)

# Mapping row-vector convention:
# q_qe @ Bqe_recip = q_prim @ Bprim_recip
#
# q_qe = q_prim @ Bprim_recip @ inv(Bqe_recip)

M = Bprim_recip @ np.linalg.inv(Bqe_recip)

print("[INFO] Matrice de mapping :")
print("[INFO] k_QE = k_SeeK-path × M")

for row in M:
    print(
        "       "
        + " ".join(
            f"{x: .10f}"
            for x in row
        )
    )

# ======================================================================
# 7. VALIDATION DU MAPPING
# ======================================================================

print("\n" + "-" * 100)
print("6. VALIDATION ALGÉBRIQUE")
print("-" * 100)

max_error = 0.0

for label, coord in seek["point_coords"].items():

    kprim = np.array(coord, dtype=float)

    kqe = kprim @ M

    cart_prim = kprim @ Bprim_recip
    cart_qe = kqe @ Bqe_recip

    err = np.linalg.norm(
        cart_prim - cart_qe
    )

    max_error = max(
        max_error,
        err
    )

    print(
        f"[CHECK] {label:8s} "
        f"erreur cartésienne = "
        f"{err:.3e} Å⁻¹"
    )

if max_error < 1e-8:
    print(
        f"[PASS] Mapping réciproque validé "
        f"(erreur max {max_error:.3e} Å⁻¹)"
    )
else:
    print(
        f"[WARN] Erreur mapping = "
        f"{max_error:.3e} Å⁻¹"
    )

# ======================================================================
# 8. COORDONNÉES QE DES POINTS
# ======================================================================

print("\n" + "-" * 100)
print("7. POINTS HAUTE SYMÉTRIE — COORDONNÉES QE")
print("-" * 100)

mapped = {}

for label, coord in seek["point_coords"].items():

    kprim = np.array(coord, dtype=float)

    kqe = kprim @ M

    # Représentation réduite [-0.5, 0.5)
    kqe_wrapped = (
        (kqe + 0.5) % 1.0
    ) - 0.5

    mapped[label] = kqe_wrapped

    print(
        f"[POINT] {label:8s} "
        f"SeeK = "
        f"({coord[0]: .8f}, "
        f"{coord[1]: .8f}, "
        f"{coord[2]: .8f})"
    )

    print(
        f"         QE   = "
        f"({kqe_wrapped[0]: .8f}, "
        f"{kqe_wrapped[1]: .8f}, "
        f"{kqe_wrapped[2]: .8f})"
    )

# ======================================================================
# 9. SEGMENTS MAPPÉS
# ======================================================================

print("\n" + "-" * 100)
print("8. SEGMENTS BZ — CONVENTION QE")
print("-" * 100)

for i, (start, end) in enumerate(
    seek["path"],
    1
):

    ks = mapped[start]
    ke = mapped[end]

    print(
        f"[SEGMENT {i:02d}] "
        f"{start} → {end}"
    )

    print(
        f"          start = "
        f"({ks[0]: .8f}, "
        f"{ks[1]: .8f}, "
        f"{ks[2]: .8f})"
    )

    print(
        f"          end   = "
        f"({ke[0]: .8f}, "
        f"{ke[1]: .8f}, "
        f"{ke[2]: .8f})"
    )

# ======================================================================
# 10. TEST POINTS DANS BZ
# ======================================================================

print("\n" + "-" * 100)
print("9. CONTRÔLE POINTS")
print("-" * 100)

for label, k in mapped.items():

    if np.all(np.isfinite(k)):
        print(
            f"[PASS] {label:8s} "
            f"coordonnées QE finies"
        )
    else:
        print(
            f"[FAIL] {label:8s} "
            f"coordonnées invalides"
        )

# ======================================================================
# 11. COMPARAISON AVEC L'ANCIEN CHEMIN
# ======================================================================

print("\n" + "-" * 100)
print("10. ANCIEN CHEMIN PROVISOIRE")
print("-" * 100)

print(
    "[WARN] Le chemin Γ-X-L-Y-Γ-Z-M-R-N-Z "
    "est CONSERVÉ UNIQUEMENT comme historique."
)

print(
    "[WARN] Il ne doit pas être utilisé pour le calcul "
    "de bandes TiFeH2."
)

# ======================================================================
# 12. RESULTAT
# ======================================================================

print("\n" + "=" * 100)
print("RÉSULTAT PHASE 79.10")
print("=" * 100)

print(
    f"[RESULT] Groupe : "
    f"{seek['spacegroup_international']} "
    f"(#{seek['spacegroup_number']})"
)

print(
    f"[RESULT] Réseau : "
    f"{seek['bravais_lattice_extended']}"
)

print(
    f"[RESULT] Points BZ : "
    f"{len(seek['point_coords'])}"
)

print(
    f"[RESULT] Segments : "
    f"{len(seek['path'])}"
)

print(
    f"[RESULT] Erreur mapping : "
    f"{max_error:.3e} Å⁻¹"
)

if max_error < 1e-8:
    print(
        "[RESULT] PASS — mapping SeeK-path → QE validé."
    )
else:
    print(
        "[RESULT] WARN — mapping à examiner."
    )

print("[INFO] Aucun calcul QE exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
print(
    "[INFO] Étape suivante : préparation contrôlée "
    "de bands.x uniquement après validation."
)
