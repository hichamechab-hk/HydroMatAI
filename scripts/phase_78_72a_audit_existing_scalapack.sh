#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE_REF="/home/hk/software/qe-7.5"
QE_SCAL="/home/hk/software/qe-7.5-scalapack"

echo "=============================================================================="
echo "PHASE 78.72A — AUDIT BUILD SCALAPACK EXISTANTE"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun fichier modifié"
echo "[INFO] Aucun fichier supprimé"
echo "[INFO] Aucun pw.x lancé"
echo

if [[ ! -d "$QE_SCAL" ]]; then
    echo "[ERREUR] Répertoire absent : $QE_SCAL"
    exit 1
fi

echo "=============================================================================="
echo "===== 1. INVENTAIRE ====================================================="
echo "=============================================================================="
echo

echo "[INFO] Répertoire :"
ls -ld "$QE_SCAL"

echo
echo "[INFO] Taille :"
du -sh "$QE_SCAL" 2>/dev/null || true

echo
echo "[INFO] make.inc :"
if [[ -f "$QE_SCAL/make.inc" ]]; then
    grep -E \
        '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
        "$QE_SCAL/make.inc" \
        || true
else
    echo "[ABSENT]"
fi

echo "=============================================================================="
echo "===== 2. CONFIGURE ======================================================="
echo "=============================================================================="
echo

for F in configure.msg config.log config.status; do
    if [[ -f "$QE_SCAL/$F" ]]; then
        echo "[OK] $F présent"
    else
        echo "[ABSENT] $F"
    fi
done

echo
echo "--- traces ScaLAPACK ---"

grep -Rni \
    -E 'scalapack|SCALAPACK_LIBS' \
    "$QE_SCAL/configure.msg" \
    "$QE_SCAL/config.log" \
    "$QE_SCAL/make.inc" \
    2>/dev/null \
    | head -100 || true

echo "=============================================================================="
echo "===== 3. PW.X ============================================================="
echo "=============================================================================="
echo

if [[ -x "$QE_SCAL/bin/pw.x" ]]; then
    echo "[OK] pw.x présent :"
    ls -lh "$QE_SCAL/bin/pw.x"

    echo
    echo "[INFO] SHA256 :"
    sha256sum "$QE_SCAL/bin/pw.x"

    echo
    echo "[INFO] ldd :"
    ldd "$QE_SCAL/bin/pw.x" \
        | grep -Ei \
        'scalapack|lapack|blas|mpi|fftw|open-rte|open-pal' \
        || true

    echo
    echo "[INFO] ScaLAPACK liée ?"
    if ldd "$QE_SCAL/bin/pw.x" \
        | grep -q 'libscalapack-openmpi'; then
        echo "[OK] OUI — pw.x utilise ScaLAPACK."
    else
        echo "[INFO] NON — aucune liaison ScaLAPACK détectée."
    fi
else
    echo "[ABSENT] $QE_SCAL/bin/pw.x"
fi

echo "=============================================================================="
echo "===== 4. OBJETS COMPILÉS ================================================="
echo "=============================================================================="
echo

echo "[INFO] Quelques fichiers compilés :"

find "$QE_SCAL" \
    -type f \
    \( -name '*.o' -o -name '*.a' -o -name '*.mod' \) \
    2>/dev/null \
    | head -50 || true

echo
echo "[INFO] Nombre approximatif :"
find "$QE_SCAL" \
    -type f \
    \( -name '*.o' -o -name '*.a' -o -name '*.mod' \) \
    2>/dev/null \
    | wc -l

echo "=============================================================================="
echo "===== 5. DIFFÉRENCE AVEC BUILD RÉFÉRENCE ================================"
echo "=============================================================================="
echo

echo "--- make.inc référence ---"
if [[ -f "$QE_REF/make.inc" ]]; then
    grep -E \
        '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
        "$QE_REF/make.inc" \
        || true
fi

echo
echo "--- make.inc ScaLAPACK ---"
if [[ -f "$QE_SCAL/make.inc" ]]; then
    grep -E \
        '^(DFLAGS|MPIF90|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
        "$QE_SCAL/make.inc" \
        || true
fi

echo "=============================================================================="
echo "===== 6. DATE DES FICHIERS ================================================="
echo "=============================================================================="
echo

if [[ -f "$QE_SCAL/bin/pw.x" ]]; then
    stat "$QE_SCAL/bin/pw.x" \
        | grep -E 'File:|Size:|Modify:|Change:' \
        || true
fi

echo "=============================================================================="
echo "===== 7. GIT / VERSION ==================================================="
echo "=============================================================================="
echo

if [[ -d "$QE_SCAL/.git" ]]; then
    cd "$QE_SCAL"
    git status --short 2>/dev/null || true
    git rev-parse HEAD 2>/dev/null || true
    git describe --tags --always 2>/dev/null || true
else
    echo "[INFO] Pas de dépôt Git local."
fi

echo
echo "=============================================================================="
echo "PHASE 78.72A TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] Aucun fichier modifié."
echo "[INFO] Ne pas supprimer la build avant examen de cette sortie."
echo
