
clear 2>/dev/null || printf '\033c'

cd /home/hk/HydroMatAI || exit 1

echo "=============================================================================="
echo "M2TiH6.29 — RECHERCHE READ-ONLY DE MAILLES ANALOGUES"
echo "=============================================================================="
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Objectif = rechercher une maille documentée pour Ba2TiH6 / Sr2TiH6"
echo "[INFO] Prototype cible = Pm-3m #221"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun fichier scientifique existant modifié"
echo "[INFO] Aucune valeur de maille inventée"
echo

BA="reports/m2tih6_reconstructed/Ba2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif"
SR="reports/m2tih6_reconstructed/Sr2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif"

echo "===== 1. CIF CIBLES ====="
echo

for CIF in "$BA" "$SR"
do
    echo "----------------------------------------------------------------------"
    echo "$(basename "$CIF")"
    echo "----------------------------------------------------------------------"

    if [ -f "$CIF" ]
    then
        grep -E \
        "^(_cell_length_a|_cell_length_b|_cell_length_c|_cell_angle_alpha|_cell_angle_beta|_cell_angle_gamma|_symmetry_space_group_name_H_M|_symmetry_Int_Tables_number)" \
        "$CIF" || true

        echo
        echo "[SHA256]"
        sha256sum "$CIF"
    else
        echo "[FAIL] CIF absent : $CIF"
    fi

    echo
done

echo "===== 2. INVENTAIRE DES CIF ====="
echo

N_CIF=$(find . \
    -type f \
    -iname "*.cif" \
    ! -path "./.git/*" \
    ! -path "./.venv/*" \
    2>/dev/null |
    wc -l)

echo "[INFO] Nombre de CIF trouvés : $N_CIF"

echo
echo "===== 3. CIF DECLARANT Pm-3m #221 ====="
echo

COUNT_PM3M=0

while IFS= read -r -d '' CIF
do

    if grep -qiE \
    "_symmetry_space_group_name_H_M.*P[[:space:]]*m[[:space:]]*-3[[:space:]]*m|_space_group_name_H_M_alt.*P[[:space:]]*m[[:space:]]*-3[[:space:]]*m" \
    "$CIF" 2>/dev/null
    then

        COUNT_PM3M=$((COUNT_PM3M + 1))

        echo "[Pm-3m] $CIF"

        grep -Ei \
        "^(_cell_length_a|_cell_length_b|_cell_length_c|_chemical_formula_sum|_symmetry_space_group_name_H_M|_symmetry_Int_Tables_number)" \
        "$CIF" 2>/dev/null |
        head -20

        echo
    fi

done < <(
    find . \
    -type f \
    -iname "*.cif" \
    ! -path "./.git/*" \
    ! -path "./.venv/*" \
    -print0 2>/dev/null
)

echo "[INFO] CIF Pm-3m détectés : $COUNT_PM3M"

echo
echo "===== 4. STRUCTURES CUBIQUES AVEC MAILLE > 1 Å ====="
echo

COUNT_CUBIC=0

while IFS= read -r -d '' CIF
do

    A=$(grep "^_cell_length_a" "$CIF" 2>/dev/null |
        awk '{print $2}' |
        head -1)

    B=$(grep "^_cell_length_b" "$CIF" 2>/dev/null |
        awk '{print $2}' |
        head -1)

    C=$(grep "^_cell_length_c" "$CIF" 2>/dev/null |
        awk '{print $2}' |
        head -1)

    if [ -n "$A" ] && [ -n "$B" ] && [ -n "$C" ]
    then

        RESULT=$(python3 - "$A" "$B" "$C" <<'PY'
import sys

try:
    a, b, c = map(float, sys.argv[1:4])
except Exception:
    sys.exit(1)

if a > 1.0 and b > 1.0 and c > 1.0:
    if abs(a-b) < 1e-4 and abs(a-c) < 1e-4:
        print("CUBIC")
PY
)

        if [ "$RESULT" = "CUBIC" ]
        then

            COUNT_CUBIC=$((COUNT_CUBIC + 1))

            echo "[CUBIC] $CIF"
            echo "        a = $A Å"
            echo "        b = $B Å"
            echo "        c = $C Å"

            grep -Ei \
            "^(_chemical_formula_sum|_symmetry_space_group_name_H_M|_symmetry_Int_Tables_number)" \
            "$CIF" 2>/dev/null |
            head -10

            echo
        fi
    fi

done < <(
    find . \
    -type f \
    -iname "*.cif" \
    ! -path "./.git/*" \
    ! -path "./.venv/*" \
    -print0 2>/dev/null
)

echo "[INFO] Structures cubiques > 1 Å : $COUNT_CUBIC"

echo
echo "===== 5. RECHERCHE Ba2TiH6 / Sr2TiH6 / M2TiH6 ====="
echo

grep -RinE \
"Ba2TiH6|Sr2TiH6|M2TiH6|A2TiH6|Ca2TiH6|Mg2TiH6" \
reports calculations results scripts \
--include="*.cif" \
--include="*.txt" \
--include="*.csv" \
--include="*.json" \
--include="*.yaml" \
--include="*.yml" \
--include="*.md" \
2>/dev/null |
head -150

echo
echo "===== 6. RECHERCHE DES ANALOGUES Ba/Sr/Ti/H ====="
echo

grep -RilE \
"BaTi|SrTi|Ba.*Ti.*H|Sr.*Ti.*H|Ca2TiH6|Mg2TiH6|TiH" \
reports calculations results \
--include="*.cif" \
--include="*.txt" \
--include="*.csv" \
--include="*.json" \
--include="*.yaml" \
--include="*.yml" \
2>/dev/null |
head -100

echo
echo "===== 7. RECHERCHE DES PARAMETRES DE MAILLE ====="
echo

grep -RinE \
"Ba2TiH6|Sr2TiH6|M2TiH6|cell_length_a|lattice_parameter|lattice_constant" \
reports calculations results scripts \
--include="*.txt" \
--include="*.csv" \
--include="*.json" \
--include="*.yaml" \
--include="*.yml" \
--include="*.md" \
2>/dev/null |
head -200

echo
echo "===== 8. VERIFICATION DU PLACEHOLDER 1 Å ====="
echo

for CIF in "$BA" "$SR"
do

    if [ -f "$CIF" ]
    then

        A=$(grep "^_cell_length_a" "$CIF" |
            awk '{print $2}')

        B=$(grep "^_cell_length_b" "$CIF" |
            awk '{print $2}')

        C=$(grep "^_cell_length_c" "$CIF" |
            awk '{print $2}')

        echo "$(basename "$CIF")"
        echo "  a = $A Å"
        echo "  b = $B Å"
        echo "  c = $C Å"

        if [ "$A" = "1.0000000000" ] &&
           [ "$B" = "1.0000000000" ] &&
           [ "$C" = "1.0000000000" ]
        then
            echo "  [CRITICAL] MAILLE 1 Å = PLACEHOLDER"
        else
            echo "  [INFO] Maille différente de 1 Å"
        fi

        echo
    fi

done

echo
echo "=============================================================================="
echo "VERDICT M2TiH6.29"
echo "=============================================================================="

if [ "$COUNT_PM3M" -gt 0 ]
then
    echo "[INFO] Des CIF Pm-3m ont été trouvés dans le dépôt."
else
    echo "[WARN] Aucun CIF Pm-3m trouvé."
fi

if [ "$COUNT_CUBIC" -gt 0 ]
then
    echo "[INFO] Des structures cubiques avec maille > 1 Å ont été trouvées."
    echo "[INFO] Elles nécessitent une vérification de provenance avant utilisation."
else
    echo "[WARN] Aucune structure cubique > 1 Å détectée."
fi

echo
echo "[STRICT] La maille a=b=c=1 Å des CIF reconstruits est un PLACEHOLDER."
echo "[STRICT] Aucune maille analogue n'est adoptée automatiquement."
echo "[STRICT] Aucune valeur de maille n'est inventée."
echo "[STRICT] Aucun calcul QE n'est lancé."
echo "[STRICT] Les CIF restent RECONSTRUCTED / NOT PUBLISHED."
echo
echo "=============================================================================="
echo "FIN M2TiH6.29"
echo "=============================================================================="


cd ~/HydroMatAI
chmod +x scripts/phase_m2tih6_29.sh
bash scripts/phase_m2tih6_29.sh

