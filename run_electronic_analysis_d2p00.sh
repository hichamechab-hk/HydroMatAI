#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# HydroMatAI - ELECTRONIC ANALYSIS D2P00
#
# SAFE_MODE=1 : préparation uniquement
# SAFE_MODE=0 : NSCF + DOS + PDOS réels
#
# Aucun processus QE existant n'est interrompu.
# ============================================================

BASE="$HOME/HydroMatAI"
QE="$HOME/software/qe-7.5/bin"

SAFE_MODE="${SAFE_MODE:-1}"

PREFIX="scan_d2p00"
OUTDIR="/tmp/HydroMatAI_real_h2_scan/d_2p00"

SCF_OUT="/tmp/HydroMatAI_real_h2_scan/outputs/C_H2_d2p00_fixed.out"
SAVE="$OUTDIR/${PREFIX}.save"

ROOT="$BASE/results/scientific_analysis/electronic"
INPUT="$ROOT/inputs"
OUTPUT="$ROOT/outputs"
FIGURES="$ROOT/figures"
REPORTS="$ROOT/reports"

mkdir -p "$INPUT" "$OUTPUT" "$FIGURES" "$REPORTS"

echo
echo "============================================================"
echo " HydroMatAI - ELECTRONIC ANALYSIS D2P00"
echo "============================================================"
echo
echo "SAFE_MODE = $SAFE_MODE"
echo

# ------------------------------------------------------------
# 1. SCF
# ------------------------------------------------------------

echo "------------------------------------------------------------"
echo "[1/8] RÉFÉRENCE SCF"
echo "------------------------------------------------------------"

test -f "$SCF_OUT" || {
    echo "[ERREUR] SCF introuvable."
    exit 1
}

grep -q "convergence has been achieved" "$SCF_OUT" || {
    echo "[ERREUR] SCF non convergé."
    exit 1
}

grep -q "JOB DONE." "$SCF_OUT" || {
    echo "[ERREUR] JOB DONE absent."
    exit 1
}

ENERGY=$(grep "!    total energy" "$SCF_OUT" | tail -1 | awk '{print $5}')

echo "[OK] SCF convergé"
echo "[OK] Energie : $ENERGY Ry"

# ------------------------------------------------------------
# 2. SAVE
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[2/8] DOSSIER SAVE"
echo "------------------------------------------------------------"

test -d "$SAVE" || {
    echo "[ERREUR] SAVE absent : $SAVE"
    exit 1
}

test -f "$SAVE/data-file-schema.xml" || {
    echo "[ERREUR] data-file-schema.xml absent."
    exit 1
}

echo "[OK] $SAVE"

# ------------------------------------------------------------
# 3. EXECUTABLES
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[3/8] EXÉCUTABLES QE"
echo "------------------------------------------------------------"

for exe in pw.x dos.x projwfc.x; do
    test -x "$QE/$exe" || {
        echo "[ERREUR] $QE/$exe absent."
        exit 1
    }
    echo "[OK] $QE/$exe"
done

# ------------------------------------------------------------
# 4. PROCESSUS ACTIFS
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[4/8] PROCESSUS QE ACTIFS"
echo "------------------------------------------------------------"

ps aux | grep -E '[p]w.x|[m]pirun' || echo "Aucun processus QE actif."

echo
echo "[OK] Aucun processus existant ne sera interrompu."

# ------------------------------------------------------------
# 5. INPUTS
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[5/8] GÉNÉRATION DES INPUTS"
echo "------------------------------------------------------------"

cat > "$INPUT/nscf_d2p00.in" <<EOF
&CONTROL
    calculation = 'nscf',
    restart_mode = 'restart',
    prefix = '$PREFIX',
    outdir = '$OUTDIR',
    pseudo_dir = '/usr/share/espresso/pseudo',
    verbosity = 'high',
/

&SYSTEM
    ibrav = 0,
    nat = 3,
    ntyp = 2,
    ecutwfc = 60.0,
    ecutrho = 480.0,
    nspin = 2,
    tot_magnetization = 2,
    occupations = 'fixed',
/

&ELECTRONS
    conv_thr = 1.0d-8,
    electron_maxstep = 300,
    mixing_beta = 0.10,
    mixing_mode = 'local-TF',
    diagonalization = 'david',
/

ATOMIC_SPECIES
C  12.011  C.pbe-n-kjpaw_psl.0.1.UPF
H  1.008   H.pbe-kjpaw.UPF

ATOMIC_POSITIONS angstrom
C  6.000000  6.000000  6.000000
H  6.000000  6.000000  8.000000
H  6.000000  6.000000  8.741400

CELL_PARAMETERS angstrom
12.000000 0.000000 0.000000
0.000000 12.000000 0.000000
0.000000 0.000000 12.000000

K_POINTS gamma
EOF

cat > "$INPUT/dos_d2p00.in" <<EOF
&DOS
    prefix = '$PREFIX',
    outdir = '$OUTDIR',
    fildos = '$OUTPUT/dos_d2p00.dat',
    Emin = -15.0,
    Emax = 15.0,
    DeltaE = 0.01,
/
EOF

cat > "$INPUT/projwfc_d2p00.in" <<EOF
&PROJWFC
    prefix = '$PREFIX',
    outdir = '$OUTDIR',
    filpdos = '$OUTPUT/pdos_d2p00',
    Emin = -15.0,
    Emax = 15.0,
    DeltaE = 0.01,
    ngauss = 0,
/
EOF

echo "[OK] NSCF input"
echo "[OK] DOS input"
echo "[OK] PDOS input"

# ------------------------------------------------------------
# SAFE MODE
# ------------------------------------------------------------

if [[ "$SAFE_MODE" == "1" ]]; then

    echo
    echo "============================================================"
    echo " MODE PRÉPARATION"
    echo "============================================================"
    echo
    echo "Aucun calcul QE lancé."
    echo
    echo "Pour lancer les calculs réels :"
    echo
    echo "SAFE_MODE=0 ./run_electronic_analysis_d2p00.sh"
    echo

    cat > "$REPORTS/electronic_manifest.txt" <<EOF
HydroMatAI Electronic Analysis
==============================

Reference:
C_H2_d2p00_fixed

Energy:
$ENERGY Ry

Status:
PREPARED

NSCF:
PREPARED

DOS:
PREPARED

PDOS:
PREPARED

No QE calculation launched.
EOF

    exit 0
fi

# ------------------------------------------------------------
# 6. NSCF
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[6/8] NSCF RÉEL"
echo "------------------------------------------------------------"

NSCF_OUT="$OUTPUT/nscf_d2p00.out"

"$QE/pw.x" \
    -in "$INPUT/nscf_d2p00.in" \
    > "$NSCF_OUT" 2>&1

if grep -q "JOB DONE." "$NSCF_OUT"; then
    echo "[OK] NSCF terminé."
else
    echo "[ERREUR] NSCF échoué."
    tail -60 "$NSCF_OUT"
    exit 1
fi

# ------------------------------------------------------------
# 7. DOS + PDOS
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[7/8] DOS"
echo "------------------------------------------------------------"

"$QE/dos.x" \
    -in "$INPUT/dos_d2p00.in" \
    > "$OUTPUT/dos_d2p00.out" 2>&1

grep -q "JOB DONE." "$OUTPUT/dos_d2p00.out" || {
    echo "[ERREUR] DOS échouée."
    tail -60 "$OUTPUT/dos_d2p00.out"
    exit 1
}

echo "[OK] DOS terminée."

echo
echo "------------------------------------------------------------"
echo "[7/8] PDOS"
echo "------------------------------------------------------------"

"$QE/projwfc.x" \
    -in "$INPUT/projwfc_d2p00.in" \
    > "$OUTPUT/projwfc_d2p00.out" 2>&1

grep -q "JOB DONE." "$OUTPUT/projwfc_d2p00.out" || {
    echo "[ERREUR] PDOS échouée."
    tail -60 "$OUTPUT/projwfc_d2p00.out"
    exit 1
}

echo "[OK] PDOS terminée."

# ------------------------------------------------------------
# 8. MANIFEST
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[8/8] RÉSULTATS"
echo "------------------------------------------------------------"

cat > "$REPORTS/electronic_manifest.txt" <<EOF
HydroMatAI Electronic Analysis
==============================

Reference:
C_H2_d2p00_fixed

SCF energy:
$ENERGY Ry

NSCF:
$NSCF_OUT

DOS:
$OUTPUT/dos_d2p00.dat

PDOS:
$OUTPUT/pdos_d2p00*

Status:
COMPLETED

Scientific rule:
The electronic gap must be extracted from calculated
electronic states and must not be artificially assigned.
EOF

echo
echo "============================================================"
echo " ANALYSE ÉLECTRONIQUE TERMINÉE"
echo "============================================================"
echo
echo "NSCF : $NSCF_OUT"
echo "DOS  : $OUTPUT/dos_d2p00.dat"
echo "PDOS : $OUTPUT/pdos_d2p00*"
echo "Rapport : $REPORTS/electronic_manifest.txt"
echo
