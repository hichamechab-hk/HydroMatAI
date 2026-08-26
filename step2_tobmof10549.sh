#!/usr/bin/env bash

BASE="$HOME/HydroMatAI"
CALC="$BASE/calculations/tobmof-10549_scf"
INPUT="$CALC/tobmof-10549_scf_20_80_nospin.in"
TMP="$CALC/tmp"
OUT="/tmp/tobmof-10549_step2_mpi1.out"
QE="/home/hk/software/qe-7.5/bin/pw.x"

echo "============================================================"
echo " HydroMatAI — tobMOF-10549 — ETAPE 2"
echo " Test MPI=1 | 20/80 Ry | nspin=1 | timeout 120 s"
echo "============================================================"

pkill -KILL -f "pw.x.*tobmof-10549" 2>/dev/null || true

rm -rf "$TMP"/*
mkdir -p "$TMP"
rm -f "$OUT"

echo
echo "[1] Lancement MPI=1..."

timeout 120s mpirun -np 1 \
    "$QE" \
    -in "$INPUT" \
    > "$OUT" 2>&1

EXIT_CODE=$?

echo
echo "[2] EXIT_CODE=$EXIT_CODE"

echo
echo "[3] Progression"
grep -E \
"Program PWSCF|available memory|number of atoms|number of electrons|Dense grid|Smooth grid|FFT dimensions|Estimated max|Estimated total|Initial potential|starting charge|negative rho|Starting wfcs|iteration #|total energy|JOB DONE|Error in routine" \
"$OUT" | tail -60

echo
echo "[4] Dernières lignes"
tail -25 "$OUT"

echo
echo "[5] Processus"
pgrep -af "pw.x.*tobmof-10549" || echo "AUCUN pw.x"

echo
echo "============================================================"
echo " FIN ETAPE 2"
echo "============================================================"
