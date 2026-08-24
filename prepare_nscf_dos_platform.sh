#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/HydroMatAI"
QE="$HOME/software/qe-7.5/bin"
REF="/tmp/HydroMatAI_real_h2_scan/outputs/C_H2_d2p00_fixed.out"

OUT="$BASE/results/scientific_analysis/electronic"
INPUTS="$OUT/inputs"
OUTPUTS="$OUT/outputs"
FIGURES="$OUT/figures"
REPORTS="$OUT/reports"

mkdir -p "$INPUTS" "$OUTPUTS" "$FIGURES" "$REPORTS"

echo "============================================================"
echo " HydroMatAI - NSCF / DOS / PDOS PLATFORM"
echo "============================================================"
echo
echo "MODE : PREPARATION UNIQUEMENT"
echo "Aucun calcul QE ne sera lancé."
echo "Le calcul actif C_H2_d2p50_rescue.in ne sera pas touché."
echo

# ------------------------------------------------------------
# 1. Vérification référence
# ------------------------------------------------------------

echo "------------------------------------------------------------"
echo "[1/6] VÉRIFICATION SCF DE RÉFÉRENCE"
echo "------------------------------------------------------------"

if [[ ! -f "$REF" ]]; then
    echo "[ERREUR] $REF introuvable"
    exit 1
fi

if ! grep -q "convergence has been achieved" "$REF"; then
    echo "[ERREUR] Le calcul de référence n'est pas convergé."
    exit 1
fi

if ! grep -q "JOB DONE." "$REF"; then
    echo "[ERREUR] JOB DONE absent."
    exit 1
fi

ENERGY=$(grep "!    total energy" "$REF" | tail -1 | awk '{print $5}')

echo "[OK] SCF convergé"
echo "[OK] Energie = $ENERGY Ry"

# ------------------------------------------------------------
# 2. Vérification fichiers sauvegarde
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[2/6] VÉRIFICATION DU DOSSIER .save"
echo "------------------------------------------------------------"

SAVE="/tmp/C_H2_new_tmp/C_H2.save"

if [[ -d "$SAVE" ]]; then
    echo "[OK] $SAVE"
else
    echo "[ATTENTION] $SAVE n'existe pas."
    echo "Le NSCF devra utiliser le bon outdir/prefix du calcul SCF."
fi

# ------------------------------------------------------------
# 3. Vérification exécutables
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[3/6] OUTILS QE"
echo "------------------------------------------------------------"

for exe in pw.x bands.x dos.x projwfc.x; do
    if [[ -x "$QE/$exe" ]]; then
        echo "[OK] $exe"
    else
        echo "[ERREUR] $exe absent"
    fi
done

# ------------------------------------------------------------
# 4. Workflow
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[4/6] CONSTRUCTION DU WORKFLOW"
echo "------------------------------------------------------------"

cat > "$REPORTS/workflow.txt" <<EOF
HYDROMATAI - ELECTRONIC WORKFLOW
================================

REFERENCE
---------
C-H2 d = 2.00 Angstrom

SCF output:
$REF

Energy:
$ENERGY Ry

WORKFLOW
--------

SCF
 |
 +--> NSCF
 |     |
 |     +--> DOS
 |     |
 |     +--> PDOS
 |
 +--> Bands
       |
       +--> VBM
       +--> CBM
       +--> Eg

POST-PROCESSING
---------------

DOS/PDOS
Bands
Fermi level
VBM
CBM
Band gap
Figures
Interpretation
Report scientifique

IMPORTANT
---------

Le système C-H2 est simulé dans une grande cellule périodique.
La définition du chemin k et du maillage NSCF doit donc être
adaptée au caractère isolé du système.

Aucun calcul n'est lancé par ce script.
EOF

echo "[OK] Workflow enregistré"

# ------------------------------------------------------------
# 5. Gabarits de fichiers
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[5/6] CRÉATION DES GABARITS"
echo "------------------------------------------------------------"

cat > "$INPUTS/README.txt" <<'EOF'
Fichiers à construire après validation :

1. nscf.in
2. bands.in
3. dos.in
4. projwfc.in

Ils doivent utiliser exactement le même :

prefix
outdir
pseudo_dir
cellule
structure

que le calcul SCF de référence.

Ne pas lancer ces fichiers avant validation.
EOF

cat > "$REPORTS/electronic_targets.txt" <<'EOF'
PROPRIÉTÉS ÉLECTRONIQUES À EXTRAIRE
====================================

[1] Energie totale
[2] Energie de Fermi
[3] VBM
[4] CBM
[5] Band gap
[6] DOS totale
[7] PDOS C
[8] PDOS H
[9] Contributions orbitalaires
[10] Structure de bandes

FIGURES
=======

band_structure.png
dos_total.png
pdos_C.png
pdos_H.png
dos_pdos_combined.png

INTERPRÉTATION
==============

Le rapport devra déterminer :

- métal ;
- semi-métal ;
- semi-conducteur ;
- isolant.

Le gap ne doit PAS être estimé artificiellement.

Il doit être déterminé à partir des données électroniques
réellement calculées.
EOF

echo "[OK] Gabarits créés"

# ------------------------------------------------------------
# 6. Vérification calcul actif
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[6/6] CALCULS ACTIFS"
echo "------------------------------------------------------------"

ACTIVE=$(ps aux | grep -E '[p]w.x|[m]pirun' || true)

if [[ -n "$ACTIVE" ]]; then
    echo "$ACTIVE"
else
    echo "Aucun pw.x/mpirun détecté."
fi

echo
echo "============================================================"
echo " PRÉPARATION NSCF / DOS / PDOS TERMINÉE"
echo "============================================================"
echo
echo "Référence : C_H2_d2p00_fixed"
echo "Energie   : $ENERGY Ry"
echo
echo "Aucun calcul QE lancé."
echo "Aucun calcul QE interrompu."
echo
echo "Étape suivante : génération contrôlée des vrais inputs"
echo "NSCF + Bands + DOS + PDOS."
echo "============================================================"
