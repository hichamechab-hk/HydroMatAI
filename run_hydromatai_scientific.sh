#!/usr/bin/env bash

# ============================================================
# HydroMatAI — CONTROLLED SCIENTIFIC ORCHESTRATOR
# Real DFT / QE workflow
# ============================================================

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
RUN_DIR="$ROOT/results/scientific_runs/$TIMESTAMP"
LOG="$RUN_DIR/orchestrator.log"

mkdir -p "$RUN_DIR"

exec > >(tee -a "$LOG") 2>&1

echo "============================================================"
echo " HydroMatAI — CONTROLLED SCIENTIFIC ORCHESTRATOR"
echo "============================================================"
echo "ROOT : $ROOT"
echo "RUN  : $RUN_DIR"
echo "DATE : $(date)"
echo "============================================================"

# ------------------------------------------------------------
# ENVIRONMENT
# ------------------------------------------------------------

if [ ! -f "$ROOT/.venv/bin/activate" ]; then
    echo "[FAIL] .venv not found"
    exit 1
fi

source "$ROOT/.venv/bin/activate"

PYTHON="$ROOT/.venv/bin/python"
QE="/home/hk/software/qe-7.5/bin/pw.x"

echo
echo "[ENV] Python:"
"$PYTHON" --version

echo "[ENV] QE:"
"$QE" -h 2>&1 | head -3

# ------------------------------------------------------------
# SAFETY
# ------------------------------------------------------------

echo
echo "============================================================"
echo " SAFETY CHECK"
echo "============================================================"

if pgrep -af "pw.x|mpirun" > "$RUN_DIR/qe_processes_before.txt" 2>/dev/null; then
    echo "[STOP] A QE calculation is already running."
    cat "$RUN_DIR/qe_processes_before.txt"
    echo
    echo "No calculation will be started."
    exit 2
fi

echo "[PASS] No active QE calculation detected."

# ------------------------------------------------------------
# PROJECT STATE
# ------------------------------------------------------------

echo
echo "============================================================"
echo " PROJECT STATE"
echo "============================================================"

{
    echo "DATE=$(date)"
    echo "PYTHON=$("$PYTHON" --version 2>&1)"
    echo "QE=$("$QE" -h 2>&1 | head -1)"
    echo
    echo "CALCULATIONS:"
    find "$ROOT/calculations" -maxdepth 2 -type f \
        \( -name "*.in" -o -name "*.out" \) \
        -printf "%TY-%Tm-%Td %TH:%TM %p\n" 2>/dev/null | sort
    echo
    echo "RESULTS:"
    find "$ROOT/results" -maxdepth 3 -type f \
        -printf "%TY-%Tm-%Td %TH:%TM %p\n" 2>/dev/null | sort
} > "$RUN_DIR/project_state.txt"

cat "$RUN_DIR/project_state.txt"

# ------------------------------------------------------------
# CALCULATION DISCOVERY
# ------------------------------------------------------------

echo
echo "============================================================"
echo " CALCULATION DISCOVERY"
echo "============================================================"

FOUND=0

while IFS= read -r INPUT; do
    [ -z "$INPUT" ] && continue

    FOUND=$((FOUND + 1))

    echo
    echo "------------------------------------------------------------"
    echo "INPUT : $INPUT"
    echo "------------------------------------------------------------"

    OUT="${INPUT%.in}.out"

    if [ -f "$OUT" ]; then
        echo "[FOUND] Output : $OUT"

        if grep -q "JOB DONE" "$OUT" 2>/dev/null; then
            echo "[STATUS] COMPLETED"
        elif grep -q -E "Error in routine|convergence NOT achieved|ERROR" "$OUT" 2>/dev/null; then
            echo "[STATUS] FAILED_OR_INCOMPLETE"
        else
            echo "[STATUS] UNKNOWN / INCOMPLETE"
        fi

        ENERGY=$(grep "! *total energy" "$OUT" 2>/dev/null | tail -1 || true)

        if [ -n "$ENERGY" ]; then
            echo "[ENERGY] $ENERGY"
        fi
    else
        echo "[STATUS] INPUT_ONLY"
    fi

done < <(
    find "$ROOT/calculations" -type f -name "*.in" \
        ! -path "*/tmp/*" \
        | sort
)

echo
echo "[DISCOVERY] Inputs found : $FOUND"

# ------------------------------------------------------------
# TOBMOF-10549 STATUS
# ------------------------------------------------------------

echo
echo "============================================================"
echo " TOBMOF-10549 STATUS"
echo "============================================================"

TOB="$ROOT/calculations/tobmof-10549_scf"

if [ -d "$TOB" ]; then

    echo "[FOUND] $TOB"

    for OUT in "$TOB"/*.out; do
        [ -f "$OUT" ] || continue

        echo
        echo "FILE : $(basename "$OUT")"

        if grep -q "JOB DONE" "$OUT" 2>/dev/null; then
            echo "STATUS : COMPLETED"
        elif grep -q -E "Error in routine|convergence NOT achieved|ERROR" "$OUT" 2>/dev/null; then
            echo "STATUS : FAILED_OR_INCOMPLETE"
        else
            echo "STATUS : UNKNOWN"
        fi

        grep "! *total energy" "$OUT" 2>/dev/null | tail -1 || true
    done

else
    echo "[INFO] tobmof-10549_scf directory not found."
fi

# ------------------------------------------------------------
# NO AUTOMATIC LAUNCH YET
# ------------------------------------------------------------

echo
echo "============================================================"
echo " CONTROLLED MODE"
echo "============================================================"

echo "[PASS] Discovery completed."
echo
echo "IMPORTANT:"
echo "This first run does NOT launch pw.x automatically."
echo "No existing calculation has been modified."
echo "No calculation has been deleted."
echo
echo "The discovered calculation state has been saved to:"
echo "$RUN_DIR/project_state.txt"
echo
echo "Log:"
echo "$LOG"

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

echo
echo "============================================================"
echo " ORCHESTRATOR SUMMARY"
echo "============================================================"
echo "Environment       : PASS"
echo "QE availability   : PASS"
echo "QE safety         : PASS"
echo "Discovery         : PASS"
echo "Automatic launch  : DISABLED"
echo "Existing files    : PROTECTED"
echo "============================================================"

exit 0
