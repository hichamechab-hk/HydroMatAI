#!/usr/bin/env bash

clear
set -u

ROOT="/home/hk/HydroMatAI"
CONV="$ROOT/calculations/new_campaign/TiFeH2/convergence"

echo "=============================================================================="
echo "TiFeH2 — AUDIT CONVERGENCE K-POINTS — 140 Ry"
echo "=============================================================================="
echo "[INFO] Calculs attendus : 3x3x3 / 4x4x4 / 5x5x5"
echo "[INFO] ecutwfc = 140 Ry"
echo "[INFO] ecutrho = 560 Ry"
echo

for k in 3 4 5; do

    OUT="$CONV/run_kpoints_${k}x${k}x${k}/TiFeH2_kpoints_${k}x${k}x${k}_140.out"
    ERR="$CONV/run_kpoints_${k}x${k}x${k}/TiFeH2_kpoints_${k}x${k}x${k}_140.err"

    echo
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

    echo
    echo "[K-POINTS]"
    grep -i "number of k points" "$OUT" | tail -1 || true

    if [ -f "$ERR" ] && [ -s "$ERR" ]; then
        echo
        echo "[STDERR]"
        tail -20 "$ERR"
    else
        echo
        echo "[STDERR] vide"
    fi

done

echo
echo "=============================================================================="
echo "FIN AUDIT"
echo "=============================================================================="
echo "Aucun calcul pw.x lancé par ce script."
echo
