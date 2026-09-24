#!/usr/bin/env bash

printf '\033[2J\033[H'

set -u

BASE="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"

SOURCE="$BASE/calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in"

STAMP="$(date +%Y%m%d_%H%M%S)"
ROOT="$BASE/calculations/phase78_64_mpi_scaling/TiFeH2/run_$STAMP"

NPROCS=(1 2 4 8 16)

mkdir -p "$ROOT"

CSV="$ROOT/mpi_scaling.csv"
REPORT="$ROOT/REPORT.txt"

echo "=============================================================================="
echo "PHASE 78.64 — TiFeH2 MPI SCALING DIAGNOSTIQUE"
echo "=============================================================================="
echo "[INFO] Mode = BENCHMARK DIAGNOSTIQUE"
echo "[INFO] Source = $SOURCE"
echo "[INFO] QE = $QE"
echo "[INFO] MPI = 1 / 2 / 4 / 8 / 16"
echo "[INFO] electron_maxstep = 2"
echo "[INFO] Aucun fichier scientifique original modifié"
echo "[INFO] Répertoire isolé : $ROOT"
echo

if [ ! -x "$QE" ]; then
    echo "[ERROR] QE introuvable : $QE"
    exit 1
fi

if [ ! -f "$SOURCE" ]; then
    echo "[ERROR] Input source introuvable : $SOURCE"
    exit 1
fi

printf "np,wall_seconds,cpu_c_bands_seconds,scf_iterations,c_bands_warnings,final_energy_ry,status\n" > "$CSV"

{
    echo "PHASE 78.64 — TiFeH2 MPI SCALING"
    echo "Date : $(date)"
    echo
    echo "SOURCE"
    echo "$SOURCE"
    echo
    echo "QE"
    "$QE" -h 2>&1 | head -5
    echo
    echo "NPROCS : ${NPROCS[*]}"
    echo
} > "$REPORT"

for NP in "${NPROCS[@]}"; do

    RUN="$ROOT/MPI_$NP"
    mkdir -p "$RUN/tmp"

    INPUT="$RUN/TiFeH2_MPI_${NP}.in"
    OUTPUT="$RUN/TiFeH2_MPI_${NP}.out"

    cp "$SOURCE" "$INPUT"

    python - "$INPUT" "$NP" "$RUN/tmp" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
np = sys.argv[2]
outdir = sys.argv[3]

text = path.read_text()

text = text.replace(
    "prefix = 'ecut140_rho560_k888'",
    f"prefix = 'TiFeH2_MPI_{np}'"
)

text = text.replace(
    "outdir = '/home/hk/HydroMatAI/calculations/top5_dft/TiFeH2/tmp_scf'",
    f"outdir = '{outdir}'"
)

# Benchmark diagnostique uniquement.
# On conserve tous les paramètres physiques et numériques,
# mais on limite le nombre d'iterations SCF.
if "electron_maxstep" not in text:
    text = text.replace(
        "&CONTROL",
        "&CONTROL\n  electron_maxstep = 2,"
    )

path.write_text(text)
PY

    echo
    echo "=============================================================================="
    echo "MPI = $NP"
    echo "=============================================================================="
    echo "[INFO] Run directory : $RUN"

    START_NS=$(date +%s%N)

    if mpirun --allow-run-as-root -np "$NP" \
        "$QE" -in "$INPUT" > "$OUTPUT" 2>&1
    then
        STATUS="OK"
    else
        STATUS="FAILED"
    fi

    END_NS=$(date +%s%N)

    WALL=$(python - "$START_NS" "$END_NS" <<'PY'
import sys
print(f"{(int(sys.argv[2])-int(sys.argv[1]))/1e9:.3f}")
PY
)

    CPU_CBANDS=$(grep "Called by c_bands" "$OUTPUT" | tail -1 | \
        sed -E 's/.*c_bands[[:space:]]*:[[:space:]]*([0-9.]+)s CPU.*/\1/' || true)

    if [ -z "$CPU_CBANDS" ]; then
        CPU_CBANDS="NA"
    fi

    ITER=$(grep -c "iteration #" "$OUTPUT" 2>/dev/null || true)

    WARN=$(grep -c "c_bands:.*eigenvalues not converged" "$OUTPUT" 2>/dev/null || true)

    ENERGY=$(grep "!" "$OUTPUT" | tail -1 | \
        sed -E 's/.*total energy[[:space:]]*=[[:space:]]*([-+0-9.Ee]+).*/\1/' || true)

    if [ -z "$ENERGY" ]; then
        ENERGY="NA"
    fi

    printf "%s,%s,%s,%s,%s,%s,%s\n" \
        "$NP" "$WALL" "$CPU_CBANDS" "$ITER" "$WARN" "$ENERGY" "$STATUS" \
        >> "$CSV"

    {
        echo
        echo "MPI = $NP"
        echo "Wall time      = $WALL s"
        echo "c_bands CPU    = $CPU_CBANDS s"
        echo "SCF iterations = $ITER"
        echo "c_bands warns  = $WARN"
        echo "Energy         = $ENERGY Ry"
        echo "Status         = $STATUS"
        echo "Output         = $OUTPUT"
    } | tee -a "$REPORT"

done

echo
echo "=============================================================================="
echo "RESULTATS"
echo "=============================================================================="

python - "$CSV" <<'PY'
import csv
import sys

path = sys.argv[1]

rows = []
with open(path, newline="") as f:
    rows = list(csv.DictReader(f))

base = None

for r in rows:
    if r["status"] == "OK":
        base = float(r["wall_seconds"])
        break

print()
print(f"{'MPI':>5} {'WALL(s)':>12} {'SPEEDUP':>10} {'EFF.%':>10} {'c_bands CPU':>15} {'WARN':>8}")
print("-" * 70)

for r in rows:
    np = r["np"]
    wall = float(r["wall_seconds"])

    if base:
        speed = base / wall
        eff = speed / int(np) * 100
    else:
        speed = 0
        eff = 0

    print(
        f"{np:>5} "
        f"{wall:>12.3f} "
        f"{speed:>10.3f} "
        f"{eff:>10.1f} "
        f"{r['cpu_c_bands_seconds']:>15} "
        f"{r['c_bands_warnings']:>8}"
    )

print()
print("CSV :", path)
PY

echo
echo "=============================================================================="
echo "FIN PHASE 78.64"
echo "=============================================================================="
echo "[INFO] Rapport : $REPORT"
echo "[INFO] CSV     : $CSV"
echo "[INFO] Les inputs originaux n'ont pas été modifiés."
