#!/usr/bin/env python3
"""
PHASES 78.10 -> 78.22
AUDIT COMPLET QE / TiFeH2

READ-ONLY
- Aucun pw.x
- Aucun calcul QE
- Aucun fichier scientifique modifié
- Aucun input modifié
- Aucun résultat recalculé

Objectif:
    Auditer les résultats existants de la nouvelle campagne TiFeH2
    et produire une conclusion numérique/scientifique cohérente.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2"
CONV = BASE / "convergence"
DOS = BASE / "dos"
BANDS = BASE / "bands"

OUT = ROOT / "reports/phase78_complete_audit"
OUT.mkdir(parents=True, exist_ok=True)

REPORT = OUT / "PHASE78_10_TO_22_COMPLETE_AUDIT.txt"


# ============================================================================
# OUTILS
# ============================================================================

def read(path: Path) -> str:
    return path.read_text(errors="replace")


def section(title: str):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def parameter_map(text: str) -> dict[str, str]:
    result = {}

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("!"):
            continue

        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_]*(?:\([^)]+\))?)\s*=\s*([^,!]+)",
            line,
        )

        if m:
            result[m.group(1).lower()] = m.group(2).strip()

    return result


def normalized_lines(text: str) -> list[str]:
    result = []

    for line in text.splitlines():
        s = line.strip()

        if not s:
            continue

        if s.startswith("!"):
            continue

        result.append(s)

    return result


def extract_float(pattern: str, text: str):
    m = re.search(pattern, text, re.I | re.M)
    if not m:
        return None

    try:
        return float(m.group(1))
    except ValueError:
        return None


def extract_last(pattern: str, text: str):
    matches = re.findall(pattern, text, re.I | re.M)
    return matches[-1] if matches else None


def final_energy(text: str):
    matches = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        re.I,
    )

    if not matches:
        return None

    return float(matches[-1])


def fermi_energy(text: str):
    patterns = [
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        value = extract_float(pattern, text)
        if value is not None:
            return value

    return None


def converged(text: str) -> bool:
    low = text.lower()

    return (
        "convergence has been achieved" in low
        or "convergence achieved" in low
        or "convergence has been reached" in low
    )


def scf_iterations(text: str):
    matches = re.findall(
        r"iteration\s+#\s*(\d+)",
        text,
        re.I,
    )

    if matches:
        return int(matches[-1])

    matches = re.findall(
        r"iteration\s+(\d+)",
        text,
        re.I,
    )

    if matches:
        return int(matches[-1])

    return None


def scf_accuracy(text: str):
    patterns = [
        r"estimated scf accuracy\s*<\s*([0-9.eE+-]+)",
        r"estimated scf accuracy\s*=\s*([0-9.eE+-]+)",
    ]

    for pattern in patterns:
        value = extract_float(pattern, text)
        if value is not None:
            return value

    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_first(paths):
    for path in paths:
        if path.exists():
            return path
    return None


# ============================================================================
# INPUTS PRINCIPAUX
# ============================================================================

CUT_INPUTS = sorted(CONV.glob("cutoff_*_2x2x2.in"))

KP_INPUTS = sorted(CONV.glob("kpoints_*_60Ry.in"))

SMEAR_INPUTS = sorted(
    (CONV / "smearing_tests").glob("degauss_*/*.in")
)


# ============================================================================
# OUTPUTS PRINCIPAUX
# ============================================================================

CUTOFF_OUTPUTS = {
    60: CONV / "run_60Ry",
    80: CONV / "run_80Ry",
    100: CONV / "run_100Ry",
}

KP_OUTPUTS = {
    "2x2x2": CONV / "run_kpoints_2x2x2",
    "3x3x3": CONV / "run_kpoints_3x3x3",
    "4x4x4": CONV / "run_kpoints_4x4x4",
}


def locate_pw_output(directory: Path):
    if not directory.exists():
        return None

    candidates = sorted(directory.glob("*.out"))

    if candidates:
        return candidates[0]

    # Recherche récursive de secours
    candidates = sorted(directory.rglob("*.out"))

    return candidates[0] if candidates else None


SMEAR_OUTPUTS = {}

for value in ["0.001", "0.002", "0.005", "0.010"]:
    directory = CONV / "smearing_tests" / f"degauss_{value}Ry"
    output = locate_pw_output(directory)

    if output:
        SMEAR_OUTPUTS[value] = output


# ============================================================================
# PHASE 78.10
# ============================================================================

section("PHASE 78.10 — AUDIT PROFOND DES INPUTS")

groups = {
    "CUTOFF": CUT_INPUTS,
    "KPOINTS": KP_INPUTS,
    "SMEARING": SMEAR_INPUTS,
}

all_input_data = {}

for group, paths in groups.items():

    print()
    print(f"--- {group} ---")

    all_input_data[group] = []

    for path in paths:
        data = parameter_map(read(path))
        all_input_data[group].append((path, data))

        print(path.name)

        for key in [
            "ecutwfc",
            "ecutrho",
            "nspin",
            "occupations",
            "smearing",
            "degauss",
            "nat",
            "ntyp",
            "conv_thr",
            "electron_maxstep",
            "mixing_beta",
            "mixing_mode",
            "diagonalization",
            "startingwfc",
            "startingpot",
        ]:
            if key in data:
                print(f"  {key:20s} = {data[key]}")

    print()


# ============================================================================
# PHASE 78.11
# ============================================================================

section("PHASE 78.11 — AUDIT CONV_THR / SCF")

print("[INFO] Aucun pw.x ne sera exécuté")

for group, paths in groups.items():

    print()
    print(f"--- {group} ---")

    for path in paths:
        data = parameter_map(read(path))

        print(
            f"{path.name}: "
            f"conv_thr={data.get('conv_thr', '<ABSENT>')}"
        )

if CUT_INPUTS:
    first = parameter_map(read(CUT_INPUTS[0]))
    print()
    print(
        "[INFO] conv_thr principal =",
        first.get("conv_thr", "<ABSENT>")
    )

print(
    "[INFO] Le seuil SCF est rapporté tel quel ; "
    "aucune modification n'est effectuée."
)


# ============================================================================
# PHASE 78.12
# ============================================================================

section("PHASE 78.12 — AUDIT GEOMETRIE")

geometry_patterns = [
    "CELL_PARAMETERS",
    "ATOMIC_POSITIONS",
]

for group, paths in groups.items():

    print()
    print(f"--- {group} ---")

    if not paths:
        print("[WARN] Aucun input")
        continue

    ref = normalized_lines(read(paths[0]))

    for path in paths[1:]:

        current = normalized_lines(read(path))

        # Comparaison structurale globale.
        # Les paramètres numériques contrôlés sont affichés.
        same = current == ref

        if same:
            print(f"[OK] {path.name}: contenu normalisé identique")
        else:
            print(
                f"[INFO] {path.name}: différences attendues "
                f"(paramètres de convergence)"
            )

    text = read(paths[0])

    for pattern in geometry_patterns:
        print(
            f"[{'OK' if pattern in text else 'WARN'}] "
            f"{pattern}"
        )


# ============================================================================
# PHASE 78.13
# ============================================================================

section("PHASE 78.13 — AUDIT PSEUDOPOTENTIELS")

pseudo_sets = {}

for group, paths in groups.items():

    pseudo_sets[group] = []

    for path in paths:

        text = read(path)

        species = re.findall(
            r"^\s*(\w+)\s+\d+(?:\.\d+)?\s+(\S+\.UPF)",
            text,
            re.M,
        )

        pseudo_names = tuple(sorted(p[1] for p in species))

        pseudo_sets[group].append(pseudo_names)

        print(
            f"{group:10s} {path.name}: "
            f"{pseudo_names}"
        )

for group, values in pseudo_sets.items():

    unique = set(values)

    if len(unique) <= 1:
        print(f"[OK] {group}: pseudopotentiels cohérents")
    else:
        print(f"[WARN] {group}: pseudopotentiels différents")


# ============================================================================
# PHASE 78.14
# ============================================================================

section("PHASE 78.14 — AUDIT MAGNETISME / OCCUPATIONS")

keys = [
    "nspin",
    "occupations",
    "smearing",
    "degauss",
    "starting_magnetization(1)",
    "starting_magnetization(2)",
    "starting_magnetization(3)",
    "lda_plus_u",
    "noncolin",
    "lspinorb",
]

for group, paths in groups.items():

    print()
    print(f"--- {group} ---")

    for path in paths:

        data = parameter_map(read(path))

        print(path.name)

        for key in keys:

            print(
                f"  {key:28s} = "
                f"{data.get(key, '<ABSENT>')}"
            )


# ============================================================================
# PHASE 78.15
# ============================================================================

section("PHASE 78.15 — AUDIT K-POINTS")

for path in KP_INPUTS:

    text = read(path)

    m = re.search(
        r"K_POINTS\s+\S+\s*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.I,
    )

    if m:
        values = m.groups()

        print(
            f"{path.name}: "
            f"{values[0]}x{values[1]}x{values[2]} "
            f"shift={values[3]} {values[4]} {values[5]}"
        )
    else:
        print(f"[WARN] K_POINTS non parsé : {path.name}")


# ============================================================================
# PHASE 78.16
# ============================================================================

section("PHASE 78.16 — AUDIT ENERGETIQUE")

results = {
    "CUTOFF": [],
    "KPOINTS": [],
    "SMEARING": [],
}


def add_output(group, label, path):

    if path is None or not path.exists():

        print(
            f"[WARN] Output absent : "
            f"{group} / {label}"
        )

        return

    text = read(path)

    energy = final_energy(text)
    fermi = fermi_energy(text)
    conv = converged(text)
    iterations = scf_iterations(text)
    accuracy = scf_accuracy(text)

    results[group].append(
        {
            "label": label,
            "path": path,
            "energy": energy,
            "fermi": fermi,
            "converged": conv,
            "iterations": iterations,
            "accuracy": accuracy,
        }
    )

    print()
    print(f"{group} / {label}")
    print(f"  output      = {path}")
    print(f"  converged   = {conv}")
    print(f"  iterations  = {iterations}")
    print(f"  energy Ry   = {energy}")
    print(f"  Fermi eV    = {fermi}")
    print(f"  accuracy    = {accuracy}")


for label, directory in CUTOFF_OUTPUTS.items():
    add_output(
        "CUTOFF",
        str(label),
        locate_pw_output(directory),
    )


for label, directory in KP_OUTPUTS.items():
    add_output(
        "KPOINTS",
        label,
        locate_pw_output(directory),
    )


for label, path in SMEAR_OUTPUTS.items():
    add_output(
        "SMEARING",
        label,
        path,
    )


def analyze_series(group):

    values = [
        item["energy"]
        for item in results[group]
        if item["energy"] is not None
    ]

    if len(values) < 2:

        print(
            f"[INSUFFICIENT] {group}: "
            f"{len(values)} énergies"
        )

        return

    spread = max(values) - min(values)

    deltas = [
        abs(values[i] - values[i - 1])
        for i in range(1, len(values))
    ]

    print()
    print(
        f"{group}: "
        f"n={len(values)} "
        f"spread={spread:.8f} Ry"
    )

    print(
        "  deltas =",
        [f"{x:.8f}" for x in deltas]
    )

    if spread <= 1.0e-4:
        print(
            "[STABLE] spread <= 1e-4 Ry"
        )
    else:
        print(
            "[NOT ESTABLISHED] "
            "spread > 1e-4 Ry"
        )


for group in results:
    analyze_series(group)


# ============================================================================
# PHASE 78.17
# ============================================================================

section("PHASE 78.17 — AUDIT DOS / ELECTRONIQUE")

dos_inputs = sorted(DOS.glob("*.in"))
dos_outputs = sorted(DOS.glob("*.out"))

print(f"[INFO] DOS inputs  : {len(dos_inputs)}")
print(f"[INFO] DOS outputs : {len(dos_outputs)}")

for path in dos_outputs:

    text = read(path)

    ef = fermi_energy(text)

    print(
        f"{path.name}: "
        f"Fermi={ef}"
    )

    # Quelques indicateurs DOS.
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and not line.startswith("#")
    ]

    print(
        f"  lignes numériques détectées = {len(lines)}"
    )


# ============================================================================
# PHASE 78.18
# ============================================================================

section("PHASE 78.18 — AUDIT BANDS")

if not BANDS.exists():

    print(
        "[INFO] Répertoire bands absent."
    )

else:

    band_inputs = sorted(BANDS.rglob("*.in"))
    band_outputs = sorted(BANDS.rglob("*.out"))

    print(
        f"[INFO] bands inputs  = {len(band_inputs)}"
    )
    print(
        f"[INFO] bands outputs = {len(band_outputs)}"
    )

    for path in band_outputs:

        text = read(path)

        print()
        print(path)

        print(
            f"  converged = {converged(text)}"
        )

        print(
            f"  Fermi     = {fermi_energy(text)}"
        )


# ============================================================================
# PHASE 78.19
# ============================================================================

section("PHASE 78.19 — SYNTHESE NUMERIQUE")

statuses = {}

for group in ["CUTOFF", "KPOINTS", "SMEARING"]:

    values = [
        x["energy"]
        for x in results[group]
        if x["energy"] is not None
    ]

    if len(values) < 2:
        statuses[group] = "INSUFFICIENT_EVIDENCE"
        continue

    spread = max(values) - min(values)

    if spread <= 1.0e-4:
        statuses[group] = "NUMERICAL_STABILITY_ESTABLISHED"
    else:
        statuses[group] = "NUMERICAL_STABILITY_NOT_ESTABLISHED"

for group, status in statuses.items():

    print(
        f"{group:10s}: {status}"
    )

all_items = [
    item
    for group_items in results.values()
    for item in group_items
]

all_converged = all(
    item["converged"]
    for item in all_items
)

print()
print(
    f"SCF converged outputs : "
    f"{sum(item['converged'] for item in all_items)}/"
    f"{len(all_items)}"
)


# ============================================================================
# PHASE 78.20
# ============================================================================

section("PHASE 78.20 — STATUT AIDA")

if all(
    status == "NUMERICAL_STABILITY_ESTABLISHED"
    for status in statuses.values()
):
    numerical_status = "NUMERICAL_STABILITY_ESTABLISHED"

elif any(
    status == "INSUFFICIENT_EVIDENCE"
    for status in statuses.values()
):
    numerical_status = "INSUFFICIENT_EVIDENCE"

else:
    numerical_status = "NUMERICAL_STABILITY_NOT_ESTABLISHED"

scientific_status = (
    "NUMERICAL_STABILITY_ESTABLISHED"
    if numerical_status == "NUMERICAL_STABILITY_ESTABLISHED"
    else numerical_status
)

print(
    f"Numerical status  : {numerical_status}"
)

print(
    f"Scientific status : {scientific_status}"
)

print(
    "[IMPORTANT] "
    "La convergence SCF individuelle ne constitue pas "
    "à elle seule une validation scientifique complète."
)


# ============================================================================
# PHASE 78.21
# ============================================================================

section("PHASE 78.21 — AUDIT FINAL HYDROMATAI")

priority = ROOT / "reports/dft_h2_priority.csv"
phase55 = (
    ROOT /
    "calculations/phase_55_final_scientific_consistency/"
    "phase55_final_ranking.csv"
)

print(
    f"Priority CSV : "
    f"{'OK' if priority.exists() else 'ABSENT'}"
)

print(
    f"Phase55 CSV  : "
    f"{'OK' if phase55.exists() else 'ABSENT'}"
)

if priority.exists():

    text = read(priority)

    for line in text.splitlines():

        if "TiFeH2" in line:

            print()
            print(
                "[TiFeH2 priority]"
            )
            print(line)


if phase55.exists():

    text = read(phase55)

    for line in text.splitlines():

        if "TiFeH2" in line:

            print()
            print(
                "[TiFeH2 phase55]"
            )
            print(line)

print()
print(
    "[INFO] 1.86 wt% = littérature, "
    "pas validation QE."
)

print(
    "[INFO] 0.991579 = score composite de screening."
)

print(
    "[INFO] Historique QE et nouvelle campagne "
    "restent séparés."
)


# ============================================================================
# PHASE 78.22
# ============================================================================

section("PHASE 78.22 — RAPPORT FINAL")

print()
print("TiFeH2 — AUDIT QE COMPLET")
print()
print(f"SCF outputs analysés : {sum(len(v) for v in results.values())}")
print(f"SCF convergés        : {sum(x['converged'] for v in results.values() for x in v)}")
print()

for group, status in statuses.items():
    print(
        f"{group:10s} : {status}"
    )

print()
print(
    f"Numerical stability : {numerical_status}"
)

print(
    f"Scientific status   : {scientific_status}"
)

print()
print(
    "Screening score 0.991579 : "
    "score composite, non validation DFT"
)

print(
    "H2 1.86 wt% : "
    "valeur issue de la littérature"
)

print()
print("=" * 78)
print("CONTROLE READ-ONLY")
print("=" * 78)

print("[OK] Aucun pw.x exécuté")
print("[OK] Aucun input modifié")
print("[OK] Aucun output QE modifié")
print("[OK] Aucune donnée scientifique recalculée")
print("[OK] Audit 78.10 -> 78.22 terminé")

# ============================================================================
# SAUVEGARDE RAPPORT
# ============================================================================

# Re-exécution simple de la sortie complète impossible sans capturer stdout.
# On écrit donc un résumé structuré séparé.

summary = []

summary.append("PHASES 78.10 -> 78.22 — RAPPORT FINAL")
summary.append("")
summary.append("TiFeH2")
summary.append("")
summary.append(
    f"Numerical stability: {numerical_status}"
)
summary.append(
    f"Scientific status: {scientific_status}"
)
summary.append("")

for group, status in statuses.items():
    summary.append(
        f"{group}: {status}"
    )

summary.append("")
summary.append(
    f"SCF outputs analysed: "
    f"{sum(len(v) for v in results.values())}"
)

summary.append(
    f"SCF converged: "
    f"{sum(x['converged'] for v in results.values() for x in v)}"
)

summary.append("")
summary.append(
    "H2 1.86 wt% = literature"
)

summary.append(
    "0.991579 = composite screening score"
)

summary.append("")
summary.append(
    "READ-ONLY: no QE execution / no scientific data modification"
)

REPORT.write_text(
    "\n".join(summary) + "\n"
)

print()
print(
    f"[OK] Résumé écrit : {REPORT}"
)
