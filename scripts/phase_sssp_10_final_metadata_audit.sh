#!/usr/bin/env bash

clear
set -u

ARCHIVE="/home/hk/HydroMatAI/data/literature_benchmarks/sssp/download/SSSP_1.3.0_PBE_precision.tar.gz"

echo "=============================================================================="
echo "SSSP 1.3.0 PBE PRECISION — AUDIT FINAL DES 10 UPF"
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

declare -A FILE
FILE[H]="H_ONCV_PBE-1.0.oncvpsp.upf"
FILE[K]="K.pbe-spn-kjpaw_psl.1.0.0.UPF"
FILE[Rb]="Rb_ONCV_PBE-1.0.oncvpsp.upf"
FILE[Ge]="ge_pbe_v1.4.uspp.F.UPF"
FILE[Sn]="Sn_pbe_v1.uspp.F.UPF"
FILE[Na]="Na.paw.z_9.ld1.psl.v1.0.0-low.upf"
FILE[Ca]="Ca_pbe_v1.uspp.F.UPF"
FILE[Sr]="Sr_pbe_v1.uspp.F.UPF"
FILE[Pd]="Pd_ONCV_PBE-1.0.oncvpsp.upf"
FILE[Ru]="Ru_ONCV_PBE-1.0.oncvpsp.upf"

ELEMENTS=(H K Rb Ge Sn Na Ca Sr Pd Ru)

declare -A TYPE
declare -A DFT
declare -A VALENCE
declare -A DETECTED
declare -A STATUS

echo "=============================================================================="
echo "1. EXTRACTION TEMPORAIRE DES 10 UPF"
echo "=============================================================================="
echo

for EL in "${ELEMENTS[@]}"; do

    MEMBER="./${FILE[$EL]}"
    OUT="$TMPDIR/$EL.UPF"

    if tar -xOf "$ARCHIVE" "$MEMBER" > "$OUT" 2>/dev/null; then
        echo "$EL  OK  ${FILE[$EL]}"
        DETECTED[$EL]="YES"
    else
        echo "$EL  ERROR  ${FILE[$EL]}"
        DETECTED[$EL]="NO"
    fi

done

echo
echo "=============================================================================="
echo "2. EXTRACTION DES METADONNEES"
echo "=============================================================================="

for EL in "${ELEMENTS[@]}"; do

    UPF="$TMPDIR/$EL.UPF"

    echo
    echo "----- $EL -----"

    if [[ ! -s "$UPF" ]]; then
        echo "STATUS : FILE ERROR"
        STATUS[$EL]="FILE_ERROR"
        continue
    fi

    # -------------------------------------------------------------------------
    # TYPE
    # -------------------------------------------------------------------------

    T="$(
        grep -i -m1 -oE 'Pseudopotential type:[[:space:]]*[A-Za-z0-9_-]+' "$UPF" \
        | sed -E 's/.*Pseudopotential type:[[:space:]]*//'
    )"

    if [[ -z "$T" ]]; then
        T="$(
            grep -m1 -oE 'pseudo_type="[A-Za-z0-9_-]+"' "$UPF" \
            | cut -d'"' -f2
        )"
    fi

    # Pour les fichiers où le type est indiqué autrement.
    if [[ -z "$T" ]]; then
        if grep -qi 'ONCV' "$UPF"; then
            T="ONCV"
        elif grep -qi 'PAW' "$UPF"; then
            T="PAW"
        elif grep -qi 'ultrasoft\|ultrasoft' "$UPF"; then
            T="USPP"
        else
            T="UNKNOWN"
        fi
    fi

    TYPE[$EL]="$T"

    # -------------------------------------------------------------------------
    # VALENCE
    # -------------------------------------------------------------------------

    V="$(
        grep -m1 -oE 'z_valence="[^\"]+"' "$UPF" \
        | cut -d'"' -f2
    )"

    if [[ -z "$V" ]]; then
        V="$(
            grep -i -m1 -E 'z_valence' "$UPF" \
            | sed -E 's/.*z_valence[^0-9]*([0-9]+([.][0-9]+)?).*/\1/'
        )"
    fi

    VALENCE[$EL]="${V:-UNKNOWN}"

    # -------------------------------------------------------------------------
    # FONCTIONNELLE
    # -------------------------------------------------------------------------

    if grep -qiE "dft[[:space:]]*=[[:space:]]*['\"]PBE['\"]" "$UPF"; then
        DFT[$EL]="PBE"
    elif grep -qiE 'Functional:[[:space:]]+.*PBE' "$UPF"; then
        DFT[$EL]="PBE"
    elif grep -qiE 'functional="[^"]*PBE[^"]*"' "$UPF"; then
        DFT[$EL]="PBE"
    else
        DFT[$EL]="NOT_EXPLICIT"
    fi

    # -------------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------------

    if [[ "${DFT[$EL]}" == "PBE" ]] &&
       [[ "${TYPE[$EL]}" != "UNKNOWN" ]] &&
       [[ "${VALENCE[$EL]}" != "UNKNOWN" ]]; then
        STATUS[$EL]="OK"
    else
        STATUS[$EL]="REVIEW"
    fi

    echo "TYPE       : ${TYPE[$EL]}"
    echo "FUNCTIONAL : ${DFT[$EL]}"
    echo "Z_VALENCE  : ${VALENCE[$EL]}"
    echo "STATUS     : ${STATUS[$EL]}"

done

echo
echo "=============================================================================="
echo "3. TABLEAU FINAL"
echo "=============================================================================="

printf "%-4s | %-42s | %-7s | %-13s | %-12s | %-8s\n" \
    "EL" "FILE" "TYPE" "FUNCTIONAL" "Z_VALENCE" "STATUS"

printf '%*s\n' 100 '' | tr ' ' '-'

for EL in "${ELEMENTS[@]}"; do

    printf "%-4s | %-42s | %-7s | %-13s | %-12s | %-8s\n" \
        "$EL" \
        "${FILE[$EL]}" \
        "${TYPE[$EL]:-UNKNOWN}" \
        "${DFT[$EL]:-UNKNOWN}" \
        "${VALENCE[$EL]:-UNKNOWN}" \
        "${STATUS[$EL]:-UNKNOWN}"

done

echo
echo "=============================================================================="
echo "4. SUMMARY"
echo "=============================================================================="

OK=0
REVIEW=0
MISSING=0

for EL in "${ELEMENTS[@]}"; do

    case "${STATUS[$EL]:-UNKNOWN}" in
        OK)
            printf "%-3s  FOUND / OK\n" "$EL"
            OK=$((OK + 1))
            ;;
        FILE_ERROR)
            printf "%-3s  MISSING / FILE ERROR\n" "$EL"
            MISSING=$((MISSING + 1))
            ;;
        *)
            printf "%-3s  FOUND / REVIEW\n" "$EL"
            REVIEW=$((REVIEW + 1))
            ;;
    esac

done

echo
echo "OK      : $OK / 10"
echo "REVIEW  : $REVIEW / 10"
echo "MISSING : $MISSING / 10"

echo
echo "=============================================================================="
echo "5. RESULTAT"
echo "=============================================================================="

if [[ "$OK" -eq 10 ]]; then
    echo "RESULT : PASS — 10/10 METADATA COHERENTES"
else
    echo "RESULT : REVIEW REQUIRED"
fi

echo
echo "=============================================================================="
echo "FIN — AUCUN pw.x LANCE"
echo "=============================================================================="
