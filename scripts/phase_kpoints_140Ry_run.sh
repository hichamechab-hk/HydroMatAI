#!/usr/bin/env bash

clear
set -u

ROOT="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"
CONV="$ROOT/calculations/new_campaign/TiFeH2/convergence"

echo "=============================================================================="
echo "TiFeH2 — CONVERGENCE K-POINTS — CUTOFF 140 Ry"
echo "=============================================================================="
echo "[INFO] QE     = $QE"
echo "[INFO] cutoff = 140 Ry"
echo "[INFO] rho    = 560 Ry"
echo "[INFO] SCF    = 3x3x3 / 4x4x4 / 5x5x5"
echo

if [ ! -x "$QE" ]; then
    echo "[ERROR] pw.x introuvable :"
    echo "        $QE"
    echo
    echo "Le terminal reste ouvert."
    exit 1
fi

for k in 3 4 5; do

    INPUT="$CONV/kpoints_${k}x${k}x${k}_140Ry.in"
    OUTDIR="$CONV/run_kpoints_${k}x${k}x${k}_140Ry"
    OUTPUT="$OUTDIR/TiFeH2_kpoints_${k}x${k}x${k}_140Ry.out"

    mkdir -p "$OUTDIR"

    echo
    echo "=============================================================================="
    echo "CALCUL ${k}x${k}x${k}"
    echo "=============================================================================="
    echo "[INFO] Input  : $INPUT"
    echo "[INFO] Output : $OUTPUT"
    echo

    if [ ! -f "$INPUT" ]; then
        echo "[ERROR] Input absent."
        continue
    fi

    if [ -f "$OUTPUT" ]; then
        echo "[WARN] Output déjà présent."
        echo "[WARN] Calcul ignoré pour éviter un écrasement."
        continue
    fi

    echo "[RUN] pw.x ..."

    "$QE" -in "$INPUT" > "$OUTPUT" 2>&1
    RC=$?

    if [ "$RC" -ne 0 ]; then
        echo "[FAIL] pw.x retour = $RC"
        continue
    fi

    if grep -q "JOB DONE." "$OUTPUT"; then
        echo "[PASS] JOB DONE."
    else
        echo "[WARN] pw.x terminé mais JOB DONE absent."
    fi

    echo "[ENERGY]"
    grep "!" "$OUTPUT" | tail -1 || true

    echo "[FERMI]"
    grep -i "Fermi energy" "$OUTPUT" | tail -1 || true

    echo "[CONVERGENCE]"
    grep -i "convergence has been achieved" "$OUTPUT" | tail -1 || true

    echo "[MAGNETIZATION]"
    grep -i "total magnetization" "$OUTPUT" | tail -1 || true

done

echo
echo "=============================================================================="
echo "AUDIT FINAL"
echo "=============================================================================="

for k in 3 4 5; do

    OUTPUT="$CONV/run_kpoints_${k}x${k}x${k}_140Ry/TiFeH2_kpoints_${k}x${k}x${k}_140Ry.out"

    echo
    echo "--- ${k}x${k}x${k} ---"

    if [ ! -f "$OUTPUT" ]; then
        echo "[ABSENT] $OUTPUT"
        continue
    fi

    if grep -q "JOB DONE." "$OUTPUT"; then
        echo "[STATUS] COMPLETE"
    else
        echo "[STATUS] INCOMPLETE/FAILED"
    fi

    grep "!" "$OUTPUT" | tail -1 || true
    grep -i "Fermi energy" "$OUTPUT" | tail -1 || true
    grep -i "convergence has been achieved" "$OUTPUT" | tail -1 || true

done

echo
echo "=============================================================================="
echo "FIN DE LA CAMPAGNE"
echo "=============================================================================="
echo "Le terminal reste ouvert."
echo
