#!/usr/bin/env python3

import csv
import math
import re
from pathlib import Path
from collections import Counter

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF_DIR = BASE / "data/literature_benchmarks/cif"
REPORT_DIR = BASE / "reports/literature_benchmarks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# REFERENCES PUBLIEES
# ============================================================================

PUBLISHED = {
    "K2GeH6": {
        "a": 7.968,
        "b": 7.968,
        "c": 7.968,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 505.991,
        "formula": "K2GeH6",
        "space_group": "Fm-3m",
        "space_group_number": 225,
        "Z": 4,
        "expected_atoms": 36,
    },
    "K2SnH6": {
        "a": 8.338,
        "b": 8.338,
        "c": 8.338,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 579.679,
        "formula": "K2SnH6",
        "space_group": "Fm-3m",
        "space_group_number": 225,
        "Z": 4,
        "expected_atoms": 36,
    },
    "Rb2GeH6": {
        "a": 8.318,
        "b": 8.318,
        "c": 8.318,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 575.574,
        "formula": "Rb2GeH6",
        "space_group": "Fm-3m",
        "space_group_number": 225,
        "Z": 4,
        "expected_atoms": 36,
    },
    "Rb2SnH6": {
        "a": 8.666,
        "b": 8.666,
        "c": 8.666,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 650.974,
        "formula": "Rb2SnH6",
        "space_group": "Fm-3m",
        "space_group_number": 225,
        "Z": 4,
        "expected_atoms": 36,
    },
    "NaPdH3": {
        "a": 3.61,
        "b": 3.61,
        "c": 3.61,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 47.08,
        "formula": "NaPdH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
    "CaPdH3": {
        "a": 3.72,
        "b": 3.72,
        "c": 3.72,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 51.46,
        "formula": "CaPdH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
    "SrPdH3": {
        "a": 3.84,
        "b": 3.84,
        "c": 3.84,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 56.60,
        "formula": "SrPdH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
    "NaRuH3": {
        "a": 3.53,
        "b": 3.53,
        "c": 3.53,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 43.87,
        "formula": "NaRuH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
    "CaRuH3": {
        "a": 3.64,
        "b": 3.64,
        "c": 3.64,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 48.21,
        "formula": "CaRuH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
    "SrRuH3": {
        "a": 3.77,
        "b": 3.77,
        "c": 3.77,
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 90.0,
        "volume": 53.42,
        "formula": "SrRuH3",
        "space_group": "Pm-3m",
        "space_group_number": 221,
        "Z": 1,
        "expected_atoms": 5,
    },
}

# Tolérances volontairement raisonnables pour les CIF reconstruits.
LATTICE_TOL_PCT = 0.10
VOLUME_TOL_PCT = 0.50
COORD_TOL = 1.0e-5
MIN_DISTANCE = 0.70

# ============================================================================
# OUTILS
# ============================================================================

def normalize_formula(s):
    if not s:
        return None
    s = s.strip().strip("'").strip('"')
    s = re.sub(r"\s+", "", s)
    return s


def parse_number(s):
    if s is None:
        return None

    s = str(s).strip().strip("'").strip('"')

    if s in ("?", "."):
        return None

    # Supporte 3.72(1)
    m = re.match(r"^([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)", s)

    if not m:
        return None

    try:
        return float(m.group(1))
    except ValueError:
        return None


def parse_cif(path):
    data = {
        "tags": {},
        "atoms": [],
    }

    lines = path.read_text(errors="replace").splitlines()

    # ------------------------------------------------------------------------
    # TAGS simples
    # ------------------------------------------------------------------------

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("_"):
            parts = stripped.split(None, 1)

            if len(parts) == 2:
                key = parts[0]
                value = parts[1].strip()

                # Ne pas confondre les colonnes atomiques avec les tags.
                if not key.startswith("_atom_site_"):
                    data["tags"][key] = value.strip("'").strip('"')

    # ------------------------------------------------------------------------
    # LOOP atom_site
    # ------------------------------------------------------------------------

    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.lower() != "loop_":
            i += 1
            continue

        headers = []
        j = i + 1

        while j < len(lines):
            s = lines[j].strip()

            if s.startswith("_"):
                headers.append(s.split()[0])
                j += 1
            else:
                break

        if not headers:
            i = j
            continue

        atom_required = {
            "_atom_site_type_symbol",
            "_atom_site_fract_x",
            "_atom_site_fract_y",
            "_atom_site_fract_z",
        }

        if not atom_required.issubset(set(headers)):
            i = j
            continue

        # Lecture des lignes de données.
        k = j

        while k < len(lines):
            s = lines[k].strip()

            if not s:
                k += 1
                continue

            if s.startswith("#"):
                k += 1
                continue

            if s.lower() == "loop_" or s.startswith("_") or s.lower().startswith("data_"):
                break

            # CIF simple : valeurs séparées par espaces.
            values = s.split()

            if len(values) < len(headers):
                k += 1
                continue

            row = dict(zip(headers, values))

            symbol = row.get("_atom_site_type_symbol")

            if symbol:
                atom = {
                    "label": row.get("_atom_site_label", "?"),
                    "symbol": symbol.strip("'").strip('"'),
                    "x": parse_number(row.get("_atom_site_fract_x")),
                    "y": parse_number(row.get("_atom_site_fract_y")),
                    "z": parse_number(row.get("_atom_site_fract_z")),
                    "occupancy": parse_number(row.get("_atom_site_occupancy")),
                }

                data["atoms"].append(atom)

            k += 1

        i = k

    return data


def cell_volume(a, b, c, alpha, beta, gamma):
    ar = math.radians(alpha)
    br = math.radians(beta)
    gr = math.radians(gamma)

    factor = (
        1
        - math.cos(ar) ** 2
        - math.cos(br) ** 2
        - math.cos(gr) ** 2
        + 2
        * math.cos(ar)
        * math.cos(br)
        * math.cos(gr)
    )

    if factor < 0:
        return None

    return a * b * c * math.sqrt(factor)


def pct_diff(value, reference):
    if reference == 0:
        return None
    return 100.0 * (value - reference) / reference


def normalize_sg(value):
    if value is None:
        return None

    s = value.strip().strip("'").strip('"')

    s = re.sub(r"\s+", "", s)

    # Normalisation des variantes usuelles.
    s = s.replace("Fm-3m", "Fm-3m")
    s = s.replace("Pm-3m", "Pm-3m")

    return s


def formula_counts(formula):
    """
    K2GeH6 -> {'K':2,'Ge':1,'H':6}
    CaPdH3 -> {'Ca':1,'Pd':1,'H':3}
    """
    if not formula:
        return {}

    formula = normalize_formula(formula)

    tokens = re.findall(r"([A-Z][a-z]?)(\d*(?:\.\d+)?)", formula)

    result = {}

    for element, number in tokens:
        if number == "":
            n = 1.0
        else:
            n = float(number)

        result[element] = result.get(element, 0.0) + n

    return result


def atom_counts(atoms):
    counts = Counter()

    for atom in atoms:
        counts[atom["symbol"]] += 1

    return dict(counts)


def infer_z(formula, counts):
    expected = formula_counts(formula)

    if not expected or not counts:
        return None

    ratios = []

    for element, n_formula in expected.items():
        n_cell = counts.get(element)

        if n_cell is None:
            return None

        if n_formula <= 0:
            return None

        ratios.append(n_cell / n_formula)

    if not ratios:
        return None

    z0 = ratios[0]

    for r in ratios[1:]:
        if abs(r - z0) > 1.0e-8:
            return None

    z_round = round(z0)

    if z_round < 1:
        return None

    # Vérification qu'aucun élément parasite n'est présent.
    for element in counts:
        if element not in expected:
            return None

    return z_round


def minimum_distance_cartesian(atoms, a, b, c):
    """
    Distance minimale avec recherche sur les translations périodiques
    -1,0,+1.
    """

    if not atoms:
        return None

    coords = []

    for atom in atoms:
        x, y, z = atom["x"], atom["y"], atom["z"]

        if None in (x, y, z):
            continue

        coords.append((atom["symbol"], x, y, z))

    if len(coords) < 2:
        return None

    min_d = float("inf")

    for i in range(len(coords)):
        _, x1, y1, z1 = coords[i]

        for j in range(i + 1, len(coords)):
            _, x2, y2, z2 = coords[j]

            dx0 = x2 - x1
            dy0 = y2 - y1
            dz0 = z2 - z1

            for tx in (-1, 0, 1):
                for ty in (-1, 0, 1):
                    for tz in (-1, 0, 1):
                        dx = dx0 + tx
                        dy = dy0 + ty
                        dz = dz0 + tz

                        # Cell cubique / orthorhombique dans nos benchmarks.
                        d = math.sqrt(
                            (dx * a) ** 2
                            + (dy * b) ** 2
                            + (dz * c) ** 2
                        )

                        if d > 1.0e-10:
                            min_d = min(min_d, d)

    if min_d == float("inf"):
        return None

    return min_d


# ============================================================================
# AUDIT
# ============================================================================

print("=" * 78)
print("PHASE LITERATURE BENCHMARK — CIF AUDIT V4")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun CIF modifié")
print("[INFO] Z = PRESENT ou INFERRED")
print("[INFO] Space group = PRESENT ou INFERRED")
print()

rows = []

cif_files = sorted(CIF_DIR.glob("*.cif"))

if not cif_files:
    print("[ERROR] Aucun CIF trouvé :", CIF_DIR)
    raise SystemExit(1)

for cif_path in cif_files:

    name = cif_path.stem

    print()
    print("=" * 78)
    print(f"FILE: {cif_path}")
    print("=" * 78)

    if name not in PUBLISHED:
        print("[WARN] Référence publiée absente :", name)
        continue

    ref = PUBLISHED[name]
    cif = parse_cif(cif_path)
    tags = cif["tags"]
    atoms = cif["atoms"]

    # ------------------------------------------------------------------------
    # FORMULE
    # ------------------------------------------------------------------------

    formula_cif = normalize_formula(
        tags.get("_chemical_formula_sum")
    )

    formula_expected = normalize_formula(ref["formula"])

    formula_status = formula_cif == formula_expected

    # ------------------------------------------------------------------------
    # CELLULE
    # ------------------------------------------------------------------------

    a = parse_number(tags.get("_cell_length_a"))
    b = parse_number(tags.get("_cell_length_b"))
    c = parse_number(tags.get("_cell_length_c"))

    alpha = parse_number(tags.get("_cell_angle_alpha"))
    beta = parse_number(tags.get("_cell_angle_beta"))
    gamma = parse_number(tags.get("_cell_angle_gamma"))

    cell_ok = all(
        x is not None
        for x in (a, b, c, alpha, beta, gamma)
    )

    lattice_status = False
    angle_status = False
    volume_status = False

    if cell_ok:
        lattice_diffs = [
            abs(pct_diff(a, ref["a"])),
            abs(pct_diff(b, ref["b"])),
            abs(pct_diff(c, ref["c"])),
        ]

        lattice_status = all(
            x <= LATTICE_TOL_PCT
            for x in lattice_diffs
        )

        angle_diffs = [
            abs(alpha - ref["alpha"]),
            abs(beta - ref["beta"]),
            abs(gamma - ref["gamma"]),
        ]

        angle_status = all(
            x <= 1.0e-6
            for x in angle_diffs
        )

        volume = cell_volume(
            a, b, c,
            alpha, beta, gamma
        )

        volume_diff_pct = pct_diff(
            volume,
            ref["volume"]
        )

        volume_status = (
            abs(volume_diff_pct) <= VOLUME_TOL_PCT
        )
    else:
        volume = None
        volume_diff_pct = None

    # ------------------------------------------------------------------------
    # ATOMES
    # ------------------------------------------------------------------------

    counts = atom_counts(atoms)

    expected_counts = formula_counts(
        formula_expected
    )

    z_inferred = infer_z(
        formula_expected,
        counts
    )

    atom_count_status = (
        len(atoms) == ref["expected_atoms"]
    )

    composition_status = (
        z_inferred == ref["Z"]
    )

    # ------------------------------------------------------------------------
    # Z
    # ------------------------------------------------------------------------

    z_cif = parse_number(
        tags.get("_cell_formula_units_Z")
    )

    if z_cif is not None:
        z_status = (
            abs(z_cif - ref["Z"]) < 1.0e-8
        )
        z_mode = "PRESENT"
        z_value = z_cif
    else:
        z_status = composition_status
        z_mode = "INFERRED"
        z_value = z_inferred

    # ------------------------------------------------------------------------
    # SPACE GROUP
    # ------------------------------------------------------------------------

    # Supporte les variantes CIF modernes et historiques.
    # Le fichier benchmark inspecté utilise :
    # _symmetry_space_group_name_H-M_alt
    sg_value = (
        tags.get("_space_group_name_H-M_alt")
        or tags.get("_symmetry_space_group_name_H-M_alt")
        or tags.get("_symmetry_space_group_name_H-M")
        or tags.get("_space_group.name_H-M_alt")
    )

    sg_number = (
        parse_number(tags.get("_space_group_IT_number"))
        or parse_number(tags.get("_symmetry_Int_Tables_number"))
    )

    sg_norm = normalize_sg(sg_value)
    sg_expected = normalize_sg(ref["space_group"])

    sg_name_status = (
        sg_norm == sg_expected
    )

    sg_number_status = (
        sg_number is not None
        and int(round(sg_number))
        == ref["space_group_number"]
    )

    if sg_value is not None and sg_number is not None:
        sg_mode = "PRESENT"
    elif sg_value is not None:
        sg_mode = "NAME_PRESENT"
    elif sg_number is not None:
        sg_mode = "NUMBER_PRESENT"
    else:
        sg_mode = "ABSENT"

    # Le groupe d'espace est considéré correctement identifié
    # si le symbole OU le numéro permet de l'identifier,
    # avec cohérence lorsqu'ils sont tous les deux présents.
    if sg_value is not None and sg_number is not None:
        space_group_status = (
            sg_name_status and sg_number_status
        )
    elif sg_value is not None:
        space_group_status = sg_name_status
    elif sg_number is not None:
        space_group_status = sg_number_status
    else:
        # Dans ce cas seulement, on pourrait éventuellement
        # inférer le groupe depuis la structure.
        space_group_status = False

    # ------------------------------------------------------------------------
    # GEOMETRIE
    # ------------------------------------------------------------------------

    min_distance = None

    if cell_ok:
        min_distance = minimum_distance_cartesian(
            atoms,
            a,
            b,
            c
        )

    geometry_status = (
        min_distance is not None
        and min_distance >= MIN_DISTANCE
    )

    # ------------------------------------------------------------------------
    # STRUCTURE STATUS
    # ------------------------------------------------------------------------

    structural_checks = [
        formula_status,
        atom_count_status,
        composition_status,
        lattice_status,
        angle_status,
        volume_status,
        geometry_status,
        space_group_status,
    ]

    structure_status = all(structural_checks)

    # ------------------------------------------------------------------------
    # METADATA STATUS
    # ------------------------------------------------------------------------

    # Métadonnées descriptives.
    # Z peut être absent mais correctement inféré depuis la composition.
    # Dans ce cas le CIF reste STRUCTURE PASS mais metadata = PARTIAL.
    metadata_checks = [
        formula_cif is not None,
        cell_ok,
        sg_value is not None,
        sg_number is not None,
    ]

    metadata_complete = all(metadata_checks)

    metadata_status = (
        "COMPLETE"
        if metadata_complete
        else "PARTIAL"
    )

    overall_status = (
        "PASS"
        if structure_status
        else "FAIL"
    )

    # ------------------------------------------------------------------------
    # AFFICHAGE
    # ------------------------------------------------------------------------

    print(f"Formula CIF       : {formula_cif}")
    print(f"Formula expected  : {formula_expected}")
    print(
        "Formula status    : "
        + ("PASS" if formula_status else "FAIL")
    )

    print()
    print(
        f"Atoms             : {len(atoms)} "
        f"(expected {ref['expected_atoms']})"
    )
    print(
        "Atom count status  : "
        + ("PASS" if atom_count_status else "FAIL")
    )

    print()
    print("Composition cellule:")
    print(f"  CIF atoms        : {counts}")
    print(f"  Formula unité    : {expected_counts}")
    print(f"  Z inferred       : {z_inferred}")
    print(f"  Z expected       : {ref['Z']}")

    print()
    print(
        f"Z CIF             : "
        f"{z_cif if z_cif is not None else '[ABSENT]'}"
    )
    print(f"Z mode            : {z_mode}")
    print(
        "Z status           : "
        + ("PASS" if z_status else "FAIL")
    )

    print()
    print(f"Space group CIF   : {sg_value if sg_value else '[ABSENT]'}")
    print(f"Space group number: {sg_number if sg_number else '[ABSENT]'}")
    print(f"Space group mode  : {sg_mode}")
    print(f"Expected          : {ref['space_group']} #{ref['space_group_number']}")
    print(
        "Space group status: "
        + ("PASS" if space_group_status else "FAIL")
    )

    print()
    print("Cell:")
    print(
        f"  a b c           : "
        f"{a:.6f} {b:.6f} {c:.6f}"
        if cell_ok else
        "  [INCOMPLETE]"
    )

    print(
        f"  alpha beta gamma: "
        f"{alpha:.6f} {beta:.6f} {gamma:.6f}"
        if cell_ok else
        "  [INCOMPLETE]"
    )

    if cell_ok:
        print(
            f"  Volume CIF      : {volume:.6f} Å³"
        )
        print(
            f"  Volume published: {ref['volume']:.6f} Å³"
        )
        print(
            f"  Volume diff     : {volume_diff_pct:+.6f}%"
        )

    print(
        "  Lattice status  : "
        + ("PASS" if lattice_status else "FAIL")
    )

    print(
        "  Angle status    : "
        + ("PASS" if angle_status else "FAIL")
    )

    print(
        "  Volume status   : "
        + ("PASS" if volume_status else "FAIL")
    )

    print()
    print(
        f"Minimum distance  : "
        f"{min_distance:.6f} Å"
        if min_distance is not None
        else
        "Minimum distance  : [UNAVAILABLE]"
    )

    print(
        "Geometry status   : "
        + ("PASS" if geometry_status else "FAIL")
    )

    print()
    print(
        "STRUCTURE_STATUS  : "
        + ("PASS" if structure_status else "FAIL")
    )

    print(
        "CIF_METADATA      : "
        + metadata_status
    )

    print(
        "OVERALL           : "
        + overall_status
    )

    rows.append({
        "material": name,
        "formula_cif": formula_cif,
        "formula_expected": formula_expected,
        "atoms": len(atoms),
        "atoms_expected": ref["expected_atoms"],
        "z_cif": "" if z_cif is None else z_cif,
        "z_inferred": "" if z_inferred is None else z_inferred,
        "z_mode": z_mode,
        "z_expected": ref["Z"],
        "space_group_cif": sg_value or "",
        "space_group_expected": ref["space_group"],
        "space_group_number_cif": "" if sg_number is None else int(round(sg_number)),
        "space_group_number_expected": ref["space_group_number"],
        "a": "" if a is None else a,
        "b": "" if b is None else b,
        "c": "" if c is None else c,
        "volume_cif": "" if volume is None else volume,
        "volume_published": ref["volume"],
        "volume_diff_pct": "" if volume_diff_pct is None else volume_diff_pct,
        "min_distance_A": "" if min_distance is None else min_distance,
        "formula_status": "PASS" if formula_status else "FAIL",
        "atom_count_status": "PASS" if atom_count_status else "FAIL",
        "composition_status": "PASS" if composition_status else "FAIL",
        "lattice_status": "PASS" if lattice_status else "FAIL",
        "angle_status": "PASS" if angle_status else "FAIL",
        "volume_status": "PASS" if volume_status else "FAIL",
        "geometry_status": "PASS" if geometry_status else "FAIL",
        "space_group_status": "PASS" if space_group_status else "FAIL",
        "structure_status": "PASS" if structure_status else "FAIL",
        "cif_metadata_status": metadata_status,
        "overall_status": overall_status,
    })


# ============================================================================
# RAPPORT CSV
# ============================================================================

csv_path = REPORT_DIR / "literature_benchmark_cif_audit_v4.csv"

fieldnames = list(rows[0].keys())

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )
    writer.writeheader()
    writer.writerows(rows)

# ============================================================================
# RAPPORT TEXTE
# ============================================================================

txt_path = REPORT_DIR / "literature_benchmark_cif_audit_v4.txt"

n_total = len(rows)
n_struct_pass = sum(
    r["structure_status"] == "PASS"
    for r in rows
)

n_metadata_complete = sum(
    r["cif_metadata_status"] == "COMPLETE"
    for r in rows
)

with txt_path.open("w", encoding="utf-8") as f:

    f.write("=" * 78 + "\n")
    f.write("LITERATURE BENCHMARK CIF AUDIT V4\n")
    f.write("=" * 78 + "\n\n")

    f.write("MODE = READ-ONLY\n")
    f.write("Aucun pw.x\n")
    f.write("Aucun CIF modifié\n\n")

    f.write(
        f"STRUCTURES PASS : {n_struct_pass}/{n_total}\n"
    )

    f.write(
        f"CIF METADATA COMPLETE : "
        f"{n_metadata_complete}/{n_total}\n\n"
    )

    for r in rows:
        f.write("-" * 78 + "\n")
        f.write(f"{r['material']}\n")
        f.write("-" * 78 + "\n")
        f.write(
            f"STRUCTURE_STATUS = {r['structure_status']}\n"
        )
        f.write(
            f"CIF_METADATA_STATUS = {r['cif_metadata_status']}\n"
        )
        f.write(
            f"OVERALL = {r['overall_status']}\n"
        )
        f.write(
            f"Z = {r['z_mode']} / "
            f"CIF={r['z_cif']} / "
            f"INFERRED={r['z_inferred']} / "
            f"EXPECTED={r['z_expected']}\n"
        )
        f.write(
            f"SPACE_GROUP = {r['space_group_cif']} / "
            f"EXPECTED={r['space_group_expected']} "
            f"#{r['space_group_number_expected']}\n"
        )
        f.write(
            f"VOLUME_DIFF = {r['volume_diff_pct']} %\n"
        )
        f.write(
            f"MIN_DISTANCE = {r['min_distance_A']} Å\n"
        )

print()
print("=" * 78)
print("SUMMARY V4")
print("=" * 78)
print(f"CIF total              : {n_total}")
print(f"STRUCTURE PASS         : {n_struct_pass}/{n_total}")
print(f"CIF METADATA COMPLETE  : {n_metadata_complete}/{n_total}")
print()
print(f"[OK] CSV : {csv_path}")
print(f"[OK] TXT : {txt_path}")
print("=" * 78)
