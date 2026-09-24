#!/usr/bin/env python3

from pathlib import Path
import re
import math
import sys

ROOT = Path("/home/hk/HydroMatAI")
NAT = 8
RY_TO_EV = 13.605693
THRESHOLD_MEV_ATOM = 1.0

SERIES = {
    4: ROOT / "calculations/phase78_50_convergence/TiFeH2/ecut140_k444.out",
    5: ROOT / "calculations/phase78_50_convergence/TiFeH2/ecut140_k555.out",
    6: ROOT / "calculations/phase78_52_convergence/TiFeH2/ecut140_k666.out",
    7: ROOT / "calculations/phase78_55_convergence/TiFeH2/ecut140_k777.out",
    8: ROOT / "calculations/phase78_53_convergence/TiFeH2/ecut140_k888.out",
}

EXPECTED = {
    4: (-880.74188345, 12.9469),
    5: (-880.73733473, 12.9531),
    6: (-880.74373796, 12.8640),
    7: (-880.74919868, 12.9245),
    8: (-880.74600306, 12.9621),
}


def parse_output(path):
    text = path.read_text(errors="ignore")

    energies = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+0-9.eEdD]+)\s+Ry",
        text,
        flags=re.IGNORECASE,
    )

    fermis = re.findall(
        r"the Fermi energy is\s+"
        r"([-+0-9.eEdD]+)\s+ev",
        text,
        flags=re.IGNORECASE,
    )

    energy = None
    fermi = None

    if energies:
        energy = float(
            energies[-1].replace("D", "E").replace("d", "e")
        )

    if fermis:
        fermi = float(
            fermis[-1].replace("D", "E").replace("d", "e")
        )

    return {
        "job_done": "JOB DONE." in text,
        "energy": energy,
        "fermi": fermi,
    }


def meV_atom(delta_ry):
    return abs(delta_ry) * RY_TO_EV * 1000.0 / NAT


def signed_meV_atom(delta_ry):
    return delta_ry * RY_TO_EV * 1000.0 / NAT


print("=" * 78)
print("PHASE 78.56 — AUDIT QUANTITATIF COMPLET 4×4×4 → 8×8×8")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] NAT = 8")
print(f"[INFO] Seuil énergétique = {THRESHOLD_MEV_ATOM:.1f} meV/atom")
print()

# ----------------------------------------------------------------------
# 1. INVENTAIRE
# ----------------------------------------------------------------------

print("===== 1. INVENTAIRE =====")
print()

data = {}

for k in sorted(SERIES):

    path = SERIES[k]

    print(f"[CHECK] {k}×{k}×{k}")
    print(f"        {path}")

    if not path.exists():
        print("        [ERROR] Fichier absent")
        continue

    result = parse_output(path)
    data[k] = result

    print(
        f"        JOB DONE = {result['job_done']}"
    )

    if result["energy"] is not None:
        print(
            f"        Energy   = "
            f"{result['energy']:.8f} Ry"
        )
    else:
        print("        Energy   = MISSING")

    if result["fermi"] is not None:
        print(
            f"        Fermi    = "
            f"{result['fermi']:.4f} eV"
        )
    else:
        print("        Fermi    = MISSING")

    print()

# ----------------------------------------------------------------------
# 2. VALIDATION DES VALEURS
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 2. VALIDATION DES DONNÉES =====")
print("=" * 78)
print()

all_valid = True

for k in sorted(EXPECTED):

    if k not in data:
        all_valid = False
        print(
            f"[ERROR] {k}×{k}×{k} absent"
        )
        continue

    measured_e = data[k]["energy"]
    expected_e = EXPECTED[k][0]

    measured_f = data[k]["fermi"]
    expected_f = EXPECTED[k][1]

    if measured_e is None or measured_f is None:
        all_valid = False
        print(
            f"[ERROR] Données incomplètes pour {k}×{k}×{k}"
        )
        continue

    de = abs(measured_e - expected_e)
    df = abs(measured_f - expected_f)

    print(
        f"{k}×{k}×{k} : "
        f"ΔE absolu = {de:.10f} Ry ; "
        f"ΔEF = {df:.6f} eV"
    )

print()

if all_valid:
    print("[OK] Toutes les données attendues sont présentes.")
else:
    print("[WARN] Certaines données sont absentes ou invalides.")

print()

# ----------------------------------------------------------------------
# 3. TABLEAU COMPLET
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 3. SÉRIE COMPLÈTE À 140 Ry =====")
print("=" * 78)
print()

print(
    f"{'K':>5} "
    f"{'Energy (Ry)':>18} "
    f"{'EF (eV)':>12} "
    f"{'JOB DONE':>10}"
)

print("-" * 55)

for k in sorted(data):

    r = data[k]

    print(
        f"{k}³ "
        f"{r['energy']:>18.8f} "
        f"{r['fermi']:>12.4f} "
        f"{str(r['job_done']):>10}"
    )

print()

# ----------------------------------------------------------------------
# 4. DELTAS SUCCESSIVES
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 4. ΔE SUCCESSIFS =====")
print("=" * 78)
print()

successive = []

for k1, k2 in zip(sorted(data)[:-1], sorted(data)[1:]):

    e1 = data[k1]["energy"]
    e2 = data[k2]["energy"]

    f1 = data[k1]["fermi"]
    f2 = data[k2]["fermi"]

    delta_ry = e2 - e1
    delta_mev = signed_meV_atom(delta_ry)
    abs_mev = abs(delta_mev)
    delta_f = f2 - f1

    successive.append(
        {
            "from": k1,
            "to": k2,
            "delta_ry": delta_ry,
            "delta_mev": delta_mev,
            "abs_mev": abs_mev,
            "delta_f": delta_f,
        }
    )

    print(
        f"{k1}×{k1}×{k1} -> "
        f"{k2}×{k2}×{k2}"
    )

    print(
        f"  ΔE       = {delta_ry:+.8f} Ry"
    )

    print(
        f"  ΔE       = {delta_mev:+.4f} meV/atom"
    )

    print(
        f"  |ΔE|     = {abs_mev:.4f} meV/atom"
    )

    print(
        f"  ΔEF      = {delta_f:+.4f} eV"
    )

    if abs_mev <= THRESHOLD_MEV_ATOM:
        print(
            "  [OK] <= 1 meV/atom"
        )
    else:
        print(
            "  [WARN] > 1 meV/atom"
        )

    print()

# ----------------------------------------------------------------------
# 5. TESTS CIBLÉS
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 5. TESTS CIBLÉS =====")
print("=" * 78)
print()

def direct_test(k1, k2):

    if k1 not in data or k2 not in data:
        print(
            f"[ERROR] Données manquantes "
            f"{k1} ou {k2}"
        )
        return

    e1 = data[k1]["energy"]
    e2 = data[k2]["energy"]
    f1 = data[k1]["fermi"]
    f2 = data[k2]["fermi"]

    de = e2 - e1
    dm = signed_meV_atom(de)
    df = f2 - f1

    print(
        f"{k1}×{k1}×{k1} -> "
        f"{k2}×{k2}×{k2}"
    )
    print(
        f"  ΔE   = {de:+.8f} Ry"
    )
    print(
        f"  ΔE   = {dm:+.4f} meV/atom"
    )
    print(
        f"  |ΔE| = {abs(dm):.4f} meV/atom"
    )
    print(
        f"  ΔEF  = {df:+.4f} eV"
    )

    if abs(dm) <= THRESHOLD_MEV_ATOM:
        print(
            "  [OK] seuil 1 meV/atom satisfait"
        )
    else:
        print(
            "  [WARN] seuil 1 meV/atom non satisfait"
        )

    print()


direct_test(6, 7)
direct_test(7, 8)
direct_test(6, 8)

# ----------------------------------------------------------------------
# 6. NON-MONOTONIE
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 6. ANALYSE DE LA MONOTONIE =====")
print("=" * 78)
print()

energies = [
    (k, data[k]["energy"])
    for k in sorted(data)
]

increases = []
decreases = []

for (k1, e1), (k2, e2) in zip(
    energies[:-1],
    energies[1:]
):

    if e2 > e1:
        increases.append((k1, k2))
    elif e2 < e1:
        decreases.append((k1, k2))

for k1, k2 in increases:
    print(
        f"[UP]   E({k2}) > E({k1})"
    )

for k1, k2 in decreases:
    print(
        f"[DOWN] E({k2}) < E({k1})"
    )

if increases and decreases:
    print()
    print(
        "[RESULT] Série énergétique NON MONOTONE."
    )
else:
    print()
    print(
        "[RESULT] Série énergétique monotone."
    )

print()

# ----------------------------------------------------------------------
# 7. MINIMUM ÉNERGÉTIQUE DE LA SÉRIE
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 7. MINIMUM ÉNERGÉTIQUE OBSERVÉ =====")
print("=" * 78)
print()

min_k, min_e = min(
    energies,
    key=lambda item: item[1]
)

max_k, max_e = max(
    energies,
    key=lambda item: item[1]
)

print(
    f"Minimum observé : "
    f"{min_k}×{min_k}×{min_k}"
)
print(
    f"E_min = {min_e:.8f} Ry"
)
print()

print(
    f"Maximum observé : "
    f"{max_k}×{max_k}×{max_k}"
)
print(
    f"E_max = {max_e:.8f} Ry"
)
print()

print(
    f"Étendue énergétique : "
    f"{abs(max_e - min_e):.8f} Ry"
)

print(
    f"Étendue énergétique : "
    f"{abs(max_e - min_e) * RY_TO_EV * 1000 / NAT:.4f} "
    f"meV/atom"
)

print()

# ----------------------------------------------------------------------
# 8. STABILITÉ DE FERMI
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 8. STABILITÉ DE L'ÉNERGIE DE FERMI =====")
print("=" * 78)
print()

fermis = [
    (k, data[k]["fermi"])
    for k in sorted(data)
]

for k, f in fermis:
    print(
        f"{k}×{k}×{k} : "
        f"EF = {f:.4f} eV"
    )

fmin = min(f for _, f in fermis)
fmax = max(f for _, f in fermis)

print()
print(f"EF min = {fmin:.4f} eV")
print(f"EF max = {fmax:.4f} eV")
print(
    f"Étendue EF = {fmax - fmin:.4f} eV"
)

print()

# ----------------------------------------------------------------------
# 9. TEST DE CONVERGENCE FINAL
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 9. TEST DE CONVERGENCE À 1 meV/ATOM =====")
print("=" * 78)
print()

last = successive[-1]

print(
    f"Dernier passage : "
    f"{last['from']}×{last['from']}×{last['from']} -> "
    f"{last['to']}×{last['to']}×{last['to']}"
)

print(
    f"|ΔE| = {last['abs_mev']:.4f} meV/atom"
)

if last["abs_mev"] <= THRESHOLD_MEV_ATOM:

    print()
    print(
        "[RESULT] CRITÈRE ÉNERGÉTIQUE SATISFAIT."
    )

else:

    print()
    print(
        "[RESULT] CRITÈRE ÉNERGÉTIQUE NON SATISFAIT."
    )

print()

# ----------------------------------------------------------------------
# 10. CONTRÔLE JOB DONE
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 10. INTÉGRITÉ DES CALCULS =====")
print("=" * 78)
print()

all_done = True

for k in sorted(data):

    status = data[k]["job_done"]

    print(
        f"{k}×{k}×{k} : JOB DONE = {status}"
    )

    if not status:
        all_done = False

print()

if all_done:
    print(
        "[OK] Tous les calculs de la série "
        "4×4×4 → 8×8×8 sont terminés."
    )
else:
    print(
        "[WARN] Au moins un calcul n'est pas "
        "terminé correctement."
    )

print()

# ----------------------------------------------------------------------
# 11. CONCLUSION
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 11. CONCLUSION PHASE 78.56 =====")
print("=" * 78)
print()

if all_done and last["abs_mev"] > THRESHOLD_MEV_ATOM:

    print(
        "[CONCLUSION] La convergence k-point "
        "à 1 meV/atom n'est PAS démontrée."
    )

    print(
        "[CONCLUSION] La série 4×4×4 → 8×8×8 "
        "reste non monotone."
    )

    print(
        "[CONCLUSION] Le passage 7×7×7 → 8×8×8 "
        "reste au-dessus du seuil."
    )

    print(
        "[NEXT] Ne pas figer 8×8×8 comme grille "
        "convergée sur ce seul critère."
    )

print()
print(
    "[INFO] Audit strictement READ-ONLY."
)
print(
    "[INFO] Aucun résultat scientifique modifié."
)

print("=" * 78)
print("PHASE 78.56 TERMINÉE")
print("=" * 78)

