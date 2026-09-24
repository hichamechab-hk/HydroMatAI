#!/usr/bin/env python3

from pathlib import Path
import sys
import importlib.util
import re
import numpy as np

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF = BASE / "calculations/top5_dft/TiFeH2/TiFeH2.cif"

print("=" * 88)
print("PHASE 79.08 — VALIDATION SYMÉTRIE CRISTALLOGRAPHIQUE TiFeH2")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun dos.x")
print("[INFO] Aucun fichier scientifique modifié")

# ================================================================
# 1. SPGLIB
# ================================================================

print("\n" + "-" * 88)
print("1. DÉPENDANCE SPGLIB")
print("-" * 88)

if importlib.util.find_spec("spglib") is None:
    print("[FAIL] spglib absent")
    sys.exit(1)

import spglib

print(f"[PASS] spglib disponible : {spglib.__version__}")

# ================================================================
# 2. CIF
# ================================================================

print("\n" + "-" * 88)
print("2. LECTURE DU CIF")
print("-" * 88)

if not CIF.exists():
    print(f"[FAIL] CIF absent : {CIF}")
    sys.exit(1)

lines = CIF.read_text(
    encoding="utf-8",
    errors="replace"
).splitlines()

def cif_float(value):
    """
    Convertit :
      5.23992610
      5.23992610(2)
      0.281859(10)
    en float.
    """
    value = value.strip()
    value = re.sub(r"\([^)]*\)", "", value)

    if value in {".", "?", "nan", "NaN"}:
        raise ValueError(value)

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

print(f"[INFO] a     = {a:.8f}")
print(f"[INFO] b     = {b:.8f}")
print(f"[INFO] c     = {c:.8f}")
print(f"[INFO] alpha = {alpha:.8f}")
print(f"[INFO] beta  = {beta:.8f}")
print(f"[INFO] gamma = {gamma:.8f}")

# ================================================================
# 3. RECHERCHE LOOP ATOMIQUE
# ================================================================

print("\n" + "-" * 88)
print("3. EXTRACTION DES POSITIONS ATOMIQUES")
print("-" * 88)

loop_start = None
tags = []
data_start = None

for i, line in enumerate(lines):

    if line.strip().lower() != "loop_":
        continue

    candidate_tags = []
    j = i + 1

    while j < len(lines):

        s = lines[j].strip()

        if s.startswith("_"):
            candidate_tags.append(s.split()[0])
            j += 1
            continue

        break

    atom_tags = [
        x.lower()
        for x in candidate_tags
        if x.lower().startswith("_atom_site_")
    ]

    if (
        "_atom_site_fract_x" in atom_tags
        and "_atom_site_fract_y" in atom_tags
        and "_atom_site_fract_z" in atom_tags
    ):
        loop_start = i
        tags = candidate_tags
        data_start = j
        break

if loop_start is None:
    print("[FAIL] Loop atom_site introuvable")
    sys.exit(1)

print(f"[PASS] loop atomique trouvé à la ligne {loop_start + 1}")

print("[INFO] Colonnes détectées :")

for idx, tag in enumerate(tags):
    print(f"       {idx:02d} : {tag}")

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

if i_type is None and i_label is None:
    print("[FAIL] Espèce atomique absente")
    sys.exit(1)

print(f"[PASS] fract_x = colonne {i_x}")
print(f"[PASS] fract_y = colonne {i_y}")
print(f"[PASS] fract_z = colonne {i_z}")

# ================================================================
# 4. LECTURE ROBUSTE DES DONNÉES
# ================================================================

atoms = []

j = data_start

while j < len(lines):

    raw = lines[j]
    s = raw.strip()

    # Ignorer lignes vides
    if not s:
        j += 1
        continue

    # Fin d'un nouveau bloc CIF
    if s.lower() == "loop_":
        break

    # Un nouveau tag commence un autre bloc
    if s.startswith("_"):
        break

    # Commentaire
    if s.startswith("#"):
        j += 1
        continue

    parts = s.split()

    # Pas assez de colonnes
    if len(parts) < len(tags):
        j += 1
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

        # Nettoyage éventuel du symbole
        species = re.sub(
            r"[^A-Za-z]",
            "",
            species
        )

        if not species:
            raise ValueError("species vide")

        atoms.append(
            (
                species,
                x,
                y,
                z
            )
        )

    except (ValueError, IndexError):
        # Ne pas interrompre le parsing
        pass

    j += 1

print(f"[INFO] Lignes analysées : {j - data_start}")

if not atoms:
    print("[FAIL] Aucune position atomique extraite")
    print("\n[DEBUG] Premières lignes après les tags atomiques :")

    for k in range(
        data_start,
        min(data_start + 15, len(lines))
    ):
        print(
            f"       {k + 1:04d}: {lines[k]!r}"
        )

    sys.exit(1)

print(f"[PASS] Atomes extraits : {len(atoms)}")

for n, (species, x, y, z) in enumerate(
    atoms,
    start=1
):
    print(
        f"       {n:02d} "
        f"{species:2s} "
        f"{x: .8f} "
        f"{y: .8f} "
        f"{z: .8f}"
    )

# ================================================================
# 5. VÉRIFICATION COMPOSITION
# ================================================================

print("\n" + "-" * 88)
print("4. VÉRIFICATION COMPOSITION")
print("-" * 88)

species_count = {}

for species, _, _, _ in atoms:
    species_count[species] = (
        species_count.get(species, 0) + 1
    )

for species, count in species_count.items():
    print(f"[INFO] {species} : {count}")

if len(atoms) != 8:
    print(
        f"[WARN] Nombre d'atomes différent de 8 : "
        f"{len(atoms)}"
    )
else:
    print("[PASS] Nombre d'atomes = 8")

expected = {
    "Ti": 2,
    "Fe": 2,
    "H": 4
}

if species_count == expected:
    print("[PASS] Composition Ti2 Fe2 H4 confirmée")
else:
    print(
        "[WARN] Composition différente de Ti2 Fe2 H4"
    )

# ================================================================
# 6. CONSTRUCTION MAILLE
# ================================================================

print("\n" + "-" * 88)
print("5. CONSTRUCTION DE LA MAILLE")
print("-" * 88)

alpha_r = np.radians(alpha)
beta_r = np.radians(beta)
gamma_r = np.radians(gamma)

avec = np.array(
    [a, 0.0, 0.0],
    dtype=float
)

bvec = np.array(
    [
        b * np.cos(gamma_r),
        b * np.sin(gamma_r),
        0.0
    ],
    dtype=float
)

cx = c * np.cos(beta_r)

cy = c * (
    np.cos(alpha_r)
    - np.cos(beta_r) * np.cos(gamma_r)
) / np.sin(gamma_r)

cz2 = c**2 - cx**2 - cy**2

if cz2 <= 0:
    print("[FAIL] Géométrie de maille invalide")
    sys.exit(1)

cvec = np.array(
    [
        cx,
        cy,
        np.sqrt(cz2)
    ],
    dtype=float
)

lattice = np.array(
    [
        avec,
        bvec,
        cvec
    ]
)

positions = np.array(
    [
        [x, y, z]
        for _, x, y, z in atoms
    ],
    dtype=float
)

numbers_map = {}
numbers = []

for species, _, _, _ in atoms:

    if species not in numbers_map:
        numbers_map[species] = (
            len(numbers_map) + 1
        )

    numbers.append(
        numbers_map[species]
    )

numbers = np.array(
    numbers,
    dtype=int
)

print("[INFO] Vecteurs directs reconstruits :")

for vec in lattice:
    print(
        "       "
        + " ".join(
            f"{v: .10f}"
            for v in vec
        )
    )

volume = abs(
    np.linalg.det(lattice)
)

print(f"[INFO] Volume = {volume:.8f} Å³")

# ================================================================
# 7. SPGLIB
# ================================================================

print("\n" + "-" * 88)
print("6. DÉTERMINATION DE LA SYMÉTRIE SPGLIB")
print("-" * 88)

cell = (
    lattice,
    positions,
    numbers
)

try:

    dataset = spglib.get_symmetry_dataset(
        cell,
        symprec=1e-5
    )

except Exception as exc:

    print(f"[FAIL] Erreur spglib : {exc}")
    sys.exit(1)

if dataset is None:
    print("[FAIL] SPGLIB ne trouve aucune symétrie")
    sys.exit(1)

def ds(name):

    try:
        return dataset[name]
    except Exception:
        return getattr(
            dataset,
            name,
            None
        )

international = ds("international")
number = ds("number")
hall_number = ds("hall_number")
hall = ds("hall")
pointgroup = ds("pointgroup")
n_operations = ds("n_operations")

print(
    f"[PASS] Groupe international : "
    f"{international}"
)

print(
    f"[PASS] Numéro espace groupe : "
    f"{number}"
)

print(
    f"[INFO] Hall number          : "
    f"{hall_number}"
)

print(
    f"[INFO] Hall symbol          : "
    f"{hall}"
)

print(
    f"[INFO] Point group          : "
    f"{pointgroup}"
)

print(
    f"[INFO] Opérations symétrie  : "
    f"{n_operations}"
)

# ================================================================
# 8. ROBUSTESSE SYMPREC
# ================================================================

print("\n" + "-" * 88)
print("7. ROBUSTESSE PAR RAPPORT À SYMPREC")
print("-" * 88)

for symprec in [
    1e-6,
    1e-5,
    1e-4,
    1e-3
]:

    try:

        d = spglib.get_symmetry_dataset(
            cell,
            symprec=symprec
        )

        if d is None:

            print(
                f"[WARN] symprec={symprec:.0e} : "
                "aucune symétrie"
            )

            continue

        print(
            f"[INFO] symprec={symprec:.0e} : "
            f"{d['international']} "
            f"(#{d['number']}), "
            f"{d['n_operations']} opérations"
        )

    except Exception as exc:

        print(
            f"[WARN] symprec={symprec:.0e} : "
            f"{exc}"
        )

# ================================================================
# 9. INVERSION
# ================================================================

print("\n" + "-" * 88)
print("8. TEST D'INVERSION")
print("-" * 88)

rotations = np.array(
    ds("rotations")
)

inversion_matrix = -np.eye(
    3,
    dtype=int
)

has_inversion = any(
    np.array_equal(
        rotation,
        inversion_matrix
    )
    for rotation in rotations
)

if has_inversion:
    print(
        "[PASS] Opération d'inversion détectée"
    )
else:
    print(
        "[INFO] Aucune opération d'inversion détectée"
    )

# ================================================================
# 10. RÉSULTAT
# ================================================================

print("\n" + "=" * 88)
print("RÉSULTAT PHASE 79.08")
print("=" * 88)

print(
    f"[RESULT] Groupe spatial : "
    f"{international} (#{number})"
)

print(
    f"[RESULT] Point group    : "
    f"{pointgroup}"
)

print(
    f"[RESULT] Opérations     : "
    f"{n_operations}"
)

print(
    "[RESULT] Inversion      : "
    + ("OUI" if has_inversion else "NON")
)

print("\n[RESULT] VALIDATION SYMÉTRIE TERMINÉE")
print("[INFO] Aucun calcul QE exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
print(
    "[INFO] Les labels BZ officiels ne sont "
    "pas encore attribués."
)
