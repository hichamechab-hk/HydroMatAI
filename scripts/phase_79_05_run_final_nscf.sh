#!/usr/bin/env bash

printf '\033[2J\033[H'

set -e

BASE="/home/hk/HydroMatAI"
QE="/home/hk/software/qe-7.5/bin/pw.x"

DIR="$BASE/calculations/phase79_final_electronic/TiFeH2"
INPUT="$DIR/TiFeH2_final_nscf.in"
OUTPUT="$DIR/TiFeH2_final_nscf.out"

echo "========================================================================================"
echo "PHASE 79.05 — NSCF FINAL TiFeH2"
echo "========================================================================================"
echo "[INFO] MODE = CALCUL DFT FINAL"
echo "[INFO] QE = $QE"
echo "[INFO] Input = $INPUT"
echo "[INFO] Output = $OUTPUT"
echo

if [ ! -x "$QE" ]; then
    echo "[FAIL] pw.x introuvable ou non exécutable"
    exit 1
fi

if [ ! -f "$INPUT" ]; then
    echo "[FAIL] Input absent"
    exit 1
fi

if [ -e "$OUTPUT" ]; then
    echo "[FAIL] Output déjà existant :"
    echo "       $OUTPUT"
    echo "[INFO] Aucun écrasement automatique."
    exit 1
fi

echo "----------------------------------------------------------------------------------------"
echo "1. PROTOCOLE"
echo "----------------------------------------------------------------------------------------"
echo "[INFO] ecutwfc = 140 Ry"
echo "[INFO] ecutrho = 560 Ry"
echo "[INFO] k-mesh  = 8x8x8"
echo "[INFO] nspin   = 2"
echo "[INFO] nbnd    = 36"
echo "[INFO] smearing = Marzari-Vanderbilt"
echo "[INFO] degauss = 0.01 Ry"
echo "[INFO] conv_thr = 1.0d-10"
echo

echo "----------------------------------------------------------------------------------------"
echo "2. LANCEMENT pw.x"
echo "----------------------------------------------------------------------------------------"

START=$(date +%s)

"$QE" -in "$INPUT" > "$OUTPUT"

END=$(date +%s)
RUNTIME=$((END-START))

echo "[PASS] pw.x terminé"
echo "[INFO] Durée = ${RUNTIME} s"
echo

echo "----------------------------------------------------------------------------------------"
echo "3. CONTRÔLES DE SORTIE"
echo "----------------------------------------------------------------------------------------"

if grep -q "JOB DONE." "$OUTPUT"; then
    echo "[PASS] JOB DONE"
else
    echo "[FAIL] JOB DONE absent"
    echo
    tail -n 80 "$OUTPUT"
    exit 1
fi

if grep -qiE "error in routine|Error in routine|fatal error|segmentation fault" "$OUTPUT"; then
    echo "[FAIL] Erreur QE détectée"
    grep -niE "error in routine|Error in routine|fatal error|segmentation fault" "$OUTPUT" | tail -n 20
    exit 1
else
    echo "[PASS] Aucune erreur QE critique détectée"
fi

echo

python3 - "$OUTPUT" <<'PY'
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
t = p.read_text(errors="ignore")

def find(pattern):
    m = re.search(pattern, t, re.I | re.M)
    return m.group(1) if m else None

energy = find(r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry")
fermi = find(r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev")
nbnd = find(r"number of Kohn-Sham states\s*=\s*(\d+)")
nelec = find(r"number of electrons\s*=\s*([-+0-9.Ee]+)")
nk = find(r"number of k points=\s*(\d+)")

print("----------------------------------------------------------------------------------------")
print("4. EXTRACTION DES GRANDEURS NSCF")
print("----------------------------------------------------------------------------------------")

print(f"[INFO] Énergie totale      = {energy if energy else '?'} Ry")
print(f"[INFO] Fermi energy        = {fermi if fermi else '?'} eV")
print(f"[INFO] Électrons           = {nelec if nelec else '?'}")
print(f"[INFO] États KS            = {nbnd if nbnd else '?'}")
print(f"[INFO] k-points            = {nk if nk else '?'}")

print()

ok = True

if nbnd is not None:
    if int(nbnd) == 36:
        print("[PASS] nbnd = 36")
    else:
        print(f"[FAIL] nbnd inattendu : {nbnd}")
        ok = False
else:
    print("[WARN] nbnd non extrait")

if nelec is not None:
    try:
        if abs(float(nelec) - 60.0) < 1e-6:
            print("[PASS] nelec = 60")
        else:
            print(f"[FAIL] nelec inattendu : {nelec}")
            ok = False
    except ValueError:
        print("[WARN] nelec non numérique")

if nk is not None:
    print(f"[PASS] k-points présents : {nk}")
else:
    print("[WARN] nombre de k-points non extrait")

print()
print("=" * 88)

if ok:
    print("[RESULT] PASS — NSCF final terminé et contrôlé.")
    print("[RESULT] Les données électroniques finales peuvent maintenant")
    print("         servir de parent pour bands.x / dos.x.")
else:
    print("[RESULT] WARN/FAIL — vérifier la sortie NSCF avant bands.x / dos.x.")

print("=" * 88)
PY

echo
echo "[INFO] Sortie complète :"
echo "       $OUTPUT"
echo "========================================================================================"
