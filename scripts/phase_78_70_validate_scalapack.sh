#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

SCALAPACK="/usr/lib/x86_64-linux-gnu/libscalapack-openmpi.so.2.2.1"
SCALAPACK_LINK="/usr/lib/x86_64-linux-gnu/libscalapack-openmpi.so"
MPI_LIB="/lib/x86_64-linux-gnu/libmpi.so.40"
LAPACK_LIB="/lib/x86_64-linux-gnu/liblapack.so.3"
BLAS_LIB="/lib/x86_64-linux-gnu/libblas.so.3"

echo "=============================================================================="
echo "PHASE 78.70 — VALIDATION READ-ONLY SCALAPACK 2.2.1"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x lancé"
echo "[INFO] Aucun calcul scientifique"
echo "[INFO] Aucun fichier scientifique modifié"
echo "[INFO] Aucune modification QE"
echo

echo "=============================================================================="
echo "===== 1. INVENTAIRE SCALAPACK ==========================================="
echo "=============================================================================="
echo

for F in "$SCALAPACK" "$SCALAPACK_LINK"; do
    if [[ -e "$F" || -L "$F" ]]; then
        echo "[OK] $F"
        ls -lh "$F"
        readlink -f "$F" || true
    else
        echo "[ABSENT] $F"
    fi
done

echo
echo "--- Version Debian ---"
dpkg-query -W -f='${Package}\t${Version}\n' \
    libscalapack-openmpi2.2 libscalapack-openmpi-dev 2>/dev/null \
    || true

echo
echo "=============================================================================="
echo "===== 2. DÉPENDANCES SCALAPACK =========================================="
echo "=============================================================================="
echo

if [[ -f "$SCALAPACK" ]]; then
    ldd "$SCALAPACK"
else
    echo "[ERREUR] Bibliothèque ScaLAPACK absente."
fi

echo
echo "--- Dépendances BLAS/LAPACK/MPI ---"
if [[ -f "$SCALAPACK" ]]; then
    ldd "$SCALAPACK" | grep -Ei \
        'blas|lapack|mpi|open-rte|open-pal|gfortran|quadmath' \
        || true
fi

echo "=============================================================================="
echo "===== 3. READelf — INFORMATIONS ELF ====================================="
echo "=============================================================================="
echo

if command -v readelf >/dev/null 2>&1 && [[ -f "$SCALAPACK" ]]; then

    echo "--- Architecture ---"
    readelf -h "$SCALAPACK" | grep -Ei \
        'Class|Machine|Type' || true

    echo
    echo "--- SONAME ---"
    readelf -d "$SCALAPACK" | grep -Ei \
        'SONAME|NEEDED' || true

    echo
    echo "--- RPATH / RUNPATH ---"
    readelf -d "$SCALAPACK" | grep -Ei \
        'RPATH|RUNPATH' || echo "[INFO] Aucun RPATH/RUNPATH."

fi

echo "=============================================================================="
echo "===== 4. SYMBOLES DE DIAGONALISATION ==================================="
echo "=============================================================================="
echo

if command -v nm >/dev/null 2>&1 && [[ -f "$SCALAPACK" ]]; then

    echo "--- Eigenvalue routines ---"

    nm -D "$SCALAPACK" 2>/dev/null | grep -Ei \
        'pdsyev|pdsyevd|pdsyevx|pdsyevr|pcheev|pzheev|pzheevd|pzheevx|pzheevr|pssyev|pssyevd' \
        | head -100 \
        || echo "[INFO] Aucun symbole eigenvalue ciblé trouvé."

    echo
    echo "--- BLAS distribuées ---"

    nm -D "$SCALAPACK" 2>/dev/null | grep -Ei \
        'pdgemm|pdgemv|pdpotrf|pdtrsm|pdsytrd|pdsyr2k|pdgemr2d' \
        | head -100 \
        || echo "[INFO] Aucun symbole BLAS distribué ciblé trouvé."

fi

echo "=============================================================================="
echo "===== 5. HEADERS / MODULES =============================================="
echo "=============================================================================="
echo

echo "--- Fichiers de développement ScaLAPACK ---"

find /usr/include \
     /usr/lib/x86_64-linux-gnu \
     -type f \
     \( \
       -iname '*scalapack*.h' \
       -o -iname '*scalapack*.mod' \
       -o -iname '*blacs*.h' \
       -o -iname '*blacs*.mod' \
     \) \
     -print 2>/dev/null \
     | head -100

echo
echo "--- Bibliothèques statiques/dynamiques ---"

find /usr/lib/x86_64-linux-gnu \
     -maxdepth 2 \
     -type f \
     \( \
       -iname '*scalapack*' \
       -o -iname '*blacs*' \
     \) \
     -print 2>/dev/null \
     | head -100

echo "=============================================================================="
echo "===== 6. BLAS / LAPACK UTILISÉS PAR SCALAPACK ==========================="
echo "=============================================================================="
echo

echo "--- BLAS système ---"
ls -lh "$BLAS_LIB" 2>/dev/null || true
readlink -f "$BLAS_LIB" 2>/dev/null || true

echo
echo "--- LAPACK système ---"
ls -lh "$LAPACK_LIB" 2>/dev/null || true
readlink -f "$LAPACK_LIB" 2>/dev/null || true

echo
echo "--- BLAS/LAPACK dans ScaLAPACK ---"

if [[ -f "$SCALAPACK" ]]; then
    ldd "$SCALAPACK" | grep -Ei \
        'blas|lapack' \
        || true
fi

echo "=============================================================================="
echo "===== 7. MPI COMPATIBILITÉ =============================================="
echo "=============================================================================="
echo

echo "--- MPI système ---"
ls -lh "$MPI_LIB" 2>/dev/null || true
readlink -f "$MPI_LIB" 2>/dev/null || true

echo
echo "--- MPI utilisé par ScaLAPACK ---"

if [[ -f "$SCALAPACK" ]]; then
    ldd "$SCALAPACK" | grep -Ei \
        'libmpi|libopen-rte|libopen-pal' \
        || true
fi

echo
echo "--- OpenMPI ---"
mpirun --version 2>/dev/null | head -5 || true

echo "=============================================================================="
echo "===== 8. PKG-CONFIG / FLAGS DE COMPILATION ============================="
echo "=============================================================================="
echo

echo "--- fichiers pkg-config ---"

find /usr/lib/x86_64-linux-gnu/pkgconfig \
     /usr/share/pkgconfig \
     -type f \
     \( \
       -iname '*scalapack*.pc' \
       -o -iname '*blas*.pc' \
       -o -iname '*lapack*.pc' \
     \) \
     -print 2>/dev/null \
     | head -100

echo
echo "--- Flags ScaLAPACK potentiels ---"

for PC in \
    /usr/lib/x86_64-linux-gnu/pkgconfig/scalapack*.pc \
    /usr/lib/x86_64-linux-gnu/pkgconfig/scalapack-openmpi*.pc
do
    if [[ -f "$PC" ]]; then
        echo "--- $PC ---"
        cat "$PC"
    fi
done

echo "=============================================================================="
echo "===== 9. LIEN AVEC QE ACTUEL ============================================"
echo "=============================================================================="
echo

QE="/home/hk/software/qe-7.5"
PW="$QE/bin/pw.x"

echo "--- QE make.inc ---"

if [[ -f "$QE/make.inc" ]]; then
    grep -E \
        '^(MPIF90|LD|BLAS_LIBS|LAPACK_LIBS|SCALAPACK_LIBS|FFT_LIBS|MPI_LIBS)' \
        "$QE/make.inc" \
        || true
else
    echo "[INFO] make.inc absent."
fi

echo
echo "--- pw.x actuel ---"

ldd "$PW" 2>/dev/null | grep -Ei \
    'scalapack|blas|lapack|mpi' \
    || true

echo
echo "[IMPORTANT]"
echo "La présence de ScaLAPACK système ne signifie PAS que le pw.x actuel"
echo "l'utilise. Cette phase vérifie uniquement la bibliothèque disponible."

echo "=============================================================================="
echo "===== 10. TESTS NON-SCIENTIFIQUES ======================================"
echo "=============================================================================="
echo

echo "[INFO] Aucun calcul matriciel QE."
echo "[INFO] Aucun lancement MPI."
echo "[INFO] Vérification limitée à ELF, symboles et dépendances."

echo
echo "--- Test de lecture bibliothèque ---"

if [[ -f "$SCALAPACK" ]]; then
    file "$SCALAPACK"
    echo "[OK] Bibliothèque ScaLAPACK lisible."
else
    echo "[FAIL] Bibliothèque ScaLAPACK introuvable."
fi

echo "=============================================================================="
echo "===== 11. RÉSUMÉ ========================================================"
echo "=============================================================================="
echo

if [[ -f "$SCALAPACK" ]]; then
    echo "[OK] ScaLAPACK 2.2.1 présente."
else
    echo "[FAIL] ScaLAPACK absente."
fi

if ldd "$SCALAPACK" 2>/dev/null | grep -q 'libmpi'; then
    echo "[OK] ScaLAPACK liée à MPI."
else
    echo "[ATTENTION] Dépendance MPI non détectée."
fi

if ldd "$SCALAPACK" 2>/dev/null | grep -q 'liblapack'; then
    echo "[OK] ScaLAPACK liée à LAPACK."
else
    echo "[ATTENTION] LAPACK non détecté dans les dépendances."
fi

if ldd "$SCALAPACK" 2>/dev/null | grep -q 'libblas'; then
    echo "[OK] ScaLAPACK liée à BLAS."
else
    echo "[ATTENTION] BLAS non détecté dans les dépendances."
fi

echo
echo "=============================================================================="
echo "PHASE 78.70 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] READ-ONLY"
echo "[INFO] Aucun pw.x lancé."
echo "[INFO] Aucun calcul scientifique."
echo "[INFO] Aucun fichier modifié."
echo
