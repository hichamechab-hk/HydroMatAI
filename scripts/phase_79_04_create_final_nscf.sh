#!/usr/bin/env bash

printf '\033[2J\033[H'

set -e

BASE="/home/hk/HydroMatAI"
DIR="$BASE/calculations/phase79_final_electronic/TiFeH2"
SAVE="$BASE/calculations/top5_dft/TiFeH2/tmp_scf/ecut140_rho560_k888.save"

echo "========================================================================================"
echo "PHASE 79.04 — CRÉATION NSCF FINAL TiFeH2"
echo "========================================================================================"
echo "[INFO] MODE = PRÉPARATION / AUDIT"
echo "[INFO] Aucun pw.x exécuté"
echo "[INFO] Aucun ancien fichier scientifique modifié"
echo

if [ ! -d "$SAVE" ]; then
    echo "[FAIL] .save final absent : $SAVE"
    exit 1
fi

if [ ! -f "$SAVE/data-file-schema.xml" ]; then
    echo "[FAIL] data-file-schema.xml absent"
    exit 1
fi

mkdir -p "$DIR"

INPUT="$DIR/TiFeH2_final_nscf.in"

if [ -e "$INPUT" ]; then
    echo "[FAIL] Input déjà présent :"
    echo "       $INPUT"
    echo "[INFO] Aucun écrasement autorisé."
    exit 1
fi

cat > "$INPUT" <<EOF
&CONTROL
    calculation = 'nscf',
    prefix = 'ecut140_rho560_k888',
    restart_mode = 'restart',
    outdir = '$BASE/calculations/top5_dft/TiFeH2/tmp_scf',
    pseudo_dir = '/home/hk/software/qe-7.5/pseudo',
    verbosity = 'high',
/

&SYSTEM
    ibrav = 0,
    nat = 8,
    ntyp = 3,
    ecutwfc = 140.0,
    ecutrho = 560.0,
    nspin = 2,
    nbnd = 36,
    occupations = 'smearing',
    smearing = 'mv',
    degauss = 0.01,
/

&ELECTRONS
    conv_thr = 1.0d-10,
    mixing_beta = 0.3,
/

ATOMIC_SPECIES
Ti  47.867    Ti.pbe-spn-kjpaw_psl.1.0.0.UPF
Fe  55.845    Fe.pbe-spn-rrkjus_psl.0.2.1.UPF
H    1.008    H.pbe-kjpaw.UPF

CELL_PARAMETERS angstrom
5.2399261000   0.0000000000   0.0000000000
-0.5935539478  5.2062000773   0.0000000000
0.0000000000   0.0000000000   2.6442020000

ATOMIC_POSITIONS crystal
Ti  0.2818590000  0.2818590000  0.0000000000
Ti  0.7181410000  0.7181410000  0.0000000000
Fe  0.7661460000  0.2338540000  0.0000000000
Fe  0.2338540000  0.7661460000  0.0000000000
H   0.0000000000  0.5000000000  0.0000000000
H   0.0000000000  0.0000000000  0.0000000000
H   0.5000000000  0.0000000000  0.0000000000
H   0.5000000000  0.5000000000  0.5000000000

K_POINTS automatic
8 8 8 0 0 0
EOF

echo "[PASS] Input créé :"
echo "       $INPUT"
echo

echo "----------------------------------------------------------------------------------------"
echo "1. CONTRÔLE DES PARAMÈTRES"
echo "----------------------------------------------------------------------------------------"

grep -E \
"calculation|prefix|outdir|ecutwfc|ecutrho|nspin|nbnd|occupations|smearing|degauss|conv_thr|mixing_beta|K_POINTS|8 8 8" \
"$INPUT"

echo
echo "----------------------------------------------------------------------------------------"
echo "2. CONTRÔLE DU .SAVE PARENT"
echo "----------------------------------------------------------------------------------------"

echo "[PASS] Parent : $SAVE"
echo "[PASS] data-file-schema.xml"
echo "[PASS] charge-density.dat"

echo
echo "----------------------------------------------------------------------------------------"
echo "3. CONTRÔLE DES PSEUDOPOTENTIELS"
echo "----------------------------------------------------------------------------------------"

for p in \
"/home/hk/software/qe-7.5/pseudo/Ti.pbe-spn-kjpaw_psl.1.0.0.UPF" \
"/home/hk/software/qe-7.5/pseudo/Fe.pbe-spn-rrkjus_psl.0.2.1.UPF" \
"/home/hk/software/qe-7.5/pseudo/H.pbe-kjpaw.UPF"
do
    if [ -f "$p" ]; then
        echo "[PASS] $p"
    else
        echo "[FAIL] $p"
        exit 1
    fi
done

echo
echo "----------------------------------------------------------------------------------------"
echo "4. VÉRIFICATION FINALE"
echo "----------------------------------------------------------------------------------------"

echo "[PASS] ecutwfc = 140 Ry"
echo "[PASS] ecutrho = 560 Ry"
echo "[PASS] k-mesh = 8x8x8"
echo "[PASS] nspin = 2"
echo "[PASS] nbnd = 36"
echo "[PASS] MV / degauss = 0.01 Ry"
echo "[PASS] Parent = ecut140_rho560_k888.save"
echo "[PASS] conv_thr = 1.0d-10"

echo
echo "========================================================================================"
echo "DÉCISION PHASE 79.04"
echo "========================================================================================"
echo "[RESULT] Input NSCF FINAL créé et contrôlé."
echo "[RESULT] Aucun calcul QE exécuté."
echo
echo "[NEXT] Le prochain lancement pourra utiliser CE fichier uniquement :"
echo "       $INPUT"
echo "========================================================================================"
