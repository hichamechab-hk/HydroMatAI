from __future__ import annotations

import hashlib
import math
import os
import re
import sys
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT = Path("/home/hk/HydroMatAI")

CIF_DIR = (
    ROOT
    / "reports"
    / "m2tih6_reconstructed"
)

TARGETS = {
    "Ba2TiH6": CIF_DIR / "Ba2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
    "Sr2TiH6": CIF_DIR / "Sr2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif",
}


# Tolérances géométriques.
LENGTH_TOL = 1.0e-4
ANGLE_TOL = 1.0e-4
COORD_TOL = 1.0e-8

# Un contact inférieur à cette valeur est signalé.
VERY_SHORT_DISTANCE = 0.70

# Pour la recherche périodique robuste.
IMAGE_RANGE = (-1, 0, 1)


# ============================================================================
# AFFICHAGE
# ============================================================================

def clear_screen() -> None:
    """
    Nettoie le terminal.

    TERM peut être absent ou incorrect dans certains environnements.
    On évite donc de dépendre exclusivement de la commande `clear`.
    """
    try:
        term = os.environ.get("TERM", "")

        if term and term != "unknown":
            os.system("clear")
        else:
            print("\033[2J\033[H", end="")

    except Exception:
        print("\033[2J\033[H", end="")


def separator(char="=", width=78):
    print(char * width)


def section(title):
    print()
    separator("=")
    print(title)
    separator("=")


def info(message):
    print(f"[INFO] {message}")


def ok(message):
    print(f"[OK] {message}")


def warn(message):
    print(f"[WARN] {message}")


def error(message):
    print(f"[ERROR] {message}")


# ============================================================================
# SHA256
# ============================================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


# ============================================================================
# CIF — OUTILS DE PARSING
# ============================================================================

def strip_cif_uncertainty(value: str) -> str:
    """
    Transforme par exemple :

        5.123(4) -> 5.123
        90.00(2) -> 90.00
        -1.234(5) -> -1.234
    """

    value = value.strip()

    # Enlève guillemets simples/doubles.
    value = value.strip("'\"")

    # Incertitude CIF finale.
    value = re.sub(
        r"\([0-9]+\)$",
        "",
        value,
    )

    return value


def clean_cif_value(value: str) -> str:
    value = value.strip()

    # Retirer commentaire inline.
    if "#" in value:
        value = value.split("#", 1)[0].strip()

    return strip_cif_uncertainty(value)


def parse_float(value):
    if value is None:
        return None

    value = clean_cif_value(value)

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def normalize_tag(tag: str) -> str:
    return tag.strip().lower()


def extract_tag(lines, possible_tags):
    """
    Recherche une valeur CIF dans les lignes simples.

    Accepte plusieurs variantes de tag.
    """

    wanted = {
        normalize_tag(tag)
        for tag in possible_tags
    }

    for line in lines:

        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if not stripped.startswith("_"):
            continue

        parts = stripped.split(None, 1)

        if not parts:
            continue

        tag = normalize_tag(parts[0])

        if tag not in wanted:
            continue

        if len(parts) == 1:
            return None

        return clean_cif_value(parts[1])

    return None


# ============================================================================
# CIF — CELLULE
# ============================================================================

def parse_cell(lines):
    tags = {
        "a": [
            "_cell_length_a",
        ],
        "b": [
            "_cell_length_b",
        ],
        "c": [
            "_cell_length_c",
        ],
        "alpha": [
            "_cell_angle_alpha",
        ],
        "beta": [
            "_cell_angle_beta",
        ],
        "gamma": [
            "_cell_angle_gamma",
        ],
    }

    cell = {}

    for key, possible_tags in tags.items():
        raw = extract_tag(lines, possible_tags)
        cell[key] = parse_float(raw)

    return cell


# ============================================================================
# CIF — FORMULE
# ============================================================================

def parse_formula(lines):
    return extract_tag(
        lines,
        [
            "_chemical_formula_sum",
            "_chemical_formula_moiety",
        ],
    )


# ============================================================================
# CIF — GROUPE D'ESPACE
# ============================================================================

def parse_space_group_name(lines):
    return extract_tag(
        lines,
        [
            "_symmetry_space_group_name_H-M",
            "_space_group_name_H-M_alt",
            "_space_group_name_H-M",
        ],
    )


def parse_space_group_number(lines):
    raw = extract_tag(
        lines,
        [
            "_symmetry_Int_Tables_number",
            "_space_group_IT_number",
        ],
    )

    if raw is None:
        return None

    try:
        return int(float(raw))
    except ValueError:
        return None


def normalize_space_group_name(name):
    if not name:
        return ""

    # Normalisation légère uniquement.
    value = name.strip()
    value = value.strip("'\"")
    value = value.replace(" ", "")
    value = value.replace("_", "")
    value = value.lower()

    return value


def is_exact_pm3m_221(name, number):
    """
    Vérification volontairement stricte.

    Pm-3m doit être confirmé par :
        - nom déclaré correspondant à Pm-3m
        ET
        - numéro IT 221 si celui-ci est présent.

    Si le numéro est absent, le nom seul peut être retenu comme
    'nom compatible', mais pas comme confirmation complète #221.
    """

    normalized = normalize_space_group_name(name)

    compatible_name = normalized in {
        "pm-3m",
        "pm3m",
        "p-m-3m",
    }

    if not compatible_name:
        return False

    if number is None:
        return False

    return number == 221


# ============================================================================
# CIF — ATOMES
# ============================================================================

def tokenize_cif_line(line: str):
    """
    Tokenisation simple adaptée aux lignes atomiques CIF.

    Les coordonnées de cette phase sont supposées être des champs
    simples séparés par des espaces.
    """
    return line.strip().split()


def locate_atom_loop(lines):
    """
    Cherche le premier loop_ contenant :

        _atom_site_label
        _atom_site_fract_x
        _atom_site_fract_y
        _atom_site_fract_z

    et éventuellement :

        _atom_site_type_symbol
    """

    i = 0

    while i < len(lines):

        if lines[i].strip().lower() != "loop_":
            i += 1
            continue

        headers = []
        j = i + 1

        while j < len(lines):

            stripped = lines[j].strip()

            if not stripped:
                j += 1
                continue

            if stripped.startswith("_"):
                header = stripped.split()[0]
                headers.append(header)
                j += 1
                continue

            break

        normalized = [
            normalize_tag(h)
            for h in headers
        ]

        required = {
            "_atom_site_fract_x",
            "_atom_site_fract_y",
            "_atom_site_fract_z",
        }

        if (
            "_atom_site_label" in normalized
            and required.issubset(set(normalized))
        ):
            return i, headers, j

        i = j

    return None, None, None


def parse_atoms(lines):
    loop_start, headers, data_start = locate_atom_loop(lines)

    if headers is None:
        return []

    normalized = [
        normalize_tag(h)
        for h in headers
    ]

    def idx(tag):
        try:
            return normalized.index(tag)
        except ValueError:
            return None

    idx_label = idx("_atom_site_label")
    idx_symbol = idx("_atom_site_type_symbol")
    idx_x = idx("_atom_site_fract_x")
    idx_y = idx("_atom_site_fract_y")
    idx_z = idx("_atom_site_fract_z")

    if (
        idx_label is None
        or idx_x is None
        or idx_y is None
        or idx_z is None
    ):
        return []

    atoms = []

    i = data_start

    while i < len(lines):

        stripped = lines[i].strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("#"):
            i += 1
            continue

        # Début d'un nouveau bloc CIF.
        if stripped.lower() == "loop_":
            break

        if stripped.startswith("_"):
            break

        tokens = tokenize_cif_line(lines[i])

        if len(tokens) < len(headers):
            i += 1
            continue

        label = tokens[idx_label]

        if idx_symbol is not None:
            symbol = tokens[idx_symbol]
        else:
            symbol = infer_symbol_from_label(label)

        symbol = normalize_element_symbol(symbol)

        x = parse_float(tokens[idx_x])
        y = parse_float(tokens[idx_y])
        z = parse_float(tokens[idx_z])

        if (
            x is None
            or y is None
            or z is None
        ):
            i += 1
            continue

        atoms.append(
            {
                "label": label,
                "symbol": symbol,
                "x": x,
                "y": y,
                "z": z,
            }
        )

        i += 1

    return atoms


def normalize_element_symbol(value):
    value = clean_cif_value(value)

    # Retire tout ce qui n'est pas alphabétique.
    value = re.sub(
        r"[^A-Za-z]",
        "",
        value,
    )

    if not value:
        return "?"

    if len(value) == 1:
        return value.upper()

    return value[0].upper() + value[1].lower()


def infer_symbol_from_label(label):
    value = re.sub(
        r"[^A-Za-z]",
        "",
        label,
    )

    if not value:
        return "?"

    match = re.match(
        r"[A-Z][a-z]?",
        value,
    )

    if match:
        return match.group(0)

    return "?"


# ============================================================================
# MATHEMATIQUES CRISTALLOGRAPHIQUES
# ============================================================================

def build_lattice_matrix(cell):
    a = cell["a"]
    b = cell["b"]
    c = cell["c"]

    alpha = math.radians(cell["alpha"])
    beta = math.radians(cell["beta"])
    gamma = math.radians(cell["gamma"])

    sin_gamma = math.sin(gamma)

    if abs(sin_gamma) < 1.0e-14:
        raise ValueError(
            "sin(gamma) est trop proche de zéro."
        )

    # Convention :
    # a = (a, 0, 0)
    # b = (bx, by, 0)
    # c = (cx, cy, cz)

    ax = a
    ay = 0.0
    az = 0.0

    bx = b * math.cos(gamma)
    by = b * sin_gamma
    bz = 0.0

    cx = c * math.cos(beta)

    cy = c * (
        math.cos(alpha)
        - math.cos(beta) * math.cos(gamma)
    ) / sin_gamma

    cz_squared = (
        c * c
        - cx * cx
        - cy * cy
    )

    if cz_squared < -1.0e-8:
        raise ValueError(
            f"Paramètres incompatibles : "
            f"cz²={cz_squared}"
        )

    cz = math.sqrt(
        max(0.0, cz_squared)
    )

    return (
        (ax, ay, az),
        (bx, by, bz),
        (cx, cy, cz),
    )


def frac_to_cart(frac, matrix):
    x, y, z = frac

    return (
        x * matrix[0][0]
        + y * matrix[1][0]
        + z * matrix[2][0],

        x * matrix[0][1]
        + y * matrix[1][1]
        + z * matrix[2][1],

        x * matrix[0][2]
        + y * matrix[1][2]
        + z * matrix[2][2],
    )


def vector_norm(v):
    return math.sqrt(
        sum(component * component for component in v)
    )


def distance_periodic(atom1, atom2, matrix):
    """
    Recherche la distance minimale en testant les 27 images
    périodiques voisines.

    Cela évite de dépendre uniquement d'un simple wrapping
    composante par composante dans une maille non orthogonale.
    """

    dx = atom2["x"] - atom1["x"]
    dy = atom2["y"] - atom1["y"]
    dz = atom2["z"] - atom1["z"]

    minimum = None

    for ix in IMAGE_RANGE:
        for iy in IMAGE_RANGE:
            for iz in IMAGE_RANGE:

                df = (
                    dx + ix,
                    dy + iy,
                    dz + iz,
                )

                cart = frac_to_cart(
                    df,
                    matrix,
                )

                d = vector_norm(cart)

                if minimum is None or d < minimum:
                    minimum = d

    return minimum


def calculate_volume(cell):
    a = cell["a"]
    b = cell["b"]
    c = cell["c"]

    alpha = math.radians(cell["alpha"])
    beta = math.radians(cell["beta"])
    gamma = math.radians(cell["gamma"])

    factor = (
        1.0
        + 2.0
        * math.cos(alpha)
        * math.cos(beta)
        * math.cos(gamma)
        - math.cos(alpha) ** 2
        - math.cos(beta) ** 2
        - math.cos(gamma) ** 2
    )

    if factor < -1.0e-10:
        return None

    return (
        a
        * b
        * c
        * math.sqrt(max(0.0, factor))
    )


# ============================================================================
# COMPOSITION
# ============================================================================

def count_elements(atoms):
    counts = {}

    for atom in atoms:
        symbol = atom["symbol"]

        counts[symbol] = (
            counts.get(symbol, 0)
            + 1
        )

    return counts


def gcd_all(values):
    values = [
        int(v)
        for v in values
        if int(v) > 0
    ]

    if not values:
        return 1

    result = values[0]

    for value in values[1:]:
        result = math.gcd(
            result,
            value,
        )

    return result


def reduce_counts(counts):
    if not counts:
        return {}

    divisor = gcd_all(
        counts.values()
    )

    return {
        element: count // divisor
        for element, count in sorted(
            counts.items()
        )
    }


def expected_composition(material):
    if material == "Ba2TiH6":
        return {
            "Ba": 2,
            "Ti": 1,
            "H": 6,
        }

    if material == "Sr2TiH6":
        return {
            "Sr": 2,
            "Ti": 1,
            "H": 6,
        }

    return {}


def stoichiometry_report(material, atoms):
    actual = count_elements(atoms)
    expected = expected_composition(material)

    reduced_actual = reduce_counts(actual)
    reduced_expected = reduce_counts(expected)

    exact = actual == expected
    reduced_match = (
        reduced_actual
        == reduced_expected
    )

    return {
        "actual": actual,
        "expected": expected,
        "reduced_actual": reduced_actual,
        "reduced_expected": reduced_expected,
        "exact": exact,
        "reduced_match": reduced_match,
    }


# ============================================================================
# COORDONNEES
# ============================================================================

def coordinate_report(atoms):
    outside = []

    for atom in atoms:

        for axis in ("x", "y", "z"):

            value = atom[axis]

            if (
                value < -COORD_TOL
                or value >= 1.0 + COORD_TOL
            ):
                outside.append(
                    (
                        atom["label"],
                        axis,
                        value,
                    )
                )

    return outside


# ============================================================================
# METRIQUE CUBIQUE
# ============================================================================

def cubic_report(cell):
    a = cell["a"]
    b = cell["b"]
    c = cell["c"]

    da_b = abs(a - b)
    db_c = abs(b - c)
    da_c = abs(a - c)

    angle_alpha = abs(
        cell["alpha"] - 90.0
    )

    angle_beta = abs(
        cell["beta"] - 90.0
    )

    angle_gamma = abs(
        cell["gamma"] - 90.0
    )

    lengths_ok = (
        da_b <= LENGTH_TOL
        and db_c <= LENGTH_TOL
        and da_c <= LENGTH_TOL
    )

    angles_ok = (
        angle_alpha <= ANGLE_TOL
        and angle_beta <= ANGLE_TOL
        and angle_gamma <= ANGLE_TOL
    )

    return {
        "da_b": da_b,
        "db_c": db_c,
        "da_c": da_c,
        "alpha_dev": angle_alpha,
        "beta_dev": angle_beta,
        "gamma_dev": angle_gamma,
        "lengths_ok": lengths_ok,
        "angles_ok": angles_ok,
        "cubic": lengths_ok and angles_ok,
    }


# ============================================================================
# DISTANCES
# ============================================================================

def calculate_all_distances(atoms, matrix):
    distances = []

    for i in range(len(atoms)):

        for j in range(i + 1, len(atoms)):

            d = distance_periodic(
                atoms[i],
                atoms[j],
                matrix,
            )

            distances.append(
                {
                    "distance": d,
                    "i": i,
                    "j": j,
                    "symbol_i": atoms[i]["symbol"],
                    "symbol_j": atoms[j]["symbol"],
                    "label_i": atoms[i]["label"],
                    "label_j": atoms[j]["label"],
                }
            )

    distances.sort(
        key=lambda item: item["distance"]
    )

    return distances


def pair_key(symbol1, symbol2):
    return tuple(
        sorted(
            (symbol1, symbol2)
        )
    )


def minimum_distance_by_pair(distances):
    result = {}

    for item in distances:

        key = pair_key(
            item["symbol_i"],
            item["symbol_j"],
        )

        if (
            key not in result
            or item["distance"]
            < result[key]["distance"]
        ):
            result[key] = item

    return result


# ============================================================================
# ANALYSE D'UN CIF
# ============================================================================

def analyze_material(material, path):
    section(
        f"M2TiH6.26 — {material}"
    )

    print(f"FILE      : {path}")

    if not path.exists():
        error("Fichier CIF introuvable.")
        return {
            "exists": False,
            "geometry_pass": False,
        }

    if not path.is_file():
        error("Le chemin existe mais n'est pas un fichier.")
        return {
            "exists": False,
            "geometry_pass": False,
        }

    print(
        f"SIZE      : "
        f"{path.stat().st_size} bytes"
    )

    # ------------------------------------------------------------------------
    # SHA256
    # ------------------------------------------------------------------------

    try:
        sha = sha256_file(path)
        print(f"SHA256    : {sha}")
    except Exception as exc:
        warn(
            f"SHA256 impossible : {exc}"
        )
        sha = None

    # ------------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------------

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        error(
            f"Lecture impossible : {exc}"
        )

        return {
            "exists": True,
            "geometry_pass": False,
        }

    lines = text.splitlines()

    # ------------------------------------------------------------------------
    # IDENTITE
    # ------------------------------------------------------------------------

    section(
        f"{material} — IDENTITE CIF"
    )

    formula = parse_formula(lines)
    space_group_name = parse_space_group_name(lines)
    space_group_number = parse_space_group_number(lines)

    print(
        f"FORMULA CIF        : "
        f"{formula if formula else 'NOT DECLARED'}"
    )

    print(
        f"SPACE GROUP NAME   : "
        f"{space_group_name if space_group_name else 'NOT DECLARED'}"
    )

    print(
        f"SPACE GROUP IT     : "
        f"{space_group_number if space_group_number is not None else 'NOT DECLARED'}"
    )

    exact_pm3m = is_exact_pm3m_221(
        space_group_name,
        space_group_number,
    )

    if exact_pm3m:
        ok(
            "Pm-3m #221 explicitement confirmé "
            "par nom + numéro IT."
        )
    else:
        warn(
            "Pm-3m #221 NON confirmé simultanément "
            "par nom + numéro IT."
        )

    # ------------------------------------------------------------------------
    # CELLULE
    # ------------------------------------------------------------------------

    section(
        f"{material} — PARAMETRES DE MAILLE"
    )

    cell = parse_cell(lines)

    for key, unit in [
        ("a", "Å"),
        ("b", "Å"),
        ("c", "Å"),
        ("alpha", "deg"),
        ("beta", "deg"),
        ("gamma", "deg"),
    ]:
        value = cell[key]

        if value is None:
            print(
                f"{key:>6} = NOT FOUND"
            )
        else:
            print(
                f"{key:>6} = "
                f"{value:.10f} {unit}"
            )

    missing = [
        key
        for key, value in cell.items()
        if value is None
    ]

    if missing:
        error(
            "Paramètres de maille manquants : "
            + ", ".join(missing)
        )

        return {
            "exists": True,
            "geometry_pass": False,
            "sha256": sha,
        }

    # ------------------------------------------------------------------------
    # VOLUME
    # ------------------------------------------------------------------------

    section(
        f"{material} — VOLUME"
    )

    try:
        vol = calculate_volume(cell)
    except Exception as exc:
        error(
            f"Calcul du volume impossible : {exc}"
        )
        vol = None

    if vol is None:
        error(
            "Volume non physique / impossible à calculer."
        )
        return {
            "exists": True,
            "geometry_pass": False,
            "sha256": sha,
        }

    print(
        f"VOLUME = {vol:.10f} Å³"
    )

    # ------------------------------------------------------------------------
    # CUBICITE
    # ------------------------------------------------------------------------

    section(
        f"{material} — CONTROLE DE LA METRIQUE CUBIQUE"
    )

    cubic = cubic_report(cell)

    print(
        f"|a-b| = {cubic['da_b']:.10f} Å"
    )

    print(
        f"|b-c| = {cubic['db_c']:.10f} Å"
    )

    print(
        f"|a-c| = {cubic['da_c']:.10f} Å"
    )

    print(
        f"|alpha-90| = "
        f"{cubic['alpha_dev']:.10f} deg"
    )

    print(
        f"|beta-90|  = "
        f"{cubic['beta_dev']:.10f} deg"
    )

    print(
        f"|gamma-90| = "
        f"{cubic['gamma_dev']:.10f} deg"
    )

    if cubic["lengths_ok"]:
        ok(
            "a = b = c à la tolérance métrique."
        )
    else:
        warn(
            "a, b, c ne sont pas égaux à la "
            "tolérance demandée."
        )

    if cubic["angles_ok"]:
        ok(
            "alpha = beta = gamma = 90° "
            "à la tolérance métrique."
        )
    else:
        warn(
            "Les angles ne sont pas tous égaux à 90°."
        )

    if cubic["cubic"]:
        ok(
            "Métrique cristalline compatible "
            "avec une maille cubique."
        )
    else:
        warn(
            "Métrique non cubique."
        )

    # ------------------------------------------------------------------------
    # MATRICE
    # ------------------------------------------------------------------------

    section(
        f"{material} — MATRICE DE MAILLE"
    )

    try:
        matrix = build_lattice_matrix(cell)

        for row in matrix:
            print(
                "  "
                + " ".join(
                    f"{value: .10f}"
                    for value in row
                )
                + " Å"
            )

    except Exception as exc:
        error(
            f"Construction de la matrice impossible : "
            f"{exc}"
        )

        return {
            "exists": True,
            "geometry_pass": False,
            "sha256": sha,
        }

    # ------------------------------------------------------------------------
    # ATOMES
    # ------------------------------------------------------------------------

    section(
        f"{material} — SITES ATOMIQUES"
    )

    atoms = parse_atoms(lines)

    print(
        f"NOMBRE DE SITES LUS = {len(atoms)}"
    )

    if not atoms:
        error(
            "Aucun site atomique exploitable."
        )

        return {
            "exists": True,
            "geometry_pass": False,
            "sha256": sha,
        }

    counts = count_elements(atoms)

    print()
    print("COMPOSITION DES SITES LISTES :")

    for element in sorted(counts):
        print(
            f"  {element:>3} : "
            f"{counts[element]}"
        )

    print()
    print("COORDONNEES FRACTIONNELLES :")

    for atom in atoms:
        print(
            f"  "
            f"{atom['label']:<12} "
            f"{atom['symbol']:>2} "
            f"{atom['x']: .10f} "
            f"{atom['y']: .10f} "
            f"{atom['z']: .10f}"
        )

    # ------------------------------------------------------------------------
    # STOECHIOMETRIE
    # ------------------------------------------------------------------------

    section(
        f"{material} — STOECHIOMETRIE"
    )

    stoich = stoichiometry_report(
        material,
        atoms,
    )

    print(
        f"ATTENDU : "
        f"{stoich['expected']}"
    )

    print(
        f"LU      : "
        f"{stoich['actual']}"
    )

    print(
        f"REDUIT LU : "
        f"{stoich['reduced_actual']}"
    )

    print(
        f"REDUIT ATTENDU : "
        f"{stoich['reduced_expected']}"
    )

    if stoich["exact"]:
        ok(
            "La composition atomique listée correspond "
            "exactement à la formule cible."
        )
    elif stoich["reduced_match"]:
        warn(
            "La stœchiométrie réduite correspond à la "
            "formule cible, mais le nombre de sites listés "
            "n'est pas celui d'une unité formule complète."
        )
    else:
        warn(
            "La stœchiométrie des sites listés "
            "ne correspond pas à la cible."
        )

    # ------------------------------------------------------------------------
    # COORDONNEES
    # ------------------------------------------------------------------------

    section(
        f"{material} — CONTROLE DES COORDONNEES"
    )

    outside = coordinate_report(atoms)

    if not outside:
        ok(
            "Toutes les coordonnées sont dans [0,1)."
        )
    else:
        warn(
            f"{len(outside)} coordonnées hors "
            "de [0,1) détectées."
        )

        for label, axis, value in outside[:20]:
            print(
                f"  {label:<12} "
                f"{axis} = {value}"
            )

    # ------------------------------------------------------------------------
    # DISTANCES
    # ------------------------------------------------------------------------

    section(
        f"{material} — DISTANCES PERIODIQUES"
    )

    distances = calculate_all_distances(
        atoms,
        matrix,
    )

    if not distances:
        warn(
            "Aucune paire atomique disponible."
        )
    else:

        print(
            "15 plus petites distances "
            "interatomiques :"
        )

        for item in distances[:15]:

            print(
                f"  "
                f"{item['symbol_i']}({item['label_i']})"
                f" - "
                f"{item['symbol_j']}({item['label_j']})"
                f" : "
                f"{item['distance']:.6f} Å"
            )

        very_short = [
            item
            for item in distances
            if item["distance"]
            < VERY_SHORT_DISTANCE
        ]

        print()

        if very_short:
            warn(
                f"{len(very_short)} contact(s) "
                f"< {VERY_SHORT_DISTANCE:.2f} Å."
            )

            for item in very_short[:20]:
                print(
                    f"  {item['symbol_i']}({item['label_i']})"
                    f" - "
                    f"{item['symbol_j']}({item['label_j']})"
                    f" = "
                    f"{item['distance']:.6f} Å"
                )
        else:
            ok(
                f"Aucun contact < "
                f"{VERY_SHORT_DISTANCE:.2f} Å."
            )

        pair_minima = minimum_distance_by_pair(
            distances
        )

        print()
        print(
            "DISTANCES MINIMALES PAR TYPE DE PAIRE :"
        )

        for pair in sorted(pair_minima):

            item = pair_minima[pair]

            print(
                f"  "
                f"{pair[0]}-{pair[1]} : "
                f"{item['distance']:.6f} Å"
            )

    # ------------------------------------------------------------------------
    # CONTROLE SPECIFIQUE Ti-H
    # ------------------------------------------------------------------------

    section(
        f"{material} — CONTROLE Ti-H"
    )

    ti_h = [
        item
        for item in distances
        if (
            (
                item["symbol_i"] == "Ti"
                and item["symbol_j"] == "H"
            )
            or
            (
                item["symbol_i"] == "H"
                and item["symbol_j"] == "Ti"
            )
        )
    ]

    if ti_h:
        ti_h.sort(
            key=lambda item: item["distance"]
        )

        print(
            f"Distance Ti-H minimale = "
            f"{ti_h[0]['distance']:.6f} Å"
        )

        print(
            "Premières distances Ti-H :"
        )

        for item in ti_h[:12]:
            print(
                f"  "
                f"{item['label_i']} - "
                f"{item['label_j']} : "
                f"{item['distance']:.6f} Å"
            )
    else:
        warn(
            "Aucune paire Ti-H détectée "
            "dans les sites explicitement listés."
        )

    # ------------------------------------------------------------------------
    # CONTROLE H-H
    # ------------------------------------------------------------------------

    section(
        f"{material} — CONTROLE H-H"
    )

    h_h = [
        item
        for item in distances
        if (
            item["symbol_i"] == "H"
            and item["symbol_j"] == "H"
        )
    ]

    if h_h:
        h_h.sort(
            key=lambda item: item["distance"]
        )

        print(
            f"Distance H-H minimale = "
            f"{h_h[0]['distance']:.6f} Å"
        )

        for item in h_h[:12]:
            print(
                f"  "
                f"{item['label_i']} - "
                f"{item['label_j']} : "
                f"{item['distance']:.6f} Å"
            )
    else:
        warn(
            "Aucune paire H-H détectée."
        )

    # ------------------------------------------------------------------------
    # DECLARATION DE PROVENANCE
    # ------------------------------------------------------------------------

    section(
        f"{material} — PROVENANCE"
    )

    print(
        "STATUS FICHIER : "
        "RECONSTRUCTED / NOT PUBLISHED"
    )

    print(
        "IMPORTANT : ce statut provient du nom et du "
        "contexte du fichier ; l'audit géométrique "
        "ne transforme pas une reconstruction en "
        "structure publiée."
    )

    print(
        "IMPORTANT : la présence de Pm-3m dans d'autres "
        "fichiers du dépôt n'est pas utilisée comme "
        "preuve de symétrie pour ce CIF."
    )

    # ------------------------------------------------------------------------
    # CONSOLIDATION
    # ------------------------------------------------------------------------

    section(
        f"{material} — CONSOLIDATION"
    )

    # Un PASS géométrique nécessite :
    # 1. cellule complète
    # 2. volume calculable
    # 3. sites présents
    # 4. stœchiométrie réduite correcte
    # 5. coordonnées valides
    # 6. métrique cubique
    #
    # Pm-3m #221 est reporté séparément.
    #
    # On ne force PAS Pm-3m comme condition géométrique,
    # car une structure peut avoir une métrique cubique
    # sans que le CIF ait correctement déclaré son groupe
    # d'espace.

    geometry_conditions = {
        "CELL_COMPLETE": not missing,
        "VOLUME_VALID": vol is not None,
        "ATOMS_PRESENT": len(atoms) > 0,
        "STOICHIOMETRY_REDUCED": stoich["reduced_match"],
        "COORDINATES_VALID": not outside,
        "CUBIC_METRIC": cubic["cubic"],
    }

    for name, status in geometry_conditions.items():
        print(
            f"[{'OK' if status else 'WARN'}] "
            f"{name}"
        )

    geometry_pass = all(
        geometry_conditions.values()
    )

    print()

    if geometry_pass:
        ok(
            f"{material} = GEOMETRY PASS"
        )
    else:
        warn(
            f"{material} = GEOMETRY REVIEW"
        )

    print()

    print(
        "SYMMETRY DECLARATION : "
        + (
            "Pm-3m #221 CONFIRMED"
            if exact_pm3m
            else "Pm-3m #221 NOT CONFIRMED"
        )
    )

    print(
        "PROVENANCE            : "
        "RECONSTRUCTED / NOT PUBLISHED"
    )

    return {
        "exists": True,
        "geometry_pass": geometry_pass,
        "sha256": sha,
        "formula": formula,
        "space_group_name": space_group_name,
        "space_group_number": space_group_number,
        "pm3m_221": exact_pm3m,
        "cell": cell,
        "volume": vol,
        "atoms": len(atoms),
        "composition": counts,
        "stoichiometry": stoich,
        "cubic": cubic["cubic"],
        "short_contacts": [
            item
            for item in distances
            if item["distance"]
            < VERY_SHORT_DISTANCE
        ],
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    clear_screen()

    separator("=")
    print(
        "M2TiH6.26 — AUDIT GEOMETRIQUE "
        "Ba2TiH6 / Sr2TiH6"
    )
    separator("=")

    print()
    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun calcul DFT")
    print("[INFO] Aucun fichier scientifique modifié")
    print("[INFO] Aucun CIF généré")
    print("[INFO] Aucun fichier de rapport écrit")
    print()

    print(
        f"[ROOT] {ROOT}"
    )

    print(
        f"[CIF ] {CIF_DIR}"
    )

    # ------------------------------------------------------------------------
    # Vérification du dépôt
    # ------------------------------------------------------------------------

    if not ROOT.exists():
        error(
            f"Répertoire ROOT introuvable : {ROOT}"
        )
        return 1

    if not CIF_DIR.exists():
        error(
            f"Répertoire CIF introuvable : {CIF_DIR}"
        )
        return 1

    # ------------------------------------------------------------------------
    # Inventaire
    # ------------------------------------------------------------------------

    section(
        "M2TiH6.26 — INVENTAIRE DES CIBLES"
    )

    for material, path in TARGETS.items():

        if path.exists():
            ok(
                f"{material} : {path.name}"
            )
        else:
            error(
                f"{material} : fichier absent"
            )

    # ------------------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------------------

    results = {}

    for material, path in TARGETS.items():

        try:
            results[material] = analyze_material(
                material,
                path,
            )

        except Exception as exc:

            error(
                f"{material} : exception inattendue : "
                f"{type(exc).__name__}: {exc}"
            )

            results[material] = {
                "exists": path.exists(),
                "geometry_pass": False,
            }

    # ------------------------------------------------------------------------
    # CONSOLIDATION GLOBALE
    # ------------------------------------------------------------------------

    section(
        "M2TiH6.26 — CONSOLIDATION GLOBALE"
    )

    for material in TARGETS:

        result = results.get(
            material,
            {},
        )

        geometry_pass = result.get(
            "geometry_pass",
            False,
        )

        pm3m = result.get(
            "pm3m_221",
            False,
        )

        print(
            f"{material:<10} "
            f"| GEOMETRY = "
            f"{'PASS' if geometry_pass else 'REVIEW':<6} "
            f"| Pm-3m #221 = "
            f"{'YES' if pm3m else 'NO'}"
        )

    print()

    print(
        "======================================================================"
    )
    print(
        "INTERPRETATION STRICTE"
    )
    print(
        "======================================================================"
    )

    print(
        "[1] GEOMETRY PASS signifie uniquement que les "
        "contrôles géométriques définis ici sont cohérents."
    )

    print(
        "[2] GEOMETRY PASS ne signifie PAS que la structure "
        "est publiée ou expérimentalement démontrée."
    )

    print(
        "[3] Pm-3m #221 n'est confirmé que si le CIF fournit "
        "le nom compatible ET le numéro IT 221."
    )

    print(
        "[4] Une occurrence de Pm-3m dans un autre fichier "
        "du dépôt n'est pas utilisée comme preuve."
    )

    print(
        "[5] Les distances sont calculées à partir des sites "
        "explicitement présents dans le CIF."
    )

    print(
        "[6] Si le CIF est une représentation réduite, "
        "l'absence de tous les sites de la maille complète "
        "n'est pas interprétée automatiquement comme une erreur."
    )

    print(
        "[7] Aucun calcul QE n'a été effectué."
    )

    print(
        "[8] Aucun fichier scientifique n'a été modifié."
    )

    print(
        "[9] Les deux structures restent classées "
        "RECONSTRUCTED / NOT PUBLISHED."
    )

    print()
    separator("=")
    print(
        "M2TiH6.26 — FIN"
    )
    separator("=")

    return 0


if __name__ == "__main__":
    sys.exit(main())
