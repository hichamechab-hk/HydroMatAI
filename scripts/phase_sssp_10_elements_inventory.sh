#!/usr/bin/env bash

clear
set -u

BASE="/home/hk/HydroMatAI"

# Adapter UNIQUEMENT si le dossier SSSP se trouve ailleurs.
PSEUDO_DIR="$BASE/calculations/global_screening/qe/TOP20/pseudo"

echo "=============================================================================="
echo "SSSP 1.3.0 PBE — INVENTAIRE DES 10 PSEUDOPOTENTIELS"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun fichier scientifique modifié"
echo
echo "[INFO] PSEUDO_DIR = $PSEUDO_DIR"
echo

if [[ ! -d "$PSEUDO_DIR" ]]; then
    echo "[ERROR] Dossier pseudo introuvable :"
    echo "        $PSEUDO_DIR"
    exit 1
fi

declare -A EXPECTED
EXPECTED[H]="H"
EXPECTED[K]="K"
EXPECTED[Rb]="Rb"
EXPECTED[Ge]="Ge"
EXPECTED[Sn]="Sn"
EXPECTED[Na]="Na"
EXPECTED[Ca]="Ca"
EXPECTED[Sr]="Sr"
EXPECTED[Pd]="Pd"
EXPECTED[Ru]="Ru"

ELEMENTS=(H K Rb Ge Sn Na Ca Sr Pd Ru)

echo "=============================================================================="
echo "1. FICHIERS UPF DISPONIBLES"
echo "=============================================================================="

mapfile -t UPFS < <(
    find "$PSEUDO_DIR" -maxdepth 1 -type f \
        \( -name "*.UPF" -o -name "*.upf" \) \
        -printf "%f\n" | sort
)

echo "[INFO] Nombre de fichiers UPF : ${#UPFS[@]}"
echo

if [[ ${#UPFS[@]} -eq 0 ]]; then
    echo "[ERROR] Aucun fichier UPF trouvé."
    exit 1
fi

printf '%s\n' "${UPFS[@]}"
echo

echo "=============================================================================="
echo "2. INVENTAIRE PAR ELEMENT"
echo "=============================================================================="

FOUND=0
MISSING=0
INCONSISTENT=0

for EL in "${ELEMENTS[@]}"; do

    matches=()

    for f in "${UPFS[@]}"; do
        base="${f%%.*}"
        lower="$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')"

        # Recherche tolérante dans le nom du fichier.
        if [[ "$base" == "$EL"* ]] || \
           [[ "$lower" == "${EL,,}"* ]]; then
            matches+=("$f")
        fi
    done

    echo
    echo "----- $EL -----"

    if [[ ${#matches[@]} -eq 0 ]]; then
        echo "STATUS : MISSING"
        MISSING=$((MISSING + 1))
        continue
    fi

    if [[ ${#matches[@]} -gt 1 ]]; then
        echo "STATUS : MULTIPLE CANDIDATES"
        printf '  %s\n' "${matches[@]}"
    fi

    file="${matches[0]}"
    path="$PSEUDO_DIR/$file"

    echo "FILE   : $file"

    # -------------------------------------------------------------------------
    # Extraction XML / UPF
    # -------------------------------------------------------------------------

    header="$(grep -m1 -E '<UPF|<PP_HEADER' "$path" 2>/dev/null || true)"

    if [[ -z "$header" ]]; then
        echo "STATUS : INCONSISTENT"
        echo "DETAIL : Impossible de trouver UPF header"
        INCONSISTENT=$((INCONSISTENT + 1))
        continue
    fi

    element="$(printf '%s\n' "$header" \
        | sed -n 's/.*element="\([^"]*\)".*/\1/p' \
        | head -n1)"

    pp_type="$(printf '%s\n' "$header" \
        | sed -n 's/.*pseudo_type="\([^"]*\)".*/\1/p' \
        | head -n1)"

    functional="$(printf '%s\n' "$header" \
        | sed -n 's/.*functional="\([^"]*\)".*/\1/p' \
        | head -n1)"

    zval="$(printf '%s\n' "$header" \
        | sed -n 's/.*z_valence="\([^"]*\)".*/\1/p' \
        | head -n1)"

    # Certains UPF ont les attributs sur plusieurs lignes.
    if [[ -z "$element" ]]; then
        element="$(grep -m1 -o 'element="[^"]*"' "$path" \
            | cut -d'"' -f2 || true)"
    fi

    if [[ -z "$pp_type" ]]; then
        pp_type="$(grep -m1 -o 'pseudo_type="[^"]*"' "$path" \
            | cut -d'"' -f2 || true)"
    fi

    if [[ -z "$functional" ]]; then
        functional="$(grep -m1 -o 'functional="[^"]*"' "$path" \
            | cut -d'"' -f2 || true)"
    fi

    if [[ -z "$zval" ]]; then
        zval="$(grep -m1 -o 'z_valence="[^"]*"' "$path" \
            | cut -d'"' -f2 || true)"
    fi

    echo "ELEMENT: ${element:-UNKNOWN}"
    echo "TYPE   : ${pp_type:-UNKNOWN}"
    echo "PBE    : ${functional:-UNKNOWN}"
    echo "VALENCE: ${zval:-UNKNOWN}"

    status="FOUND"

    if [[ "$element" != "$EL" ]]; then
        echo "CHECK  : ELEMENT MISMATCH (expected $EL)"
        status="INCONSISTENT"
    fi

    if [[ -z "$pp_type" ]]; then
        echo "CHECK  : pseudo_type absent"
        status="INCONSISTENT"
    fi

    if [[ -z "$functional" ]]; then
        echo "CHECK  : functional absent"
        status="INCONSISTENT"
    elif [[ "${functional,,}" != *"pbe"* ]]; then
        echo "CHECK  : functional does not contain PBE"
        status="INCONSISTENT"
    fi

    if [[ -z "$zval" ]]; then
        echo "CHECK  : z_valence absent"
        status="INCONSISTENT"
    fi

    if [[ "$status" == "FOUND" ]]; then
        echo "STATUS : FOUND"
        FOUND=$((FOUND + 1))
    else
        echo "STATUS : INCONSISTENT"
        INCONSISTENT=$((INCONSISTENT + 1))
    fi

done

echo
echo "=============================================================================="
echo "3. SUMMARY"
echo "=============================================================================="
echo

for EL in "${ELEMENTS[@]}"; do

    status="MISSING"
    detail=""

    for f in "${UPFS[@]}"; do

        lower="$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')"

        if [[ "$f" == "$EL"* ]] || [[ "$lower" == "${EL,,}"* ]]; then

            path="$PSEUDO_DIR/$f"

            header="$(grep -m1 -E '<UPF|<PP_HEADER' "$path" 2>/dev/null || true)"

            element="$(printf '%s\n' "$header" \
                | sed -n 's/.*element="\([^"]*\)".*/\1/p' \
                | head -n1)"

            functional="$(printf '%s\n' "$header" \
                | sed -n 's/.*functional="\([^"]*\)".*/\1/p' \
                | head -n1)"

            zval="$(printf '%s\n' "$header" \
                | sed -n 's/.*z_valence="\([^"]*\)".*/\1/p' \
                | head -n1)"

            if [[ "$element" == "$EL" ]] && \
               [[ "${functional,,}" == *"pbe"* ]] && \
               [[ -n "$zval" ]]; then
                status="FOUND"
            else
                status="INCONSISTENT"
            fi

            break
        fi
    done

    printf "%-3s  %s\n" "$EL" "$status"

done

echo
echo "=============================================================================="
echo "4. GLOBAL RESULT"
echo "=============================================================================="
echo

if [[ "$MISSING" -eq 0 && "$INCONSISTENT" -eq 0 && "$FOUND" -eq 10 ]]; then
    echo "RESULT : PASS"
    echo
    echo "Les 10 éléments sont présents et leurs métadonnées minimales"
    echo "sont cohérentes avec un pseudopotentiel PBE."
    echo
else
    echo "RESULT : REVIEW REQUIRED"
    echo
    echo "FOUND        : $FOUND"
    echo "MISSING      : $MISSING"
    echo "INCONSISTENT : $INCONSISTENT"
fi

echo
echo "=============================================================================="
echo "FIN — AUCUN pw.x LANCE"
echo "=============================================================================="
