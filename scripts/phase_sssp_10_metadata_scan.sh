#!/usr/bin/env bash

clear
set -u

BASE="/home/hk/HydroMatAI"
ARCHIVE="$BASE/data/literature_benchmarks/sssp/download/SSSP_1.3.0_PBE_precision.tar.gz"

echo "=============================================================================="
echo "SSSP 1.3.0 PBE — SCAN METADONNEES UPF PAR CONTENU"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Archive non modifiée"
echo

if [[ ! -f "$ARCHIVE" ]]; then
    echo "[ERROR] Archive introuvable : $ARCHIVE"
    exit 1
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

ELEMENTS=(H K Rb Ge Sn Na Ca Sr Pd Ru)

echo "=============================================================================="
echo "1. INVENTAIRE DES UPF"
echo "=============================================================================="

mapfile -t MEMBERS < <(
    tar -tzf "$ARCHIVE" 2>/dev/null \
    | grep -Ei '\.(upf|UPF)$' \
    | sort
)

echo "[INFO] UPF trouvés dans l'archive : ${#MEMBERS[@]}"
echo

echo "=============================================================================="
echo "2. SCAN DES ELEMENTS CIBLES"
echo "=============================================================================="

declare -A FOUND_FILE
declare -A FOUND_TYPE
declare -A FOUND_VALENCE
declare -A FOUND_DFT
declare -A FOUND_CONF

for MEMBER in "${MEMBERS[@]}"; do

    BASENAME="$(basename "$MEMBER")"

    # Extraction temporaire en mémoire vers un fichier temporaire.
    SAFE_NAME="$(printf '%s' "$BASENAME" | tr '/ ' '__')"
    UPF="$TMPDIR/$SAFE_NAME"

    if ! tar -xOf "$ARCHIVE" "$MEMBER" > "$UPF" 2>/dev/null; then
        continue
    fi

    # -------------------------------------------------------------------------
    # ELEMENT
    # -------------------------------------------------------------------------

    ELEMENT="$(
        grep -m1 -oE 'Element:[[:space:]]*[A-Z][a-z]?' "$UPF" 2>/dev/null \
        | sed -E 's/.*Element:[[:space:]]*//'
    )"

    if [[ -z "$ELEMENT" ]]; then
        ELEMENT="$(
            grep -m1 -oE 'element="[A-Z][a-z]+"' "$UPF" 2>/dev/null \
            | cut -d'"' -f2
        )"
    fi

    if [[ -z "$ELEMENT" ]]; then
        ELEMENT="$(
            grep -m1 -oE "title='[A-Z][a-z]?'" "$UPF" 2>/dev/null \
            | cut -d"'" -f2
        )"
    fi

    # -------------------------------------------------------------------------
    # Seuls les 10 éléments demandés nous intéressent.
    # -------------------------------------------------------------------------

    TARGET=0

    for EL in "${ELEMENTS[@]}"; do
        if [[ "$ELEMENT" == "$EL" ]]; then
            TARGET=1
            break
        fi
    done

    [[ "$TARGET" -eq 0 ]] && continue

    # -------------------------------------------------------------------------
    # TYPE
    # -------------------------------------------------------------------------

    TYPE="$(
        grep -m1 -oE 'Pseudopotential type:[[:space:]]*[A-Za-z0-9_-]+' "$UPF" \
        | sed -E 's/.*Pseudopotential type:[[:space:]]*//'
    )"

    if [[ -z "$TYPE" ]]; then
        TYPE="$(
            grep -m1 -oE 'pseudo_type="[A-Za-z0-9_-]+"' "$UPF" \
            | cut -d'"' -f2
        )"
    fi

    # -------------------------------------------------------------------------
    # Z VALENCE
    # -------------------------------------------------------------------------

    VALENCE="$(
        grep -m1 -oE 'z_valence="[^\"]+"' "$UPF" \
        | cut -d'"' -f2
    )"

    # -------------------------------------------------------------------------
    # DFT / PBE
    # -------------------------------------------------------------------------

    DFT="$(
        grep -m1 -oEi "dft[[:space:]]*=[[:space:]]*['\"]PBE['\"]" "$UPF" \
        | grep -oi 'PBE' \
        | head -n1
    )"

    if [[ -z "$DFT" ]]; then
        DFT="$(
            grep -m1 -oiE 'PBE' "$UPF" 2>/dev/null \
            | head -n1
        )"
    fi

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    CONFIG="$(
        grep -m1 -oE "config='[^']*'" "$UPF" \
        | sed "s/^config='//;s/'$//"
    )"

    # -------------------------------------------------------------------------
    # STOCKAGE
    # -------------------------------------------------------------------------

    if [[ -z "${FOUND_FILE[$ELEMENT]:-}" ]]; then
        FOUND_FILE["$ELEMENT"]="$MEMBER"
        FOUND_TYPE["$ELEMENT"]="${TYPE:-UNKNOWN}"
        FOUND_VALENCE["$ELEMENT"]="${VALENCE:-UNKNOWN}"
        FOUND_DFT["$ELEMENT"]="${DFT:-UNKNOWN}"
        FOUND_CONF["$ELEMENT"]="${CONFIG:-UNKNOWN}"
    fi

done

echo
echo "=============================================================================="
echo "3. RESULTATS DETAILLES"
echo "=============================================================================="

for EL in "${ELEMENTS[@]}"; do

    echo
    echo "----- $EL -----"

    if [[ -z "${FOUND_FILE[$EL]:-}" ]]; then
        echo "STATUS      : MISSING"
        continue
    fi

    echo "STATUS      : FOUND"
    echo "FILE        : ${FOUND_FILE[$EL]}"
    echo "TYPE        : ${FOUND_TYPE[$EL]}"
    echo "FUNCTIONAL  : ${FOUND_DFT[$EL]}"
    echo "Z_VALENCE   : ${FOUND_VALENCE[$EL]}"
    echo "CONFIG      : ${FOUND_CONF[$EL]}"

done

echo
echo "=============================================================================="
echo "4. SUMMARY"
echo "=============================================================================="

FOUND=0
MISSING=0
INCONSISTENT=0

for EL in "${ELEMENTS[@]}"; do

    if [[ -z "${FOUND_FILE[$EL]:-}" ]]; then

        printf "%-3s  MISSING\n" "$EL"
        MISSING=$((MISSING + 1))
        continue
    fi

    TYPE="${FOUND_TYPE[$EL]}"
    DFT="${FOUND_DFT[$EL]}"
    VAL="${FOUND_VALENCE[$EL]}"

    if [[ "$TYPE" != "UNKNOWN" ]] &&
       [[ "$DFT" == "PBE" || "$DFT" == "pbe" ]] &&
       [[ "$VAL" != "UNKNOWN" ]]; then

        printf "%-3s  FOUND\n" "$EL"
        FOUND=$((FOUND + 1))

    else

        printf "%-3s  INCONSISTENT\n" "$EL"
        INCONSISTENT=$((INCONSISTENT + 1))

    fi

done

echo
echo "=============================================================================="
echo "5. GLOBAL RESULT"
echo "=============================================================================="
echo

echo "FOUND        : $FOUND / 10"
echo "MISSING      : $MISSING / 10"
echo "INCONSISTENT : $INCONSISTENT / 10"

echo

if [[ "$FOUND" -eq 10 && "$MISSING" -eq 0 && "$INCONSISTENT" -eq 0 ]]; then
    echo "RESULT : PASS"
else
    echo "RESULT : REVIEW REQUIRED"
fi

echo
echo "=============================================================================="
echo "FIN — AUCUN pw.x LANCE"
echo "=============================================================================="
