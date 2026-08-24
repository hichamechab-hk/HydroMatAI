#!/usr/bin/env bash

set -u

PROJECT="$HOME/HydroMatAI"
cd "$PROJECT" || exit 1

if [[ -f "$PROJECT/.venv/bin/activate" ]]; then
    source "$PROJECT/.venv/bin/activate"
fi

echo "============================================================"
echo " HydroMatAI - AUTOMATIC PROPERTY ANALYSIS"
echo "============================================================"

RESULTS="$PROJECT/results"
ELECTRONIC="$RESULTS/electronic"
OPTICAL="$RESULTS/optical"
FIGURES="$RESULTS/figures"
REPORTS="$RESULTS/reports"
INTERPRETATIONS="$RESULTS/interpretations"

mkdir -p \
    "$ELECTRONIC" \
    "$OPTICAL" \
    "$FIGURES" \
    "$REPORTS" \
    "$INTERPRETATIONS"

echo
echo "[1/6] Vérification Python"
python --version

echo
echo "[2/6] Vérification HydroMatAI"

python - <<'PY'
from hydromatai.properties.electronic import *
from hydromatai.properties.optical import *
from hydromatai.analysis.convergence import *
from hydromatai.analysis.interpretation import *
from hydromatai.visualization.electronic_plots import *
from hydromatai.visualization.optical_plots import *
from hydromatai.reports.property_report import *

print("[OK] Electronic")
print("[OK] Optical")
print("[OK] Convergence")
print("[OK] Interpretation")
print("[OK] Electronic plots")
print("[OK] Optical plots")
print("[OK] Reports")
PY

echo
echo "[3/6] Recherche des résultats QE disponibles"

QE_OUTPUTS=()

while IFS= read -r file; do
    QE_OUTPUTS+=("$file")
done < <(
    find /tmp "$PROJECT" \
        -type f \
        \( -name "*.out" -o -name "*.log" \) \
        2>/dev/null |
    grep -Ei 'QE|C_H2|HydroMatAI|scf|relax|bench' |
    head -50
)

if [[ ${#QE_OUTPUTS[@]} -eq 0 ]]; then
    echo "[INFO] Aucun fichier QE approprié détecté."
else
    echo "[OK] Résultats détectés : ${#QE_OUTPUTS[@]}"
    for f in "${QE_OUTPUTS[@]}"; do
        echo "     $f"
    done
fi

echo
echo "[4/6] Préparation des répertoires de résultats"

touch "$ELECTRONIC/.gitkeep"
touch "$OPTICAL/.gitkeep"
touch "$FIGURES/.gitkeep"
touch "$REPORTS/.gitkeep"
touch "$INTERPRETATIONS/.gitkeep"

echo "[OK] Répertoires créés"

echo
echo "[5/6] Vérification des tests"

if python -m pytest -q; then
    echo "[OK] Tests Python réussis"
else
    echo "[WARNING] Certains tests échouent."
fi

echo
echo "[6/6] Génération du manifeste"

cat > "$RESULTS/analysis_manifest.txt" <<EOF
HydroMatAI Automatic Property Analysis
======================================

Date:
$(date)

Project:
$PROJECT

Electronic:
$ELECTRONIC

Optical:
$OPTICAL

Figures:
$FIGURES

Reports:
$REPORTS

Interpretations:
$INTERPRETATIONS

QE calculations:
Les calculs QE existants n'ont pas été lancés,
arrêtés ou modifiés par ce script.

Status:
Infrastructure d'analyse prête.
EOF

echo "[OK] Manifest créé : $RESULTS/analysis_manifest.txt"

echo
echo "============================================================"
echo " ANALYSE HYDROMATAI TERMINÉE"
echo "============================================================"

echo
echo "Résultats :"
echo "  $RESULTS"

echo
echo "Important :"
echo "  Aucun nouveau calcul pw.x n'a été lancé."
echo "  Les calculs QE existants n'ont pas été interrompus."

echo
