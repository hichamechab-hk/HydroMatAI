#!/usr/bin/env python3

from pathlib import Path
import csv
import math
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF_DIR = BASE / "data/literature_benchmarks/cif"
REPORT_DIR = BASE / "reports/literature_benchmarks"

CSV_OUT = REPORT_DIR / "literature_benchmark_cif_audit_v2.csv"
TXT_OUT = REPORT_DIR / "literature_benchmark_cif_audit_v2.txt"

# ============================================================================
# DONNEES PUBLIEES — NE PAS MODIFIER LES CIF
# ============================================================================

PUBLISHED = {
    "CaPdH3":  {"formula": "CaPdH3",  "sg": "Pm-3m", "a": 3.72,  "volume": 51.46,  "atoms": 5},
    "CaRuH3":  {"formula": "CaRuH3",  "sg": "Pm-3m", "a": 3.64,  "volume": 48.21,  "atoms": 5},
    "NaPdH3":  {"formula": "NaPdH3",  "sg": "Pm-3m", "a": 3.61,  "volume": 47.08,  "atoms": 5},
    "NaRuH3":  {"formula": "NaRuH3",  "sg": "Pm-3m", "a": 3.53,  "volume": 43.87,  "atoms": 5},
    "SrPdH3":  {"formula": "SrPdH3",  "sg": "Pm-3m", "a": 3.84,  "volume": 56.60,  "atoms": 5},
    "SrRuH3":  {"formula": "SrRuH3",  "sg": "Pm-3m", "a": 3.77,  "volume": 53.42,  "atoms": 5},

    "K2GeH6":  {"formula": "K2GeH6",  "sg": "Fm-3m", "a": 7.968, "volume": 505.991, "atoms": 36},
    "K2SnH6":  {"formula": "K2SnH6",  "sg": "Fm-3m", "a": 8.338, "volume": 579.679, "atoms": 36},
    "Rb2GeH6": {"formula": "Rb2GeH6", "sg": "Fm-3m", "a": 8.318, "volume": 575.574, "atoms": 36},
    "Rb2SnH6": {"formula": "Rb2SnH6", "sg": "Fm-3m", "a": 8.666, "volume": 650.974, "atoms": 36},
}

EXPECTED_COMPOSITION = {
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

# Les volumes publies des articles sont arrondis independamment.
# On valide donc principalement la cellule reconstruite via a,b,c,angles.
VOLUME_TOL_PERCENT = 0.50
LATTICE_TOL_PERCENT = 0.01

# ============================================================================
# OUTILS
# ============================================================================

def normalize_formula(formula):
    if not formula:
        return ""
    return re.sub(r"[\s'\"_]", "", formula)


def parse_formula(formula):
    """
    Parse simple : CaPdH3, K2GeH6, etc.
    """
    formula = normalize_formula(formula)

    tokens = re.findall(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)", formula)

    result = {}
    reconstructed = ""

    for element, count in tokens:
        n = float(count) if count else 1.0
        result[element] = result.get(element, 0.0) + n

    return result


def formula_string(comp):
    parts = []
    for element in sorted(comp.keys()):
        value = comp[element]

        if abs(value - round(value)) < 1e-8:
            value = int(round(value))

        if value == 1:
            parts.append(element)
        else:
            parts.append(f"{element}{value}")

    return "".join(parts)


def extract_cif(path):
    data = {}
    atom_headers = []
    atom_rows = []

    lines = path.read_text(errors="replace").splitlines()

    in_loop = False
    headers = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.lower() == "loop_":
            in_loop = True
            headers = []
            continue

        if in_loop and stripped.startswith("_"):
            headers.append(stripped.split()[0])
            continue

        if in_loop and headers and not stripped.startswith("_"):
            # Atom loop
            if any(h.startswith("_atom_site_") for h in headers):
                if len(stripped.split()) >= len(headers):
                    values = stripped.split()
                    row = dict(zip(headers, values))
                    atom_rows.append(row)

            continue

        if stripped.startswith("_"):
            parts = stripped.split(None, 1)
            key = parts[0]
            value = parts[1].strip() if len(parts) > 1 else ""
            data[key] = value

    # Deuxième passage robuste pour les tags simples
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("_"):
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                data[parts[0]] = parts[1].strip()

    return data, atom_rows


def clean_value(value):
    if value is None:
        return None

    value = value.strip().strip("'").strip('"')

    # Enlève incertitude cristallographique : 3.720(1) -> 3.720
    value = re.sub(r"\([0-9]+\)$", "", value)

    return value


def get_float(data, key, default=None):
    value = data.get(key)

    if value is None:
        return default

    value = clean_value(value)

    try:
        return float(value)
    except ValueError:
        return default


def calculate_volume(a, b, c, alpha, beta, gamma):
    ar = math.radians(alpha)
    br = math.radians(beta)
    gr = math.radians(gamma)

    term = (
        1
        - math.cos(ar) ** 2
        - math.cos(br) ** 2
        - math.cos(gr) ** 2
        + 2 * math.cos(ar) * math.cos(br) * math.cos(gr)
    )

    return a * b * c * math.sqrt(max(term, 0.0))


def element_from_label(label):
    if not label:
        return None

    m = re.match(r"([A-Z][a-z]?)", label)
    return m.group(1) if m else None


# ============================================================================
# AUDIT
# ============================================================================

REPORT_DIR.mkdir(parents=True, exist_ok=True)

cifs = sorted(CIF_DIR.glob("*.cif"))

print("=" * 78)
print("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT V2")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier CIF modifié")
print(f"[INFO] CIF trouvés : {len(cifs)}")
print()

results = []

for cif in cifs:

    name = cif.stem

    if name not in PUBLISHED:
        print(f"[WARN] Structure non référencée : {name}")
        continue

    pub = PUBLISHED[name]
    expected = EXPECTED_COMPOSITION[name]

    data, atom_rows = extract_cif(cif)

    formula_cif = clean_value(data.get("_chemical_formula_sum", ""))
    sg = clean_value(
        data.get(
            "_symmetry_space_group_name_H-M",
            data.get("_space_group_name_H-M_alt", "")
        )
    )

    a = get_float(data, "_cell_length_a")
    b = get_float(data, "_cell_length_b")
    c = get_float(data, "_cell_length_c")

    alpha = get_float(data, "_cell_angle_alpha", 90.0)
    beta = get_float(data, "_cell_angle_beta", 90.0)
    gamma = get_float(data, "_cell_angle_gamma", 90.0)

    volume = calculate_volume(a, b, c, alpha, beta, gamma)

    # ------------------------------------------------------------------------
    # Composition réelle à partir des sites atomiques explicites
    # ------------------------------------------------------------------------

    composition = {}

    for row in atom_rows:
        label = (
            row.get("_atom_site_type_symbol")
            or row.get("_atom_site_label")
        )

        element = element_from_label(clean_value(label))

        if element:
            composition[element] = composition.get(element, 0) + 1

    formula_expected = formula_string(expected)

    # ------------------------------------------------------------------------
    # Formula
    # ------------------------------------------------------------------------

    formula_sites = formula_string(composition)

    formula_site_pass = composition == expected

    formula_declared = parse_formula(formula_cif)

    formula_declared_pass = formula_declared == expected

    # On valide la reconstruction à partir des sites.
    # Le champ CIF est ensuite signalé séparément.
    formula_status = "PASS" if formula_site_pass else "FAIL"

    # ------------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------------

    composition_pass = composition == expected

    # ------------------------------------------------------------------------
    # Atom count
    # ------------------------------------------------------------------------

    atom_count = len(atom_rows)
    atom_count_pass = atom_count == pub["atoms"]

    # ------------------------------------------------------------------------
    # Lattice
    # ------------------------------------------------------------------------

    err_a = 100.0 * (a - pub["a"]) / pub["a"]

    lattice_pass = abs(err_a) <= LATTICE_TOL_PERCENT

    # ------------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------------

    err_volume = 100.0 * (volume - pub["volume"]) / pub["volume"]

    # IMPORTANT :
    # volume = f(a,b,c,alpha,beta,gamma)
    # et non une valeur indépendante à forcer.
    volume_pass = abs(err_volume) <= VOLUME_TOL_PERCENT

    # ------------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------------

    geometry_pass = (
        abs(alpha - 90.0) < 1e-6
        and abs(beta - 90.0) < 1e-6
        and abs(gamma - 90.0) < 1e-6
        and a > 0
        and b > 0
        and c > 0
    )

    # ------------------------------------------------------------------------
    # Global status
    # ------------------------------------------------------------------------

    status = (
        "PASS"
        if (
            formula_site_pass
            and composition_pass
            and atom_count_pass
            and lattice_pass
            and volume_pass
            and geometry_pass
        )
        else "FAIL"
    )

    result = {
        "name": name,
        "formula_expected": formula_expected,
        "formula_cif": formula_cif,
        "formula_sites": formula_sites,
        "space_group": sg,
        "atom_count": atom_count,
        "expected_atoms": pub["atoms"],
        "a": a,
        "b": b,
        "c": c,
        "volume_calculated": volume,
        "volume_published": pub["volume"],
        "volume_error_percent": err_volume,
        "a_error_percent": err_a,
        "formula_pass": formula_site_pass,
        "declared_formula_pass": formula_declared_pass,
        "composition_pass": composition_pass,
        "atom_count_pass": atom_count_pass,
        "lattice_pass": lattice_pass,
        "volume_pass": volume_pass,
        "geometry_pass": geometry_pass,
        "status": status,
    }

    results.append(result)

    print("-" * 78)
    print(f"[CIF] {name}")
    print(f"  Formula publiée        : {formula_expected}")
    print(f"  Formula CIF déclarée   : {formula_cif}")
    print(f"  Formula sites atomiques: {formula_sites}")
    print(f"  Space group            : {sg}")
    print(f"  Atomes                 : {atom_count}")
    print(f"  Cellule                : a={a:.6f} b={b:.6f} c={c:.6f} Å")
    print(f"  Volume calculé         : {volume:.6f} Å³")
    print(f"  Volume publié          : {pub['volume']:.6f} Å³")
    print(f"  Erreur volume          : {err_volume:+.6f} %")
    print(f"  Erreur a               : {err_a:+.6f} %")
    print(f"  Formula sites          : {'PASS' if formula_site_pass else 'FAIL'}")
    print(f"  Formula CIF déclarée   : {'PASS' if formula_declared_pass else 'CHECK'}")
    print(f"  Composition            : {'PASS' if composition_pass else 'FAIL'}")
    print(f"  Atom count             : {'PASS' if atom_count_pass else 'FAIL'}")
    print(f"  Lattice                : {'PASS' if lattice_pass else 'FAIL'}")
    print(f"  Volume                 : {'PASS' if volume_pass else 'FAIL'}")
    print(f"  Geometry               : {'PASS' if geometry_pass else 'FAIL'}")
    print(f"  STATUS                 : {status}")

# ============================================================================
# RAPPORT CSV
# ============================================================================

fields = list(results[0].keys()) if results else []

with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

# ============================================================================
# RAPPORT TXT
# ============================================================================

with TXT_OUT.open("w", encoding="utf-8") as f:

    f.write("=" * 78 + "\n")
    f.write("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT V2\n")
    f.write("=" * 78 + "\n\n")

    f.write("MODE = READ-ONLY\n")
    f.write("Aucun pw.x\n")
    f.write("Aucun fichier CIF modifié\n\n")

    for r in results:

        f.write("-" * 78 + "\n")
        f.write(f"{r['name']}\n")
        f.write(f"Formula publiée       : {r['formula_expected']}\n")
        f.write(f"Formula CIF déclarée  : {r['formula_cif']}\n")
        f.write(f"Formula sites         : {r['formula_sites']}\n")
        f.write(f"Space group           : {r['space_group']}\n")
        f.write(f"Atom count            : {r['atom_count']}/{r['expected_atoms']}\n")
        f.write(f"a                     : {r['a']:.6f} Å\n")
        f.write(f"Volume calculé        : {r['volume_calculated']:.6f} Å³\n")
        f.write(f"Volume publié         : {r['volume_published']:.6f} Å³\n")
        f.write(f"Erreur volume         : {r['volume_error_percent']:+.6f} %\n")
        f.write(f"Erreur a              : {r['a_error_percent']:+.6f} %\n")
        f.write(f"Formula sites         : {r['formula_pass']}\n")
        f.write(f"Formula CIF déclarée  : {r['declared_formula_pass']}\n")
        f.write(f"Composition           : {r['composition_pass']}\n")
        f.write(f"Atom count            : {r['atom_count_pass']}\n")
        f.write(f"Lattice               : {r['lattice_pass']}\n")
        f.write(f"Volume                : {r['volume_pass']}\n")
        f.write(f"Geometry              : {r['geometry_pass']}\n")
        f.write(f"STATUS                : {r['status']}\n")

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
# SYNTHESE TERMINAL
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
