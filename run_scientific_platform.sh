#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# HydroMatAI - SCIENTIFIC PLATFORM
# Version : orchestration SAFE / PREPARATION
# ============================================================

BASE="$HOME/HydroMatAI"

SCAN="/tmp/HydroMatAI_real_h2_scan"
SCF="$SCAN/outputs/C_H2_d2p00_fixed.out"
SAVE="$SCAN/d_2p00/scan_d2p00.save"

ROOT="$BASE/results/scientific_analysis"
ELEC="$ROOT/electronic"
OPT="$ROOT/optical"

E_INPUT="$ELEC/inputs"
E_OUTPUT="$ELEC/outputs"
E_FIG="$ELEC/figures"
E_REPORT="$ELEC/reports"

O_INPUT="$OPT/inputs"
O_OUTPUT="$OPT/outputs"
O_FIG="$OPT/figures"
O_REPORT="$OPT/reports"

mkdir -p \
    "$E_INPUT" \
    "$E_OUTPUT" \
    "$E_FIG" \
    "$E_REPORT" \
    "$O_INPUT" \
    "$O_OUTPUT" \
    "$O_FIG" \
    "$O_REPORT"

echo "============================================================"
echo " HydroMatAI - SCIENTIFIC PLATFORM"
echo "============================================================"
echo
echo "MODE : SAFE / PREPARATION"
echo "Aucun calcul QE ne sera lancé."
echo "Aucun processus QE ne sera interrompu."
echo

# ============================================================
# 1. PROCESSUS QE
# ============================================================

echo "------------------------------------------------------------"
echo "[1/8] PROCESSUS QE ACTIFS"
echo "------------------------------------------------------------"

QE_ACTIVE="$(ps aux | grep -E '[p]w.x|[m]pirun' || true)"

if [[ -n "$QE_ACTIVE" ]]; then
    echo "$QE_ACTIVE"
else
    echo "[INFO] Aucun processus QE actif."
fi

echo
echo "[OK] Processus existants laissés totalement indépendants."

# ============================================================
# 2. SCF DE REFERENCE
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[2/8] SCF DE RÉFÉRENCE"
echo "------------------------------------------------------------"

if [[ ! -f "$SCF" ]]; then
    echo "[ERREUR] Fichier SCF absent :"
    echo "$SCF"
    exit 1
fi

if grep -q "convergence has been achieved" "$SCF" &&
   grep -q "JOB DONE." "$SCF"; then

    SCF_STATUS="COMPLETED"
    ENERGY="$(grep "!    total energy" "$SCF" | tail -1 | awk '{print $5}')"

    echo "[OK] SCF convergé"
    echo "[OK] Référence : C_H2_d2p00_fixed"
    echo "[OK] Energie   : $ENERGY Ry"

else

    SCF_STATUS="FAILED_OR_INCOMPLETE"
    ENERGY="N/A"

    echo "[ERREUR] SCF non confirmé comme terminé."
    exit 1
fi

# ============================================================
# 3. SAVE QE
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[3/8] DONNÉES QE SAVE"
echo "------------------------------------------------------------"

if [[ -d "$SAVE" &&
      -f "$SAVE/data-file-schema.xml" ]]; then

    SAVE_STATUS="AVAILABLE"

    echo "[OK] SAVE disponible"
    echo "$SAVE"

else

    SAVE_STATUS="MISSING"

    echo "[ERREUR] SAVE QE incomplet"
    exit 1
fi

# ============================================================
# 4. DONNEES ELECTRONIQUES
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[4/8] DONNÉES ÉLECTRONIQUES"
echo "------------------------------------------------------------"

DOS_FILE=""
BAND_FILE=""
PDOS_FILES=""

# DOS
for f in \
    "$E_OUTPUT"/*.dos \
    "$E_OUTPUT"/*.dat \
    "$SCAN"/*.dos \
    "$SCAN"/*.dat
do
    if [[ -f "$f" ]]; then
        if grep -qi "dos" <<< "$(basename "$f")"; then
            DOS_FILE="$f"
            break
        fi
    fi
done

if [[ -n "$DOS_FILE" ]]; then
    DOS_STATUS="AVAILABLE"
    echo "[OK] DOS trouvée : $DOS_FILE"
else
    DOS_STATUS="PENDING"
    echo "[PENDING] DOS réelle non disponible"
fi

# BANDES
for f in \
    "$E_OUTPUT"/*band* \
    "$E_OUTPUT"/*bands* \
    "$SCAN"/*band* \
    "$SCAN"/*bands*
do
    if [[ -f "$f" ]]; then
        BAND_FILE="$f"
        break
    fi
done

if [[ -n "$BAND_FILE" ]]; then
    BAND_STATUS="AVAILABLE"
    echo "[OK] Bandes trouvées : $BAND_FILE"
else
    BAND_STATUS="PENDING"
    echo "[PENDING] Structure de bandes réelle non disponible"
fi

# PDOS
PDOS_COUNT="$(find "$E_OUTPUT" -type f \
    \( -iname "*pdos*" -o -iname "*.pdos*" \) \
    2>/dev/null | wc -l)"

if [[ "$PDOS_COUNT" -gt 0 ]]; then
    PDOS_STATUS="AVAILABLE"
    echo "[OK] Fichiers PDOS : $PDOS_COUNT"
else
    PDOS_STATUS="PENDING"
    echo "[PENDING] PDOS réelles non disponibles"
fi

# ============================================================
# 5. PROPRIETES ELECTRONIQUES
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[5/8] PROPRIÉTÉS ÉLECTRONIQUES"
echo "------------------------------------------------------------"

if [[ "$BAND_STATUS" == "AVAILABLE" ]]; then
    VBM_STATUS="READY_FOR_ANALYSIS"
    CBM_STATUS="READY_FOR_ANALYSIS"
    GAP_STATUS="READY_FOR_ANALYSIS"
else
    VBM_STATUS="PENDING"
    CBM_STATUS="PENDING"
    GAP_STATUS="PENDING"
fi

cat > "$E_REPORT/electronic_status.txt" <<EOF
HydroMatAI - Electronic Analysis
================================

REFERENCE
---------
System        : C-H2
Distance      : 2.00 Angstrom
SCF           : $SCF
Energy        : $ENERGY Ry

SCF STATUS
----------
$SCF_STATUS

QE SAVE
-------
$SAVE
Status : $SAVE_STATUS

ELECTRONIC DATA
---------------

DOS:
$DOS_STATUS

PDOS:
$PDOS_STATUS

Bands:
$BAND_STATUS

VBM:
$VBM_STATUS

CBM:
$CBM_STATUS

Band gap:
$GAP_STATUS

SCIENTIFIC POLICY
-----------------

The band gap is NOT estimated artificially.

VBM and CBM must come from calculated electronic
data.

No classification as metal, semimetal,
semiconductor or insulator is allowed before
real electronic data are available.
EOF

echo "[OK] État électronique enregistré"

# ============================================================
# 6. PROPRIETES OPTIQUES
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[6/8] PROPRIÉTÉS OPTIQUES"
echo "------------------------------------------------------------"

cat > "$O_REPORT/optical_status.txt" <<EOF
HydroMatAI - Optical Analysis
=============================

REFERENCE
---------
System   : C-H2
Distance : 2.00 Angstrom

STATUS
------

Dielectric function:
PENDING

epsilon_1:
PENDING

epsilon_2:
PENDING

Refractive index n:
PENDING

Extinction coefficient k:
PENDING

Reflectivity:
PENDING

Absorption coefficient:
PENDING

Optical conductivity:
PENDING

Energy loss:
PENDING

SCIENTIFIC POLICY
-----------------

No optical quantity is invented.

Optical properties will only be reported
from actual calculated electronic-response data.
EOF

echo "[OK] État optique enregistré"

# ============================================================
# 7. MANIFESTE SCIENTIFIQUE
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[7/8] MANIFESTE"
echo "------------------------------------------------------------"

cat > "$ROOT/scientific_manifest.txt" <<EOF
============================================================
HYDROMATAI SCIENTIFIC PLATFORM
============================================================

REFERENCE
---------
C-H2
d = 2.00 Angstrom

SCF
---
Status : $SCF_STATUS
Energy : $ENERGY Ry

QE SAVE
-------
Status : $SAVE_STATUS
Path   : $SAVE

ELECTRONIC
----------

DOS      : $DOS_STATUS
PDOS     : $PDOS_STATUS
Bands    : $BAND_STATUS
VBM      : $VBM_STATUS
CBM      : $CBM_STATUS
Band gap : $GAP_STATUS

OPTICAL
-------

Dielectric function : PENDING
n                   : PENDING
k                   : PENDING
Reflectivity        : PENDING
Absorption          : PENDING
Conductivity        : PENDING
Energy loss         : PENDING

SCIENTIFIC RULES
----------------

1. No artificial band gap.
2. No artificial VBM or CBM.
3. No artificial optical constants.
4. No scientific classification without calculated data.
5. Existing QE calculations are never interrupted.
6. d2p50 remains independent.

EXECUTION
---------

SAFE / PREPARATION ONLY

No pw.x executed.
No dos.x executed.
No projwfc.x executed.
EOF

echo "[OK] Manifest créé"

# ============================================================
# 8. RAPPORT GLOBAL
# ============================================================

echo
echo "------------------------------------------------------------"
echo "[8/8] RAPPORT GLOBAL"
echo "------------------------------------------------------------"

cat > "$ROOT/scientific_platform_report.txt" <<EOF
============================================================
HYDROMATAI - SCIENTIFIC PLATFORM REPORT
============================================================

SYSTEM
------
C-H2
H2-C distance = 2.00 Angstrom

REFERENCE SCF
-------------
Energy = $ENERGY Ry
Status = $SCF_STATUS

ELECTRONIC
----------

DOS       : $DOS_STATUS
PDOS      : $PDOS_STATUS
Bands     : $BAND_STATUS
VBM       : $VBM_STATUS
CBM       : $CBM_STATUS
Band gap  : $GAP_STATUS

OPTICAL
-------

All optical properties : PENDING

CONCLUSION
----------

The SCF reference calculation is validated.

The electronic analysis infrastructure is ready.

However, DOS, PDOS and band-structure results are not
yet available. Therefore VBM, CBM and the band gap are
NOT scientifically determined at this stage.

No artificial value has been introduced.

The optical analysis remains pending.

CALCULATION POLICY
------------------

This script does not launch QE calculations.

Existing QE processes are not interrupted.

The d2p50 calculation remains independent.
============================================================
EOF

echo "[OK] Rapport global créé"

echo
echo "============================================================"
echo " PLATEFORME SCIENTIFIQUE PRÉPARÉE"
echo "============================================================"
echo
echo "Référence : C_H2_d2p00_fixed"
echo "Énergie   : $ENERGY Ry"
echo
echo "SCF       : $SCF_STATUS"
echo "SAVE      : $SAVE_STATUS"
echo "DOS       : $DOS_STATUS"
echo "PDOS      : $PDOS_STATUS"
echo "Bands     : $BAND_STATUS"
echo "VBM       : $VBM_STATUS"
echo "CBM       : $CBM_STATUS"
echo "Gap       : $GAP_STATUS"
echo
echo "Optique   : PENDING"
echo
echo "AUCUN calcul QE lancé."
echo "AUCUN calcul QE interrompu."
echo "============================================================"
