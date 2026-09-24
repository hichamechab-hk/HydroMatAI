import os
os.system("clear")

from pathlib import Path
import re

print("=" * 78)
print("PHASE 78.46 — CORRECTED NUMERICAL STABILITY AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")
ROOT = BASE / "calculations/new_campaign/TiFeH2"

ENERGY_TOL = 1.0e-4
FERMI_TOL = 1.0e-2

# ============================================================================
# INVENTAIRE CIBLE
# ============================================================================

print("1. INVENTAIRE CIBLÉ")
print("-" * 78)

all_outputs = list(ROOT.rglob("*.out"))

print(f"Total *.out trouvés : {len(all_outputs)}")

# Exclusion explicite des sorties auxiliaires déjà identifiées.
EXCLUDED = [
    "kpoints_smearing_0.002Ry",
]

def is_excluded(path):
    s = str(path)
    return any(x in s for x in EXCLUDED)

usable = [
    p for p in all_outputs
    if not is_excluded(p)
]

print(
    f"Sorties après exclusion auxiliaires : "
    f"{len(usable)}"
)

# ============================================================================
# EXTRACTION
# ============================================================================

def parse(path):

    text = path.read_text(errors="replace")

    energies = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+0-9.eE]+)\s+Ry",
        text,
    )

    fermis = re.findall(
        r"the Fermi energy is\s+"
        r"([-+0-9.eE]+)\s+ev",
        text,
        re.IGNORECASE,
    )

    return {
        "path": path,
        "energy": float(energies[-1]) if energies else None,
        "fermi": float(fermis[-1]) if fermis else None,
        "job_done": "JOB DONE" in text,
    }

parsed = {
    p: parse(p)
    for p in usable
}

# ============================================================================
# IDENTIFICATION PAR PARAMÈTRES RÉELS DU FICHIER
# ============================================================================

def get_float(text, key):

    m = re.search(
        rf"\b{re.escape(key)}\s*=\s*"
        rf"([-+]?[0-9]*\.?[0-9]+(?:[dDeE][-+]?[0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if not m:
        return None

    value = m.group(1).replace("d", "e").replace("D", "E")

    return float(value)


def get_kpoints(text):

    m = re.search(
        r"K_POINTS\s+automatic\s*"
        r".*?\n\s*(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not m:
        return None

    return tuple(
        int(x)
        for x in m.groups()
    )


# ============================================================================
# CLASSIFICATION STRICTE
# ============================================================================

cutoff = []
kpoints = []
smearing = []

for path, result in parsed.items():

    text = path.read_text(errors="replace")

    ecut = get_float(text, "ecutwfc")
    degauss = get_float(text, "degauss")
    kp = get_kpoints(text)

    # Série cutoff : valeurs 60/80/100 Ry
    if (
        ecut in {60.0, 80.0, 100.0}
        and kp == (2, 2, 2)
        and degauss == 0.01
    ):
        cutoff.append((ecut, result))

    # Série k-points : 2/3/4, paramètres de référence
    if (
        ecut == 60.0
        and kp in {
            (2, 2, 2),
            (3, 3, 3),
            (4, 4, 4),
        }
        and degauss == 0.01
    ):
        kpoints.append((kp, result))

    # Série smearing : 0.001/0.002/0.005/0.010
    if (
        ecut == 60.0
        and kp == (2, 2, 2)
        and degauss in {
            0.001,
            0.002,
            0.005,
            0.010,
        }
    ):
        smearing.append((degauss, result))

# ============================================================================
# DÉDUPLICATION PAR IDENTIFIANT PHYSIQUE
# ============================================================================

def unique_by_label(entries):

    out = {}

    for label, result in entries:

        if label not in out:
            out[label] = result
            continue

        # Si doublon exact, on conserve une seule entrée.
        old = out[label]

        if (
            old["energy"] == result["energy"]
            and old["fermi"] == result["fermi"]
        ):
            continue

        print(
            "[WARN] Conflit pour",
            label,
            result["path"],
        )

    return sorted(
        out.items(),
        key=lambda x: str(x[0]),
    )


cutoff = unique_by_label(cutoff)
kpoints = unique_by_label(kpoints)
smearing = unique_by_label(smearing)

# ============================================================================
# 2. RÉSULTATS CIBLÉS
# ============================================================================

print()
print("2. SÉRIES PRINCIPALES RETENUES")
print("-" * 78)

groups = {
    "CUTOFF": cutoff,
    "KPOINTS": kpoints,
    "SMEARING": smearing,
}

for name, entries in groups.items():

    print()
    print(name)

    for label, result in entries:

        print(
            f"  {str(label):12s} "
            f"E={result['energy']} Ry "
            f"EF={result['fermi']} eV "
            f"JOB_DONE={result['job_done']}"
        )

# ============================================================================
# 3. CONTRÔLE DU NOMBRE ATTENDU
# ============================================================================

print()
print("3. CONTRÔLE DU NOMBRE DE CALCULS")
print("-" * 78)

expected = {
    "CUTOFF": 3,
    "KPOINTS": 3,
    "SMEARING": 4,
}

counts_ok = True

for name, entries in groups.items():

    n = len(entries)
    exp = expected[name]

    ok = n == exp

    print(
        f"{name:9s} : {n}/{exp} "
        f"{'[OK]' if ok else '[ERROR]'}"
    )

    if not ok:
        counts_ok = False

if not counts_ok:
    raise SystemExit(
        "[ERROR] Le filtrage ne retrouve pas exactement "
        "les séries principales attendues."
    )

# ============================================================================
# 4. STATISTIQUES
# ============================================================================

print()
print("4. SPREADS")
print("-" * 78)

statuses = {}

for name, entries in groups.items():

    energies = [
        r["energy"]
        for _, r in entries
        if r["energy"] is not None
    ]

    fermis = [
        r["fermi"]
        for _, r in entries
        if r["fermi"] is not None
    ]

    e_spread = max(energies) - min(energies)
    f_spread = max(fermis) - min(fermis)

    stable = (
        e_spread <= ENERGY_TOL
        and f_spread <= FERMI_TOL
    )

    statuses[name] = stable

    print()
    print(name)

    print(
        f"  Energie min/max : "
        f"{min(energies):.8f} / {max(energies):.8f} Ry"
    )

    print(
        f"  Spread énergie  : "
        f"{e_spread:.8f} Ry"
    )

    print(
        f"  EF min/max      : "
        f"{min(fermis):.6f} / {max(fermis):.6f} eV"
    )

    print(
        f"  Spread EF       : "
        f"{f_spread:.6f} eV"
    )

    print(
        "  STATUS           : "
        + (
            "NUMERICAL_STABILITY_ESTABLISHED"
            if stable
            else "NUMERICAL_STABILITY_NOT_ESTABLISHED"
        )
    )

# ============================================================================
# 5. VÉRIFICATION JOB DONE
# ============================================================================

print()
print("5. CONVERGENCE INDIVIDUELLE")
print("-" * 78)

total = 0
done = 0

for name, entries in groups.items():

    for label, result in entries:

        total += 1

        if result["job_done"]:
            done += 1

        print(
            f"{name:9s} {str(label):12s} "
            f"JOB DONE={'YES' if result['job_done'] else 'NO'}"
        )

print()
print(
    f"JOB DONE : {done}/{total}"
)

# ============================================================================
# 6. SYNTHÈSE FINALE
# ============================================================================

print()
print("=" * 78)
print("6. SYNTHÈSE CORRIGÉE")
print("=" * 78)

for name in ["CUTOFF", "KPOINTS", "SMEARING"]:

    print(
        f"{name:9s} : "
        + (
            "ESTABLISHED"
            if statuses[name]
            else "NOT_ESTABLISHED"
        )
    )

global_stable = all(statuses.values())

print()
print(
    "GLOBAL NUMERICAL STABILITY : "
    + (
        "ESTABLISHED"
        if global_stable
        else "NOT_ESTABLISHED"
    )
)

print()
print("[IMPORTANT]")
print(
    "Les sorties auxiliaires kpoints_smearing_0.002Ry "
    "sont exclues."
)
print(
    "Chaque série contient maintenant uniquement ses "
    "configurations physiques principales."
)
print(
    "La convergence JOB DONE et la stabilité paramétrique "
    "restent deux critères distincts."
)
print(
    "Aucun calcul QE n'a été lancé."
)
print(
    "Aucun fichier n'a été modifié."
)

print()
print("=" * 78)
print("PHASE 78.46 TERMINÉE — READ-ONLY")
print("=" * 78)
