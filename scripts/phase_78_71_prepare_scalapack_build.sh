#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE="/home/hk/software/qe-7.5"
SCALAPACK_PC="/usr/lib/x86_64-linux-gnu/pkgconfig/scalapack-openmpi.pc"

echo "=============================================================================="
echo "PHASE 78.71 — PRÉPARATION BUILD QE + SCALAPACK"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucune compilation"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun calcul scientifique"
echo "[INFO] Aucun fichier QE modifié"
echo

echo "=============================================================================="
echo "===== 1. VERSIONS COMPILATEURS =========================================="
echo "=============================================================================="
echo

echo "--- gfortran ---"
command -v gfortran || true
gfortran --version | head -3 || true

echo
echo "--- gcc ---"
command -v gcc || true
gcc --version | head -3 || true

echo
echo "--- mpif90 ---"
command -v mpif90 || true
mpif90 --version | head -5 || true

echo
echo "--- mpif90 wrapper ---"
mpif90 --show 2>/dev/null || true
mpif90 --showme 2>/dev/null || true

echo "=============================================================================="
echo "===== 2. PKG-CONFIG SCALAPACK ==========================================="
echo "=============================================================================="
echo

if command -v pkg-config >/dev/null 2>&1; then

    echo "--- Nom détecté ---"
    pkg-config --list-all 2>/dev/null \
        | grep -Ei 'scalapack|blas|lapack|mpi' \
        | head -50 || true

    echo
    echo "--- scalapack-openmpi ---"
    pkg-config --modversion scalapack-openmpi 2>/dev/null || true

    echo
    echo "--- CFLAGS ---"
    pkg-config --cflags scalapack-openmpi 2>/dev/null || true

    echo
    echo "--- LIBS ---"
    pkg-config --libs scalapack-openmpi 2>/dev/null || true

    echo
    echo "--- LIBS détaillées ---"
    pkg-config --libs-only-L scalapack-openmpi 2>/dev/null || true
    pkg-config --libs-only-l scalapack-openmpi 2>/dev/null || true
fi

echo "=============================================================================="
echo "===== 3. FICHIER PKG-CONFIG ============================================="
echo "=============================================================================="
echo

if [[ -f "$SCALAPACK_PC" ]]; then
    cat "$SCALAPACK_PC"
else
    echo "[ERREUR] $SCALAPACK_PC absent."
fi

echo "=============================================================================="
echo "===== 4. FICHIERS DE DÉVELOPPEMENT ====================================="
echo "=============================================================================="
echo

echo "--- ScaLAPACK ---"
dpkg -L libscalapack-openmpi-dev 2>/dev/null \
    | grep -Ei \
    'include|libscalapack|scalapack|blacs' \
    | head -100 || true

echo
echo "--- BLAS/LAPACK ---"
dpkg -L libblas-dev liblapack-dev 2>/dev/null \
    | grep -Ei \
    'include|\.a$|\.so$' \
    | head -100 || true

echo "=============================================================================="
echo "===== 5. LIBRAIRIES D'ÉDITION DE LIENS ================================"
echo "=============================================================================="
echo

for LIB in \
    /usr/lib/x86_64-linux-gnu/libscalapack-openmpi.so \
    /usr/lib/x86_64-linux-gnu/libscalapack-openmpi.so.2.2.1 \
    /usr/lib/x86_64-linux-gnu/libblas.so \
    /usr/lib/x86_64-linux-gnu/liblapack.so
do
    echo
    if [[ -e "$LIB" || -L "$LIB" ]]; then
        echo "[OK] $LIB"
        ls -lh "$LIB"
        readlink -f "$LIB" || true
    else
        echo "[ABSENT] $LIB"
    fi
done

echo "=============================================================================="
echo "===== 6. QE 7.5 — CONFIGURATION ========================================"
echo "=============================================================================="
echo

echo "--- Répertoire QE ---"
ls -ld "$QE"

echo
echo "--- make.inc actuel ---"
if [[ -f "$QE/make.inc" ]]; then
    grep -E \
        '^(MPIF90|F90|FC|LD|LDFLAGS|LD_LIBS|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
        "$QE/make.inc" \
        || true
fi

echo
echo "--- Options ScaLAPACK dans configure ---"
grep -E \
    -- '--with-scalapack|--with-scalapack-qrcp|--with-elpa|--enable-openmp' \
    "$QE/install/configure" 2>/dev/null \
    | head -30 || true

echo "=============================================================================="
echo "===== 7. CMAKE / BUILD SUPPORT ========================================="
echo "=============================================================================="
echo

if command -v cmake >/dev/null 2>&1; then
    echo "--- cmake ---"
    cmake --version | head -2
else
    echo "[INFO] cmake absent."
fi

echo
echo "--- fichiers CMake QE ---"
find "$QE" \
    -maxdepth 3 \
    -type f \
    \( \
        -iname 'CMakeLists.txt' \
        -o -iname '*scalapack*' \
        -o -iname '*laxlib*' \
    \) \
    -print 2>/dev/null \
    | head -100

echo "=============================================================================="
echo "===== 8. VARIABLES ENVIRONNEMENT ======================================="
echo "=============================================================================="
echo

env | grep -E \
    '^(PATH|LD_LIBRARY_PATH|LIBRARY_PATH|CPATH|PKG_CONFIG_PATH|FC|F90|CC|MPIF90)=' \
    | sort || true

echo "=============================================================================="
echo "===== 9. CHEMINS BIBLIOTHÈQUES =========================================="
echo "=============================================================================="
echo

echo "--- ldconfig ScaLAPACK ---"
ldconfig -p 2>/dev/null \
    | grep -Ei 'scalapack|blas|lapack' \
    | head -50 || true

echo
echo "--- pkg-config paths ---"
pkg-config --variable pc_path pkg-config 2>/dev/null || true

echo "=============================================================================="
echo "===== 10. TEST DE LIEN MINIMAL NON-SCIENTIFIQUE ========================"
echo "=============================================================================="
echo

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/test_scalapack.f90" <<'EOF'
program test_scalapack
  implicit none
  integer :: ctxt
  print *, "SCALAPACK_LINK_TEST"
end program test_scalapack
EOF

echo "[INFO] Test demandé : vérification de l'édition de liens uniquement."
echo "[INFO] Aucun calcul scientifique."

if mpif90 "$TMPDIR/test_scalapack.f90" \
    $(pkg-config --libs scalapack-openmpi 2>/dev/null) \
    -o "$TMPDIR/test_scalapack" \
    >/dev/null 2>&1; then

    echo "[OK] Édition de liens avec les flags pkg-config réussie."

    echo
    echo "--- Dépendances du test ---"
    ldd "$TMPDIR/test_scalapack" \
        | grep -Ei \
        'scalapack|blas|lapack|mpi|open-rte|open-pal' \
        || true
else
    echo "[FAIL] Édition de liens avec ScaLAPACK impossible."
    echo "[INFO] Aucun fichier QE n'a été modifié."
fi

echo "=============================================================================="
echo "===== 11. RÉSUMÉ ========================================================"
echo "=============================================================================="
echo

echo "[INFO] ScaLAPACK :"
pkg-config --modversion scalapack-openmpi 2>/dev/null \
    || echo "[ABSENT] pkg-config"

echo
echo "[INFO] Flags :"
pkg-config --libs scalapack-openmpi 2>/dev/null \
    || true

echo
echo "[INFO] MPI :"
mpif90 --show 2>/dev/null || true

echo
echo "[INFO] Build QE actuelle :"
grep -E '^SCALAPACK_LIBS' "$QE/make.inc" 2>/dev/null || true

echo
echo "=============================================================================="
echo "PHASE 78.71 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] READ-ONLY pour QE."
echo "[INFO] Le test de lien utilise uniquement /tmp."
echo "[INFO] Aucun pw.x lancé."
echo "[INFO] Aucun calcul scientifique."
echo
