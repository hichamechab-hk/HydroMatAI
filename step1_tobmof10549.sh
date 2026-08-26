#!/usr/bin/env bash

BASE="$HOME/HydroMatAI"
CALC="$BASE/calculations/tobmof-10549_scf"
INPUT="$CALC/tobmof-10549_scf_20_80_nospin.in"
TMP="$CALC/tmp"
OUT="/tmp/tobmof-10549_step1_mpi4.out"
QE="/home/hk/software/qe-7.5/bin/pw.x"

echo "============================================================"
echo " HydroMatAI — tobMOF-10549 — ETAPE 1"
echo " Test MPI=4 | 20/80 Ry | nspin=1 | timeout 120 s"
echo "============================================================"

pkill -KILL -f "pw.x.*tobmof-10549" 2>/dev/null || true

rm -rf "$TMP"/*
mkdir -p "$TMP"
rm -f "$OUT"

echo
echo "[1] Vérification input..."
test -f "$INPUT" || {
    echo "ERREUR : input absent"
    exit 1
}

echo "Input : OK"

echo
echo "[2] Lancement MPI=4..."

timeout 120s mpirun -np 4 \
    "$QE" \
    -in "$INPUT" \
    > "$OUT" 2>&1

EXIT_CODE=$?

echo
echo "[3] Résultat"
echo "EXIT_CODE=$EXIT_CODE"

echo
echo "[4] Progression QE"
grep -E \
"Program PWSCF|available memory|number of atoms|number of electrons|Dense grid|Smooth grid|FFT dimensions|Generating pointlists|new r_m|iteration #|total energy|convergence has been achieved|JOB DONE|Error in routine" \
"$OUT" | tail -50

echo
echo "[5] Dernières lignes"
tail -20 "$OUT"

echo
echo "[6] Processus"
pgrep -af "pw.x.*tobmof-10549" || echo "AUCUN pw.x"

echo
echo "============================================================"
echo " FIN ETAPE 1"
echo "============================================================"
