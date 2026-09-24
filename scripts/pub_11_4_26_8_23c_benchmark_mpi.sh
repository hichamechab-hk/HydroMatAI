#!/usr/bin/env bash

# ==============================================================================
# PUB-11.4.26.8.23C — BENCHMARK MPI 1/2/4/8/16
# ==============================================================================

set -u
set -o pipefail

printf '\033[2J\033[H'

BASE="/home/hk/HydroMatAI"

# IMPORTANT :
# Mettre ici le pw.in EXACT du benchmark PUB-11.4.26.8.23B
INPUT="/home/hk/HydroMatAI/calculations/benchmark/PUB-11.4.26.8.23B/pw.in"

QE="/home/hk/software/qe-7.5/bin/pw.x"
MPIEXEC="$(command -v mpirun || true)"

NPROCS=(1 2 4 8 16)

STAMP="$(date +%Y%m%d_%H%M%S)"
ROOT="${BASE}/calculations/benchmark_MPI_1_2_4_8_16"
RUNROOT="${ROOT}/runs_${STAMP}"

SUMMARY="${RUNROOT}/MPI_BENCHMARK_SUMMARY.csv"
REPORT="${RUNROOT}/MPI_BENCHMARK_REPORT.txt"

die() {
    echo
    echo "[ERROR] $1"
    exit 1
}

echo "=============================================================================="
echo "PUB-11.4.26.8.23C — BENCHMARK MPI 1/2/4/8/16"
echo "=============================================================================="
echo
echo "[INFO] MODE = BENCHMARK DIAGNOSTIQUE"
echo "[INFO] Aucun fichier scientifique original ne sera modifié."
echo

[[ -d "$BASE" ]] || die "HydroMatAI introuvable : $BASE"
[[ -f "$INPUT" ]] || die "pw.in introuvable : $INPUT"
[[ -x "$QE" ]] || die "pw.x introuvable : $QE"
[[ -n "$MPIEXEC" ]] || die "mpirun introuvable."

mkdir -p "$RUNROOT"

cp -- "$INPUT" "${RUNROOT}/pw.in.reference"

echo "===== ENVIRONNEMENT ====="
echo "QE      = $QE"
echo "MPI     = $MPIEXEC"
echo "INPUT   = $INPUT"
echo

"$MPIEXEC" --version 2>&1 | head -n 2 || true

echo
echo "===== MPI TESTES ====="
printf '%s\n' "${NPROCS[@]}"
echo

cat > "$SUMMARY" <<'EOF'
mpi_processes,status,wall_time_seconds,scf_iterations,c_bands_messages,eigenvalue_warnings,final_energy_ry,speedup,efficiency_percent
EOF

{
    echo "PUB-11.4.26.8.23C — BENCHMARK MPI 1/2/4/8/16"
    echo "Date : $(date)"
    echo "QE   : $QE"
    echo "MPI  : $MPIEXEC"
    echo "INPUT: $INPUT"
    echo
} > "$REPORT"

BASELINE_TIME=""

for NP in "${NPROCS[@]}"; do

    RUN="${RUNROOT}/MPI_${NP}"
    OUTDIR="${RUN}/outdir"
    OUT="${RUN}/pw.out"
    INPUT_RUN="${RUN}/pw.in"

    mkdir -p "$OUTDIR"

    cp -- "$INPUT" "$INPUT_RUN"

    # --------------------------------------------------------------------------
    # Modifier uniquement la COPIE du pw.in.
    # --------------------------------------------------------------------------

    if grep -qi "^[[:space:]]*prefix[[:space:]]*=" "$INPUT_RUN"; then
        sed -i \
            "s#^[[:space:]]*prefix[[:space:]]*=.*#   prefix = 'mpi_benchmark_${NP}',#" \
            "$INPUT_RUN"
    fi

    if grep -qi "^[[:space:]]*outdir[[:space:]]*=" "$INPUT_RUN"; then
        sed -i \
            "s#^[[:space:]]*outdir[[:space:]]*=.*#   outdir = '${OUTDIR}',#" \
            "$INPUT_RUN"
    fi

    echo
    echo "=============================================================================="
    echo "MPI = ${NP}"
    echo "=============================================================================="
    echo "[INFO] RUN    = $RUN"
    echo "[INFO] OUTPUT = $OUT"
    echo

    START_NS="$(date +%s%N)"

    set +e

    "$MPIEXEC" -np "$NP" "$QE" -in "$INPUT_RUN" > "$OUT" 2>&1

    RC=$?

    set -e

    END_NS="$(date +%s%N)"

    WALL_NS=$((END_NS - START_NS))
    WALL_SEC=$((WALL_NS / 1000000000))

    if [[ -z "$BASELINE_TIME" && "$RC" -eq 0 ]]; then
        BASELINE_TIME="$WALL_SEC"
    fi

    SCF_ITERS="$(
        grep -c "iteration #" "$OUT" 2>/dev/null || true
    )"

    CBANDS="$(
        grep -ci "c_bands" "$OUT" 2>/dev/null || true
    )"

    EIG_WARN="$(
        grep -Eic \
        "eigenvalues.*not converged|not converged.*eigenvalues|eigenvalue.*not converged" \
        "$OUT" 2>/dev/null || true
    )"

    FINAL_ENERGY="$(
        grep -E "!\s+total energy" "$OUT" \
        | tail -n 1 \
        | sed -E 's/.*total energy[[:space:]]*=[[:space:]]*([-+0-9.eE]+).*/\1/' \
        || true
    )"

    [[ -n "$SCF_ITERS" ]] || SCF_ITERS=0
    [[ -n "$CBANDS" ]] || CBANDS=0
    [[ -n "$EIG_WARN" ]] || EIG_WARN=0
    [[ -n "$FINAL_ENERGY" ]] || FINAL_ENERGY="NA"

    if [[ "$RC" -eq 0 ]] && grep -q "JOB DONE" "$OUT"; then
        STATUS="OK"
    elif [[ "$RC" -eq 0 ]]; then
        STATUS="NO_JOB_DONE"
    else
        STATUS="FAILED_RC_${RC}"
    fi

    if [[ -n "$BASELINE_TIME" && "$WALL_SEC" -gt 0 ]]; then
        SPEEDUP="$(
            awk -v b="$BASELINE_TIME" -v t="$WALL_SEC" \
            'BEGIN { printf "%.4f", b/t }'
        )"

        EFFICIENCY="$(
            awk -v s="$SPEEDUP" -v n="$NP" \
            'BEGIN { printf "%.2f", (s/n)*100 }'
        )"
    else
        SPEEDUP="NA"
        EFFICIENCY="NA"
    fi

    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
        "$NP" \
        "$STATUS" \
        "$WALL_SEC" \
        "$SCF_ITERS" \
        "$CBANDS" \
        "$EIG_WARN" \
        "$FINAL_ENERGY" \
        "$SPEEDUP" \
        "$EFFICIENCY" \
        >> "$SUMMARY"

    {
        echo "MPI                : $NP"
        echo "Return code        : $RC"
        echo "Status             : $STATUS"
        echo "Wall time (s)      : $WALL_SEC"
        echo "SCF iterations     : $SCF_ITERS"
        echo "c_bands messages   : $CBANDS"
        echo "Eigenvalue warns   : $EIG_WARN"
        echo "Final energy (Ry)  : $FINAL_ENERGY"
        echo "Speedup            : $SPEEDUP"
        echo "Efficiency (%)     : $EFFICIENCY"
        echo
    } >> "$REPORT"

    echo "[RESULT] STATUS         = $STATUS"
    echo "[RESULT] WALL TIME      = ${WALL_SEC} s"
    echo "[RESULT] SCF ITERATIONS = $SCF_ITERS"
    echo "[RESULT] c_bands        = $CBANDS"
    echo "[RESULT] EIG WARNINGS   = $EIG_WARN"
    echo "[RESULT] ENERGY         = $FINAL_ENERGY Ry"
    echo "[RESULT] SPEEDUP        = $SPEEDUP"
    echo "[RESULT] EFFICIENCY     = ${EFFICIENCY}%"

done

echo
echo "=============================================================================="
echo "TABLEAU FINAL"
echo "=============================================================================="

printf "%-8s %-16s %-12s %-10s %-10s %-12s %-15s\n" \
    "MPI" "STATUS" "TIME(s)" "SCF" "c_bands" "EIG_WARN" "ENERGY(Ry)"

echo "--------------------------------------------------------------------------------"

tail -n +2 "$SUMMARY" | while IFS=',' read -r NP STATUS TIME SCF CBANDS EIG ENERGY SPEED EFF; do
    printf "%-8s %-16s %-12s %-10s %-10s %-12s %-15s\n" \
        "$NP" "$STATUS" "$TIME" "$SCF" "$CBANDS" "$EIG" "$ENERGY"
done

echo
echo "=============================================================================="
echo "SPEEDUP / EFFICACITE"
echo "=============================================================================="

printf "%-8s %-15s %-15s\n" "MPI" "SPEEDUP" "EFFICIENCY"
echo "-------------------------------------------"

tail -n +2 "$SUMMARY" | while IFS=',' read -r NP STATUS TIME SCF CBANDS EIG ENERGY SPEED EFF; do
    printf "%-8s %-15s %-15s\n" \
        "$NP" "$SPEED" "${EFF}%"
done

echo
echo "=============================================================================="
echo "ANALYSE DES MESSAGES DE DIAGONALISATION"
echo "=============================================================================="

for NP in "${NPROCS[@]}"; do

    OUT="${RUNROOT}/MPI_${NP}/pw.out"

    echo
    echo "--- MPI ${NP} ---"

    if [[ ! -f "$OUT" ]]; then
        echo "[WARN] pw.out absent"
        continue
    fi

    echo -n "c_bands : "
    grep -ci "c_bands" "$OUT" 2>/dev/null || true

    echo -n "eigenvalues not converged : "
    grep -Eic \
        "eigenvalues.*not converged|not converged.*eigenvalues|eigenvalue.*not converged" \
        "$OUT" 2>/dev/null || true

    echo -n "JOB DONE : "
    grep -c "JOB DONE" "$OUT" 2>/dev/null || true

done

echo
echo "=============================================================================="
echo "BENCHMARK TERMINE"
echo "=============================================================================="
echo
echo "[INFO] CSV :"
echo "       $SUMMARY"
echo
echo "[INFO] RAPPORT :"
echo "       $REPORT"
echo
echo "[INFO] RUNS :"
for NP in "${NPROCS[@]}"; do
    echo "       ${RUNROOT}/MPI_${NP}"
done
echo
echo "=============================================================================="
