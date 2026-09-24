#!/usr/bin/env bash
clear
set -u

echo "======================================================================"
echo "M2TiH6.25 — QE PRE-TEST SCF Ba2TiH6"
echo "======================================================================"
echo "[INFO] MODE = CONTROLLED PRE-TEST"
echo "[INFO] Cible = Ba2TiH6"
echo "[INFO] Sr2TiH6 = NON LANCE"
echo

ROOT="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"

echo "[1] Vérification QE"
if [ ! -x "$QE" ]; then
    echo "[ERROR] pw.x introuvable : $QE"
    exit 1
fi
"$QE" -h 2>&1 | head -n 3
echo

echo "[2] Recherche de l'input Ba2TiH6"
mapfile -t INPUTS < <(
    find "$ROOT" \
        -type f \
        \( -iname '*Ba2TiH6*.in' -o -iname '*Ba_2TiH_6*.in' \) \
        -not -path '*/.git/*' \
        -print
)

if [ "${#INPUTS[@]}" -eq 0 ]; then
    echo "[ERROR] Aucun input Ba2TiH6 trouvé."
    echo
    echo "Inputs .in disponibles contenant Ba/Ba2/TiH6 :"
    find "$ROOT" -type f -name '*.in' \
        -not -path '*/.git/*' | grep -Ei 'Ba|TiH6' || true
    exit 1
fi

if [ "${#INPUTS[@]}" -gt 1 ]; then
    echo "[ERROR] Plusieurs inputs Ba2TiH6 trouvés :"
    printf '  %s\n' "${INPUTS[@]}"
    echo
    echo "[ACTION] Sélection explicite nécessaire — aucun calcul lancé."
    exit 2
fi

INPUT="${INPUTS[0]}"
echo "[OK] Input = $INPUT"
echo

echo "[3] Vérification du contenu"
grep -E 'calculation|prefix|pseudo_dir|outdir|nat[[:space:]]*=|ntyp[[:space:]]*=|ecutwfc|ecutrho|K_POINTS' \
    "$INPUT" || true
echo

echo "[4] Vérification des pseudopotentiels référencés"
PSEUDO_DIR=$(grep -i "pseudo_dir" "$INPUT" | head -n1 | sed -E "s/.*pseudo_dir[[:space:]]*=[[:space:]]*['\"]([^'\"]+)['\"].*/\1/")

if [ -z "$PSEUDO_DIR" ]; then
    echo "[ERROR] pseudo_dir non trouvé."
    exit 3
fi

echo "[INFO] pseudo_dir = $PSEUDO_DIR"

if [ ! -d "$PSEUDO_DIR" ]; then
    echo "[ERROR] pseudo_dir inexistant."
    exit 4
fi

echo
echo "[5] Pseudopotentiels Ba / Ti / H"
grep -Ei 'Ba|Ti|H' "$INPUT" | grep -E '\.(UPF|upf)' || true
echo

echo "[6] Lancement SCF Ba2TiH6"
echo "----------------------------------------------------------------------"

OUT="${INPUT%.in}.out"

"$QE" -in "$INPUT" > "$OUT"

RC=$?

echo
echo "----------------------------------------------------------------------"
echo "[7] RESULTAT"
echo "----------------------------------------------------------------------"
echo "[INFO] return code = $RC"
echo "[INFO] output = $OUT"
echo

if grep -q "JOB DONE" "$OUT"; then
    echo "[PASS] QE terminé avec JOB DONE."
else
    echo "[WARN] JOB DONE absent."
fi

echo
echo "===== CONVERGENCE ====="
grep -Ei "convergence has been achieved|convergence NOT achieved|iteration #|estimated scf accuracy" \
    "$OUT" | tail -n 20 || true

echo
echo "===== ENERGIE ====="
grep -E "!" "$OUT" | tail -n 5 || true

echo
echo "===== ERREURS / WARNINGS ====="
grep -Ei "error|warning|cannot open|not found|failed" "$OUT" | tail -n 30 || true

echo
echo "======================================================================"
echo "FIN M2TiH6.25 — Ba2TiH6"
echo "======================================================================"

exit "$RC"
