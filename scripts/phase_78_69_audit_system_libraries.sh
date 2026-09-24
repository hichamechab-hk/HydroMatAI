#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE="/home/hk/software/qe-7.5"
PW="$QE/bin/pw.x"

echo "=============================================================================="
echo "PHASE 78.69 — AUDIT SYSTÈME SCALAPACK / ELPA / BLAS / LAPACK"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x lancé"
echo "[INFO] Aucun calcul scientifique"
echo "[INFO] Aucun fichier scientifique modifié"
echo "[INFO] Aucune modification QE"
echo

# -----------------------------------------------------------------------------
# 1. Système
# -----------------------------------------------------------------------------

echo "=============================================================================="
echo "===== 1. SYSTÈME ========================================================"
echo "=============================================================================="
echo

echo "--- OS ---"
cat /etc/os-release 2>/dev/null | grep -E '^(NAME|VERSION)=' || true

echo
echo "--- Architecture ---"
uname -m
uname -r

echo
echo "--- CPU ---"
lscpu 2>/dev/null | grep -E \
    'Model name|Socket|Core|Thread|CPU\(s\)' | head -20 || true

# -----------------------------------------------------------------------------
# 2. Bibliothèques connues par ldconfig
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 2. LDCONFIG — SCALAPACK =========================================="
echo "=============================================================================="
echo

if command -v ldconfig >/dev/null 2>&1; then
    echo "--- ScaLAPACK ---"
    ldconfig -p 2>/dev/null | grep -Ei \
        'scalapack|scalapack-openmpi|scalapack-mpich' \
        || echo "[INFO] ScaLAPACK non trouvé via ldconfig."

    echo
    echo "--- ELPA ---"
    ldconfig -p 2>/dev/null | grep -Ei \
        'elpa' \
        || echo "[INFO] ELPA non trouvé via ldconfig."

    echo
    echo "--- BLAS ---"
    ldconfig -p 2>/dev/null | grep -Ei \
        'libblas|openblas|blis|flexiblas|mkl' \
        | head -50 \
        || echo "[INFO] BLAS alternatif non trouvé via ldconfig."

    echo
    echo "--- LAPACK ---"
    ldconfig -p 2>/dev/null | grep -Ei \
        'liblapack' \
        | head -50 \
        || true
fi

# -----------------------------------------------------------------------------
# 3. Recherche fichiers système
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 3. FICHIERS SCALAPACK / ELPA ====================================="
echo "=============================================================================="
echo

echo "--- /usr/lib /usr/local/lib ---"

find /usr/lib /usr/local/lib \
    -type f \
    \( \
        -iname 'libscalapack*' -o \
        -iname 'libelpa*' -o \
        -iname 'libopenblas*' -o \
        -iname 'libblis*' -o \
        -iname 'libflexiblas*' \
    \) \
    -print 2>/dev/null \
    | head -200

# -----------------------------------------------------------------------------
# 4. Recherche plus large ciblée
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 4. RECHERCHE /OPT /HOME ==========================================="
echo "=============================================================================="
echo

for ROOT in /opt /home/hk/software /home/hk; do
    if [[ -d "$ROOT" ]]; then
        echo
        echo "--- ROOT: $ROOT ---"

        find "$ROOT" \
            -type f \
            \( \
                -iname 'libscalapack*.so*' -o \
                -iname 'libscalapack*.a' -o \
                -iname 'libelpa*.so*' -o \
                -iname 'libelpa*.a' \
            \) \
            -print 2>/dev/null \
            | head -100
    fi
done

# -----------------------------------------------------------------------------
# 5. pkg-config
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 5. PKG-CONFIG ====================================================="
echo "=============================================================================="
echo

if command -v pkg-config >/dev/null 2>&1; then

    echo "--- scalapack ---"
    pkg-config --modversion scalapack 2>/dev/null \
        || echo "[INFO] pkg-config: scalapack absent"

    echo
    echo "--- elpa ---"
    pkg-config --modversion elpa 2>/dev/null \
        || echo "[INFO] pkg-config: elpa absent"

    echo
    echo "--- openblas ---"
    pkg-config --modversion openblas 2>/dev/null \
        || echo "[INFO] pkg-config: openblas absent"

    echo
    echo "--- blas ---"
    pkg-config --modversion blas 2>/dev/null \
        || echo "[INFO] pkg-config: blas absent"

    echo
    echo "--- lapack ---"
    pkg-config --modversion lapack 2>/dev/null \
        || echo "[INFO] pkg-config: lapack absent"
fi

# -----------------------------------------------------------------------------
# 6. Debian packages si disponibles
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 6. PAQUETS SYSTÈME ================================================"
echo "=============================================================================="
echo

if command -v dpkg-query >/dev/null 2>&1; then
    dpkg-query -W -f='${Package}\t${Version}\n' 2>/dev/null \
        | grep -Ei \
        'scalapack|elpa|openblas|blis|flexiblas|lapack|blas|openmpi' \
        | head -100 \
        || echo "[INFO] Aucun paquet correspondant trouvé."
fi

# -----------------------------------------------------------------------------
# 7. OpenMPI
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 7. OPENMPI ========================================================"
echo "=============================================================================="
echo

echo "--- mpirun ---"
command -v mpirun || true
mpirun --version 2>/dev/null | head -10 || true

echo
echo "--- ompi_info ---"

if command -v ompi_info >/dev/null 2>&1; then
    ompi_info 2>/dev/null \
        | grep -Ei \
        'Open MPI|version|scalapack|blas|lapack|elpa|thread|openmp' \
        | head -100 \
        || true
else
    echo "[INFO] ompi_info indisponible."
fi

# -----------------------------------------------------------------------------
# 8. BLAS/LAPACK alternatives
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 8. ALTERNATIVES BLAS / LAPACK ===================================="
echo "=============================================================================="
echo

if command -v update-alternatives >/dev/null 2>&1; then
    echo "--- BLAS ---"
    update-alternatives --display libblas.so-x86_64-linux-gnu 2>/dev/null \
        | head -100 || true

    echo
    echo "--- LAPACK ---"
    update-alternatives --display liblapack.so-x86_64-linux-gnu 2>/dev/null \
        | head -100 || true
fi

# -----------------------------------------------------------------------------
# 9. Vérification exacte des bibliothèques actuelles de pw.x
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 9. BUILD ACTUELLE pw.x ============================================"
echo "=============================================================================="
echo

echo "--- pw.x ---"
ls -lh "$PW"

echo
echo "--- BLAS/LAPACK liés ---"
ldd "$PW" 2>/dev/null \
    | grep -Ei \
    'blas|lapack|openblas|blis|flexiblas|mkl|atlas' \
    || true

echo
echo "--- ScaLAPACK / ELPA liés ---"
ldd "$PW" 2>/dev/null \
    | grep -Ei \
    'scalapack|elpa' \
    || echo "[INFO] Aucun lien ScaLAPACK/ELPA."

# -----------------------------------------------------------------------------
# 10. Recherche headers
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 10. HEADERS / MODULES ============================================="
echo "=============================================================================="
echo

echo "--- ScaLAPACK headers ---"
find /usr/include /usr/local/include /opt /home/hk/software \
    -type f \
    \( \
        -iname '*scalapack*.h' -o \
        -iname '*scalapack*.mod' \
    \) \
    -print 2>/dev/null \
    | head -100

echo
echo "--- ELPA headers/modules ---"
find /usr/include /usr/local/include /opt /home/hk/software \
    -type f \
    \( \
        -iname '*elpa*.h' -o \
        -iname '*elpa*.mod' \
    \) \
    -print 2>/dev/null \
    | head -100

# -----------------------------------------------------------------------------
# 11. Versions éventuelles
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 11. VERSIONS IDENTIFIABLES ======================================="
echo "=============================================================================="
echo

echo "--- OpenBLAS ---"
if command -v openblas_info >/dev/null 2>&1; then
    openblas_info 2>/dev/null | head -50 || true
else
    echo "[INFO] openblas_info absent."
fi

echo
echo "--- ELPA binaries ---"
find /usr /opt /home/hk/software \
    -type f \
    \( -iname 'elpa_*' -o -iname 'elpa' \) \
    -executable \
    -print 2>/dev/null \
    | head -50

# -----------------------------------------------------------------------------
# 12. Résumé
# -----------------------------------------------------------------------------

echo
echo "=============================================================================="
echo "===== 12. RÉSUMÉ ========================================================"
echo "=============================================================================="
echo

HAS_SCALAPACK=0
HAS_ELPA=0
HAS_OPENBLAS=0

if ldconfig -p 2>/dev/null | grep -qi 'scalapack'; then
    HAS_SCALAPACK=1
fi

if ldconfig -p 2>/dev/null | grep -qi 'elpa'; then
    HAS_ELPA=1
fi

if ldconfig -p 2>/dev/null | grep -qi 'openblas'; then
    HAS_OPENBLAS=1
fi

echo "[RESULT] ScaLAPACK système détecté : $HAS_SCALAPACK"
echo "[RESULT] ELPA système détecté      : $HAS_ELPA"
echo "[RESULT] OpenBLAS système détecté  : $HAS_OPENBLAS"

echo
echo "[RESULT] pw.x actuel :"
ldd "$PW" 2>/dev/null | grep -Ei \
    'blas|lapack|scalapack|elpa|openblas|blis|mkl' \
    || true

echo
echo "=============================================================================="
echo "PHASE 78.69 TERMINÉE"
echo "=============================================================================="
echo
echo "[INFO] READ-ONLY"
echo "[INFO] Aucun calcul QE."
echo "[INFO] Aucune modification scientifique."
echo "[INFO] Aucune modification de QE."
echo
