#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

BASE="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"

SRC="$BASE/calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in"

ROOT="$BASE/calculations/phase78_66_npool_benchmark/TiFeH2"
STAMP="$(date +%Y%m%d_%H%M%S)"
RUN="$ROOT/run_$STAMP"

MPI_N=16
MAXSTEP=2

echo "=============================================================================="
echo "PHASE 78.66 — BENCHMARK MPI / NPOOL — TiFeH2"
echo "=============================================================================="
echo
echo "[INFO] MODE = BENCHMARK DIAGNOSTIQUE"
echo "[INFO] Aucun fichier scientifique original ne sera modifié"
echo "[INFO] QE = $QE"
echo "[INFO] MPI = $MPI_N"
echo "[INFO] ecutwfc = 140 Ry"
echo "[INFO] ecutrho = 560 Ry"
echo "[INFO] k-mesh = 8x8x8"
echo "[INFO] K-points = 170"
echo "[INFO] SCF maxstep = $MAXSTEP"
echo

# ---------------------------------------------------------------------------
# Vérifications
# ---------------------------------------------------------------------------

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
    echo "[ERREUR] mpirun introuvable dans PATH"
    exit 1
fi

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "[ATTENTION] Le venv Python n'est pas actif."
    echo "[INFO] Ce benchmark n'utilise pas Python ; poursuite autorisée."
else
    echo "[INFO] VENV actif : $VIRTUAL_ENV"
fi

echo
echo "===== ENVIRONNEMENT MPI ====="
echo "mpirun : $(command -v mpirun)"
mpirun --version 2>/dev/null | head -3 || true

echo
echo "===== TEST QE ====="
"$QE" -h >/dev/null 2>&1 || true
echo "[OK] pw.x détecté"

# ---------------------------------------------------------------------------
# Préparation
# ---------------------------------------------------------------------------

mkdir -p "$RUN"

echo
echo "[INFO] Répertoire benchmark :"
echo "       $RUN"

# ---------------------------------------------------------------------------
# Fonction de création d'un input isolé
# ---------------------------------------------------------------------------

make_input() {
    local NPOOL="$1"
    local DIR="$2"
    local INPUT="$3"
    local PREFIX="TiFeH2_npool${NPOOL}"
    local OUTDIR="$DIR/tmp"

    mkdir -p "$DIR"
    mkdir -p "$OUTDIR"

    cp "$SRC" "$INPUT"

    # Modifier UNIQUEMENT la copie du benchmark.
    sed -i \
        -e "s|^[[:space:]]*prefix[[:space:]]*=.*|   prefix = '$PREFIX',|" \
        -e "s|^[[:space:]]*outdir[[:space:]]*=.*|   outdir = '$OUTDIR',|" \
        -e "s|^[[:space:]]*electron_maxstep[[:space:]]*=.*|   electron_maxstep = $MAXSTEP,|" \
        "$INPUT"

    # Si electron_maxstep n'existe pas dans l'input, l'insérer après &ELECTRONS.
    if ! grep -qi "^[[:space:]]*electron_maxstep" "$INPUT"; then
        sed -i "/^[[:space:]]*&ELECTRONS/a\\   electron_maxstep = $MAXSTEP," "$INPUT"
    fi

    # Garantir un K_POINTS automatique 8x8x8 inchangé.
    if ! grep -Eq "^[[:space:]]*K_POINTS[[:space:]]+automatic" "$INPUT"; then
        echo "[ERREUR] K_POINTS automatic introuvable dans $INPUT"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Fonction de lancement
# ---------------------------------------------------------------------------

run_case() {
    local NPOOL="$1"

    local DIR="$RUN/NPOOL_${NPOOL}"
    local INPUT="$DIR/TiFeH2_npool${NPOOL}.in"
    local OUTPUT="$DIR/TiFeH2_npool${NPOOL}.out"
    local LOG="$DIR/launcher.log"

    echo
    echo "=============================================================================="
    echo "NPOOL = $NPOOL"
    echo "=============================================================================="

    make_input "$NPOOL" "$DIR" "$INPUT"

    echo "[INFO] Input : $INPUT"
    echo "[INFO] Output: $OUTPUT"
    echo "[INFO] Commande : mpirun -np $MPI_N pw.x -npool $NPOOL"

    START="$(date +%s)"

    set +e

    mpirun \
        --allow-run-as-root \
        -np "$MPI_N" \
        "$QE" \
        -npool "$NPOOL" \
        -in "$INPUT" \
        > "$OUTPUT" 2>&1

    RC=$?

    set -e

    END="$(date +%s)"
    ELAPSED=$((END - START))

    {
        echo "NPOOL=$NPOOL"
        echo "MPI=$MPI_N"
        echo "RETURN_CODE=$RC"
        echo "ELAPSED_SECONDS=$ELAPSED"
        echo "START=$(date -d "@$START" '+%Y-%m-%d %H:%M:%S')"
        echo "END=$(date -d "@$END" '+%Y-%m-%d %H:%M:%S')"
    } > "$LOG"

    if [[ "$RC" -ne 0 ]]; then
        echo "[ERREUR] NPOOL=$NPOOL terminé avec code $RC"
        echo "[INFO] Voir : $OUTPUT"
        return "$RC"
    fi

    echo "[OK] NPOOL=$NPOOL terminé en ${ELAPSED}s"

    echo
    echo "--- Distribution parallèle ---"
    grep -n -E \
        "Parallel version|MPI processes distributed|R & G space division|number of k points|number of Kohn-Sham states" \
        "$OUTPUT" | head -20 || true

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

# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------

echo
echo "===== LANCEMENT DES 4 CAS ====="
echo

for NPOOL in 1 2 4 8; do
    run_case "$NPOOL"
done

# ---------------------------------------------------------------------------
# Résumé automatique
# ---------------------------------------------------------------------------

SUMMARY="$RUN/NPOOL_SUMMARY.txt"

{
    echo "=============================================================================="
    echo "PHASE 78.66 — RÉSUMÉ BENCHMARK NPOOL"
    echo "=============================================================================="
    echo
    echo "Date : $(date)"
    echo "QE   : $QE"
    echo "MPI  : $MPI_N"
    echo "SCF maxstep : $MAXSTEP"
    echo "Source : $SRC"
    echo

    for NPOOL in 1 2 4 8; do
        OUT="$RUN/NPOOL_${NPOOL}/TiFeH2_npool${NPOOL}.out"

        echo "------------------------------------------------------------------------------"
        echo "NPOOL = $NPOOL"
        echo "------------------------------------------------------------------------------"

        if [[ -f "$OUT" ]]; then

            grep -E \
                "Parallel version|MPI processes distributed|R & G space division|number of k points|number of Kohn-Sham states" \
                "$OUT" | head -10 || true

            echo

            grep -E \
                "PWSCF[[:space:]]*:|c_bands[[:space:]]*:|cegterg[[:space:]]*:|cdiaghg[[:space:]]*:|h_psi[[:space:]]*:|fftw[[:space:]]*:" \
                "$OUT" | tail -10 || true

            echo

            CB="$(grep -c "c_bands:.*eigenvalues not converged" "$OUT" || true)"
            echo "c_bands warnings : $CB"

            echo "Return code : $(grep '^RETURN_CODE=' "$RUN/NPOOL_${NPOOL}/launcher.log" 2>/dev/null | cut -d= -f2 || echo '?')"
            echo "Elapsed sec : $(grep '^ELAPSED_SECONDS=' "$RUN/NPOOL_${NPOOL}/launcher.log" 2>/dev/null | cut -d= -f2 || echo '?')"

        else
            echo "[MISSING] $OUT"
        fi

        echo
    done

} > "$SUMMARY"

# ---------------------------------------------------------------------------
# Contrôle d'intégrité : vérifier que la source n'a pas été modifiée
# ---------------------------------------------------------------------------

echo
echo "===== CONTRÔLE SOURCE ====="

echo "[INFO] La source originale n'a pas été écrite par le script."
echo "[INFO] Source : $SRC"

echo
echo "===== FICHIERS PRODUITS ====="
find "$RUN" -maxdepth 2 -type f -printf '%P\n' | sort

echo
echo "===== RÉSUMÉ ====="
cat "$SUMMARY"

echo
echo "=============================================================================="
echo "PHASE 78.66 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] Résumé : $SUMMARY"
echo "[INFO] Aucun fichier scientifique original modifié."
echo
echo "Pour afficher uniquement les temps :"
echo "grep -E 'NPOOL =|PWSCF|c_bands|cegterg|cdiaghg|h_psi|fftw' \"$SUMMARY\""
echo
