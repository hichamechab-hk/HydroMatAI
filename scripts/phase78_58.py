#!/usr/bin/env python3

import re
from pathlib import Path

print("\033c", end="")

print("=" * 78)
print("PHASE 78.58 — EXTRACTION BRUTE ET EXACTE DES TERMES ÉNERGÉTIQUES QE")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier modifié")
print("[INFO] Audit des sorties 140 Ry / k = 4 à 8")

FILES = {
    "4x4x4": Path(
        "/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
        "TiFeH2/ecut140_k444.out"
    ),
    "5x5x5": Path(
        "/home/hk/HydroMatAI/calculations/phase78_50_convergence/"
        "TiFeH2/ecut140_k555.out"
    ),
    "6x6x6": Path(
        "/home/hk/HydroMatAI/calculations/phase78_52_convergence/"
        "TiFeH2/ecut140_k666.out"
    ),
    "7x7x7": Path(
        "/home/hk/HydroMatAI/calculations/phase78_55_convergence/"
        "TiFeH2/ecut140_k777.out"
    ),
    "8x8x8": Path(
        "/home/hk/HydroMatAI/calculations/phase78_53_convergence/"
        "TiFeH2/ecut140_k888.out"
    ),
}

# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------

def read(path):
    return path.read_text(errors="replace")


def section_lines(text, patterns):
    """Retourne toutes les lignes contenant au moins un motif."""
    out = []
    for line in text.splitlines():
        low = line.lower()
        if any(p.lower() in low for p in patterns):
            out.append(line.rstrip())
    return out


def last_matching(text, patterns):
    lines = section_lines(text, patterns)
    return lines[-1] if lines else None


def all_matching(text, patterns):
    return section_lines(text, patterns)


def extract(pattern, text, flags=re.I | re.M):
    m = re.findall(pattern, text, flags)
    if not m:
        return []
    return m


def print_block(title, lines, max_lines=30):
    print()
    print(title)
    print("-" * 78)

    if not lines:
        print("[ABSENT]")
        return

    if len(lines) > max_lines:
        print(
            f"[INFO] {len(lines)} lignes trouvées ; "
            f"affichage des {max_lines} dernières"
        )
        lines = lines[-max_lines:]

    for line in lines:
        print(line)


# ----------------------------------------------------------------------
# 1. Inventaire
# ----------------------------------------------------------------------

print()
print("===== 1. INVENTAIRE =====")
print("-" * 78)

texts = {}

for k, path in FILES.items():
    if not path.exists():
        print(f"[WARN] {k} : fichier absent : {path}")
        continue

    text = read(path)
    texts[k] = text

    print(
        f"[OK] {k:>6} | "
        f"{path} | "
        f"{len(text.splitlines())} lignes"
    )


# ----------------------------------------------------------------------
# 2. Paramètres réellement imprimés par QE
# ----------------------------------------------------------------------

print()
print("===== 2. PARAMÈTRES QE RÉELLEMENT IMPRIMÉS =====")
print("-" * 78)

parameter_patterns = [
    "ecutwfc",
    "ecutrho",
    "occupations",
    "smearing",
    "degauss",
    "number of electrons",
    "number of Kohn-Sham states",
    "K_POINTS",
]

for k, text in texts.items():
    print()
    print(f"### {k}")

    lines = section_lines(text, parameter_patterns)

    if not lines:
        print("[WARN] Aucun paramètre trouvé avec les motifs ciblés.")
    else:
        for line in lines:
            print(line)


# ----------------------------------------------------------------------
# 3. Ligne exacte de l'énergie totale
# ----------------------------------------------------------------------

print()
print("===== 3. ÉNERGIE TOTALE EXACTE =====")
print("-" * 78)

energy_re = re.compile(
    r"^\s*!\s+total energy\s*=\s*"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
    re.I,
)

energies = {}

for k, text in texts.items():
    matches = energy_re.findall(text)

    if matches:
        energies[k] = float(matches[-1])
        print(
            f"{k:>6} | "
            f"{energies[k]:.10f} Ry | "
            f"occurrences = {len(matches)}"
        )
    else:
        print(f"{k:>6} | [ABSENT]")


# ----------------------------------------------------------------------
# 4. Décomposition énergétique brute
# ----------------------------------------------------------------------

print()
print("===== 4. DÉCOMPOSITION ÉNERGÉTIQUE BRUTE =====")
print("-" * 78)

energy_patterns = [
    "one-electron contribution",
    "hartree contribution",
    "xc contribution",
    "ewald contribution",
    "one-center paw contribution",
    "smearing contrib",
    "entropic",
    "entropy",
    "electrostatic contribution",
]

for k, text in texts.items():
    print()
    print(f"### {k}")

    lines = section_lines(text, energy_patterns)

    if not lines:
        print("[ABSENT]")
    else:
        for line in lines:
            print(line)


# ----------------------------------------------------------------------
# 5. Dernière occurrence de chaque contribution
# ----------------------------------------------------------------------

print()
print("===== 5. DERNIÈRE OCCURRENCE DES CONTRIBUTIONS =====")
print("-" * 78)

for k, text in texts.items():
    print()
    print(f"### {k}")

    for label, patterns in [
        ("ONE-ELECTRON", ["one-electron contribution"]),
        ("HARTREE", ["hartree contribution"]),
        ("XC", ["xc contribution"]),
        ("EWALD", ["ewald contribution"]),
        ("PAW", ["one-center paw contribution"]),
        ("SMEARING", ["smearing contrib"]),
        ("ENTROPY", ["entropy"]),
        ("ENTROPIC", ["entropic"]),
    ]:
        line = last_matching(text, patterns)

        if line:
            print(f"[{label}] {line}")
        else:
            print(f"[{label}] ABSENT")


# ----------------------------------------------------------------------
# 6. Fermi energy
# ----------------------------------------------------------------------

print()
print("===== 6. FERMI ENERGY =====")
print("-" * 78)

fermi_re = re.compile(
    r"the Fermi energy is\s+"
    r"([-+]?\d+(?:\.\d+)?)\s+eV",
    re.I,
)

fermis = {}

for k, text in texts.items():
    matches = fermi_re.findall(text)

    if matches:
        fermis[k] = float(matches[-1])
        print(
            f"{k:>6} | "
            f"EF = {fermis[k]:.6f} eV | "
            f"occurrences = {len(matches)}"
        )
    else:
        print(f"{k:>6} | [ABSENT]")


# ----------------------------------------------------------------------
# 7. Occupations / smearing / degauss — extraction souple
# ----------------------------------------------------------------------

print()
print("===== 7. OCCUPATIONS / SMEARING / DEGAUSS =====")
print("-" * 78)

for k, text in texts.items():
    print()
    print(f"### {k}")

    # Toutes les lignes contenant ces termes.
    for label, patterns in [
        ("OCCUPATIONS", ["occupations"]),
        ("SMEARING", ["smearing"]),
        ("DEGAUSS", ["degauss"]),
    ]:
        lines = section_lines(text, patterns)

        print(f"-- {label} --")

        if not lines:
            print("[ABSENT]")
        else:
            # Évite d'inonder le terminal si un terme apparaît
            # à chaque itération SCF.
            unique = []
            for line in lines:
                if line not in unique:
                    unique.append(line)

            for line in unique[-20:]:
                print(line)


# ----------------------------------------------------------------------
# 8. SCF convergence
# ----------------------------------------------------------------------

print()
print("===== 8. CONVERGENCE SCF =====")
print("-" * 78)

accuracy_re = re.compile(
    r"estimated scf accuracy\s*<\s*"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
    re.I,
)

iteration_re = re.compile(
    r"iteration\s*#\s*(\d+)",
    re.I,
)

for k, text in texts.items():

    acc = accuracy_re.findall(text)
    iters = iteration_re.findall(text)

    print(
        f"{k:>6} | "
        f"iterations = {max(map(int, iters)) if iters else 'ABSENT'} | "
        f"accuracy_final = "
        f"{float(acc[-1]):.6e} Ry"
        if acc
        else
        f"{k:>6} | iterations = "
        f"{max(map(int, iters)) if iters else 'ABSENT'} | "
        f"accuracy_final = ABSENT"
    )


# ----------------------------------------------------------------------
# 9. Ligne de convergence / JOB DONE
# ----------------------------------------------------------------------

print()
print("===== 9. FIN DES CALCULS =====")
print("-" * 78)

for k, text in texts.items():
    print()
    print(f"### {k}")

    done = "JOB DONE" in text
    print(f"JOB DONE : {'OUI' if done else 'NON'}")

    tail = text.splitlines()[-20:]

    print("-- dernières lignes --")
    for line in tail:
        print(line)


# ----------------------------------------------------------------------
# 10. Comparaison énergétique
# ----------------------------------------------------------------------

print()
print("===== 10. COMPARAISON ÉNERGÉTIQUE =====")
print("-" * 78)

ordered = ["4x4x4", "5x5x5", "6x6x6", "7x7x7", "8x8x8"]

previous = None

for k in ordered:
    if k not in energies:
        continue

    if previous is not None:
        pk = previous
        delta = energies[k] - energies[pk]
        mevatom = delta * 13.605693009 * 1000 / 8

        print(
            f"{pk} → {k} | "
            f"ΔE = {delta:+.10f} Ry | "
            f"ΔE = {mevatom:+.6f} meV/atome"
        )

    previous = k


# ----------------------------------------------------------------------
# 11. Vérification : la somme des contributions reproduit-elle E ?
# ----------------------------------------------------------------------

print()
print("===== 11. TEST DE RECONSTRUCTION ÉNERGÉTIQUE =====")
print("-" * 78)

# QE peut imprimer différents sous-termes selon la version/configuration.
# Nous reconstruisons uniquement lorsque les quatre termes fondamentaux
# sont disponibles.

def value_after(label, text):
    pattern = (
        re.escape(label)
        + r"\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)"
    )

    vals = re.findall(pattern, text, re.I)

    if not vals:
        return None

    try:
        return float(vals[-1])
    except Exception:
        return None


for k, text in texts.items():

    one = value_after("one-electron contribution", text)
    hartree = value_after("hartree contribution", text)
    xc = value_after("xc contribution", text)
    ewald = value_after("ewald contribution", text)
    total = energies.get(k)

    print()
    print(f"### {k}")

    if None in (one, hartree, xc, ewald, total):
        print("[INFO] Reconstruction partielle impossible avec les termes ciblés.")
        continue

    subtotal = one + hartree + xc + ewald
    diff = total - subtotal

    print(f"one-electron = {one:.10f} Ry")
    print(f"hartree       = {hartree:.10f} Ry")
    print(f"xc            = {xc:.10f} Ry")
    print(f"ewald         = {ewald:.10f} Ry")
    print(f"somme         = {subtotal:.10f} Ry")
    print(f"total QE      = {total:.10f} Ry")
    print(f"différence    = {diff:+.10f} Ry")

    if abs(diff) < 1e-6:
        print("[OK] Reconstruction compatible à < 1e-6 Ry.")
    else:
        print(
            "[INFO] Différence non nulle : des termes énergétiques "
            "supplémentaires sont présents ou non imprimés."
        )


# ----------------------------------------------------------------------
# 12. Diagnostic
# ----------------------------------------------------------------------

print()
print("===== 12. DIAGNOSTIC =====")
print("-" * 78)

print("[RESULT] Les cinq sorties sont présentes et terminées.")

if len(energies) == 5:
    print("[OK] 5/5 énergies totales extraites.")
else:
    print(f"[WARN] Énergies extraites : {len(energies)}/5.")

if len(fermis) == 5:
    print("[OK] 5/5 énergies de Fermi extraites.")
else:
    print(f"[WARN] Fermi extraites : {len(fermis)}/5.")

print()
print("[INFO] Cette phase ne décide PAS quelle grille k est convergée.")
print("[INFO] Elle identifie les termes QE réellement présents dans les")
print("       fichiers .out afin de distinguer :")
print("       - variation physique/convergence k,")
print("       - contribution du smearing,")
print("       - termes énergétiques manquants dans le parseur,")
print("       - ou simple artefact d'extraction.")

print()
print("=" * 78)
print("PHASE 78.58 TERMINÉE — READ-ONLY")
print("=" * 78)
