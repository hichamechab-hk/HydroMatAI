import os
os.system("clear")

from pathlib import Path
import re
import math

print("=" * 78)
print("PHASE 78.45 — GLOBAL NUMERICAL STABILITY AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")
ROOT = BASE / "calculations/new_campaign/TiFeH2"

# ============================================================================
# 1. RECHERCHE DES SORTIES
# ============================================================================

print("1. INVENTAIRE DES SÉRIES NUMÉRIQUES")
print("-" * 78)

series = {
    "CUTOFF": [],
    "KPOINTS": [],
    "SMEARING": [],
}

for path in ROOT.rglob("*.out"):

    name = path.name.lower()

    # ------------------------------------------------------------------------
    # cutoff
    # ------------------------------------------------------------------------
    if "ecut" in name or "cutoff" in str(path).lower():

        m = re.search(
            r"(?:ecutwfc|ecut|cutoff)[_\-]?(\d+(?:\.\d+)?)",
            name,
            re.IGNORECASE,
        )

        if m:
            try:
                value = float(m.group(1))
                series["CUTOFF"].append((value, path))
            except ValueError:
                pass

    # ------------------------------------------------------------------------
    # k-points
    # ------------------------------------------------------------------------
    if "kpoint" in str(path).lower():

        m = re.search(
            r"(\d)x(\d)x(\d)",
            str(path),
        )

        if m:
            kp = tuple(
                int(x)
                for x in m.groups()
            )

            series["KPOINTS"].append((kp, path))

    # ------------------------------------------------------------------------
    # smearing
    # ------------------------------------------------------------------------
    if "smearing" in str(path).lower():

        m = re.search(
            r"(?:smearing|degauss)[_\-]?0?(\d+)[._](\d+)",
            name,
            re.IGNORECASE,
        )

        if m:

            try:
                value = float(
                    "0." + m.group(2)
                )

                series["SMEARING"].append(
                    (value, path)
                )

            except ValueError:
                pass

for key, values in series.items():

    print(
        f"{key:9s} : {len(values)} fichiers détectés"
    )

# ============================================================================
# 2. PARSING QE
# ============================================================================

print()
print("2. EXTRACTION DES VALEURS QE")
print("-" * 78)

def parse_output(path):

    text = path.read_text(errors="replace")

    energy = None
    fermi = None
    converged = "JOB DONE" in text

    energies = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+0-9.eE]+)\s+Ry",
        text,
    )

    if energies:
        energy = float(energies[-1])

    fermis = re.findall(
        r"the Fermi energy is\s+"
        r"([-+0-9.eE]+)\s+ev",
        text,
        re.IGNORECASE,
    )

    if fermis:
        fermi = float(fermis[-1])

    return {
        "path": path,
        "energy": energy,
        "fermi": fermi,
        "converged": converged,
    }


parsed = {
    key: []
    for key in series
}

for key, entries in series.items():

    for label, path in entries:

        result = parse_output(path)

        parsed[key].append(
            (
                label,
                result,
            )
        )

# ============================================================================
# 3. AFFICHAGE DES RÉSULTATS BRUTS
# ============================================================================

for key in ["CUTOFF", "KPOINTS", "SMEARING"]:

    print()
    print(f"3.{['CUTOFF','KPOINTS','SMEARING'].index(key)+1} {key}")
    print("-" * 78)

    for label, result in sorted(
        parsed[key],
        key=lambda x: str(x[0])
    ):

        print(
            f"{str(label):12s} "
            f"E={str(result['energy']):>16s} Ry "
            f"EF={str(result['fermi']):>12s} eV "
            f"JOB_DONE={result['converged']}"
        )

# ============================================================================
# 4. STATISTIQUES
# ============================================================================

print()
print("4. STATISTIQUES DE VARIATION")
print("-" * 78)

def statistics(values):

    values = [
        x for x in values
        if x is not None
    ]

    if not values:
        return None

    mn = min(values)
    mx = max(values)
    spread = mx - mn

    mean = sum(values) / len(values)

    return {
        "min": mn,
        "max": mx,
        "spread": spread,
        "mean": mean,
    }


for key in ["CUTOFF", "KPOINTS", "SMEARING"]:

    energies = [
        result["energy"]
        for _, result in parsed[key]
    ]

    fermis = [
        result["fermi"]
        for _, result in parsed[key]
    ]

    e_stats = statistics(energies)
    f_stats = statistics(fermis)

    print()
    print(f"{key}")

    if e_stats:

        print(
            "  Energie : "
            f"min={e_stats['min']:.8f} Ry "
            f"max={e_stats['max']:.8f} Ry "
            f"spread={e_stats['spread']:.8f} Ry"
        )

    if f_stats:

        print(
            "  EF      : "
            f"min={f_stats['min']:.6f} eV "
            f"max={f_stats['max']:.6f} eV "
            f"spread={f_stats['spread']:.6f} eV"
        )

# ============================================================================
# 5. CRITÈRE NUMÉRIQUE
# ============================================================================

print()
print("5. CRITÈRE DE STABILITÉ")
print("-" * 78)

ENERGY_TOL = 1.0e-4
FERMI_TOL = 1.0e-2

print(
    f"Critère énergie : spread <= {ENERGY_TOL:.1e} Ry"
)
print(
    f"Critère EF       : spread <= {FERMI_TOL:.1e} eV"
)

statuses = {}

for key in ["CUTOFF", "KPOINTS", "SMEARING"]:

    energies = [
        result["energy"]
        for _, result in parsed[key]
        if result["energy"] is not None
    ]

    fermis = [
        result["fermi"]
        for _, result in parsed[key]
        if result["fermi"] is not None
    ]

    e_spread = (
        max(energies) - min(energies)
        if energies else math.inf
    )

    f_spread = (
        max(fermis) - min(fermis)
        if fermis else math.inf
    )

    stable = (
        e_spread <= ENERGY_TOL
        and f_spread <= FERMI_TOL
    )

    statuses[key] = stable

    print()
    print(f"{key}")

    print(
        f"  spread énergie = {e_spread:.8e} Ry"
    )

    print(
        f"  spread EF      = {f_spread:.8e} eV"
    )

    print(
        "  STATUS         = "
        + (
            "NUMERICAL_STABILITY_ESTABLISHED"
            if stable
            else "NUMERICAL_STABILITY_NOT_ESTABLISHED"
        )
    )

# ============================================================================
# 6. CONVERGENCE INDIVIDUELLE
# ============================================================================

print()
print("6. CONVERGENCE INDIVIDUELLE DES CALCULS")
print("-" * 78)

all_jobs = []

for key in ["CUTOFF", "KPOINTS", "SMEARING"]:

    for label, result in parsed[key]:

        all_jobs.append(
            (
                key,
                label,
                result["converged"],
            )
        )

for key, label, done in all_jobs:

    print(
        f"{key:9s} {str(label):12s} "
        f"JOB DONE={'YES' if done else 'NO'}"
    )

print()
print(
    f"Total jobs audités : {len(all_jobs)}"
)

print(
    f"Jobs JOB DONE      : "
    f"{sum(x[2] for x in all_jobs)}/{len(all_jobs)}"
)

# ============================================================================
# 7. SYNTHÈSE
# ============================================================================

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

for key in ["CUTOFF", "KPOINTS", "SMEARING"]:

    print(
        f"{key:9s} : "
        + (
            "ESTABLISHED"
            if statuses[key]
            else "NOT_ESTABLISHED"
        )
    )

all_stable = all(statuses.values())

print()
print(
    "GLOBAL NUMERICAL STABILITY : "
    + (
        "ESTABLISHED"
        if all_stable
        else "NOT_ESTABLISHED"
    )
)

print()
print("[IMPORTANT]")
print(
    "La convergence individuelle JOB DONE ne signifie pas "
    "que la convergence paramétrique est établie."
)
print(
    "Le spread entre les configurations est évalué "
    "séparément."
)
print(
    "Aucune modification de résultat n'est effectuée."
)
print(
    "Aucun calcul QE n'est lancé."
)

print()
print("=" * 78)
print("PHASE 78.45 TERMINÉE — READ-ONLY")
print("=" * 78)
