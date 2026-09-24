#!/usr/bin/env python3

from pathlib import Path
import csv
import math
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF_DIR = BASE / "data/literature_benchmarks/cif"
REPORT_DIR = BASE / "reports/literature_benchmarks"

CSV_OUT = REPORT_DIR / "literature_benchmark_cif_audit_v3.csv"
TXT_OUT = REPORT_DIR / "literature_benchmark_cif_audit_v3.txt"

# ============================================================================
# REFERENCE DATA FROM THE PUBLISHED ARTICLES
# ============================================================================

PUBLISHED = {
    "CaPdH3":  {"formula": "CaPdH3",  "sg": "Pm-3m", "a": 3.72,  "volume": 51.46,  "Z": 1},
    "CaRuH3":  {"formula": "CaRuH3",  "sg": "Pm-3m", "a": 3.64,  "volume": 48.21,  "Z": 1},
    "NaPdH3":  {"formula": "NaPdH3",  "sg": "Pm-3m", "a": 3.61,  "volume": 47.08,  "Z": 1},
    "NaRuH3":  {"formula": "NaRuH3",  "sg": "Pm-3m", "a": 3.53,  "volume": 43.87, "Z": 1},
    "SrPdH3":  {"formula": "SrPdH3",  "sg": "Pm-3m", "a": 3.84,  "volume": 56.60,  "Z": 1},
    "SrRuH3":  {"formula": "SrRuH3",  "sg": "Pm-3m", "a": 3.77,  "volume": 53.42, "Z": 1},

    "K2GeH6":  {"formula": "K2GeH6",  "sg": "Fm-3m", "a": 7.968, "volume": 505.991, "Z": 4},
    "K2SnH6":  {"formula": "K2SnH6",  "sg": "Fm-3m", "a": 8.338, "volume": 579.679, "Z": 4},
    "Rb2GeH6": {"formula": "Rb2GeH6", "sg": "Fm-3m", "a": 8.318, "volume": 575.574, "Z": 4},
    "Rb2SnH6": {"formula": "Rb2SnH6", "sg": "Fm-3m", "a": 8.666, "volume": 650.974, "Z": 4},
}

EXPECTED = {
    "CaPdH3":  {"Ca": 1, "Pd": 1, "H": 3},
    "CaRuH3":  {"Ca": 1, "Ru": 1, "H": 3},
    "NaPdH3":  {"Na": 1, "Pd": 1, "H": 3},
    "NaRuH3":  {"Na": 1, "Ru": 1, "H": 3},
    "SrPdH3":  {"Sr": 1, "Pd": 1, "H": 3},
    "SrRuH3":  {"Sr": 1, "Ru": 1, "H": 3},

    "K2GeH6":  {"K": 2, "Ge": 1, "H": 6},
    "K2SnH6":  {"K": 2, "Sn": 1, "H": 6},
    "Rb2GeH6": {"Rb": 2, "Ge": 1, "H": 6},
    "Rb2SnH6": {"Rb": 2, "Sn": 1, "H": 6},
}

LATTICE_TOL = 0.01
VOLUME_TOL = 0.50


def clean(v):
    if v is None:
        return None
    v = v.strip().strip("'").strip('"')
    v = re.sub(r"\([0-9]+\)$", "", v)
    return v


def parse_float(v):
    if v is None:
        return None
    try:
        return float(clean(v))
    except Exception:
        return None


def parse_formula(formula):
    formula = clean(formula or "")
    tokens = re.findall(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)", formula)

    result = {}

    for el, n in tokens:
        value = float(n) if n else 1.0
        result[el] = result.get(el, 0.0) + value

    return result


def normalize_comp(comp):
    return {
        k: int(round(v)) if abs(v - round(v)) < 1e-8 else v
        for k, v in comp.items()
    }


def formula_string(comp):
    out = []

    for el in sorted(comp):
        n = comp[el]

        if abs(n - 1) < 1e-8:
            out.append(el)
        elif abs(n - round(n)) < 1e-8:
            out.append(f"{el}{int(round(n))}")
        else:
            out.append(f"{el}{n}")

    return "".join(out)


def calculate_volume(a, b, c, alpha, beta, gamma):
    ar = math.radians(alpha)
    br = math.radians(beta)
    gr = math.radians(gamma)

    term = (
        1
        - math.cos(ar) ** 2
        - math.cos(br) ** 2
        - math.cos(gr) ** 2
        + 2
        * math.cos(ar)
        * math.cos(br)
        * math.cos(gr)
    )

    return a * b * c * math.sqrt(max(term, 0.0))


def parse_cif(path):
    lines = path.read_text(errors="replace").splitlines()

    tags = {}
    atom_rows = []

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if not line or line.startswith("#"):
            i += 1
            continue

        # --------------------------------------------------------------------
        # LOOP
        # --------------------------------------------------------------------

        if line.lower() == "loop_":

            headers = []
            j = i + 1

            while j < len(lines):
                s = lines[j].strip()

                if not s or s.startswith("#"):
                    j += 1
                    continue

                if s.startswith("_"):
                    headers.append(s.split()[0])
                    j += 1
                    continue

                break

            if headers and any(h.startswith("_atom_site") for h in headers):

                while j < len(lines):

                    s = lines[j].strip()

                    if not s or s.startswith("#"):
                        j += 1
                        continue

                    if s.lower() == "loop_" or s.startswith("_"):
                        break

                    values = s.split()

                    if len(values) >= len(headers):
                        atom_rows.append(
                            dict(zip(headers, values[:len(headers)]))
                        )

                    j += 1

                i = j
                continue

        # --------------------------------------------------------------------
        # SIMPLE TAG
        # --------------------------------------------------------------------

        if line.startswith("_"):
            parts = line.split(None, 1)

            if len(parts) == 2:
                tags[parts[0]] = parts[1].strip()

        i += 1

    return tags, atom_rows


def element_from_row(row):

    value = (
        row.get("_atom_site_type_symbol")
        or row.get("_atom_site_label")
        or ""
    )

    value = clean(value)

    m = re.match(r"([A-Z][a-z]?)", value)

    return m.group(1) if m else None


def scaled_expected(formula, z):
    return {
        el: count * z
        for el, count in formula.items()
    }


# ============================================================================
# START
# ============================================================================

REPORT_DIR.mkdir(parents=True, exist_ok=True)

cifs = sorted(CIF_DIR.glob("*.cif"))

print("=" * 78)
print("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT V3")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier CIF modifié")
print(f"[INFO] CIF trouvés : {len(cifs)}")
print()

results = []

for path in cifs:

    name = path.stem

    if name not in PUBLISHED:
        continue

    ref = PUBLISHED[name]
    expected_formula = EXPECTED[name]

    tags, atoms = parse_cif(path)

    formula_cif = clean(tags.get("_chemical_formula_sum", ""))
    sg = clean(
        tags.get("_symmetry_space_group_name_H-M")
        or tags.get("_space_group_name_H-M_alt")
        or tags.get("_space_group_name_H-M")
        or ""
    )

    z_cif = parse_float(tags.get("_cell_formula_units_Z"))

    a = parse_float(tags.get("_cell_length_a"))
    b = parse_float(tags.get("_cell_length_b"))
    c = parse_float(tags.get("_cell_length_c"))

    alpha = parse_float(tags.get("_cell_angle_alpha")) or 90.0
    beta = parse_float(tags.get("_cell_angle_beta")) or 90.0
    gamma = parse_float(tags.get("_cell_angle_gamma")) or 90.0

    volume = calculate_volume(a, b, c, alpha, beta, gamma)

    # ------------------------------------------------------------------------
    # ATOMIC CONTENT
    # ------------------------------------------------------------------------

    composition = {}

    for row in atoms:

        el = element_from_row(row)

        if el:
            composition[el] = composition.get(el, 0) + 1

    composition = normalize_comp(composition)

    # Formula of one chemical unit
    expected_formula_norm = normalize_comp(expected_formula)

    # Contents expected in the complete conventional cell
    expected_cell = normalize_comp(
        scaled_expected(expected_formula_norm, ref["Z"])
    )

    # ------------------------------------------------------------------------
    # Z
    # ------------------------------------------------------------------------

    z_pass = (
        z_cif is not None
        and abs(z_cif - ref["Z"]) < 1e-8
    )

    # ------------------------------------------------------------------------
    # FORMULA DECLARED
    # ------------------------------------------------------------------------

    formula_declared = normalize_comp(parse_formula(formula_cif))

    formula_declared_pass = (
        formula_declared == expected_formula_norm
    )

    # ------------------------------------------------------------------------
    # CELL CONTENTS
    # ------------------------------------------------------------------------

    cell_composition_pass = (
        composition == expected_cell
    )

    # ------------------------------------------------------------------------
    # ATOM COUNT
    # ------------------------------------------------------------------------

    expected_atoms = sum(expected_cell.values())
    atom_count = len(atoms)

    atom_count_pass = (
        atom_count == expected_atoms
    )

    # ------------------------------------------------------------------------
    # SPACE GROUP
    # ------------------------------------------------------------------------

    sg_norm = (sg or "").replace(" ", "").lower()

    expected_sg_norm = ref["sg"].replace(" ", "").lower()

    sg_pass = (
        sg_norm == expected_sg_norm
        or ref["sg"].lower() in sg_norm
        or sg_norm in ref["sg"].lower()
    )

    # ------------------------------------------------------------------------
    # LATTICE
    # ------------------------------------------------------------------------

    err_a = 100.0 * (a - ref["a"]) / ref["a"]

    lattice_pass = (
        abs(err_a) <= LATTICE_TOL
        and abs(b - ref["a"]) / ref["a"] * 100 <= LATTICE_TOL
        and abs(c - ref["a"]) / ref["a"] * 100 <= LATTICE_TOL
    )

    # ------------------------------------------------------------------------
    # VOLUME
    # ------------------------------------------------------------------------

    err_volume = 100.0 * (volume - ref["volume"]) / ref["volume"]

    volume_pass = abs(err_volume) <= VOLUME_TOL

    # ------------------------------------------------------------------------
    # GEOMETRY
    # ------------------------------------------------------------------------

    geometry_pass = (
        a > 0
        and b > 0
        and c > 0
        and abs(alpha - 90.0) < 1e-6
        and abs(beta - 90.0) < 1e-6
        and abs(gamma - 90.0) < 1e-6
    )

    # ------------------------------------------------------------------------
    # GLOBAL
    # ------------------------------------------------------------------------

    status = (
        "PASS"
        if (
            formula_declared_pass
            and z_pass
            and cell_composition_pass
            and atom_count_pass
            and sg_pass
            and lattice_pass
            and volume_pass
            and geometry_pass
        )
        else "FAIL"
    )

    r = {
        "name": name,
        "published_formula": formula_string(expected_formula_norm),
        "cif_formula": formula_cif,
        "space_group": sg,
        "published_space_group": ref["sg"],
        "Z_cif": z_cif,
        "Z_expected": ref["Z"],
        "atom_count": atom_count,
        "expected_atom_count": expected_atoms,
        "a": a,
        "b": b,
        "c": c,
        "volume_calculated": volume,
        "volume_published": ref["volume"],
        "a_error_percent": err_a,
        "volume_error_percent": err_volume,
        "formula_declared_pass": formula_declared_pass,
        "Z_pass": z_pass,
        "cell_composition_pass": cell_composition_pass,
        "atom_count_pass": atom_count_pass,
        "space_group_pass": sg_pass,
        "lattice_pass": lattice_pass,
        "volume_pass": volume_pass,
        "geometry_pass": geometry_pass,
        "status": status,
    }

    results.append(r)

    print("-" * 78)
    print(f"[CIF] {name}")
    print(f"  Formula publiée        : {r['published_formula']}")
    print(f"  Formula CIF            : {formula_cif}")
    print(f"  Space group CIF        : {sg or '[ABSENT]'}")
    print(f"  Space group publié     : {ref['sg']}")
    print(f"  Z CIF                  : {z_cif}")
    print(f"  Z attendu              : {ref['Z']}")
    print(f"  Atomes                 : {atom_count}")
    print(f"  Atomes attendus        : {expected_atoms}")
    print(f"  Cellule                : a={a:.6f} b={b:.6f} c={c:.6f} Å")
    print(f"  Volume calculé         : {volume:.6f} Å³")
    print(f"  Volume publié          : {ref['volume']:.6f} Å³")
    print(f"  Erreur volume          : {err_volume:+.6f} %")
    print(f"  Erreur a               : {err_a:+.6f} %")
    print(f"  Formula                : {'PASS' if formula_declared_pass else 'FAIL'}")
    print(f"  Z                      : {'PASS' if z_pass else 'FAIL'}")
    print(f"  Cell composition       : {'PASS' if cell_composition_pass else 'FAIL'}")
    print(f"  Atom count             : {'PASS' if atom_count_pass else 'FAIL'}")
    print(f"  Space group            : {'PASS' if sg_pass else 'FAIL'}")
    print(f"  Lattice                : {'PASS' if lattice_pass else 'FAIL'}")
    print(f"  Volume                 : {'PASS' if volume_pass else 'FAIL'}")
    print(f"  Geometry               : {'PASS' if geometry_pass else 'FAIL'}")
    print(f"  STATUS                 : {status}")

# ============================================================================
# REPORT CSV
# ============================================================================

fields = list(results[0].keys()) if results else []

with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

# ============================================================================
# REPORT TXT
# ============================================================================

with TXT_OUT.open("w", encoding="utf-8") as f:

    f.write("=" * 78 + "\n")
    f.write("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT V3\n")
    f.write("=" * 78 + "\n")
    f.write("MODE = READ-ONLY\n")
    f.write("Aucun pw.x\n")
    f.write("Aucun fichier CIF modifié\n\n")

    for r in results:
        f.write("-" * 78 + "\n")
        for k, v in r.items():
            f.write(f"{k}: {v}\n")

    total = len(results)
    passed = sum(r["status"] == "PASS" for r in results)
    failed = total - passed

    f.write("\n")
    f.write("=" * 78 + "\n")
    f.write("SYNTHESE\n")
    f.write("=" * 78 + "\n")
    f.write(f"TOTAL : {total}\n")
    f.write(f"PASS  : {passed}\n")
    f.write(f"FAIL  : {failed}\n")

# ============================================================================
# TERMINAL SUMMARY
# ============================================================================

total = len(results)
passed = sum(r["status"] == "PASS" for r in results)
failed = total - passed

print()
print("=" * 78)
print("SYNTHÈSE")
print("=" * 78)
print(f"TOTAL : {total}")
print(f"PASS  : {passed}")
print(f"FAIL  : {failed}")
print()
print(f"[CSV] {CSV_OUT}")
print(f"[TXT] {TXT_OUT}")
print("=" * 78)
