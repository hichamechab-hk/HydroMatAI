#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# HydroMatAI - MASTER SETUP SAFE
# ============================================================
# Ce script :
#   - vérifie HydroMatAI
#   - vérifie Python
#   - vérifie Quantum ESPRESSO sans lancer pw.x
#   - vérifie MPI / OpenMP
#   - prépare Electronic Properties
#   - prépare Optical Properties
#   - prépare Analysis / Visualization / Reports
#   - vérifie les tests Python
#   - vérifie les calculs QE en cours
#
# IMPORTANT :
#   Ce script NE lance aucun calcul QE.
#   Il NE supprime aucun fichier QE.
#   Il NE touche pas aux calculs dans /tmp.
# ============================================================

PROJECT="${HOME}/HydroMatAI"
QE="${HOME}/software/qe-7.5/bin/pw.x"
PYTHON="${PROJECT}/.venv/bin/python"
PIP="${PROJECT}/.venv/bin/pip"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

export HYDROMATAI_QE="${QE}"
export HYDROMATAI_MPI="${HYDROMATAI_MPI:-4}"

echo
echo "============================================================"
echo "             HydroMatAI - MASTER SETUP SAFE"
echo "============================================================"
echo

# ============================================================
# 1. PROJET
# ============================================================

echo "------------------------------------------------------------"
echo "[1/8] PROJET"
echo "------------------------------------------------------------"

if [[ ! -d "$PROJECT" ]]; then
    echo "ERREUR : projet HydroMatAI introuvable :"
    echo "$PROJECT"
    exit 1
fi

cd "$PROJECT"

echo "Projet : $PROJECT"
echo "Répertoire : $(pwd)"

# ============================================================
# 2. GIT
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[2/8] GIT"
echo "------------------------------------------------------------"

if command -v git >/dev/null 2>&1 && [[ -d ".git" ]]; then

    echo "Branche : $(git branch --show-current 2>/dev/null || echo unknown)"

    echo
    echo "État Git :"
    git status --short || true

else

    echo "AVERTISSEMENT : dépôt Git non détecté."

fi

# ============================================================
# 3. PYTHON
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[3/8] PYTHON"
echo "------------------------------------------------------------"

if [[ ! -x "$PYTHON" ]]; then
    echo "ERREUR : Python du venv introuvable :"
    echo "$PYTHON"
    exit 1
fi

echo "Python :"
"$PYTHON" --version

echo
echo "Pip :"

if [[ -x "$PIP" ]]; then
    "$PIP" --version
else
    echo "AVERTISSEMENT : pip du venv introuvable."
fi

# ============================================================
# 4. QUANTUM ESPRESSO
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[4/8] QUANTUM ESPRESSO"
echo "------------------------------------------------------------"

if [[ ! -x "$QE" ]]; then
    echo "ERREUR : pw.x introuvable :"
    echo "$QE"
    exit 1
fi

echo "pw.x trouvé :"
ls -lh "$QE"

echo
echo "Chemin réel :"
readlink -f "$QE"

echo
echo "Version QE :"

QE_VERSION=$(
    strings "$QE" 2>/dev/null |
    grep -m1 "Program PWSCF" ||
    true
)

if [[ -n "$QE_VERSION" ]]; then
    echo "$QE_VERSION"
else
    echo "Quantum ESPRESSO détecté."
    echo "Chemin : $QE"
fi

echo
echo "Aucun calcul pw.x n'a été lancé."

# ============================================================
# 5. MPI / OPENMP
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[5/8] MPI / OPENMP"
echo "------------------------------------------------------------"

echo "MPI :"

if command -v mpirun >/dev/null 2>&1; then
    which mpirun
    mpirun --version | head -2
else
    echo "AVERTISSEMENT : mpirun introuvable."
fi

echo
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "HYDROMATAI_MPI=$HYDROMATAI_MPI"

# ============================================================
# 6. ARCHITECTURE SCIENTIFIQUE
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[6/8] ARCHITECTURE ELECTRONIC / OPTICAL"
echo "------------------------------------------------------------"

mkdir -p \
    src/hydromatai/properties \
    src/hydromatai/properties/electronic \
    src/hydromatai/properties/optical \
    src/hydromatai/analysis \
    src/hydromatai/visualization \
    src/hydromatai/reports \
    tests/properties \
    tests/analysis \
    tests/visualization

create_init() {

    local file="$1"

    if [[ ! -f "$file" ]]; then

        cat > "$file" <<'EOF'
"""HydroMatAI module."""
EOF

        echo "Créé : $file"

    else

        echo "Existe déjà : $file"

    fi
}

create_init \
    src/hydromatai/properties/__init__.py

create_init \
    src/hydromatai/properties/electronic/__init__.py

create_init \
    src/hydromatai/properties/optical/__init__.py

create_init \
    src/hydromatai/analysis/__init__.py

create_init \
    src/hydromatai/visualization/__init__.py

create_init \
    src/hydromatai/reports/__init__.py

echo
echo "Répertoires préparés :"

find src/hydromatai \
    -maxdepth 3 \
    -type d \
    | sort

# ============================================================
# 7. TESTS PYTHON
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[7/8] TESTS PYTHON"
echo "------------------------------------------------------------"

if [[ -f "pyproject.toml" ]]; then

    echo "pyproject.toml trouvé."

    if "$PYTHON" -m pytest --collect-only -q \
        > /tmp/hydromatai_pytest_collect.log 2>&1; then

        echo "Collection des tests : OK"

    else

        echo
        echo "ATTENTION : problème lors de la collection des tests."
        echo
        echo "Diagnostic :"
        tail -40 /tmp/hydromatai_pytest_collect.log || true

        echo
        echo "Le script continue."

    fi

else

    echo "AVERTISSEMENT : pyproject.toml absent."
    echo "Tests ignorés."

fi

# ============================================================
# 8. CALCULS QE EN COURS
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[8/8] CALCULS QE EN COURS"
echo "------------------------------------------------------------"

echo "Recherche des processus pw.x / mpirun..."

QE_PROCESSES=$(
    ps aux |
    grep -E 'pw\.x|mpirun' |
    grep -v grep ||
    true
)

if [[ -n "$QE_PROCESSES" ]]; then

    echo
    echo "ATTENTION : calcul(s) QE actuellement actif(s) :"
    echo
    echo "$QE_PROCESSES"

else

    echo "Aucun processus pw.x/mpirun actif détecté."

fi

# ============================================================
# RESUME
# ============================================================

echo
echo
echo "============================================================"
echo "                    RÉSUMÉ FINAL"
echo "============================================================"

echo
echo "Projet :"
echo "  $PROJECT"

echo
echo "Python :"
echo "  $PYTHON"

echo
echo "Quantum ESPRESSO :"
echo "  $QE"

echo
echo "MPI recommandé :"
echo "  $HYDROMATAI_MPI"

echo
echo "OpenMP :"
echo "  $OMP_NUM_THREADS"

echo
echo "Modules préparés :"
echo "  [OK] Electronic Properties"
echo "  [OK] Optical Properties"
echo "  [OK] Analysis"
echo "  [OK] Visualization"
echo "  [OK] Reports"

echo
echo "Calculs QE :"

if [[ -n "$QE_PROCESSES" ]]; then
    echo "  [ACTIFS] Des calculs QE sont en cours."
else
    echo "  [LIBRES] Aucun calcul QE détecté."
fi

echo
echo "============================================================"
echo "             SETUP HYDROMATAI TERMINÉ"
echo "============================================================"
echo
echo "Aucun calcul QE n'a été lancé par ce script."
echo
