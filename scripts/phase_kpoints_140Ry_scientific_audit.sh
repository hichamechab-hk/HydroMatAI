#!/usr/bin/env bash

clear
set -u

ROOT="/home/hk/HydroMatAI"
CONV="$ROOT/calculations/new_campaign/TiFeH2/convergence"

echo "=============================================================================="
echo "TiFeH2 — AUDIT SCIENTIFIQUE K-POINTS — 140/560 Ry"
echo "=============================================================================="
echo "[INFO] Série contrôlée : 3x3x3 / 4x4x4 / 5x5x5"
echo "[INFO] ecutwfc = 140 Ry"
echo "[INFO] ecutrho = 560 Ry"
echo "[INFO] seuil AIDA = 1e-4 Ry"
echo

for k in 3 4 5; do

    OUT="$CONV/run_kpoints_${k}x${k}x${k}_140Ry/TiFeH2_kpoints_${k}x${k}x${k}_140.out"

    echo "------------------------------------------------------------------------------"
    echo "${k}x${k}x${k}"
    echo "------------------------------------------------------------------------------"

    if [ ! -f "$OUT" ]; then
        echo "[STATUS] OUTPUT ABSENT"
        continue
    fi

    echo "[FILE] $OUT"

    if grep -q "JOB DONE." "$OUT"; then
        echo "[JOB] COMPLETE"
    else
        echo "[JOB] INCOMPLETE"
    fi

    if grep -qi "convergence has been achieved" "$OUT"; then
        echo "[SCF] CONVERGED"
    else
        echo "[SCF] NOT CONFIRMED"
    fi

    echo
    echo "[ENERGY]"
    grep "!" "$OUT" | tail -1 || true

    echo
    echo "[FERMI]"
    grep -i "Fermi energy" "$OUT" | tail -1 || true

    echo
    echo "[MAGNETIZATION]"
    grep -i "total magnetization" "$OUT" | tail -1 || true
    grep -i "absolute magnetization" "$OUT" | tail -1 || true

    echo
    echo "[K-POINTS]"
    grep -i "number of k points" "$OUT" | tail -1 || true

    echo
    echo "[TIME]"
    grep -E "PWSCF.*CPU|WALL" "$OUT" | tail -2 || true

    echo

done

echo "=============================================================================="
echo "COMPARAISON ENERGETIQUE"
echo "=============================================================================="

.venv/bin/python - <<'PY'
from pathlib import Path
import re

root = Path("/home/hk/HydroMatAI")
base = root / "calculations/new_campaign/TiFeH2/convergence"

energies = {}

for k in (3, 4, 5):
    path = (
        base
        / f"run_kpoints_{k}x{k}x{k}_140Ry"
        / f"TiFeH2_kpoints_{k}x{k}x{k}_140.out"
    )

    if not path.exists():
        print(f"{k}x{k}x{k}: ABSENT")
        continue

    text = path.read_text(errors="replace")

    values = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        flags=re.IGNORECASE,
    )

    if not values:
        print(f"{k}x{k}x{k}: ENERGIE ABSENTE")
        continue

    energies[k] = float(values[-1])

    print(f"{k}x{k}x{k}: {energies[k]:.10f} Ry")

print()

if len(energies) >= 2:
    values = list(energies.values())
    spread = max(values) - min(values)

    print(f"SPREAD GLOBAL = {spread:.10f} Ry")
    print("SEUIL AIDA    = 0.0001000000 Ry")

    if spread <= 1e-4:
        print("[STATUS] STABLE selon le critère AIDA")
    else:
        print("[STATUS] NON STABLE selon le critère AIDA")

if 3 in energies and 4 in energies:
    print(
        f"DELTA 3x3x3 -> 4x4x4 = "
        f"{abs(energies[4] - energies[3]):.10f} Ry"
    )

if 4 in energies and 5 in energies:
    print(
        f"DELTA 4x4x4 -> 5x5x5 = "
        f"{abs(energies[5] - energies[4]):.10f} Ry"
    )

PY

echo
echo "=============================================================================="
echo "FIN DE L'AUDIT"
echo "=============================================================================="
echo "[INFO] Aucun calcul pw.x lancé."
echo
