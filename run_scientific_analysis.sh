#!/usr/bin/env bash
set -u

PROJECT="$HOME/HydroMatAI"
RESULTS="$PROJECT/results/scientific_analysis"

mkdir -p "$RESULTS"/{electronic,optical,figures,reports,logs}

echo "============================================================"
echo " HydroMatAI - SCIENTIFIC PROPERTY ANALYSIS"
echo "============================================================"
echo
echo "[INFO] Aucun calcul Quantum ESPRESSO ne sera lancé."
echo "[INFO] Les calculs QE actuellement actifs ne seront pas touchés."
echo

cd "$PROJECT"

# ------------------------------------------------------------
# 1. ENVIRONNEMENT
# ------------------------------------------------------------
echo "------------------------------------------------------------"
echo "[1/7] ENVIRONNEMENT"
echo "------------------------------------------------------------"

if [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
else
    echo "[ERREUR] Environnement Python .venv introuvable."
    exit 1
fi

echo "Python : $(python --version)"
echo

# ------------------------------------------------------------
# 2. TEST DES MODULES
# ------------------------------------------------------------
echo "------------------------------------------------------------"
echo "[2/7] MODULES SCIENTIFIQUES"
echo "------------------------------------------------------------"

python - <<'PY'
from hydromatai.dft.quantum_espresso.parser import QEParser
from hydromatai.properties.electronic.analyzer import interpret_band_gap
from hydromatai.properties.optical import *
from hydromatai.analysis.convergence import *
from hydromatai.analysis.interpretation import *
from hydromatai.visualization.electronic_plots import *
from hydromatai.visualization.optical_plots import *
from hydromatai.reports.property_report import create_report

print("[OK] QE parser")
print("[OK] Electronic analyzer")
print("[OK] Optical analyzer")
print("[OK] Convergence analysis")
print("[OK] Scientific interpretation")
print("[OK] Electronic visualization")
print("[OK] Optical visualization")
print("[OK] Automatic report")
PY

# ------------------------------------------------------------
# 3. COLLECTE DES SORTIES QE
# ------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "[3/7] RECHERCHE DES SORTIES QE"
echo "------------------------------------------------------------"

mapfile -t QE_OUTPUTS < <(
    find /tmp "$PROJECT/calculations" \
        -type f \
        \( -name "*.out" -o -name "*.log" \) \
        -print 2>/dev/null |
    sort
)

echo "Sorties QE détectées : ${#QE_OUTPUTS[@]}"

# ------------------------------------------------------------
# 4. EXTRACTION DES ENERGIES
# ------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "[4/7] EXTRACTION DES DONNÉES DFT"
echo "------------------------------------------------------------"

SUMMARY="$RESULTS/qe_energy_summary.csv"

echo "file,total_energy_Ry,status,scf_convergence" > "$SUMMARY"

for OUT in "${QE_OUTPUTS[@]}"; do

    ENERGY=$(
        grep -E "!\s+total energy\s+=" "$OUT" 2>/dev/null |
        tail -1 |
        sed -E 's/.*=\s*([-+0-9.Ee]+)\s+Ry.*/\1/'
    )

    if [[ -z "$ENERGY" ]]; then
        continue
    fi

    if grep -q "convergence has been achieved" "$OUT" 2>/dev/null; then
        STATUS="converged"
    elif grep -q "convergence NOT achieved" "$OUT" 2>/dev/null; then
        STATUS="not_converged"
    else
        STATUS="unknown"
    fi

    BASENAME=$(basename "$OUT")

    echo "\"$OUT\",$ENERGY,$STATUS,$STATUS" >> "$SUMMARY"

    echo "[DATA] $BASENAME"
    echo "       Energy = $ENERGY Ry"
    echo "       Status = $STATUS"
done

# ------------------------------------------------------------
# 5. ANALYSE DE CONVERGENCE
# ------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "[5/7] ANALYSE DE CONVERGENCE"
echo "------------------------------------------------------------"

python - "$SUMMARY" "$RESULTS/convergence_report.txt" <<'PY'
from pathlib import Path
import csv
import sys

summary = Path(sys.argv[1])
report = Path(sys.argv[2])

rows = []

if summary.exists():
    with summary.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

converged = [r for r in rows if r["status"] == "converged"]
not_converged = [r for r in rows if r["status"] == "not_converged"]

text = f"""
HYDROMATAI - CONVERGENCE ANALYSIS
==================================

Total QE outputs analysed : {len(rows)}
Converged calculations     : {len(converged)}
Non-converged calculations  : {len(not_converged)}

Interpretation
--------------

Les calculs marqués "converged" peuvent être utilisés comme
base pour les analyses scientifiques suivantes, sous réserve
de vérifier les paramètres DFT, les pseudopotentiels et les
critères de convergence.

Les calculs "not_converged" doivent être considérés comme
préliminaires et ne doivent pas être utilisés seuls pour une
conclusion scientifique finale.

"""

report.write_text(text.strip() + "\n", encoding="utf-8")

print("[OK] Rapport de convergence :", report)
PY

# ------------------------------------------------------------
# 6. PROPRIÉTÉS ÉLECTRONIQUES ET OPTIQUES
# ------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "[6/7] PROPRIÉTÉS ÉLECTRONIQUES + OPTIQUES"
echo "------------------------------------------------------------"

python - "$RESULTS" <<'PY'
from pathlib import Path
import math
import sys

results = Path(sys.argv[1])

electronic = results / "electronic" / "electronic_interpretation.txt"
optical = results / "optical" / "optical_interpretation.txt"

# ------------------------------------------------------------
# Electronic properties
# ------------------------------------------------------------

gap = 1.5

if gap <= 0.05:
    classification = "métallique / semi-métallique"
elif gap < 3.0:
    classification = "semi-conducteur"
else:
    classification = "isolant"

electronic_text = f"""
PROPRIÉTÉS ÉLECTRONIQUES
========================

Gap électronique utilisé pour le test : {gap:.4f} eV

Classification :
{classification}

Interprétation :
Un gap compris entre 0 et environ 3 eV est compatible avec
un comportement semi-conducteur. Cette classification doit
être confirmée par un calcul de structure de bandes et/ou
de densité d'états (DOS) convergé.

IMPORTANT :
La valeur de {gap:.4f} eV est une valeur de démonstration
du module et ne doit pas être présentée comme une propriété
DFT du système C-H2 tant qu'elle n'a pas été extraite d'un
calcul électronique convergé.
"""

electronic.write_text(electronic_text.strip() + "\n", encoding="utf-8")

# ------------------------------------------------------------
# Optical properties
# ------------------------------------------------------------

n = 2.015329455153383
k = 0.24809839340235618
R = 0.11934398257935644

optical_text = f"""
PROPRIÉTÉS OPTIQUES
===================

Indice de réfraction n :
{n:.8f}

Coefficient d'extinction k :
{k:.8f}

Réflectivité R :
{R:.8f}

Interprétation :
L'indice de réfraction caractérise la propagation de la
lumière dans le matériau.

Le coefficient d'extinction décrit l'atténuation de
l'onde électromagnétique.

La réflectivité indique la fraction de l'intensité
incidente réfléchie par le matériau.

IMPORTANT :
Ces valeurs sont actuellement utilisées pour vérifier
le fonctionnement de la plateforme. Elles ne constituent
pas encore des résultats optiques DFT du système C-H2.
Pour une étude scientifique complète, il faudra calculer
la fonction diélectrique complexe ε1(ω), ε2(ω), puis
déduire n(ω), k(ω), absorption et réflectivité en fonction
de l'énergie photonique.
"""

optical.write_text(optical_text.strip() + "\n", encoding="utf-8")

print("[OK] Analyse électronique préparée")
print("[OK] Analyse optique préparée")
print("[INFO] Les valeurs de démonstration sont explicitement identifiées.")
PY

# ------------------------------------------------------------
# 7. RAPPORT FINAL
# ------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "[7/7] RAPPORT SCIENTIFIQUE FINAL"
echo "------------------------------------------------------------"

python - "$RESULTS" <<'PY'
from pathlib import Path
from datetime import datetime
import sys

results = Path(sys.argv[1])

electronic = (
    results / "electronic" / "electronic_interpretation.txt"
).read_text(encoding="utf-8")

optical = (
    results / "optical" / "optical_interpretation.txt"
).read_text(encoding="utf-8")

convergence = (
    results / "convergence_report.txt"
).read_text(encoding="utf-8")

report = results / "reports" / "HydroMatAI_scientific_report.txt"

text = f"""
HYDROMATAI
SCIENTIFIC ELECTRONIC + OPTICAL ANALYSIS
=========================================

Date :
{datetime.now().isoformat(timespec="seconds")}

STATUT
------

Cette analyse n'a lancé aucun nouveau calcul Quantum ESPRESSO.

Les calculs QE existants n'ont pas été interrompus.

{electronic}

{optical}

{convergence}

CONCLUSION
----------

La plateforme HydroMatAI dispose maintenant d'une chaîne
d'analyse destinée à :

1. récupérer les résultats QE ;
2. analyser la convergence ;
3. analyser les propriétés électroniques ;
4. analyser les propriétés optiques ;
5. produire automatiquement des rapports ;
6. préparer la génération automatique des figures.

Les propriétés électroniques et optiques quantitatives
finales devront être calculées à partir de sorties QE
convergées correspondant exactement au système étudié.

Le calcul C_H2_d2p00_fixed.in reste indépendant de cette
analyse et peut continuer son exécution.
"""

report.write_text(text.strip() + "\n", encoding="utf-8")

print("[OK] Rapport créé :", report)
PY

echo
echo "============================================================"
echo " ANALYSE SCIENTIFIQUE TERMINÉE"
echo "============================================================"
echo
echo "Résultats :"
echo "  $RESULTS"
echo
echo "Aucun calcul QE n'a été lancé."
echo "Aucun calcul QE existant n'a été interrompu."
echo
echo "Prochaine étape :"
echo "  extraction réelle des bandes + DOS + fonction diélectrique"
echo "  puis génération des figures scientifiques."
echo "============================================================"
