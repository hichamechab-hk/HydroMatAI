#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/HydroMatAI"
OUT="$BASE/results/scientific_analysis/electronic"
QE="$HOME/software/qe-7.5/bin"

REFERENCE="/tmp/HydroMatAI_real_h2_scan/outputs/C_H2_d2p00_fixed.out"

echo "============================================================"
echo " HydroMatAI - ELECTRONIC ANALYSIS PREPARATION"
echo "============================================================"
echo
echo "SAFE MODE : préparation uniquement"
echo "Aucun pw.x / bands.x / dos.x ne sera lancé."
echo

if [[ ! -f "$REFERENCE" ]]; then
    echo "[ERREUR] Résultat de référence introuvable:"
    echo "$REFERENCE"
    exit 1
fi

echo "[1/5] Vérification du calcul de référence"

grep -q "convergence has been achieved" "$REFERENCE" \
    || { echo "[ERREUR] SCF non convergé"; exit 1; }

grep -q "JOB DONE." "$REFERENCE" \
    || { echo "[ERREUR] JOB DONE absent"; exit 1; }

ENERGY=$(grep "!    total energy" "$REFERENCE" | tail -1 | awk '{print $5}')

echo "[OK] SCF convergé"
echo "[OK] Énergie finale : $ENERGY Ry"

echo
echo "[2/5] Vérification des exécutables QE"

for exe in pw.x bands.x dos.x projwfc.x; do
    if [[ -x "$QE/$exe" ]]; then
        echo "[OK] $QE/$exe"
    else
        echo "[ATTENTION] $exe non trouvé"
    fi
done

echo
echo "[3/5] Création du manifeste électronique"

cat > "$OUT/reports/electronic_workflow.txt" <<EOF
HydroMatAI - Electronic Workflow
================================

REFERENCE
---------
C-H2 distance : 2.00 Angstrom
SCF output    : $REFERENCE
Final energy  : $ENERGY Ry
SCF status    : CONVERGED

WORKFLOW
--------
1. SCF converged
2. NSCF calculation
3. Band structure
4. DOS
5. PDOS
6. VBM
7. CBM
8. Band gap
9. Automatic plots
10. Scientific interpretation

IMPORTANT
---------
This preparation script does not launch QE.

The active calculation C_H2_d2p50_rescue.in is not touched.

FINAL ELECTRONIC OUTPUTS
------------------------
band_structure.dat
dos.dat
pdos_*.dat
electronic_gap.txt
band_structure.png
dos.png
pdos.png
electronic_report.txt
EOF

echo "[OK] Manifeste créé"

echo
echo "[4/5] Création du dossier de données"

touch "$OUT/inputs/.keep"
touch "$OUT/outputs/.keep"
touch "$OUT/figures/.keep"

echo "[OK] Structure prête"

echo
echo "[5/5] État des calculs"

ps aux | grep -E '[p]w.x|[m]pirun' || true

echo
echo "============================================================"
echo " PRÉPARATION ÉLECTRONIQUE TERMINÉE"
echo "============================================================"
echo
echo "Référence : C_H2_d2p00_fixed"
echo "Énergie   : $ENERGY Ry"
echo
echo "Aucun calcul QE lancé."
echo "Aucun calcul QE interrompu."
echo
echo "============================================================"
