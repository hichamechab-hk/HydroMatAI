#!/usr/bin/env python3

from pathlib import Path
import re

print("\033c", end="")

print("=" * 78)
print("PHASE 78.59 — AUDIT EXACT INPUTS + RECONSTRUCTION ÉNERGÉTIQUE QE")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier modifié")
print("[INFO] Vérification des inputs 140 Ry / k = 4 à 8")

# ----------------------------------------------------------------------
# Fichiers
# ----------------------------------------------------------------------

FILES = {
    "4x4x4": (
        Path("/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
             "TiFeH2/ecut140_k444.in"),
        Path("/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
             "TiFeH2/ecut140_k444.out"),
    ),
    "5x5x5": (
        Path("/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
             "TiFeH2/ecut140_k555.in"),
        Path("/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
             "TiFeH2/ecut140_k555.out"),
    ),
    "6x6x6": (
        Path("/home/hk/HydroMatAI/calculations/phase78_52_convergence/"
             "TiFeH2/ecut140_k666.in"),
        Path("/home/hk/HydroMatAI/calculations/phase78_52_convergence/"
             "TiFeH2/ecut140_k666.out"),
    ),
    "7x7x7": (
        Path("/home/hk/HydroMatAI/calculations/phase78_55_convergence/"
             "TiFeH2/ecut140_k777.in"),
        Path("/home/hk/HydroMatAI/calculations/phase78_55_convergence/"
             "TiFeH2/ecut140_k777.out"),
    ),
    "8x8x8": (
        Path("/home/hk/HydroMatAI/calculations/phase78_53_convergence/"
             "TiFeH2/ecut140_k888.in"),
        Path("/home/hk/HydroMatAI/calculations/phase78_53_convergence/"
             "TiFeH2/ecut140_k888.out"),
    ),
}

ORDER = ["4x4x4", "5x5x5", "6x6x6", "7x7x7", "8x8x8"]

RY_TO_EV = 13.605693009
NAT = 8


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def read(path):
    return path.read_text(errors="replace")


def first_float(pattern, text):
    m = re.search(pattern, text, re.I | re.M)
    return float(m.group(1)) if m else None


def first_str(pattern, text):
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1) if m else None


def extract_block(text, start_pattern, end_patterns):
    lines = text.splitlines()
    start = None

    for i, line in enumerate(lines):
        if re.search(start_pattern, line, re.I):
            start = i
            break

    if start is None:
        return []

    result = []

    for line in lines[start:]:
        if result and any(
            re.search(p, line, re.I) for p in end_patterns
        ):
            break

        result.append(line)

    return result


def get_param(text, name):
    pattern = (
        rf"^\s*{re.escape(name)}\s*=\s*"
        rf"([^,\n/]+)"
    )
    m = re.search(pattern, text, re.I | re.M)
    if not m:
        return None
    return m.group(1).strip()


def extract_energy_components(text):
    labels = {
        "one_electron":
            r"one-electron contribution\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",

        "hartree":
            r"hartree contribution\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",

        "xc":
            r"xc contribution\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",

        "ewald":
            r"ewald contribution\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",

        "smearing":
            r"smearing contrib\.\s*\(-TS\)\s*=\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    }

    result = {}

    for key, pattern in labels.items():
        matches = re.findall(pattern, text, re.I)
        result[key] = float(matches[-1]) if matches else None

    return result


def extract_total_energy(text):
    # QE imprime généralement :
    # !    total energy              =   -880.xxxxx Ry
    #
    # On accepte différents espaces et éventuels caractères
    # supplémentaires entre '=' et la valeur.
    patterns = [
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",

        r"total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.I)
        if matches:
            return float(matches[-1])

    return None


def extract_fermi(text):
    patterns = [
        r"the Fermi energy is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",

        r"Fermi energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.I)
        if matches:
            return float(matches[-1])

    return None


def extract_kpoints(text):
    # Cherche la ligne "K_POINTS automatic" puis la ligne suivante.
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if re.search(r"K_POINTS\s+automatic", line, re.I):
            if i + 1 < len(lines):
                vals = re.findall(r"\d+", lines[i + 1])
                if len(vals) >= 3:
                    return tuple(map(int, vals[:3]))

    return None


# ----------------------------------------------------------------------
# 1. Inventaire
# ----------------------------------------------------------------------

print()
print("===== 1. INVENTAIRE INPUT / OUTPUT =====")
print("-" * 78)

records = {}

for k in ORDER:
    inp, out = FILES[k]

    print()
    print(f"### {k}")
    print(f"INPUT : {inp}")
    print(f"OUTPUT: {out}")

    if not inp.exists():
        print("[WARN] INPUT absent")
        continue

    if not out.exists():
        print("[WARN] OUTPUT absent")
        continue

    in_text = read(inp)
    out_text = read(out)

    records[k] = {
        "in": in_text,
        "out": out_text,
    }

    print("[OK] INPUT + OUTPUT présents")


# ----------------------------------------------------------------------
# 2. Paramètres exacts des INPUTS
# ----------------------------------------------------------------------

print()
print("===== 2. PARAMÈTRES EXACTS DES INPUTS =====")
print("-" * 78)

param_names = [
    "ecutwfc",
    "ecutrho",
    "occupations",
    "smearing",
    "degauss",
    "nspin",
    "nat",
    "ntyp",
    "prefix",
    "pseudo_dir",
]

for k in ORDER:
    if k not in records:
        continue

    text = records[k]["in"]

    print()
    print(f"### {k}")

    for name in param_names:
        value = get_param(text, name)

        if value is None:
            print(f"{name:12} = ABSENT")
        else:
            print(f"{name:12} = {value}")


# ----------------------------------------------------------------------
# 3. K_POINTS exact
# ----------------------------------------------------------------------

print()
print("===== 3. K_POINTS EXACTS =====")
print("-" * 78)

for k in ORDER:
    if k not in records:
        continue

    kp = extract_kpoints(records[k]["in"])

    if kp:
        print(f"{k:>6} | K_POINTS = {kp[0]} {kp[1]} {kp[2]}")
    else:
        print(f"{k:>6} | K_POINTS = ABSENT")


# ----------------------------------------------------------------------
# 4. Vérification ecutrho / ecutwfc
# ----------------------------------------------------------------------

print()
print("===== 4. AUDIT ecutrho / ecutwfc =====")
print("-" * 78)

for k in ORDER:
    if k not in records:
        continue

    text = records[k]["in"]

    ecutwfc = get_param(text, "ecutwfc")
    ecutrho = get_param(text, "ecutrho")

    try:
        ew = float(ecutwfc)
        er = float(ecutrho)
    except (TypeError, ValueError):
        print(f"{k:>6} | impossible de calculer le ratio")
        continue

    ratio = er / ew
    qe_reference = 4.0 * ew

    print(
        f"{k:>6} | "
        f"ecutwfc={ew:.3f} Ry | "
        f"ecutrho={er:.3f} Ry | "
        f"ratio={ratio:.4f} | "
        f"4×ecutwfc={qe_reference:.3f} Ry"
    )

    if er < qe_reference:
        print(
            f"        [WARN] ecutrho inférieur à 4×ecutwfc "
            f"de {qe_reference - er:.3f} Ry"
        )
    else:
        print("        [OK] ecutrho >= 4×ecutwfc")


# ----------------------------------------------------------------------
# 5. Signature physique commune
# ----------------------------------------------------------------------

print()
print("===== 5. SIGNATURE PHYSIQUE DES CINQ CALCULS =====")
print("-" * 78)

signatures = {}

for k in ORDER:
    if k not in records:
        continue

    text = records[k]["in"]

    signature = {
        "ecutwfc": get_param(text, "ecutwfc"),
        "ecutrho": get_param(text, "ecutrho"),
        "occupations": get_param(text, "occupations"),
        "smearing": get_param(text, "smearing"),
        "degauss": get_param(text, "degauss"),
        "nspin": get_param(text, "nspin"),
        "nat": get_param(text, "nat"),
        "ntyp": get_param(text, "ntyp"),
        "pseudo_dir": get_param(text, "pseudo_dir"),
    }

    signatures[k] = signature

    print(f"{k:>6} | {signature}")


print()
print("----- comparaison des paramètres communs -----")

common_keys = [
    "ecutwfc",
    "ecutrho",
    "occupations",
    "smearing",
    "degauss",
    "nspin",
    "nat",
    "ntyp",
    "pseudo_dir",
]

all_equal = True

for key in common_keys:
    values = {
        signatures[k][key]
        for k in signatures
        if signatures[k][key] is not None
    }

    print(f"{key:12} : {values}")

    if len(values) > 1:
        all_equal = False

if all_equal:
    print("[OK] Tous les paramètres communs sont identiques.")
else:
    print("[WARN] Au moins un paramètre commun diffère.")


# ----------------------------------------------------------------------
# 6. Énergies totales exactes
# ----------------------------------------------------------------------

print()
print("===== 6. ÉNERGIES TOTALES EXACTES =====")
print("-" * 78)

energies = {}

for k in ORDER:
    if k not in records:
        continue

    value = extract_total_energy(records[k]["out"])

    if value is None:
        print(f"{k:>6} | [ABSENT]")
    else:
        energies[k] = value
        print(f"{k:>6} | {value:.10f} Ry")


# ----------------------------------------------------------------------
# 7. Contributions énergétiques
# ----------------------------------------------------------------------

print()
print("===== 7. CONTRIBUTIONS ÉNERGÉTIQUES =====")
print("-" * 78)

components = {}

for k in ORDER:
    if k not in records:
        continue

    c = extract_energy_components(records[k]["out"])
    components[k] = c

    print()
    print(f"### {k}")

    for key, value in c.items():
        if value is None:
            print(f"{key:15} = ABSENT")
        else:
            print(f"{key:15} = {value:.10f} Ry")


# ----------------------------------------------------------------------
# 8. Reconstruction partielle
# ----------------------------------------------------------------------

print()
print("===== 8. RECONSTRUCTION DES CONTRIBUTIONS =====")
print("-" * 78)

for k in ORDER:
    if k not in components or k not in energies:
        continue

    c = components[k]

    required = [
        c["one_electron"],
        c["hartree"],
        c["xc"],
        c["ewald"],
    ]

    print()
    print(f"### {k}")

    if any(v is None for v in required):
        print("[INFO] Termes fondamentaux incomplets.")
        continue

    subtotal = sum(required)
    total = energies[k]
    diff = total - subtotal

    print(f"somme 4 termes = {subtotal:.10f} Ry")
    print(f"total QE        = {total:.10f} Ry")
    print(f"différence      = {diff:+.10f} Ry")
    print(
        f"différence      = "
        f"{diff * RY_TO_EV * 1000 / NAT:+.6f} meV/atome"
    )

    if c["smearing"] is not None:
        print(
            f"(-TS)            = "
            f"{c['smearing']:+.10f} Ry"
        )


# ----------------------------------------------------------------------
# 9. Variation de chaque terme avec k
# ----------------------------------------------------------------------

print()
print("===== 9. VARIATION DES CONTRIBUTIONS AVEC k =====")
print("-" * 78)

for component in [
    "one_electron",
    "hartree",
    "xc",
    "ewald",
    "smearing",
]:

    print()
    print(f"--- {component} ---")

    previous_k = None

    for k in ORDER:
        if k not in components:
            continue

        value = components[k][component]

        if value is None:
            print(f"{k:>6} | ABSENT")
            continue

        if previous_k is None:
            print(f"{k:>6} | {value:+.10f} Ry")
        else:
            previous_value = components[previous_k][component]

            if previous_value is None:
                print(f"{k:>6} | {value:+.10f} Ry")
            else:
                delta = value - previous_value
                mevatom = delta * RY_TO_EV * 1000 / NAT

                print(
                    f"{previous_k} → {k} | "
                    f"Δ = {delta:+.10f} Ry | "
                    f"{mevatom:+.6f} meV/atome"
                )

        previous_k = k


# ----------------------------------------------------------------------
# 10. Fermi energy
# ----------------------------------------------------------------------

print()
print("===== 10. FERMI ENERGY =====")
print("-" * 78)

fermis = {}

for k in ORDER:
    if k not in records:
        continue

    value = extract_fermi(records[k]["out"])

    if value is not None:
        fermis[k] = value
        print(f"{k:>6} | EF = {value:.6f} eV")
    else:
        print(f"{k:>6} | EF ABSENT")


# ----------------------------------------------------------------------
# 11. Nombre de k-points irréductibles
# ----------------------------------------------------------------------

print()
print("===== 11. K-POINTS EFFECTIFS IMPRIMÉS PAR QE =====")
print("-" * 78)

for k in ORDER:
    if k not in records:
        continue

    text = records[k]["out"]

    matches = re.findall(
        r"number of k points\s*=\s*(\d+)",
        text,
        re.I,
    )

    if matches:
        print(
            f"{k:>6} | "
            f"{matches[-1]} k-points après symétrie"
        )
    else:
        print(f"{k:>6} | ABSENT")


# ----------------------------------------------------------------------
# 12. Reconstruction de la différence d'énergie
# ----------------------------------------------------------------------

print()
print("===== 12. DÉCOMPOSITION DES ΔE ENTRE GRILLES =====")
print("-" * 78)

for a, b in zip(ORDER[:-1], ORDER[1:]):

    if a not in components or b not in components:
        continue

    print()
    print(f"### {a} → {b}")

    total_delta = None

    if a in energies and b in energies:
        total_delta = energies[b] - energies[a]

        print(
            f"ΔE total = {total_delta:+.10f} Ry "
            f"= {total_delta * RY_TO_EV * 1000 / NAT:+.6f} meV/atome"
        )

    component_sum = 0.0
    complete = True

    for key in [
        "one_electron",
        "hartree",
        "xc",
        "ewald",
        "smearing",
    ]:

        va = components[a][key]
        vb = components[b][key]

        if va is None or vb is None:
            complete = False
            print(f"{key:15} : ABSENT")
            continue

        delta = vb - va
        component_sum += delta

        print(
            f"{key:15} : "
            f"{delta:+.10f} Ry "
            f"({delta * RY_TO_EV * 1000 / NAT:+.6f} meV/atome)"
        )

    if complete and total_delta is not None:
        residual = total_delta - component_sum

        print(
            f"{'somme termes':15} : "
            f"{component_sum:+.10f} Ry"
        )
        print(
            f"{'résidu':15} : "
            f"{residual:+.10f} Ry "
            f"({residual * RY_TO_EV * 1000 / NAT:+.6f} meV/atome)"
        )


# ----------------------------------------------------------------------
# 13. Diagnostic final
# ----------------------------------------------------------------------

print()
print("===== 13. DIAGNOSTIC FINAL =====")
print("-" * 78)

if all_equal:
    print(
        "[OK] Les paramètres physiques communs sont identiques "
        "entre les cinq calculs."
    )
else:
    print(
        "[WARN] Les calculs ne sont pas strictement identiques "
        "hors maillage k."
    )

if len(energies) == 5:
    print("[OK] 5/5 énergies totales extraites correctement.")
else:
    print(
        f"[WARN] Seulement {len(energies)}/5 énergies totales extraites."
    )

print()
print("[IMPORTANT]")
print("Cette phase ne sélectionne aucune grille k comme convergée.")
print("Elle cherche uniquement à établir si la dispersion observée")
print("est entièrement liée au maillage k et à ses conséquences")
print("sur les contributions électroniques.")

print()
print("=" * 78)
print("PHASE 78.59 TERMINÉE — READ-ONLY")
print("=" * 78)
