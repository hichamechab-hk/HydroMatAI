#!/usr/bin/env python3

import csv
import math
import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
CIF_DIR = BASE / "data/literature_benchmarks/cif"
REPORT_DIR = BASE / "reports/literature_benchmarks"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = REPORT_DIR / "literature_benchmark_cif_audit.csv"
OUT_TXT = REPORT_DIR / "literature_benchmark_cif_audit.txt"

# Valeurs publiées extraites des articles fournis.
PUBLISHED = {
    "K2GeH6":  {"a": 7.968, "volume": 505.991, "atoms": 36},
    "K2SnH6":  {"a": 8.338, "volume": 579.679, "atoms": 36},
    "Rb2GeH6": {"a": 8.318, "volume": 575.574, "atoms": 36},
    "Rb2SnH6": {"a": 8.666, "volume": 650.974, "atoms": 36},

    "NaPdH3": {"a": 3.61, "volume": 47.08, "atoms": 5},
    "CaPdH3": {"a": 3.72, "volume": 51.46, "atoms": 5},
    "SrPdH3": {"a": 3.84, "volume": 56.60, "atoms": 5},

    "NaRuH3": {"a": 3.53, "volume": 43.87, "atoms": 5},
    "CaRuH3": {"a": 3.64, "volume": 48.21, "atoms": 5},
    "SrRuH3": {"a": 3.77, "volume": 53.42, "atoms": 5},
}

EXPECTED = {
    "K2GeH6":  {"K": 8, "Ge": 4, "H": 24},
    "K2SnH6":  {"K": 8, "Sn": 4, "H": 24},
    "Rb2GeH6": {"Rb": 8, "Ge": 4, "H": 24},
    "Rb2SnH6": {"Rb": 8, "Sn": 4, "H": 24},

    "NaPdH3": {"Na": 1, "Pd": 1, "H": 3},
    "CaPdH3": {"Ca": 1, "Pd": 1, "H": 3},
    "SrPdH3": {"Sr": 1, "Pd": 1, "H": 3},

    "NaRuH3": {"Na": 1, "Ru": 1, "H": 3},
    "CaRuH3": {"Ca": 1, "Ru": 1, "H": 3},
    "SrRuH3": {"Sr": 1, "Ru": 1, "H": 3},
}


def parse_formula(formula):
    formula = formula.replace(" ", "")
    result = {}

    for elem, count in re.findall(r"([A-Z][a-z]?)([0-9]*)", formula):
        result[elem] = result.get(elem, 0) + (int(count) if count else 1)

    return result


def parse_cif(path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    data = {
        "name": path.stem,
        "formula": None,
        "a": None,
        "b": None,
        "c": None,
        "alpha": None,
        "beta": None,
        "gamma": None,
        "spacegroup": None,
        "number": None,
        "atoms": [],
    }

    for line in lines:
        s = line.strip()

        if s.startswith("_chemical_formula_sum"):
            data["formula"] = s.split(None, 1)[1].strip().strip("'\"")

        elif s.startswith("_cell_length_a"):
            data["a"] = float(s.split()[1])

        elif s.startswith("_cell_length_b"):
            data["b"] = float(s.split()[1])

        elif s.startswith("_cell_length_c"):
            data["c"] = float(s.split()[1])

        elif s.startswith("_cell_angle_alpha"):
            data["alpha"] = float(s.split()[1])

        elif s.startswith("_cell_angle_beta"):
            data["beta"] = float(s.split()[1])

        elif s.startswith("_cell_angle_gamma"):
            data["gamma"] = float(s.split()[1])

        elif s.startswith("_symmetry_space_group_name_H-M_alt"):
            data["spacegroup"] = s.split(None, 1)[1].strip().strip("'\"")

        elif s.startswith("_symmetry_Int_Tables_number"):
            data["number"] = int(s.split()[1])

    # Locate atom loop.
    for i, line in enumerate(lines):
        if line.strip() == "_atom_site_label":
            headers = []
            j = i

            while j < len(lines) and lines[j].strip().startswith("_atom_site_"):
                headers.append(lines[j].strip())
                j += 1

            while j < len(lines):
                s = lines[j].strip()

                if not s or s.startswith("#"):
                    j += 1
                    continue

                if s.startswith("_") or s.startswith("loop_") or s.startswith("data_"):
                    break

                parts = s.split()

                if len(parts) >= len(headers):
                    row = dict(zip(headers, parts))

                    try:
                        atom = {
                            "label": row.get("_atom_site_label"),
                            "element": row.get("_atom_site_type_symbol"),
                            "x": float(row.get("_atom_site_fract_x")),
                            "y": float(row.get("_atom_site_fract_y")),
                            "z": float(row.get("_atom_site_fract_z")),
                        }
                        data["atoms"].append(atom)
                    except (TypeError, ValueError):
                        pass

                j += 1

            break

    return data


def cell_volume(a, b, c, alpha, beta, gamma):
    ar = math.radians(alpha)
    br = math.radians(beta)
    gr = math.radians(gamma)

    factor = (
        1
        + 2 * math.cos(ar) * math.cos(br) * math.cos(gr)
        - math.cos(ar) ** 2
        - math.cos(br) ** 2
        - math.cos(gr) ** 2
    )

    return a * b * c * math.sqrt(max(factor, 0.0))


def frac_distance(atom1, atom2, a, b, c):
    dx = atom1["x"] - atom2["x"]
    dy = atom1["y"] - atom2["y"]
    dz = atom1["z"] - atom2["z"]

    # Minimum image for cubic cells.
    dx -= round(dx)
    dy -= round(dy)
    dz -= round(dz)

    return math.sqrt(
        (dx * a) ** 2 +
        (dy * b) ** 2 +
        (dz * c) ** 2
    )


def analyze(data):
    name = data["name"]
    expected = EXPECTED.get(name, {})

    counts = {}
    for atom in data["atoms"]:
        counts[atom["element"]] = counts.get(atom["element"], 0) + 1

    formula_counts = parse_formula(data["formula"]) if data["formula"] else {}

    volume = None
    if all(
        data[x] is not None
        for x in ["a", "b", "c", "alpha", "beta", "gamma"]
    ):
        volume = cell_volume(
            data["a"], data["b"], data["c"],
            data["alpha"], data["beta"], data["gamma"]
        )

    published = PUBLISHED.get(name, {})
    volume_error = None
    lattice_error = None

    if volume is not None and published:
        volume_error = 100 * (volume - published["volume"]) / published["volume"]

    if data["a"] is not None and published:
        lattice_error = 100 * (data["a"] - published["a"]) / published["a"]

    min_dist = None
    min_pair = None

    atoms = data["atoms"]

    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            d = frac_distance(
                atoms[i],
                atoms[j],
                data["a"],
                data["b"],
                data["c"],
            )

            if d > 1e-8 and (min_dist is None or d < min_dist):
                min_dist = d
                min_pair = (
                    atoms[i]["label"],
                    atoms[j]["label"],
                    atoms[i]["element"],
                    atoms[j]["element"],
                )

    formula_ok = counts == formula_counts

    expected_ok = counts == expected if expected else True

    published_atoms_ok = (
        len(atoms) == published.get("atoms", len(atoms))
    )

    volume_ok = (
        abs(volume_error) < 0.05
        if volume_error is not None
        else False
    )

    lattice_ok = (
        abs(lattice_error) < 0.05
        if lattice_error is not None
        else False
    )

    geometry_ok = min_dist is not None and min_dist > 0.5

    status = "PASS"

    if not formula_ok:
        status = "FAIL_FORMULA"

    elif not expected_ok:
        status = "FAIL_COMPOSITION"

    elif not published_atoms_ok:
        status = "FAIL_ATOM_COUNT"

    elif not lattice_ok:
        status = "FAIL_LATTICE"

    elif not volume_ok:
        status = "FAIL_VOLUME"

    elif not geometry_ok:
        status = "FAIL_GEOMETRY"

    return {
        "name": name,
        "formula": data["formula"],
        "spacegroup": data["spacegroup"],
        "number": data["number"],
        "atoms": len(atoms),
        "a": data["a"],
        "b": data["b"],
        "c": data["c"],
        "volume": volume,
        "published_volume": published.get("volume"),
        "volume_error_pct": volume_error,
        "published_a": published.get("a"),
        "lattice_error_pct": lattice_error,
        "formula_counts": str(formula_counts),
        "atom_counts": str(counts),
        "expected_counts": str(expected),
        "min_distance_A": min_dist,
        "min_pair": str(min_pair),
        "formula_ok": formula_ok,
        "composition_ok": expected_ok,
        "atom_count_ok": published_atoms_ok,
        "lattice_ok": lattice_ok,
        "volume_ok": volume_ok,
        "geometry_ok": geometry_ok,
        "status": status,
    }


files = sorted(CIF_DIR.glob("*.cif"))

print("=" * 78)
print("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier CIF modifié")
print(f"[INFO] CIF trouvés : {len(files)}")
print()

results = []

for path in files:
    data = parse_cif(path)
    result = analyze(data)
    results.append(result)

    print("-" * 78)
    print(f"[CIF] {result['name']}")
    print(f"  Formula       : {result['formula']}")
    print(f"  Space group   : {result['spacegroup']} #{result['number']}")
    print(f"  Atomes        : {result['atoms']}")
    print(
        f"  Cellule       : "
        f"a={result['a']:.6f} "
        f"b={result['b']:.6f} "
        f"c={result['c']:.6f} Å"
    )
    print(f"  Volume        : {result['volume']:.6f} Å³")
    print(f"  Volume publié : {result['published_volume']:.6f} Å³")
    print(f"  Erreur volume : {result['volume_error_pct']:+.6f} %")
    print(f"  Erreur a      : {result['lattice_error_pct']:+.6f} %")
    print(f"  Distance min. : {result['min_distance_A']:.6f} Å")
    print(f"  Formule       : {'PASS' if result['formula_ok'] else 'FAIL'}")
    print(f"  Composition    : {'PASS' if result['composition_ok'] else 'FAIL'}")
    print(f"  Atom count     : {'PASS' if result['atom_count_ok'] else 'FAIL'}")
    print(f"  Lattice        : {'PASS' if result['lattice_ok'] else 'FAIL'}")
    print(f"  Volume         : {'PASS' if result['volume_ok'] else 'FAIL'}")
    print(f"  Geometry       : {'PASS' if result['geometry_ok'] else 'FAIL'}")
    print(f"  STATUS         : {result['status']}")

fieldnames = list(results[0].keys()) if results else []

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

with OUT_TXT.open("w") as f:
    f.write("PHASE LITERATURE BENCHMARK — CIF STRUCTURAL AUDIT\n")
    f.write("=" * 78 + "\n")
    f.write("MODE = READ-ONLY\n")
    f.write("Aucun pw.x exécuté.\n")
    f.write("Aucun CIF scientifique modifié.\n\n")

    for r in results:
        f.write(
            f"{r['name']:12s} "
            f"{r['formula']:10s} "
            f"{r['spacegroup']:8s} "
            f"#{r['number']:<3d} "
            f"N={r['atoms']:<3d} "
            f"V={r['volume']:.3f} "
            f"errV={r['volume_error_pct']:+.4f}% "
            f"errA={r['lattice_error_pct']:+.4f}% "
            f"minD={r['min_distance_A']:.4f} Å "
            f"{r['status']}\n"
        )

    passed = sum(r["status"] == "PASS" for r in results)
    failed = len(results) - passed

    f.write("\n")
    f.write(f"TOTAL = {len(results)}\n")
    f.write(f"PASS  = {passed}\n")
    f.write(f"FAIL  = {failed}\n")

print()
print("=" * 78)
print("SYNTHÈSE")
print("=" * 78)

passed = sum(r["status"] == "PASS" for r in results)
failed = len(results) - passed

print(f"TOTAL : {len(results)}")
print(f"PASS  : {passed}")
print(f"FAIL  : {failed}")
print()
print(f"[CSV] {OUT_CSV}")
print(f"[TXT] {OUT_TXT}")
print("=" * 78)
