#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE_SRC="/home/hk/software/qe-7.5"
QE_NEW="/home/hk/software/qe-7.5-scalapack"

SCALAPACK_LIBS="-L/usr/lib/x86_64-linux-gnu -lscalapack-openmpi"
BLAS_LIBS="-lblas"
LAPACK_LIBS="-L/usr/lib/x86_64-linux-gnu -llapack -lblas"
FFT_LIBS="-lfftw3"

echo "=============================================================================="
echo "PHASE 78.72 — BUILD QE 7.5 + SCALAPACK"
echo "=============================================================================="
echo
echo "[INFO] MODE = NOUVELLE BUILD ISOLÉE"
echo "[INFO] Source      : $QE_SRC"
echo "[INFO] Destination : $QE_NEW"
echo "[INFO] ScaLAPACK  : 2.2.1"
echo "[INFO] MPI         : OpenMPI"
echo "[INFO] OpenMP      : NON ACTIVÉ"
echo

if [[ ! -x "$QE_SRC/configure" ]]; then
    echo "[ERREUR] configure QE absent : $QE_SRC/configure"
    exit 1
fi

if [[ -e "$QE_NEW" ]]; then
    echo "[ERREUR] Destination déjà existante : $QE_NEW"
    echo
    echo "[INFO] Pour éviter tout écrasement, aucune opération effectuée."
    exit 1
fi

echo "=============================================================================="
echo "===== 1. VÉRIFICATION BUILD DE RÉFÉRENCE ==============================="
echo "=============================================================================="
echo

if [[ ! -x "$QE_SRC/bin/pw.x" ]]; then
    echo "[ERREUR] pw.x de référence absent."
    exit 1
fi

echo "[OK] Build de référence présente :"
ls -lh "$QE_SRC/bin/pw.x"

echo
echo "[INFO] SHA256 pw.x référence :"
sha256sum "$QE_SRC/bin/pw.x"

echo "=============================================================================="
echo "===== 2. VÉRIFICATION SCALAPACK ========================================"
echo "=============================================================================="
echo

if ! ldconfig -p 2>/dev/null \
    | grep -q 'libscalapack-openmpi.so'; then
    echo "[ERREUR] ScaLAPACK OpenMPI non détectée par ldconfig."
    exit 1
fi

echo "[OK] ScaLAPACK détectée."

echo
echo "[INFO] Version pkg-config :"
pkg-config --modversion scalapack-openmpi

echo
echo "[INFO] Bibliothèque :"
ls -lh /usr/lib/x86_64-linux-gnu/libscalapack-openmpi.so*

echo "=============================================================================="
echo "===== 3. COPIE PROPRE DU CODE SOURCE ==================================="
echo "=============================================================================="
echo

echo "[INFO] Création : $QE_NEW"

mkdir -p "$QE_NEW"

echo "[INFO] Copie des sources..."

rsync -a \
    --exclude='.git/' \
    --exclude='*.o' \
    --exclude='*.mod' \
    --exclude='*.a' \
    --exclude='make.inc' \
    --exclude='config.log' \
    --exclude='config.status' \
    --exclude='configure.msg' \
    --exclude='bin/*' \
    "$QE_SRC/" "$QE_NEW/"

echo "[OK] Copie terminée."

echo "=============================================================================="
echo "===== 4. CONFIGURATION QE ==============================================="
echo "=============================================================================="
echo

cd "$QE_NEW"

echo "[INFO] configure avec :"
echo "       --enable-parallel"
echo "       --with-scalapack=yes"
echo

export MPIF90="mpif90"
export LD="mpif90"

export BLAS_LIBS="$BLAS_LIBS"
export LAPACK_LIBS="$LAPACK_LIBS"
export SCALAPACK_LIBS="$SCALAPACK_LIBS"
export FFT_LIBS="$FFT_LIBS"

./configure \
    --enable-parallel \
    --with-scalapack=yes \
    MPIF90="$MPIF90" \
    LD="$LD" \
    BLAS_LIBS="$BLAS_LIBS" \
    LAPACK_LIBS="$LAPACK_LIBS" \
    SCALAPACK_LIBS="$SCALAPACK_LIBS" \
    FFT_LIBS="$FFT_LIBS"

echo
echo "[OK] configure terminé."

echo "=============================================================================="
echo "===== 5. AUDIT MAKE.INC AVANT COMPILATION ============================="
echo "=============================================================================="
echo

if [[ ! -f make.inc ]]; then
    echo "[ERREUR] make.inc non généré."
    exit 1
fi

grep -E \
    '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
    make.inc \
    || true

echo
echo "--- Recherche ScaLAPACK dans configure.msg ---"
grep -i -A5 -B5 scalapack configure.msg 2>/dev/null \
    | head -100 || true

echo "=============================================================================="
echo "===== 6. CONTRÔLE CRITIQUE ============================================="
echo "=============================================================================="
echo

SCALAPACK_LINE="$(grep '^SCALAPACK_LIBS' make.inc || true)"

echo "[INFO] $SCALAPACK_LINE"

if ! grep -q -- '-lscalapack-openmpi' make.inc; then
    echo
    echo "[ERREUR] ScaLAPACK n'est pas présente dans make.inc."
    echo "[INFO] La compilation est arrêtée."
    echo "[INFO] La build de référence n'a pas été modifiée."
    exit 1
fi

echo "[OK] ScaLAPACK configurée dans make.inc."

echo "=============================================================================="
echo "===== 7. COMPILATION PW.X ==============================================="
echo "=============================================================================="
echo

NPROC="$(nproc)"

echo "[INFO] CPU logiques détectés : $NPROC"
echo "[INFO] Compilation parallèle de pw.x"

make -j"$NPROC" pw

echo
echo "[OK] Compilation pw terminée."

echo "=============================================================================="
echo "===== 8. VÉRIFICATION PW.X =============================================="
echo "=============================================================================="
echo

if [[ ! -x bin/pw.x ]]; then
    echo "[ERREUR] bin/pw.x absent après compilation."
    exit 1
fi

echo "[OK] Nouveau pw.x :"
ls -lh bin/pw.x

echo
echo "[INFO] SHA256 nouveau pw.x :"
sha256sum bin/pw.x

echo "=============================================================================="
echo "===== 9. LDD — DÉPENDANCES RUNTIME ====================================="
echo "=============================================================================="
echo

ldd bin/pw.x \
    | grep -Ei \
    'scalapack|lapack|blas|mpi|fftw|open-rte|open-pal' \
    || true

echo
echo "--- Vérification directe ScaLAPACK ---"

if ldd bin/pw.x | grep -q 'libscalapack-openmpi'; then
    echo "[OK] pw.x est lié dynamiquement à ScaLAPACK."
else
    echo "[ERREUR] pw.x ne semble PAS être lié à ScaLAPACK."
    exit 1
fi

echo "=============================================================================="
echo "===== 10. SYMBOLES SCALAPACK ============================================"
echo "=============================================================================="
echo

echo "[INFO] Quelques symboles ScaLAPACK détectables :"

nm -D bin/pw.x 2>/dev/null \
    | grep -Ei \
    'pdgemm|pdsyev|pzheev|pdgesv|pzgemm|scalapack' \
    | head -30 \
    || true

echo "=============================================================================="
echo "===== 11. TEST VERSION PW.X ============================================="
echo "=============================================================================="
echo

bin/pw.x -h 2>&1 | head -25 || true

echo "=============================================================================="
echo "===== 12. RÉSUMÉ ========================================================="
echo "=============================================================================="
echo

echo "[OK] Nouvelle installation :"
echo "     $QE_NEW"

echo
echo "[OK] pw.x ScaLAPACK :"
echo "     $QE_NEW/bin/pw.x"

echo
echo "[OK] Build de référence INCHANGÉE :"
echo "     $QE_SRC/bin/pw.x"

echo
echo "[INFO] Les deux exécutables sont maintenant séparés."

echo
echo "=============================================================================="
echo "PHASE 78.72 TERMINÉE"
echo "=============================================================================="
