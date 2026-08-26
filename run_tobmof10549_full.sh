#!/usr/bin/env bash

set -u

# ============================================================
# HydroMatAI — tobMOF-10549
# Processus complet SCF contrôlé
# ============================================================

BASE="$HOME/HydroMatAI"
CALC="$BASE/calculations/tobmof-10549_scf"
INPUT="$CALC/tobmof-10549_scf.in"
INPUT_60300="$CALC/tobmof-10549_scf_60_300.in"
OUT="$CALC/tobmof-10549_scf.out"
TEST_OUT="/tmp/tobmof-10549_memory_test.out"
TMP="$CALC/tmp"

QE="/home/hk/software/qe-7.5/bin/pw.x"

# ------------------------------------------------------------
# Paramètres
# ------------------------------------------------------------

TEST_ECUTWFC=40
TEST_ECUTRHO=200

# RAM maximale que nous acceptons pour un processus QE
MAX_RAM_GB=100

# MPI choisi après le test
DEFAULT_MPI=2

# ------------------------------------------------------------
# Fonctions
# ------------------------------------------------------------

die()
{
    echo
    echo "============================================================"
    echo "ERREUR : $1"
    echo "============================================================"
    exit 1
}

section()
{
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

# ------------------------------------------------------------
# Vérification QE
# ------------------------------------------------------------

section "1. VERIFICATION QE"

test -x "$QE" || die "pw.x introuvable : $QE"

"$QE" -h >/dev/null 2>&1 || true

echo "QE : $QE"
"$QE" -h 2>&1 | head -5

# ------------------------------------------------------------
# Arrêt d'anciens calculs
# ------------------------------------------------------------

section "2. ARRET DES ANCIENS CALCULS"

OLD_PIDS=$(pgrep -f "pw.x.*tobmof-10549" || true)

if [ -n "$OLD_PIDS" ]; then
    echo "Processus trouvés :"
    echo "$OLD_PIDS"

    pkill -TERM -f "pw.x.*tobmof-10549" || true
    sleep 5

    if pgrep -f "pw.x.*tobmof-10549" >/dev/null; then
        echo "Forçage de l'arrêt..."
        pkill -KILL -f "pw.x.*tobmof-10549" || true
        sleep 2
    fi
else
    echo "Aucun ancien pw.x."
fi

if pgrep -f "pw.x.*tobmof-10549" >/dev/null; then
    die "Un ancien pw.x est encore actif."
fi

# ------------------------------------------------------------
# Préparation répertoire
# ------------------------------------------------------------

section "3. PREPARATION"

test -f "$INPUT" || die "Input absent : $INPUT"

mkdir -p "$CALC"
mkdir -p "$TMP"

rm -rf "$TMP"/*

# ------------------------------------------------------------
# Sauvegarde 60/300
# ------------------------------------------------------------

section "4. SAUVEGARDE DE LA REFERENCE 60/300"

if [ ! -f "$INPUT_60300" ]; then
    cp "$INPUT" "$INPUT_60300"
    echo "Sauvegarde créée :"
    echo "$INPUT_60300"
else
    echo "Sauvegarde déjà présente :"
    echo "$INPUT_60300"
fi

echo
echo "Reference :"
grep -E "ecutwfc|ecutrho" "$INPUT_60300"

# ------------------------------------------------------------
# Création de l'input test 40/200
# ------------------------------------------------------------

section "5. PREPARATION DU TEST 40/200"

sed -i \
    -e "s/ecutwfc = [0-9.]\+/ecutwfc = ${TEST_ECUTWFC}/" \
    -e "s/ecutrho = [0-9.]\+/ecutrho = ${TEST_ECUTRHO}/" \
    "$INPUT"

echo "Input actuel :"
grep -E "ecutwfc|ecutrho" "$INPUT"

# ------------------------------------------------------------
# Vérification structure
# ------------------------------------------------------------

section "6. VALIDATION INPUT"

echo
echo "Paramètres :"

grep -E \
"calculation|prefix|outdir|nat =|ntyp =|ecutwfc|ecutrho|nspin|starting_magnetization|conv_thr|electron_maxstep|mixing_beta" \
"$INPUT"

echo
echo "Pseudopotentiels :"

grep -A4 "ATOMIC_SPECIES" "$INPUT"

echo
echo "Positions atomiques :"

NAT=$(grep -E "nat =" "$INPUT" | sed 's/.*nat = *\([0-9]*\).*/\1/')

NPOS=$(sed -n '/ATOMIC_POSITIONS/,/K_POINTS/p' "$INPUT" |
       grep -E '^[[:space:]]*(C|Cu|H|N)[[:space:]]' |
       wc -l)

echo "nat  = $NAT"
echo "positions = $NPOS"

[ "$NAT" = "$NPOS" ] || die "Nombre de positions incorrect."

# ------------------------------------------------------------
# Nettoyage sortie test
# ------------------------------------------------------------

section "7. TEST MEMOIRE 1 MPI"

rm -f "$TEST_OUT"

echo "Lancement contrôlé :"
echo "$QE -in $INPUT"

"$QE" -in "$INPUT" > "$TEST_OUT" 2>&1 &

TEST_PID=$!

echo
echo "PID = $TEST_PID"
echo "Surveillance..."

ESTIMATE_FOUND=0
RAM_PER_PROCESS=0

# ------------------------------------------------------------
# Surveillance jusqu'à estimation mémoire ou fin
# ------------------------------------------------------------

for i in $(seq 1 120); do

    if grep -q "Estimated max dynamical RAM per process" "$TEST_OUT"; then
        ESTIMATE_FOUND=1
        break
    fi

    if ! kill -0 "$TEST_PID" 2>/dev/null; then
        break
    fi

    sleep 2
done

# ------------------------------------------------------------
# Affichage grille
# ------------------------------------------------------------

echo
echo "Grille FFT :"

grep -E "Dense  grid|Smooth grid|FFT dimensions" \
"$TEST_OUT" | tail -10 || true

# ------------------------------------------------------------
# Analyse mémoire
# ------------------------------------------------------------

echo
echo "Estimation mémoire :"

grep -E "Estimated max dynamical RAM|Estimated total dynamical RAM" \
"$TEST_OUT" | tail -10 || true

if grep -q "Estimated max dynamical RAM per process" "$TEST_OUT"; then

    RAM_PER_PROCESS=$(grep "Estimated max dynamical RAM per process" "$TEST_OUT" |
        tail -1 |
        awk '{for(i=1;i<=NF;i++) if($i ~ /GB/) {print $(i-1); exit}}')

    echo
    echo "RAM maximale estimée/processus : ${RAM_PER_PROCESS} GB"

else

    echo
    echo "ATTENTION : QE n'a pas encore fourni l'estimation RAM."

fi

# ------------------------------------------------------------
# Décision sécurité
# ------------------------------------------------------------

if [ "$ESTIMATE_FOUND" -eq 1 ] && [ -n "$RAM_PER_PROCESS" ]; then

    RAM_INT=${RAM_PER_PROCESS%.*}

    if [ "$RAM_INT" -ge "$MAX_RAM_GB" ]; then

        echo
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "MEMOIRE TROP ELEVEE"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo
        echo "RAM/processus : ${RAM_PER_PROCESS} GB"
        echo "Limite       : ${MAX_RAM_GB} GB"
        echo
        echo "Arrêt automatique du test."

        kill -TERM "$TEST_PID" 2>/dev/null || true
        sleep 3
        kill -KILL "$TEST_PID" 2>/dev/null || true

        wait "$TEST_PID" 2>/dev/null || true

        echo
        echo "Le calcul n'est PAS lancé."
        echo
        echo "Dernières informations :"
        tail -30 "$TEST_OUT"

        exit 2
    fi

fi

# ------------------------------------------------------------
# Si le test n'est pas terminé, attendre
# ------------------------------------------------------------

if kill -0 "$TEST_PID" 2>/dev/null; then

    echo
    echo "Le test mémoire est suffisamment raisonnable."
    echo "On attend sa fin..."

    wait "$TEST_PID"
    TEST_STATUS=$?

else
    wait "$TEST_PID" 2>/dev/null
    TEST_STATUS=$?
fi

# ------------------------------------------------------------
# Résultat test
# ------------------------------------------------------------

section "8. RESULTAT DU TEST"

grep -E \
"convergence has been achieved|total energy|estimated scf accuracy|JOB DONE|Error in routine|%%%%%%%%%%%%%%%" \
"$TEST_OUT" | tail -30 || true

if grep -q "JOB DONE" "$TEST_OUT"; then
    echo
    echo "TEST SCF 40/200 : CONVERGENCE"
else
    echo
    echo "TEST SCF 40/200 : NON TERMINE OU NON CONVERGE"
fi

# ------------------------------------------------------------
# Nettoyage avant calcul définitif
# ------------------------------------------------------------

section "9. PREPARATION SCF"

rm -rf "$TMP"/*

# ------------------------------------------------------------
# Choix MPI
# ------------------------------------------------------------

MPI="$DEFAULT_MPI"

echo
echo "MPI retenu : $MPI"

# Si la mémoire par processus est connue, sécurité supplémentaire
if [ -n "$RAM_PER_PROCESS" ]; then

    RAM_INT=${RAM_PER_PROCESS%.*}

    if [ "$RAM_INT" -gt 50 ]; then
        MPI=1
        echo "RAM/processus élevée -> MPI=1"
    fi

fi

echo "Nombre final de processus MPI : $MPI"

# ------------------------------------------------------------
# Lancement SCF définitif
# ------------------------------------------------------------

section "10. LANCEMENT SCF DEFINITIF"

rm -f "$OUT"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

echo "Commande :"
echo
echo "mpirun -np $MPI $QE -in $INPUT"
echo
echo "Sortie : $OUT"
echo

mpirun -np "$MPI" \
    "$QE" \
    -in "$INPUT" \
    > "$OUT" 2>&1

SCF_STATUS=$?

# ------------------------------------------------------------
# Résultat final
# ------------------------------------------------------------

section "11. RESULTAT FINAL"

echo "Code retour : $SCF_STATUS"

echo
echo "Convergence :"

grep -E \
"convergence has been achieved|JOB DONE|Error in routine" \
"$OUT" | tail -20 || true

echo
echo "Energies finales :"

grep "!    total energy" "$OUT" | tail -10 || true

echo
echo "Magnétisation :"

grep -Ei \
"total magnetization|absolute magnetization" \
"$OUT" | tail -10 || true

echo
echo "SCF accuracy :"

grep "estimated scf accuracy" "$OUT" | tail -10 || true

# ------------------------------------------------------------
# Diagnostic erreurs
# ------------------------------------------------------------

if grep -q "Error in routine" "$OUT"; then

    echo
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "ERREUR QE DETECTEE"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

    grep -A5 -B5 "Error in routine" "$OUT" | tail -30

fi

# ------------------------------------------------------------
# Résumé
# ------------------------------------------------------------

section "12. RESUME"

echo "Structure : tobmof-10549"
echo "Atomes    : 212"
echo "Cutoff    : ${TEST_ECUTWFC}/${TEST_ECUTRHO} Ry"
echo "MPI       : $MPI"
echo

if grep -q "JOB DONE" "$OUT"; then
    echo "SCF : COMPLETED"
else
    echo "SCF : NOT COMPLETED"
fi

echo
echo "Input final :"
echo "$INPUT"

echo
echo "Input référence 60/300 :"
echo "$INPUT_60300"

echo
echo "Output final :"
echo "$OUT"

echo
echo "============================================================"
echo "FIN DU PROCESSUS"
echo "============================================================"

exit "$SCF_STATUS"
