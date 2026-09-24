#!/usr/bin/env bash

clear
set -u

BASE="/home/hk/HydroMatAI"
ARCHIVE="$BASE/data/literature_benchmarks/sssp/download/SSSP_1.3.0_PBE_precision.tar.gz"

echo "=============================================================================="
echo "SSSP 1.3.0 PBE — DEEP SCAN DES ELEMENTS MANQUANTS"
echo "=============================================================================="
echo
echo "[INFO] READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Archive non modifiée"
echo

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

TARGETS=(H Ge Sn Ca Sr)

mapfile -t MEMBERS < <(
    tar -tzf "$ARCHIVE" 2>/dev/null \
    | grep -Ei '\.(upf|UPF)$' \
    | sort
)

echo "[INFO] UPF inspectés : ${#MEMBERS[@]}"
echo

for MEMBER in "${MEMBERS[@]}"; do

    BASENAME="$(basename "$MEMBER")"

    SAFE="$(printf '%s' "$BASENAME" | tr '/ ' '__')"
    UPF="$TMPDIR/$SAFE"

    tar -xOf "$ARCHIVE" "$MEMBER" > "$UPF" 2>/dev/null || continue

    # On récupère quelques signatures fortes.
    ELEMENT="$(
        grep -i -m1 -oE 'Element:[[:space:]]*[A-Z][a-z]?' "$UPF" \
        | sed -E 's/.*Element:[[:space:]]*//'
    )"

    [[ -z "$ELEMENT" ]] && \
    ELEMENT="$(
        grep -i -m1 -oE 'element="[A-Z][a-z]+"' "$UPF" \
        | cut -d'"' -f2
    )"

    [[ -z "$ELEMENT" ]] && \
    ELEMENT="$(
        grep -i -m1 -oE "title=['\"][A-Z][a-z]?['\"]" "$UPF" \
        | sed -E "s/title=['\"]//;s/['\"]$//"
    )"

    # Signature PBE
    PBE="$(
        grep -i -m1 -oE "dft[[:space:]]*=[[:space:]]*['\"]PBE['\"]" "$UPF" \
        || true
    )"

    # Cherche explicitement les signatures élémentaires.
    MATCH=""

    for EL in "${TARGETS[@]}"; do

        if [[ "$ELEMENT" == "$EL" ]]; then
            MATCH="$EL"
            break
        fi

        # Nom de fichier.
        if [[ "$BASENAME" =~ (^|[^A-Za-z])${EL}([^A-Za-z]|$) ]]; then
            MATCH="$EL"
            break
        fi

        # PP_INPUTFILE / title / Element.
        if grep -Eiq \
            "(Element:[[:space:]]*$EL([[:space:]]|$)|element=[\"']$EL[\"']|title=[\"']$EL[\"']|title=[\"']$EL,[\"'])" \
            "$UPF"; then
            MATCH="$EL"
            break
        fi
    done

    [[ -z "$MATCH" ]] && continue

    echo
    echo "=============================================================================="
    echo "CANDIDAT : $MATCH"
    echo "=============================================================================="
    echo "FILE : $MEMBER"

    echo
    echo "--- SIGNATURES ---"

    grep -i -m3 -E \
        'Element:|element=|title=|z_valence=|dft=|Pseudopotential type:' \
        "$UPF" \
        | sed 's/^/  /'

    echo
    echo "--- CONTEXTE ELEMENT ---"

    grep -in -E \
        "Element|element=|title=|zed=|z_valence=|dft=|config=" \
        "$UPF" \
        | head -n 20 \
        | sed 's/^/  /'

done

echo
echo "=============================================================================="
echo "FIN DU DEEP SCAN"
echo "=============================================================================="
echo "Aucun pw.x lancé."
echo "=============================================================================="
