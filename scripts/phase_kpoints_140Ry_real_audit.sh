#!/usr/bin/env bash

clear
set -euo pipefail

ROOT="/home/hk/HydroMatAI"
BASE="$ROOT/calculations/new_campaign/TiFeH2/convergence"

echo "============================================================"
echo "K-POINT 140/560 Ry — AUDIT SCIENTIFIQUE RÉEL"
echo "============================================================"
echo "[MODE] READ-ONLY"
echo "[INFO] Aucun pw.x ne sera lancé"
echo "[INFO] Aucun fichier QE ne sera modifié"
echo

export PYTHONPATH="$ROOT/src"

"$ROOT/.venv/bin/python" - <<'PY'
from pathlib import Path

from hydromatai.dft.validation import (
    energy_spread,
    parse_kpoint_output,
    successive_energy_differences,
)

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"

CASES = [
    (
        "3x3x3",
        BASE
        / "run_kpoints_3x3x3_140Ry"
        / "TiFeH2_kpoints_3x3x3_140.out",
    ),
    (
        "4x4x4",
        BASE
        / "run_kpoints_4x4x4_140Ry"
        / "TiFeH2_kpoints_4x4x4_140.out",
    ),
    (
        "5x5x5",
        BASE
        / "run_kpoints_5x5x5_140Ry"
        / "TiFeH2_kpoints_5x5x5_140.out",
    ),
]

results = []

for grid, path in CASES:
    print("=" * 60)
    print(f"{grid} — 140/560 Ry")
    print("=" * 60)

    if not path.exists():
        print("[STATUS] FICHIER ABSENT")
        print(f"[PATH]   {path}")
        print()
        continue

    result = parse_kpoint_output(grid, path)
    results.append(result)

    print(f"[PATH]       {path}")
    print(f"[ENERGY]     {result.energy_ry} Ry")
    print(f"[FERMI]      {result.fermi_ev} eV")
    print(f"[KPOINTS]    {result.irreducible_kpoints}")
    print(f"[SCF]        {'CONVERGED' if result.scf_converged else 'INCOMPLETE'}")
    print(f"[JOB DONE]   {'YES' if result.job_done else 'NO'}")

    if result.energy_ry is None:
        print("[STATUS]     NO FINAL ENERGY")
    elif result.scf_converged and result.job_done:
        print("[STATUS]     COMPLETE")
    else:
        print("[STATUS]     INCOMPLETE")

    print()

print("=" * 60)
print("ANALYSE ÉNERGÉTIQUE")
print("=" * 60)

complete = [
    result
    for result in results
    if result.energy_ry is not None
    and result.scf_converged
    and result.job_done
]

print(f"Calculs complets : {len(complete)}/{len(CASES)}")

if len(complete) >= 2:
    spread = energy_spread(complete)

    print()
    print(f"ENERGY SPREAD = {spread:.12f} Ry")
    print("AIDA THRESHOLD = 0.000100000000 Ry")

    if spread <= 1.0e-4:
        print("AIDA K-POINT STATUS = NUMERICAL_STABILITY_ESTABLISHED")
    else:
        print("AIDA K-POINT STATUS = NUMERICAL_STABILITY_NOT_ESTABLISHED")

    print()
    print("DIFFÉRENCES SUCCESSIVES")

    for previous, current, delta in successive_energy_differences(complete):
        print(
            f"{previous} -> {current} : "
            f"{delta:.12f} Ry"
        )

else:
    print()
    print(
        "[ATTENTE] Au moins deux calculs complets sont nécessaires "
        "pour évaluer la convergence."
    )

print()
print("=" * 60)
print("FIN AUDIT")
print("=" * 60)
PY
