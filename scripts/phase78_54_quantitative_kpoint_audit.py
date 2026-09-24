#!/usr/bin/env python3

from pathlib import Path
import re
import math

ROOT = Path("/home/hk/HydroMatAI")

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

NAT = 8

SOURCES = [
    (
        "78.48",
        ROOT / "calculations/phase78_48_convergence/TiFeH2"
    ),
    (
        "78.50",
        ROOT / "calculations/phase78_50_convergence/TiFeH2"
    ),
    (
        "78.52",
        ROOT / "calculations/phase78_52_convergence/TiFeH2"
    ),
    (
        "78.53",
        ROOT / "calculations/phase78_53_convergence/TiFeH2"
    ),
]

EXPECTED = {
    (100, (2, 2, 2)): "ecut100_k222.out",
    (100, (3, 3, 3)): "ecut100_k333.out",
    (100, (4, 4, 4)): "ecut100_k444.out",
    (100, (5, 5, 5)): "ecut100_k555.out",
    (100, (6, 6, 6)): "ecut100_k666.out",

    (120, (4, 4, 4)): "ecut120_k444.out",
    (120, (5, 5, 5)): "ecut120_k555.out",

    (140, (2, 2, 2)): "ecut140_k222.out",
    (140, (3, 3, 3)): "ecut140_k333.out",
    (140, (4, 4, 4)): "ecut140_k444.out",
    (140, (5, 5, 5)): "ecut140_k555.out",
    (140, (6, 6, 6)): "ecut140_k666.out",
    (140, (7, 7, 7)): "ecut140_k777.out",
    (140, (8, 8, 8)): "ecut140_k888.out",
}

# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------

def parse_output(path):

    text = path.read_text(errors="ignore")

    energies = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+0-9.eEdD]+)\s+Ry",
        text,
        flags=re.IGNORECASE
    )

    fermis = re.findall(
        r"the Fermi energy is\s+"
        r"([-+0-9.eEdD]+)\s+ev",
        text,
        flags=re.IGNORECASE
    )

    energy = None
    fermi = None

    if energies:
        value = energies[-1].replace("D", "E").replace("d", "e")
        energy = float(value)

    if fermis:
        value = fermis[-1].replace("D", "E").replace("d", "e")
        fermi = float(value)

    return {
        "path": path,
        "job_done": "JOB DONE." in text,
        "energy": energy,
        "fermi": fermi,
    }


def find_output(name):

    for phase, directory in SOURCES:

        path = directory / name

        if path.exists():
            return phase, path

    return None, None


def ry_to_mev_per_atom(delta_ry):

    # 1 Ry = 13.605693 eV
    # 1000 meV/eV
    # / NAT atoms
    return abs(delta_ry) * 13.605693 * 1000.0 / NAT


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------

print("=" * 78)
print("PHASE 78.54 — AUDIT QUANTITATIF COMPLET K-POINTS")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] NAT = 8")
print("[INFO] Conversion : 1 Ry = 13.605693 eV")
print()

# ----------------------------------------------------------------------
# 1. Inventaire
# ----------------------------------------------------------------------

print("===== 1. INVENTAIRE DES RÉSULTATS =====")
print()

records = {}

for key, filename in EXPECTED.items():

    ecut, kgrid = key
    phase, path = find_output(filename)

    label = f"{ecut:3d} Ry / {kgrid[0]}x{kgrid[1]}x{kgrid[2]}"

    if path is None:

        print(f"[MISSING] {label:24s} -> {filename}")
        continue

    result = parse_output(path)

    records[key] = result

    print(
        f"[FOUND]   {label:24s} "
        f"phase={phase:5s} "
        f"JOB_DONE={str(result['job_done']):5s}"
    )

    if result["energy"] is not None:
        print(
            f"          Energy = "
            f"{result['energy']:.8f} Ry"
        )
    else:
        print("          Energy = MISSING")

    if result["fermi"] is not None:
        print(
            f"          Fermi  = "
            f"{result['fermi']:.4f} eV"
        )
    else:
        print("          Fermi  = MISSING")

print()

# ----------------------------------------------------------------------
# 2. Série 140 Ry
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 2. SÉRIE K-POINTS À 140 Ry =====")
print("=" * 78)
print()

series_140 = []

for k in range(2, 9):

    key = (140, (k, k, k))

    if key not in records:
        continue

    r = records[key]

    series_140.append(
        (
            k,
            r["energy"],
            r["fermi"],
            r["job_done"]
        )
    )

    print(
        f"{k}x{k}x{k} : "
        f"E = "
        f"{r['energy']:.8f} Ry   "
        f"EF = "
        f"{r['fermi']:.4f} eV   "
        f"JOB_DONE = "
        f"{r['job_done']}"
    )

print()

# ----------------------------------------------------------------------
# 3. Delta E successifs
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 3. ΔE SUCCESSIFS — 140 Ry =====")
print("=" * 78)
print()

for i in range(1, len(series_140)):

    k_prev, e_prev, ef_prev, _ = series_140[i - 1]
    k_now, e_now, ef_now, _ = series_140[i]

    delta_ry = e_now - e_prev
    delta_mev_atom = ry_to_mev_per_atom(delta_ry)
    delta_fermi = ef_now - ef_prev

    print(
        f"{k_prev}x{k_prev}x{k_prev}"
        f" -> "
        f"{k_now}x{k_now}x{k_now}"
    )

    print(
        f"    ΔE      = {delta_ry:+.8f} Ry"
    )

    print(
        f"    |ΔE|    = "
        f"{delta_mev_atom:.4f} meV/atom"
    )

    print(
        f"    ΔFermi  = "
        f"{delta_fermi:+.4f} eV"
    )

    if delta_mev_atom <= 1.0:
        print(
            "    [OK] |ΔE| <= 1 meV/atom"
        )
    else:
        print(
            "    [WARN] |ΔE| > 1 meV/atom"
        )

    print()

# ----------------------------------------------------------------------
# 4. Comparaison 6 -> 8
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 4. TEST DIRECT 6x6x6 -> 8x8x8 =====")
print("=" * 78)
print()

key6 = (140, (6, 6, 6))
key8 = (140, (8, 8, 8))

if key6 in records and key8 in records:

    e6 = records[key6]["energy"]
    e8 = records[key8]["energy"]

    ef6 = records[key6]["fermi"]
    ef8 = records[key8]["fermi"]

    delta_ry = e8 - e6
    delta_mev = ry_to_mev_per_atom(delta_ry)

    print(f"E(6x6x6) = {e6:.8f} Ry")
    print(f"E(8x8x8) = {e8:.8f} Ry")
    print()
    print(f"ΔE(6->8)  = {delta_ry:+.8f} Ry")
    print(f"|ΔE|       = {delta_mev:.4f} meV/atom")
    print()
    print(f"EF(6x6x6) = {ef6:.4f} eV")
    print(f"EF(8x8x8) = {ef8:.4f} eV")
    print(
        f"ΔEF        = {ef8 - ef6:+.4f} eV"
    )
    print()

    if delta_mev <= 1.0:
        print(
            "[OK] Convergence énergétique "
            "6x6x6 -> 8x8x8 <= 1 meV/atom"
        )
    else:
        print(
            "[WARN] Convergence énergétique "
            "6x6x6 -> 8x8x8 > 1 meV/atom"
        )

else:

    print(
        "[ERROR] Données 6x6x6 ou 8x8x8 manquantes."
    )

print()

# ----------------------------------------------------------------------
# 5. Stabilité de EF
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 5. STABILITÉ DE L'ÉNERGIE DE FERMI =====")
print("=" * 78)
print()

fermi_values = [
    (k, ef)
    for k, _, ef, done in series_140
    if ef is not None and done
]

for k, ef in fermi_values:

    print(
        f"{k}x{k}x{k} : "
        f"EF = {ef:.4f} eV"
    )

if fermi_values:

    ef_min = min(ef for _, ef in fermi_values)
    ef_max = max(ef for _, ef in fermi_values)

    print()
    print(f"EF min = {ef_min:.4f} eV")
    print(f"EF max = {ef_max:.4f} eV")
    print(
        f"Étendue = {ef_max - ef_min:.4f} eV"
    )

print()

# ----------------------------------------------------------------------
# 6. Test de convergence énergétique
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 6. TEST DE CONVERGENCE =====")
print("=" * 78)
print()

THRESHOLD = 1.0

if len(series_140) >= 2:

    last_k, last_e, last_ef, _ = series_140[-1]
    prev_k, prev_e, prev_ef, _ = series_140[-2]

    delta_last = ry_to_mev_per_atom(
        last_e - prev_e
    )

    print(
        f"Dernier test : "
        f"{prev_k}x{prev_k}x{prev_k}"
        f" -> "
        f"{last_k}x{last_k}x{last_k}"
    )

    print(
        f"|ΔE| = {delta_last:.4f} meV/atom"
    )

    if delta_last <= THRESHOLD:

        print()
        print(
            "[RESULT] CRITÈRE ÉNERGÉTIQUE SATISFAIT"
        )

    else:

        print()
        print(
            "[RESULT] CRITÈRE ÉNERGÉTIQUE NON SATISFAIT"
        )

        print(
            "[INFO] Ne pas déclarer la convergence "
            "k-point à 1 meV/atom."
        )

print()

# ----------------------------------------------------------------------
# 7. Test JOB DONE
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 7. INTÉGRITÉ DES CALCULS =====")
print("=" * 78)
print()

all_done = True

for key, result in sorted(records.items()):

    if key[0] != 140:
        continue

    k = key[1][0]

    status = result["job_done"]

    print(
        f"140 Ry / {k}x{k}x{k} : "
        f"JOB DONE = {status}"
    )

    if not status:
        all_done = False

print()

if all_done:
    print(
        "[OK] Tous les calculs 140 Ry disponibles "
        "sont terminés proprement."
    )
else:
    print(
        "[WARN] Au moins un calcul 140 Ry "
        "n'est pas terminé."
    )

print()

# ----------------------------------------------------------------------
# 8. Conclusion automatique
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 8. CONCLUSION PHASE 78.54 =====")
print("=" * 78)
print()

if len(series_140) >= 2:

    last_k, last_e, last_ef, _ = series_140[-1]
    prev_k, prev_e, prev_ef, _ = series_140[-2]

    delta_last = ry_to_mev_per_atom(
        last_e - prev_e
    )

    if delta_last <= 1.0:

        print(
            "[CONCLUSION] La dernière variation "
            "énergétique est <= 1 meV/atom."
        )

        print(
            "[CONCLUSION] La convergence k-point "
            "atteint le seuil énergétique défini."
        )

    else:

        print(
            "[CONCLUSION] La dernière variation "
            "énergétique reste > 1 meV/atom."
        )

        print(
            "[CONCLUSION] La convergence k-point "
            "n'est PAS démontrée à 1 meV/atom."
        )

        print(
            "[NEXT] Une extension de la série k-point "
            "peut être nécessaire."
        )

print()
print(
    "[INFO] Cet audit est descriptif : "
    "aucun calcul ni fichier scientifique n'a été modifié."
)

print("=" * 78)
print("PHASE 78.54 TERMINÉE")
print("=" * 78)
