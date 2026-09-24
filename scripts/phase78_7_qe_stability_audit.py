from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"

THRESHOLD = 1e-4


def energy(path: Path):
    text = path.read_text(errors="replace")
    m = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
    )
    return float(m[-1]) if m else None


def report(name, records):
    print()
    print(f"===== {name} =====")

    values = []

    for label, path in records:
        e = energy(path)
        print(f"{label:12s} : ", end="")
        if e is None:
            print("ENERGY ABSENTE")
        else:
            print(f"{e:.8f} Ry")
            values.append((label, e))

    if len(values) < 2:
        print("[FAIL] Nombre insuffisant de valeurs")
        return

    minimum = min(v for _, v in values)
    maximum = max(v for _, v in values)
    spread = maximum - minimum

    print(f"Min        : {minimum:.8f} Ry")
    print(f"Max        : {maximum:.8f} Ry")
    print(f"Spread     : {spread:.8f} Ry")
    print(f"Threshold  : {THRESHOLD:.8f} Ry")

    if spread <= THRESHOLD:
        print("[RESULT] NUMERICAL_STABILITY_ESTABLISHED")
    else:
        print("[RESULT] NUMERICAL_STABILITY_NOT_ESTABLISHED")


print("=" * 78)
print("PHASE 78.7 — AUDIT QUANTITATIF DE STABILITE QE")
print("=" * 78)
print("[MODE] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier QE modifié")
print()

cutoff = [
    ("60 Ry", BASE / "run_60Ry/TiFeH2_cutoff_60.out"),
    ("80 Ry", BASE / "run_80Ry/TiFeH2_cutoff_80.out"),
    ("100 Ry", BASE / "run_100Ry/TiFeH2_cutoff_100.out"),
]

kpoints = [
    ("2x2x2", BASE / "run_kpoints_2x2x2/TiFeH2_kpoints_2.out"),
    ("3x3x3", BASE / "run_kpoints_3x3x3/TiFeH2_kpoints_3.out"),
    ("4x4x4", BASE / "run_kpoints_4x4x4/TiFeH2_kpoints_4.out"),
]

smearing = [
    ("0.001 Ry", BASE / "smearing_tests/degauss_0.001Ry/TiFeH2_degauss_0.001Ry.out"),
    ("0.002 Ry", BASE / "smearing_tests/degauss_0.002Ry/TiFeH2_degauss_0.002Ry.out"),
    ("0.005 Ry", BASE / "smearing_tests/degauss_0.005Ry/TiFeH2_degauss_0.005Ry.out"),
    ("0.010 Ry", BASE / "smearing_tests/degauss_0.010Ry/TiFeH2_degauss_0.010Ry.out"),
]

for label, records in (
    ("CUTOFF", cutoff),
    ("K-POINTS", kpoints),
    ("SMEARING", smearing),
):
    for _, path in records:
        if not path.exists():
            raise SystemExit(f"[FAIL] Fichier absent : {path}")

    report(label, records)

print()
print("=" * 78)
print("CONTROLE DES 10 CALCULS PRINCIPAUX")
print("=" * 78)

all_records = cutoff + kpoints + smearing
energies = []

for label, path in all_records:
    e = energy(path)
    if e is not None:
        energies.append((label, e))

print(f"Calculs attendus : 10")
print(f"Energies trouvees : {len(energies)}")

if len(energies) != 10:
    raise SystemExit("[FAIL] Les 10 calculs principaux ne sont pas tous exploitables")

print("[OK] 10/10 sorties principales exploitables")

print()
print("=" * 78)
print("CONCLUSION PHASE 78.7")
print("=" * 78)
print("[OK] Les trois séries sont mesurées directement depuis les OUT QE.")
print("[OK] Aucun calcul supplémentaire nécessaire pour cet audit.")
print("[OK] Les résultats précédents restent inchangés.")
