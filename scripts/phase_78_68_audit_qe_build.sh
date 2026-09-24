#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

BASE="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5"
PW="$QE/bin/pw.x"

echo "=============================================================================="
echo "PHASE 78.68 — AUDIT READ-ONLY BUILD QUANTUM ESPRESSO"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x lancé"
echo "[INFO] Aucun fichier QE modifié"
echo "[INFO] Aucun calcul scientifique lancé"
echo

# -----------------------------------------------------------------------------
# Vérification de la build
# -----------------------------------------------------------------------------

echo "===== 1. IDENTIFICATION QE ====="
echo

if [[ ! -x "$PW" ]]; then
    echo "[ERREUR] pw.x introuvable : $PW"
    exit 1
fi

echo "[INFO] QE root : $QE"
echo "[INFO] pw.x    : $PW"

echo
echo "--- Version / chemin ---"
ls -lh "$PW"
readlink -f "$PW" || true

echo
echo "--- Version strings ---"
strings "$PW" 2>/dev/null | grep -Ei \
    "Quantum ESPRESSO|PWSCF|version [0-9]" | head -20 || true

# -----------------------------------------------------------------------------
# Dépendances dynamiques
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 2. DÉPENDANCES DYNAMIQUES DE pw.x ================================"
echo "=============================================================================="
echo

ldd "$PW" 2>/dev/null | tee /tmp/phase78_68_ldd.txt

echo
echo "--- BLAS / LAPACK / ScaLAPACK / ELPA ---"

ldd "$PW" 2>/dev/null | grep -Ei \
    "blas|lapack|scalapack|elpa|mkl|openblas|blis|flexiblas|atlas" \
    || echo "[INFO] Aucune bibliothèque correspondante visible via ldd."

# -----------------------------------------------------------------------------
# MPI
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 3. MPI ==========================================================="
echo "=============================================================================="
echo

echo "--- mpirun ---"
command -v mpirun || true
mpirun --version 2>/dev/null | head -10 || true

echo
echo "--- mpicc ---"
command -v mpicc || true

if command -v mpicc >/dev/null 2>&1; then
    mpicc --show 2>/dev/null || true
    mpicc --showme 2>/dev/null || true
fi

echo
echo "--- MPI dans ldd ---"
ldd "$PW" 2>/dev/null | grep -Ei \
    "mpi|open-rte|open-pal" \
    || true

# -----------------------------------------------------------------------------
# BLAS / LAPACK / ScaLAPACK / ELPA dans l'installation QE
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 4. INVENTAIRE BIBLIOTHÈQUES QE ==================================="
echo "=============================================================================="
echo

echo "--- Recherche limitée dans $QE ---"

find "$QE" \
    -type f \
    \( \
        -iname "*blas*" -o \
        -iname "*lapack*" -o \
        -iname "*scalapack*" -o \
        -iname "*elpa*" \
    \) \
    -print 2>/dev/null | head -100

# -----------------------------------------------------------------------------
# Configuration / make.inc
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 5. CONFIGURATION DE COMPILATION =================================="
echo "=============================================================================="
echo

for F in \
    "$QE/make.inc" \
    "$QE/configure.msg" \
    "$QE/install/configure.msg" \
    "$QE/bin/../make.inc"
do
    if [[ -f "$F" ]]; then
        echo
        echo "--- FILE: $F ---"
        grep -Ei \
            "BLAS|LAPACK|SCALAPACK|ELPA|MPI|FFTW|OPENMP|OMP|MKL|OPENBLAS|BLIS" \
            "$F" 2>/dev/null | head -150 || true
    fi
done

# -----------------------------------------------------------------------------
# Recherche de configuration sans modifier quoi que ce soit
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 6. CONFIG / BUILD FLAGS ==========================================="
echo "=============================================================================="
echo

for F in \
    "$QE/configure" \
    "$QE/install/configure" \
    "$QE/README" \
    "$QE/README.md"
do
    if [[ -f "$F" ]]; then
        echo
        echo "--- $F ---"
        grep -Ei \
            "scalapack|elpa|blas|lapack|fftw|openmp|mpi" \
            "$F" 2>/dev/null | head -100 || true
    fi
done

# -----------------------------------------------------------------------------
# Symboles liés à ScaLAPACK / ELPA
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 7. SYMBOLES SCALAPACK / ELPA ====================================="
echo "=============================================================================="
echo

echo "--- Symboles ScaLAPACK ---"

nm -D "$PW" 2>/dev/null | grep -Ei \
    "pdgemm|pdgemv|pdpotrf|pdsygv|pdsygvd|pdsyev|pzheev|pzhegv|scalapack" \
    | head -100 \
    || echo "[INFO] Aucun symbole ScaLAPACK évident trouvé."

echo
echo "--- Symboles ELPA ---"

nm -D "$PW" 2>/dev/null | grep -Ei \
    "elpa|elpa_[a-z0-9_]+" \
    | head -100 \
    || echo "[INFO] Aucun symbole ELPA évident trouvé."

# -----------------------------------------------------------------------------
# OpenMP
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 8. OPENMP ========================================================="
echo "=============================================================================="
echo

echo "--- Bibliothèques OpenMP ---"

ldd "$PW" 2>/dev/null | grep -Ei \
    "gomp|omp|iomp|libomp" \
    || echo "[INFO] Aucune bibliothèque OpenMP détectée via ldd."

echo
echo "--- Variables environnement actuelles ---"

env | grep -E \
    "^(OMP|MKL|OPENBLAS|BLIS|GOTO|VECLIB)" \
    | sort \
    || echo "[INFO] Aucune variable OMP/MKL/BLAS spécifique définie."

# -----------------------------------------------------------------------------
# FFTW
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 9. FFTW ==========================================================="
echo "=============================================================================="
echo

ldd "$PW" 2>/dev/null | grep -Ei \
    "fftw" \
    || echo "[INFO] FFTW non visible via ldd."

# -----------------------------------------------------------------------------
# Résumé automatique
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 10. RÉSUMÉ ========================================================"
echo "=============================================================================="
echo

echo "[INFO] pw.x : $PW"

echo
echo "--- MPI ---"
ldd "$PW" 2>/dev/null | grep -Ei "mpi|open-rte|open-pal" | head -20 || true

echo
echo "--- BLAS/LAPACK ---"
ldd "$PW" 2>/dev/null | grep -Ei \
    "blas|lapack|mkl|openblas|blis|flexiblas|atlas" | head -30 || true

echo
echo "--- ScaLAPACK ---"
ldd "$PW" 2>/dev/null | grep -Ei "scalapack" | head -20 || true

echo
echo "--- ELPA ---"
ldd "$PW" 2>/dev/null | grep -Ei "elpa" | head -20 || true

echo
echo "--- FFTW ---"
ldd "$PW" 2>/dev/null | grep -Ei "fftw" | head -20 || true

echo
echo "--- OpenMP ---"
ldd "$PW" 2>/dev/null | grep -Ei "gomp|iomp|libomp" | head -20 || true

echo
echo "=============================================================================="
echo "PHASE 78.68 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] AUDIT READ-ONLY"
echo "[INFO] Aucun calcul lancé."
echo "[INFO] Aucun fichier scientifique modifié."
echo
