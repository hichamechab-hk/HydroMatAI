#!/usr/bin/env bash

# ============================================================
# HydroMatAI — MASTER DEVELOPMENT PIPELINE
# Stages 02 → 09
# ============================================================

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

START_TIME="$(date '+%Y%m%d_%H%M%S')"
LOG_DIR="$ROOT/results/master_pipeline"
LOG="$LOG_DIR/hydromatai_master_${START_TIME}.log"

mkdir -p "$LOG_DIR"

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

exec > >(tee -a "$LOG") 2>&1

echo
echo "============================================================"
echo " HydroMatAI — MASTER DEVELOPMENT PIPELINE"
echo "============================================================"
echo "ROOT      : $ROOT"
echo "DATE      : $(date)"
echo "LOG       : $LOG"
echo "============================================================"
echo

# ------------------------------------------------------------
# ENVIRONMENT
# ------------------------------------------------------------

echo "========== ENVIRONMENT =========="

if [ -f "$ROOT/.venv/bin/activate" ]; then
    source "$ROOT/.venv/bin/activate"
    echo "[PASS] .venv activated"
else
    echo "[FAIL] .venv not found"
    exit 1
fi

PYTHON="$ROOT/.venv/bin/python"

echo "[PASS] Python : $PYTHON"
"$PYTHON" --version

echo

# ------------------------------------------------------------
# QUANTUM ESPRESSO
# ------------------------------------------------------------

QE="/home/hk/software/qe-7.5/bin/pw.x"

echo "========== QUANTUM ESPRESSO =========="

if [ -x "$QE" ]; then
    echo "[PASS] QE found : $QE"
    "$QE" -h 2>&1 | head -5
else
    echo "[FAIL] QE not found : $QE"
    exit 1
fi

echo

# ------------------------------------------------------------
# PYTHON IMPORT
# ------------------------------------------------------------

echo "========== HYDROMATAI IMPORT =========="

if "$PYTHON" -c "import hydromatai" 2>/dev/null; then
    echo "[PASS] hydromatai import"
else
    echo "[FAIL] hydromatai import"
    exit 1
fi

echo

# ------------------------------------------------------------
# TEST COLLECTION
# ------------------------------------------------------------

echo "========== TEST COLLECTION =========="

TEST_COUNT=$(
    "$PYTHON" -m pytest --collect-only -q 2>/dev/null |
    grep -Eo '[0-9]+ tests? collected' |
    tail -1
)

if [ -n "$TEST_COUNT" ]; then
    echo "[PASS] $TEST_COUNT"
else
    echo "[WARNING] Unable to determine test count"
fi

echo

# ------------------------------------------------------------
# STAGES
# ------------------------------------------------------------

declare -a STAGES=(
    "02|stage_02_dft_engine_complete_v2.sh|DFT ENGINE"
    "03|stage_03_electronic_properties_complete.sh|ELECTRONIC PROPERTIES"
    "04|stage_04_optical_properties_complete.sh|OPTICAL PROPERTIES"
    "05|stage_05_scientific_analysis_complete.sh|SCIENTIFIC ANALYSIS"
    "06|stage_06_mof_h2_discovery_complete.sh|MOF / H2 DISCOVERY"
    "07|stage_07_mofxdb_integration_complete.sh|MOFX-DB INTEGRATION"
    "08|stage_08_platform_integration_complete.sh|PLATFORM INTEGRATION"
    "09|stage_09_scientific_validation_complete.sh|SCIENTIFIC VALIDATION"
)

declare -a RESULTS=()

GLOBAL_STATUS=0

# ------------------------------------------------------------
# RUN STAGES
# ------------------------------------------------------------

for ENTRY in "${STAGES[@]}"; do

    IFS='|' read -r NUM SCRIPT NAME <<< "$ENTRY"

    echo
    echo "============================================================"
    echo " STAGE $NUM — $NAME"
    echo "============================================================"
    echo "SCRIPT : $SCRIPT"
    echo "START  : $(date)"
    echo

    if [ ! -f "$ROOT/$SCRIPT" ]; then
        echo "[FAIL] Script missing : $SCRIPT"
        RESULTS+=("STAGE $NUM|MISSING|$SCRIPT")
        GLOBAL_STATUS=1
        continue
    fi

    chmod +x "$ROOT/$SCRIPT"

    STAGE_START=$(date +%s)

    bash "$ROOT/$SCRIPT"

    RC=$?

    STAGE_END=$(date +%s)
    DURATION=$((STAGE_END - STAGE_START))

    echo
    echo "------------------------------------------------------------"

    if [ "$RC" -eq 0 ]; then
        echo "[PASS] STAGE $NUM"
        echo "Duration : ${DURATION}s"
        RESULTS+=("STAGE $NUM|PASS|${DURATION}s")
    else
        echo "[FAIL] STAGE $NUM"
        echo "Return code : $RC"
        echo "Duration    : ${DURATION}s"
        RESULTS+=("STAGE $NUM|FAIL|RC=$RC")
        GLOBAL_STATUS=1

        echo
        echo "[STOP] Pipeline stopped because Stage $NUM failed."
        break
    fi

done

# ------------------------------------------------------------
# FINAL PYTEST
# ------------------------------------------------------------

echo
echo "============================================================"
echo " FINAL GLOBAL TEST"
echo "============================================================"

"$PYTHON" -m pytest -q
PYTEST_RC=$?

echo

if [ "$PYTEST_RC" -eq 0 ]; then
    echo "[PASS] Final pytest"
else
    echo "[FAIL] Final pytest — RC=$PYTEST_RC"
    GLOBAL_STATUS=1
fi

# ------------------------------------------------------------
# QE SAFETY CHECK
# ------------------------------------------------------------

echo
echo "============================================================"
echo " QE SAFETY CHECK"
echo "============================================================"

if pgrep -af "pw.x" >/tmp/hydromatai_pw_processes.txt 2>/dev/null; then
    echo "[INFO] pw.x process(es) currently detected:"
    cat /tmp/hydromatai_pw_processes.txt
    echo
    echo "[INFO] Existing QE calculations were NOT touched."
else
    echo "[INFO] No pw.x process detected."
fi

rm -f /tmp/hydromatai_pw_processes.txt

# ------------------------------------------------------------
# GIT STATUS
# ------------------------------------------------------------

echo
echo "============================================================"
echo " GIT STATUS"
echo "============================================================"

git status --short

# ------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------

echo
echo
echo "============================================================"
echo " HYDROMATAI — FINAL DEVELOPMENT REPORT"
echo "============================================================"
echo

for RESULT in "${RESULTS[@]}"; do
    IFS='|' read -r STAGE STATUS INFO <<< "$RESULT"

    if [ "$STATUS" = "PASS" ]; then
        printf " %-10s : %-8s %s\n" "$STAGE" "$STATUS" "$INFO"
    else
        printf " %-10s : %-8s %s\n" "$STAGE" "$STATUS" "$INFO"
    fi
done

echo
echo " Final pytest : $([ "$PYTEST_RC" -eq 0 ] && echo PASS || echo FAIL)"
echo " Log          : $LOG"
echo " Finished     : $(date)"
echo

if [ "$GLOBAL_STATUS" -eq 0 ]; then
    echo "============================================================"
    echo " ALL DEVELOPMENT STAGES PASSED"
    echo " HydroMatAI development pipeline : SUCCESS"
    echo "============================================================"
else
    echo "============================================================"
    echo " DEVELOPMENT PIPELINE REQUIRES ATTENTION"
    echo "============================================================"
fi

echo

exit "$GLOBAL_STATUS"
