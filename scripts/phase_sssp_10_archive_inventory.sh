#!/usr/bin/env bash

clear
set -u

BASE="/home/hk/HydroMatAI"
ARCHIVE="$BASE/data/literature_benchmarks/sssp/download/SSSP_1.3.0_PBE_precision.tar.gz"

echo "=============================================================================="
echo "SSSP 1.3.0 PBE PRECISION — AUDIT ARCHIVE DES 10 ELEMENTS"
echo "=============================================================================="
echo
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun fichier scientifique modifié"
echo "[INFO] Aucune extraction permanente"
echo
echo "[INFO] ARCHIVE : $ARCHIVE"
echo

if [[ ! -f "$ARCHIVE" ]]; then
    echo "[ERROR] Archive introuvable."
    exit 1
fi

echo "=============================================================================="
echo "1. INTEGRITE / INVENTAIRE DE L'ARCHIVE"
echo "=============================================================================="

ls -lh "$ARCHIVE"

echo
echo "[INFO] Nombre de membres :"
tar -tzf "$ARCHIVE" | wc -l

echo
echo "=============================================================================="
echo "2. RECHERCHE DES 10 ELEMENTS"
echo "=============================================================================="

ELEMENTS=(H K Rb Ge Sn Na Ca Sr Pd Ru)

FOUND=0
MISSING=0

declare -A FILES

for EL in "${ELEMENTS[@]}"; do

    echo
    echo "----- $EL -----"

    matches="$(
        tar -tzf "$ARCHIVE" 2>/dev/null \
        | grep -E '/'"$EL"'\.[Uu][Pp][Ff]$|(^|/)'"$EL"'\.[^/]*\.[Uu][Pp][Ff]$|(^|/)'"$EL"'\.[^/]*$' \
        | sort -u
    )"

    if [[ -z "$matches" ]]; then
        echo "STATUS : MISSING"
        MISSING=$((MISSING + 1))
    else
        echo "STATUS : FOUND"
        FOUND=$((FOUND + 1))
        printf '%s\n' "$matches"

        first="$(printf '%s\n' "$matches" | head -n1)"
        FILES["$EL"]="$first"
    fi

done

echo
echo "=============================================================================="
echo "3. EXTRACTION TEMPORAIRE DES UPF CIBLES"
echo "=============================================================================="

TMPDIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "[INFO] Répertoire temporaire : $TMPDIR"
echo

for EL in "${ELEMENTS[@]}"; do

    path="${FILES[$EL]:-}"

    if [[ -z "$path" ]]; then
        continue
    fi

    echo "[$EL]"
    echo "  ARCHIVE : $path"

    mkdir -p "$TMPDIR/$EL"

    if tar -xOf "$ARCHIVE" "$path" > "$TMPDIR/$EL/pseudo.UPF" 2>/dev/null; then
        echo "  EXTRACTION : OK"
    else
        echo "  EXTRACTION : FAILED"
    fi

done

echo
echo "=============================================================================="
echo "4. METADONNEES UPF"
echo "=============================================================================="

for EL in "${ELEMENTS[@]}"; do

    path="${FILES[$EL]:-}"

    if [[ -z "$path" ]]; then
        continue
    fi

    UPF="$TMPDIR/$EL/pseudo.UPF"

    echo
    echo "----- $EL -----"
    echo "FILE : $(basename "$path")"

    if [[ ! -s "$UPF" ]]; then
        echo "STATUS : UNREADABLE"
        continue
    fi

    # Recherche indépendante des attributs pour gérer les headers
    # répartis sur plusieurs lignes.
    element="$(
        grep -o 'element="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    pseudo_type="$(
        grep -o 'pseudo_type="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    functional="$(
        grep -o 'functional="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    z_valence="$(
        grep -o 'z_valence="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    generated="$(
        grep -o 'generated="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    author="$(
        grep -o 'author="[^\"]*"' "$UPF" 2>/dev/null \
        | head -n1 \
        | cut -d'"' -f2
    )"

    echo "ELEMENT     : ${element:-UNKNOWN}"
    echo "PSEUDO TYPE : ${pseudo_type:-UNKNOWN}"
    echo "FUNCTIONAL  : ${functional:-UNKNOWN}"
    echo "Z_VALENCE   : ${z_valence:-UNKNOWN}"
    echo "GENERATED   : ${generated:-UNKNOWN}"
    echo "AUTHOR      : ${author:-UNKNOWN}"

    echo
    echo "HEADER :"

    sed -n '1,35p' "$UPF" \
        | sed 's/^/  /'

done

echo
echo "=============================================================================="
echo "5. SUMMARY"
echo "=============================================================================="

echo
for EL in "${ELEMENTS[@]}"; do
    if [[ -n "${FILES[$EL]:-}" ]]; then
        printf "%-3s  FOUND\n" "$EL"
    else
        printf "%-3s  MISSING\n" "$EL"
    fi
done

echo
echo "=============================================================================="
echo "6. RESULTAT GLOBAL"
echo "=============================================================================="

echo
echo "FOUND   : $FOUND / 10"
echo "MISSING : $MISSING / 10"
echo

if [[ "$FOUND" -eq 10 ]]; then
    echo "RESULT : ALL 10 ELEMENTS FOUND"
else
    echo "RESULT : INCOMPLETE — REVIEW REQUIRED"
fi

echo
echo "=============================================================================="
echo "FIN — AUCUN pw.x LANCE"
echo "=============================================================================="
