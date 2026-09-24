#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

BASE="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"

SRC="$BASE/calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in"

ROOT="$BASE/calculations/phase78_67_ndiag_benchmark/TiFeH2"
STAMP="$(date +%Y%m%d_%H%M%S)"
RUN="$ROOT/run_$STAMP"

MPI_N=16
NPOOL=2
MAXSTEP=2

echo "=============================================================================="
echo "PHASE 78.67 — BENCHMARK MPI / NPOOL / NDIAG — TiFeH2"
echo "=============================================================================="
echo
echo "[INFO] MODE = BENCHMARK DIAGNOSTIQUE"
echo "[INFO] Aucun fichier scientifique original ne sera modifié"
echo
echo "[INFO] QE        = $QE"
echo "[INFO] MPI       = $MPI_N"
echo "[INFO] NPOOL     = $NPOOL"
echo "[INFO] NDIAG     = 1 / 2 / 4 / 8"
echo "[INFO] ecutwfc   = 140 Ry"
echo "[INFO] ecutrho   = 560 Ry"
echo "[INFO] k-mesh    = 8x8x8"
echo "[INFO] K-points  = 170"
echo "[INFO] KS states = 36"
echo "[INFO] SCF       = $MAXSTEP iterations"
echo

# -----------------------------------------------------------------------------
# Vérifications
# -----------------------------------------------------------------------------

if [[ ! -x "$QE" ]]; then
    echo "[ERREUR] pw.x introuvable ou non exécutable :"
    echo "         $QE"
    exit 1
fi

if [[ ! -f "$SRC" ]]; then
    echo "[ERREUR] Input source introuvable :"
    echo "         $SRC"
    exit 1
fi

if ! command -v mpirun >/dev/null 2>&1; then
    echo "[ERREUR] mpirun introuvable."
    exit 1
fi

echo "[OK] pw.x trouvé"
echo "[OK] mpirun trouvé"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "[INFO] VENV actif : $VIRTUAL_ENV"
else
    echo "[INFO] Aucun VENV actif — non nécessaire pour ce benchmark"
fi

# -----------------------------------------------------------------------------
# Préparation
# -----------------------------------------------------------------------------

mkdir -p "$RUN"

echo
echo "[INFO] Répertoire benchmark :"
echo "       $RUN"

# -----------------------------------------------------------------------------
# Création d'un input isolé
# -----------------------------------------------------------------------------

make_input() {
    local NDIAG="$1"
    local DIR="$2"
    local INPUT="$3"

    local PREFIX="TiFeH2_np${NPOOL}_nd${NDIAG}"
    local OUTDIR="$DIR/tmp"

    mkdir -p "$DIR"
    mkdir -p "$OUTDIR"

    cp "$SRC" "$INPUT"

    # -------------------------------------------------------------------------
    # Modification uniquement de la COPIE du benchmark
    # -------------------------------------------------------------------------

    sed -i \
        -e "s|^[[:space:]]*prefix[[:space:]]*=.*|   prefix = '$PREFIX',|" \
        -e "s|^[[:space:]]*outdir[[:space:]]*=.*|   outdir = '$OUTDIR',|" \
        -e "s|^[[:space:]]*electron_maxstep[[:space:]]*=.*|   electron_maxstep = $MAXSTEP,|" \
        "$INPUT"

    # Si electron_maxstep n'existe pas
    if ! grep -qi "^[[:space:]]*electron_maxstep" "$INPUT"; then
        sed -i "/^[[:space:]]*&ELECTRONS/a\\   electron_maxstep = $MAXSTEP," "$INPUT"
    fi
}

# -----------------------------------------------------------------------------
# Lancement d'un cas
# -----------------------------------------------------------------------------

run_case() {

    local NDIAG="$1"

    local DIR="$RUN/NDIAG_${NDIAG}"
    local INPUT="$DIR/TiFeH2_np${NPOOL}_nd${NDIAG}.in"
    local OUTPUT="$DIR/TiFeH2_np${NPOOL}_nd${NDIAG}.out"
    local LOG="$DIR/launcher.log"

    echo
    echo "=============================================================================="
    echo "NDIAG = $NDIAG"
    echo "=============================================================================="

    make_input "$NDIAG" "$DIR" "$INPUT"

    echo "[INFO] Input  : $INPUT"
    echo "[INFO] Output : $OUTPUT"
    echo "[INFO] Command:"
    echo "       mpirun --allow-run-as-root -np $MPI_N \\"
    echo "       $QE -npool $NPOOL -ndiag $NDIAG -in $INPUT"

    START="$(date +%s)"

    set +e

    mpirun \
        --allow-run-as-root \
        -np "$MPI_N" \
        "$QE" \
        -npool "$NPOOL" \
        -ndiag "$NDIAG" \
        -in "$INPUT" \
        > "$OUTPUT" 2>&1

    RC=$?

    set -e

    END="$(date +%s)"
    ELAPSED=$((END - START))

    {
        echo "NDIAG=$NDIAG"
        echo "NPOOL=$NPOOL"
        echo "MPI=$MPI_N"
        echo "RETURN_CODE=$RC"
        echo "ELAPSED_SECONDS=$ELAPSED"
        echo "START=$(date -d "@$START" '+%Y-%m-%d %H:%M:%S')"
        echo "END=$(date -d "@$END" '+%Y-%m-%d %H:%M:%S')"
    } > "$LOG"

    if [[ "$RC" -ne 0 ]]; then
        echo "[ERREUR] NDIAG=$NDIAG terminé avec code $RC"
        echo "[INFO] Voir : $OUTPUT"
        return "$RC"
    fi

    echo "[OK] NDIAG=$NDIAG terminé en ${ELAPSED}s"

    echo
    echo "--- Distribution parallèle ---"

    grep -n -E \
        "Parallel version|MPI processes distributed|R & G space division|number of k points|number of Kohn-Sham states|diagonalization" \
        "$OUTPUT" | head -30 || true

    echo
    echo "--- Temps principaux ---"

    grep -n -E \
        "PWSCF[[:space:]]*:|c_bands[[:space:]]*:|cegterg[[:space:]]*:|cdiaghg[[:space:]]*:|h_psi[[:space:]]*:|fftw[[:space:]]*:" \
        "$OUTPUT" | tail -20 || true

    echo
    echo "--- Warnings c_bands ---"

    CB="$(grep -c "c_bands:.*eigenvalues not converged" "$OUTPUT" || true)"

    echo "c_bands non-converged messages = $CB"
}

# -----------------------------------------------------------------------------
# Exécution
# -----------------------------------------------------------------------------

echo
echo "===== LANCEMENT DES 4 CAS ====="
echo

for NDIAG in 1 2 4 8; do
    run_case "$NDIAG"
done

# -----------------------------------------------------------------------------
# Résumé
# -----------------------------------------------------------------------------

SUMMARY="$RUN/NDIAG_SUMMARY.txt"

{
    echo "=============================================================================="
    echo "PHASE 78.67 — RÉSUMÉ BENCHMARK NDIAG"
    echo "=============================================================================="
    echo
    echo "Date : $(date)"
    echo "QE   : $QE"
    echo "MPI  : $MPI_N"
    echo "NPOOL: $NPOOL"
    echo "SCF maxstep : $MAXSTEP"
    echo "Source : $SRC"
    echo

    for NDIAG in 1 2 4 8; do

        OUT="$RUN/NDIAG_${NDIAG}/TiFeH2_np${NPOOL}_nd${NDIAG}.out"
        LOG="$RUN/NDIAG_${NDIAG}/launcher.log"

        echo "------------------------------------------------------------------------------"
        echo "NDIAG = $NDIAG"
        echo "------------------------------------------------------------------------------"

        if [[ -f "$OUT" ]]; then

            grep -E \
                "Parallel version|MPI processes distributed|R & G space division|number of k points|number of Kohn-Sham states|diagonalization" \
                "$OUT" | head -15 || true

            echo

            grep -E \
                "PWSCF[[:space:]]*:|c_bands[[:space:]]*:|cegterg[[:space:]]*:|cdiaghg[[:space:]]*:|h_psi[[:space:]]*:|fftw[[:space:]]*:" \
                "$OUT" | tail -10 || true

            echo

            CB="$(grep -c "c_bands:.*eigenvalues not converged" "$OUT" || true)"
            echo "c_bands warnings : $CB"

            echo "Return code : $(grep '^RETURN_CODE=' "$LOG" 2>/dev/null | cut -d= -f2 || echo '?')"
            echo "Elapsed sec : $(grep '^ELAPSED_SECONDS=' "$LOG" 2>/dev/null | cut -d= -f2 || echo '?')"

        else
            echo "[MISSING] $OUT"
        fi

        echo
    done

} > "$SUMMARY"

# -----------------------------------------------------------------------------
# Contrôle de la source
# -----------------------------------------------------------------------------

echo
echo "===== CONTRÔLE SOURCE ====="

echo "[INFO] Source originale :"
echo "       $SRC"

echo "[INFO] Aucune écriture sur la source."

# -----------------------------------------------------------------------------
# Fichiers produits
# -----------------------------------------------------------------------------

echo
echo "===== FICHIERS PRODUITS ====="

find "$RUN" -maxdepth 2 -type f -printf '%P\n' | sort

# -----------------------------------------------------------------------------
# Résumé final
# -----------------------------------------------------------------------------

echo
echo "===== RÉSUMÉ ====="

cat "$SUMMARY"

echo
echo "=============================================================================="
echo "PHASE 78.67 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] Résumé :"
echo "       $SUMMARY"
echo
echo "[INFO] Aucun fichier scientifique original modifié."
echo
echo "Pour extraire les temps :"
echo "grep -E 'NDIAG =|PWSCF|c_bands|cegterg|cdiaghg|h_psi|fftw' \"$SUMMARY\""
echo
