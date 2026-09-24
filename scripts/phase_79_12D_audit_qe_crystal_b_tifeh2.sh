#!/usr/bin/env bash

printf '\033[2J\033[H'

set -u

echo "=============================================================================="
echo "PHASE 79.12D — AUDIT QE 7.5 / K_POINTS crystal_b — TiFeH2"
echo "=============================================================================="
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun calcul DFT"
echo "[INFO] Aucun fichier scientifique modifié"
echo

QE="/home/hk/software/qe-7.5/bin/pw.x"
IN="/home/hk/HydroMatAI/calculations/phase79_final_bands/TiFeH2/TiFeH2_bands_path_corrected.in"
QE_ROOT="/home/hk/software/qe-7.5"

PASS=0
FAIL=0

pass() {
    echo "[PASS] $1"
    PASS=$((PASS+1))
}

fail() {
    echo "[FAIL] $1"
    FAIL=$((FAIL+1))
}

echo "===== 1. QE 7.5 ====="

if [[ -x "$QE" ]]; then
    pass "pw.x trouvé : $QE"
else
    fail "pw.x introuvable : $QE"
fi

echo
echo "===== 2. INPUT BANDS ====="

if [[ -f "$IN" ]]; then
    pass "Input trouvé : $IN"
else
    fail "Input introuvable : $IN"
    echo
    echo "=============================================================================="
    echo "[RESULT] AUDIT IMPOSSIBLE"
    echo "=============================================================================="
    exit 1
fi

echo
echo "===== 3. TYPE K_POINTS ====="

KP_LINE=$(grep -iE '^[[:space:]]*K_POINTS[[:space:]]+crystal_b' "$IN" | head -1 || true)

if [[ -n "$KP_LINE" ]]; then
    pass "K_POINTS crystal_b détecté"
    echo "       $KP_LINE"
else
    fail "K_POINTS crystal_b non détecté"
fi

echo
echo "===== 4. NOMBRE DE SOMMETS ====="

NVERT=$(awk '
    BEGIN {found=0}
    /^[[:space:]]*K_POINTS[[:space:]]+crystal_b/ {
        found=1
        next
    }
    found && $0 !~ /^[[:space:]]*$/ {
        print $1
        exit
    }
' "$IN")

if [[ "$NVERT" == "15" ]]; then
    pass "15 sommets déclarés"
else
    fail "Nombre de sommets inattendu : ${NVERT:-INCONNU}"
fi

echo
echo "===== 5. EXTRACTION DU BLOC K_POINTS ====="

awk '
    /^[[:space:]]*K_POINTS[[:space:]]+crystal_b/ {
        print
        found=1
        next
    }
    found {
        print
        count++
        if (count >= 16) exit
    }
' "$IN"

echo
echo "===== 6. VALIDATION DES VERTICES ====="

EXPECTED_NAMES=(
    "GAMMA"
    "Y"
    "C_0"
    "SIGMA_0"
    "GAMMA"
    "Z"
    "A_0"
    "E_0"
    "T"
    "Y"
    "GAMMA"
    "S"
    "R"
    "Z"
    "T"
)

INDEX=0

while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    if [[ "$line" =~ ^[[:space:]]*([+-]?[0-9.]+)[[:space:]]+([+-]?[0-9.]+)[[:space:]]+([+-]?[0-9.]+)[[:space:]]+([0-9]+) ]]; then

        INDEX=$((INDEX+1))

        X="${BASH_REMATCH[1]}"
        Y="${BASH_REMATCH[2]}"
        Z="${BASH_REMATCH[3]}"
        N="${BASH_REMATCH[4]}"

        COMMENT=$(echo "$line" | sed -n 's/.*![[:space:]]*//p')

        echo "[$INDEX] $COMMENT"
        echo "     k = ($X, $Y, $Z), N = $N"

        if [[ "$INDEX" -le 15 ]]; then
            EXPECTED="${EXPECTED_NAMES[$((INDEX-1))]}"

            if [[ "$COMMENT" == "$EXPECTED" ]]; then
                pass "Sommet $INDEX = $EXPECTED"
            else
                fail "Sommet $INDEX attendu = $EXPECTED ; trouvé = ${COMMENT:-SANS_LABEL}"
            fi
        fi
    fi

    [[ "$INDEX" -ge 15 ]] && break

done < <(
    awk '
        /^[[:space:]]*K_POINTS[[:space:]]+crystal_b/ {
            found=1
            next
        }
        found {
            if ($0 ~ /^[[:space:]]*[+-]?[0-9]/) print
            count++
            if (count >= 16) exit
        }
    ' "$IN"
)

echo
echo "===== 7. CONTROLE DES COUPURES DE CHEMIN ====="

ZERO_COUNT=$(awk '
    /^[[:space:]]*K_POINTS[[:space:]]+crystal_b/ {
        found=1
        next
    }
    found && $0 ~ /^[[:space:]]*[+-]?[0-9]/ {
        n++
        if ($4 == 0) z++
        if (n >= 15) exit
    }
    END {print z+0}
' "$IN")

echo "[INFO] Sommets avec N=0 : $ZERO_COUNT"

if [[ "$ZERO_COUNT" -eq 3 ]]; then
    pass "3 coupures explicites détectées"
else
    fail "Nombre de coupures N=0 inattendu : $ZERO_COUNT"
fi

echo
echo "===== 8. RECHERCHE DOCUMENTATION QE ====="

if [[ -d "$QE_ROOT" ]]; then

    DOC_COUNT=$(grep -Ril --include='*.f90' --include='*.f' --include='*.html' \
        --include='*.txt' --include='*.md' \
        'crystal_b' "$QE_ROOT" 2>/dev/null | wc -l)

    echo "[INFO] Fichiers contenant 'crystal_b' : $DOC_COUNT"

    if [[ "$DOC_COUNT" -gt 0 ]]; then
        pass "Référence crystal_b trouvée dans l'arborescence QE"
        grep -Rin --include='*.f90' --include='*.f' --include='*.html' \
            --include='*.txt' --include='*.md' \
            'crystal_b' "$QE_ROOT" 2>/dev/null | head -20
    else
        echo "[WARN] Aucune référence textuelle crystal_b trouvée"
    fi

else
    echo "[WARN] Répertoire QE non accessible : $QE_ROOT"
fi

echo
echo "===== 9. TEST pw.x -h ====="

if [[ -x "$QE" ]]; then

    HELP_OUT=$("$QE" -h 2>&1 || true)

    if echo "$HELP_OUT" | grep -qiE 'Quantum ESPRESSO|pw.x|Usage'; then
        pass "pw.x -h répond correctement"
    else
        fail "Réponse inattendue de pw.x -h"
    fi

    echo
    echo "--- première partie de l'aide ---"
    echo "$HELP_OUT" | head -25

else
    fail "Impossible de tester pw.x -h"
fi

echo
echo "===== 10. CONTROLE ABSENCE DE CALCUL ====="

if ps aux | grep '[p]w.x' >/dev/null 2>&1; then
    echo "[WARN] Un processus pw.x existe actuellement :"
    ps aux | grep '[p]w.x'
else
    pass "Aucun processus pw.x actif"
fi

echo
echo "=============================================================================="
echo "RESULTAT PHASE 79.12D"
echo "=============================================================================="
echo "[INFO] PASS = $PASS"
echo "[INFO] FAIL = $FAIL"

if [[ "$FAIL" -eq 0 ]]; then
    echo "[PASS] AUDIT 79.12D TERMINÉ"
    echo "[PASS] AUCUN CALCUL DFT EFFECTUÉ"
    echo
    echo "[NEXT] Phase 79.12E = validation définitive des coordonnées QE"
    echo "[NEXT] puis préparation du calcul bands isolé"
    exit 0
else
    echo "[FAIL] AUDIT 79.12D À CORRIGER AVANT TOUT CALCUL"
    exit 2
fi
