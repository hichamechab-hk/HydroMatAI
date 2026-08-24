#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/HydroMatAI"
ROOT="$BASE/results/scientific_analysis/optical"

mkdir -p "$ROOT"/{inputs,outputs,figures,reports}

echo "============================================================"
echo " HydroMatAI - OPTICAL PLATFORM"
echo "============================================================"

echo
echo "[1/6] Vérification Python"

source "$BASE/.venv/bin/activate"

python --version

echo
echo "[2/6] Vérification des modules"

python - <<'PY'
from hydromatai.properties.electronic import *
from hydromatai.properties.optical import *
from hydromatai.analysis.interpretation import *
from hydromatai.visualization.electronic_plots import *
from hydromatai.visualization.optical_plots import *
from hydromatai.reports.property_report import *

print("[OK] Electronic")
print("[OK] Optical")
print("[OK] Interpretation")
print("[OK] Electronic visualization")
print("[OK] Optical visualization")
print("[OK] Reports")
PY

echo
echo "[3/6] Préparation des propriétés optiques"

cat > "$ROOT/inputs/optical_targets.txt" <<'EOF'
HydroMatAI - Optical Properties
===============================

PROPRIETÉS À EXTRAIRE

1. Dielectric function
   epsilon_1(E)
   epsilon_2(E)

2. Refractive index
   n(E)

3. Extinction coefficient
   k(E)

4. Reflectivity
   R(E)

5. Absorption coefficient
   alpha(E)

6. Optical conductivity
   sigma(E)

7. Energy-loss function
   L(E)

8. Optical band-edge

INTERPRÉTATION

Le rapport devra discuter :

- régions de forte absorption ;
- seuil optique ;
- comportement de epsilon_1 ;
- transitions associées à epsilon_2 ;
- indice de réfraction ;
- extinction ;
- réflectivité ;
- potentiel optoélectronique.

IMPORTANT

Les propriétés optiques finales doivent être calculées
à partir des données électroniques QE réellement obtenues.

Aucune valeur artificielle ne doit être utilisée comme
résultat scientifique final.
EOF

echo "[OK] optical_targets.txt"

echo
echo "[4/6] Préparation du rapport"

cat > "$ROOT/reports/optical_workflow.txt" <<'EOF'
HYDROMATAI - OPTICAL WORKFLOW
=============================

SCF
 |
 +--> NSCF
       |
       +--> Electronic states
       |
       +--> Dielectric response
       |
       +--> epsilon_1(E)
       |
       +--> epsilon_2(E)
       |
       +--> n(E)
       |
       +--> k(E)
       |
       +--> R(E)
       |
       +--> alpha(E)
       |
       +--> sigma(E)
       |
       +--> L(E)
       |
       +--> Figures
       |
       +--> Scientific interpretation
       |
       +--> Final report

FIGURES

epsilon_real.png
epsilon_imaginary.png
refractive_index.png
extinction_coefficient.png
reflectivity.png
absorption_coefficient.png
optical_conductivity.png
energy_loss.png
optical_summary.png

STATUS

Platform prepared.
No Quantum ESPRESSO calculation launched.
EOF

echo "[OK] optical_workflow.txt"

echo
echo "[5/6] Vérification des calculs actifs"

ps aux | grep -E '[p]w.x|[m]pirun' || true

echo
echo "[6/6] Manifest"

cat > "$ROOT/reports/optical_manifest.txt" <<EOF
HydroMatAI Optical Platform
===========================

Prepared:
$(date '+%Y-%m-%d %H:%M:%S')

Status:
READY

Calculs QE:
NOT STARTED BY THIS SCRIPT

Active calculations:
NOT MODIFIED

Target properties:
epsilon1
epsilon2
n
k
R
absorption
conductivity
energy loss
EOF

echo
echo "============================================================"
echo " PLATEFORME OPTIQUE PRÊTE"
echo "============================================================"

echo
echo "Aucun calcul QE lancé."
echo "Aucun calcul QE interrompu."
echo
echo "Prochaine étape :"
echo "Données électroniques réelles"
echo "        -> réponse diélectrique"
echo "        -> propriétés optiques"
echo "        -> figures"
echo "        -> interprétation"
echo "        -> rapport scientifique"
echo
