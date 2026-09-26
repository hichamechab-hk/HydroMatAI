#!/usr/bin/env bash

clear
set -euo pipefail

ROOT="/home/hk/HydroMatAI"
CONV="$ROOT/calculations/new_campaign/TiFeH2/convergence"
PSEUDO="$ROOT/calculations/new_campaign/TiFeH2/pseudo"

BASE="$CONV/cutoff_140Ry_2x2x2.in"

echo "=============================================================================="
echo "TiFeH2 — PREPARATION CONVERGENCE K-POINTS — CUTOFF 140 Ry"
echo "=============================================================================="
echo "[INFO] MODE = PREPARATION / AUDIT READ-ONLY"
echo "[INFO] Aucun pw.x ne sera lancé"
echo "[INFO] ecutwfc = 140 Ry"
echo "[INFO] ecutrho = 560 Ry"
echo "[INFO] K-mesh = 3x3x3, 4x4x4, 5x5x5"
echo "[INFO] conv_thr = 1.0d-10 Ry"
echo

if [ ! -f "$BASE" ]; then
    echo "[ERROR] Input de référence absent :"
    echo "        $BASE"
    exit 1
fi

if [ ! -d "$PSEUDO" ]; then
    echo "[ERROR] Répertoire pseudopotentiels absent :"
    echo "        $PSEUDO"
    exit 1
fi

for k in 3 4 5; do
    OUT="$CONV/kpoints_${k}x${k}x${k}_140Ry.in"

    awk -v k="$k" '
    BEGIN { changed=0 }

    /^ *K_POINTS[[:space:]]+automatic/ {
        print "K_POINTS automatic"
        print k, k, k, 0, 0, 0
        changed=1
        skip_next=1
        next
    }

    skip_next==1 {
        skip_next=0
        next
    }

    { print }
    ' "$BASE" > "$OUT"

    echo "[OK] Créé : $OUT"
done

echo
echo "=============================================================================="
echo "AUDIT DES INPUTS"
echo "=============================================================================="

for k in 3 4 5; do
    FILE="$CONV/kpoints_${k}x${k}x${k}_140Ry.in"

    echo
    echo "--- ${k}x${k}x${k} ---"

    grep -E "ecutwfc|ecutrho|conv_thr|nspin|occupations|smearing|degauss|starting_magnetization|pseudo_dir|K_POINTS" "$FILE"

    echo "K-point réel :"
    awk '
    /K_POINTS automatic/ {
        getline
        print "  " $0
        exit
    }' "$FILE"

    echo "Pseudos :"
    grep -A3 "ATOMIC_SPECIES" "$FILE"
done

echo
echo "=============================================================================="
echo "VERIFICATION STRUCTURE / PARAMETRES COMMUNS"
echo "=============================================================================="

python3 - "$CONV" <<'PY'
from pathlib import Path
import re
import sys

conv = Path(sys.argv[1])

files = [
    conv / "kpoints_3x3x3_140Ry.in",
    conv / "kpoints_4x4x4_140Ry.in",
    conv / "kpoints_5x5x5_140Ry.in",
]

required = {
    "ecutwfc": r"ecutwfc\s*=\s*140",
    "ecutrho": r"ecutrho\s*=\s*560",
    "conv_thr": r"conv_thr\s*=\s*1\.0d-10",
    "nspin": r"nspin\s*=\s*2",
    "smearing": r"smearing\s*=\s*['\"]mv['\"]",
    "degauss": r"degauss\s*=\s*0\.01",
}

ok = True

for f in files:
    text = f.read_text()

    print(f"\nFILE: {f.name}")

    for name, pattern in required.items():
        if re.search(pattern, text, re.I):
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")
            ok = False

    if "ATOMIC_POSITIONS" not in text:
        print("  [FAIL] ATOMIC_POSITIONS absent")
        ok = False
    else:
        print("  [PASS] ATOMIC_POSITIONS")

    if "CELL_PARAMETERS" not in text:
        print("  [FAIL] CELL_PARAMETERS absent")
        ok = False
    else:
        print("  [PASS] CELL_PARAMETERS")

if not ok:
    print("\n[ERROR] Audit échoué.")
    sys.exit(1)

print("\n[PASS] Tous les paramètres communs sont cohérents.")
PY

echo
echo "=============================================================================="
echo "RESULTAT"
echo "=============================================================================="
echo "[PASS] Inputs 3x3x3 / 4x4x4 / 5x5x5 préparés."
echo "[PASS] Cutoff = 140/560 Ry."
echo "[PASS] Aucun calcul pw.x lancé."
echo
echo "Fichiers :"
echo "  $CONV/kpoints_3x3x3_140Ry.in"
echo "  $CONV/kpoints_4x4x4_140Ry.in"
echo "  $CONV/kpoints_5x5x5_140Ry.in"
echo
echo "=============================================================================="
