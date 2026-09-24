#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE_REF="/home/hk/software/qe-7.5"
QE_SCAL="/home/hk/software/qe-7.5-scalapack"

PW_REF="$QE_REF/bin/pw.x"
PW_SCAL="$QE_SCAL/bin/pw.x"

echo "=============================================================================="
echo "PHASE 78.73 — AUDIT IDENTITÉ BUILDS QE 7.5"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x exécuté"
echo "[INFO] Aucun calcul scientifique"
echo "[INFO] Aucun fichier modifié"
echo

for F in "$PW_REF" "$PW_SCAL"; do
    if [[ ! -x "$F" ]]; then
        echo "[ERREUR] Exécutable absent : $F"
        exit 1
    fi
done

echo "=============================================================================="
echo "===== 1. EXISTENCE ET TAILLE ============================================"
echo "=============================================================================="
echo

for NAME in REF SCALAPACK; do
    if [[ "$NAME" == "REF" ]]; then
        PW="$PW_REF"
    else
        PW="$PW_SCAL"
    fi

    echo "--- $NAME ---"
    ls -lh "$PW"
    file "$PW"
    stat "$PW" | grep -E 'Size:|Modify:' || true
    echo
done

echo "=============================================================================="
echo "===== 2. SHA256 ========================================================="
echo "=============================================================================="
echo

echo "[REF]"
sha256sum "$PW_REF"

echo
echo "[SCALAPACK]"
sha256sum "$PW_SCAL"

echo "=============================================================================="
echo "===== 3. LDD — RÉFÉRENCE ==============================================="
echo "=============================================================================="
echo

ldd "$PW_REF" \
    | grep -Ei \
    'scalapack|lapack|blas|mpi|fftw|open-rte|open-pal|omp|gomp|iomp|mkl' \
    || true

echo "=============================================================================="
echo "===== 4. LDD — SCALAPACK ================================================"
echo "=============================================================================="
echo

ldd "$PW_SCAL" \
    | grep -Ei \
    'scalapack|lapack|blas|mpi|fftw|open-rte|open-pal|omp|gomp|iomp|mkl' \
    || true

echo "=============================================================================="
echo "===== 5. MAKE.INC — COMPARAISON ========================================"
echo "=============================================================================="
echo

echo "--- RÉFÉRENCE ---"
grep -E \
    '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
    "$QE_REF/make.inc" \
    || true

echo
echo "--- SCALAPACK ---"
grep -E \
    '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
    "$QE_SCAL/make.inc" \
    || true

echo "=============================================================================="
echo "===== 6. FLAGS SCALAPACK ================================================="
echo "=============================================================================="
echo

echo "[REF]"
grep -E '__SCALAPACK|SCALAPACK_LIBS' "$QE_REF/make.inc" || true

echo
echo "[SCALAPACK]"
grep -E '__SCALAPACK|SCALAPACK_LIBS' "$QE_SCAL/make.inc" || true

echo "=============================================================================="
echo "===== 7. OPENMP / MKL / OPENBLAS ========================================"
echo "=============================================================================="
echo

echo "--- Référence ---"
ldd "$PW_REF" \
    | grep -Ei 'libgomp|libomp|libiomp|mkl|openblas' \
    || echo "[OK] Aucun runtime OpenMP/MKL/OpenBLAS détecté."

echo
echo "--- ScaLAPACK ---"
ldd "$PW_SCAL" \
    | grep -Ei 'libgomp|libomp|libiomp|mkl|openblas' \
    || echo "[OK] Aucun runtime OpenMP/MKL/OpenBLAS détecté."

echo "=============================================================================="
echo "===== 8. SYMBOLS SCALAPACK =============================================="
echo "=============================================================================="
echo

echo "--- Référence ---"
nm -D "$PW_REF" 2>/dev/null \
    | grep -Ei 'pdgemm_|pdsyev_|pzheev_|pdgesv_|pzgemm_' \
    | head -20 \
    || echo "[INFO] Aucun symbole ScaLAPACK détecté."

echo
echo "--- ScaLAPACK ---"
nm -D "$PW_SCAL" 2>/dev/null \
    | grep -Ei 'pdgemm_|pdsyev_|pzheev_|pdgesv_|pzgemm_' \
    | head -20 \
    || echo "[INFO] Aucun symbole ScaLAPACK exporté directement."

echo "=============================================================================="
echo "===== 9. LIBRAIRIES RUNTIME ============================================="
echo "=============================================================================="
echo

echo "--- ScaLAPACK système ---"
ldconfig -p 2>/dev/null \
    | grep 'libscalapack-openmpi.so' \
    || true

echo
echo "--- BLAS/LAPACK système ---"
ldconfig -p 2>/dev/null \
    | grep -E 'lib(blas|lapack)\.so' \
    | head -20 \
    || true

echo "=============================================================================="
echo "===== 10. ENVIRONNEMENT MPI ============================================="
echo "=============================================================================="
echo

echo "[INFO] mpif90 :"
command -v mpif90

echo
echo "[INFO] mpirun :"
command -v mpirun

echo
echo "[INFO] OpenMPI :"
mpirun --version | head -3

echo
echo "[INFO] gfortran :"
gfortran --version | head -3

echo "=============================================================================="
echo "===== 11. COMPARAISON BINAIRE ==========================================="
echo "=============================================================================="
echo

if cmp -s "$PW_REF" "$PW_SCAL"; then
    echo "[ERREUR] Les deux pw.x sont identiques."
    echo "[ERREUR] La différenciation ScaLAPACK n'est pas effective."
else
    echo "[OK] Les deux pw.x sont différents."
fi

echo "=============================================================================="
echo "===== 12. RÉSUMÉ ========================================================="
echo "=============================================================================="
echo

echo "[REF]"
echo "  $PW_REF"
echo "  SHA256 = $(sha256sum "$PW_REF" | awk '{print $1}')"

echo
echo "[SCALAPACK]"
echo "  $PW_SCAL"
echo "  SHA256 = $(sha256sum "$PW_SCAL" | awk '{print $1}')"

echo
if ldd "$PW_SCAL" | grep -q 'libscalapack-openmpi'; then
    echo "[OK] Build ScaLAPACK correctement liée."
else
    echo "[ERREUR] Build ScaLAPACK non détectée dans ldd."
fi

echo
echo "=============================================================================="
echo "PHASE 78.73 TERMINÉE"
echo "=============================================================================="
