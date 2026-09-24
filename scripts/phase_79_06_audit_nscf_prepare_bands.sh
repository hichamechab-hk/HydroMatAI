#!/usr/bin/env bash

printf '\033[2J\033[H'
set -e

BASE="/home/hk/HydroMatAI"
DIR="$BASE/calculations/phase79_final_electronic/TiFeH2"
OUT="$DIR/TiFeH2_final_nscf.out"
SAVE="$BASE/calculations/top5_dft/TiFeH2/tmp_scf/ecut140_rho560_k888.save"

echo "========================================================================================"
echo "PHASE 79.06 — AUDIT NSCF FINAL / PRÉPARATION BANDS TiFeH2"
echo "========================================================================================"
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun bands.x"
echo "[INFO] Aucun dos.x"
echo "[INFO] Aucun fichier scientifique modifié"
echo

echo "----------------------------------------------------------------------------------------"
echo "1. NSCF FINAL"
echo "----------------------------------------------------------------------------------------"

if [ ! -f "$OUT" ]; then
    echo "[FAIL] Sortie NSCF absente"
    exit 1
fi

grep -E "JOB DONE|total energy|Fermi energy|number of electrons|number of Kohn-Sham states|number of k points" "$OUT" \
    | tail -n 20

echo

echo "----------------------------------------------------------------------------------------"
echo "2. CONTRÔLE DU PARENT .SAVE"
echo "----------------------------------------------------------------------------------------"

[ -d "$SAVE" ] && echo "[PASS] $SAVE" || {
    echo "[FAIL] .save absent"
    exit 1
}

[ -f "$SAVE/data-file-schema.xml" ] && echo "[PASS] data-file-schema.xml"
[ -f "$SAVE/charge-density.dat" ] && echo "[PASS] charge-density.dat"

echo

echo "----------------------------------------------------------------------------------------"
echo "3. EXTRACTION EXACTE"
echo "----------------------------------------------------------------------------------------"

python3 - "$OUT" <<'PY'
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
t = p.read_text(errors="ignore")

patterns = {
    "energy": r"!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry",
    "fermi": r"the Fermi energy is\s+([-+0-9.Ee]+)\s+ev",
    "electrons": r"number of electrons\s*=\s*([-+0-9.Ee]+)",
    "nbnd": r"number of Kohn-Sham states\s*=\s*(\d+)",
    "nk": r"number of k points=\s*(\d+)",
}

vals = {}

for key, pat in patterns.items():
    matches = re.findall(pat, t, re.I)
    vals[key] = matches[-1] if matches else None

print(f"[INFO] Énergie totale = {vals['energy'] or '?'} Ry")
print(f"[INFO] Fermi energy   = {vals['fermi'] or '?'} eV")
print(f"[INFO] Électrons      = {vals['electrons'] or '?'}")
print(f"[INFO] États KS       = {vals['nbnd'] or '?'}")
print(f"[INFO] k-points       = {vals['nk'] or '?'}")

if vals["energy"]:
    print("[PASS] Énergie NSCF extraite")
else:
    print("[WARN] Énergie non extraite par ce motif")

if vals["fermi"]:
    ef = float(vals["fermi"])
    if abs(ef - 12.8861) < 0.01:
        print("[PASS] EF cohérent avec le SCF final")
    else:
        print("[WARN] EF différent du SCF final")

if vals["electrons"]:
    print("[PASS] Nombre d'électrons identifié")

if vals["nbnd"] == "36":
    print("[PASS] nbnd = 36")
else:
    print("[FAIL] nbnd != 36")

if vals["nk"] == "170":
    print("[PASS] 170 k-points irréductibles")
else:
    print("[WARN] k-points différent de 170")

print(f"[PASS] JOB DONE = {'JOB DONE.' in t}")

print()
print("========================================================================================")
print("DÉCISION PHASE 79.06")
print("========================================================================================")

if "JOB DONE." in t and vals["nbnd"] == "36" and vals["electrons"]:
    print("[RESULT] PASS — NSCF FINAL validé.")
    print("[RESULT] Le NSCF final peut servir de parent électronique.")
    print("[NEXT] Étape suivante : définir la trajectoire BANDS et préparer bands.x.")
else:
    print("[RESULT] FAIL — audit NSCF incomplet.")

print("========================================================================================")
PY
