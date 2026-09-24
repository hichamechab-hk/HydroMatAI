#!/bin/bash

clear 2>/dev/null || printf '\033c'

cd /home/hk/HydroMatAI || {
    echo "[CRITICAL] Impossible d'entrer dans /home/hk/HydroMatAI"
    exit 1
}

echo "=============================================================================="
echo "M2TiH6.34 — AUDIT QE PRE-CALCUL Ba2TiH6 / Sr2TiH6"
echo "=============================================================================="
echo "[INFO] MODE = READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun fichier scientifique modifié"
echo "[INFO] Aucun CIF modifié"
echo "[INFO] Aucun paramètre de maille inventé"
echo

BA="reports/m2tih6_reconstructed/Ba2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif"
SR="reports/m2tih6_reconstructed/Sr2TiH6_RECONSTRUCTED_NOT_PUBLISHED.cif"

###############################################################################
echo "===== 1. VERIFICATION DES CIF CIBLES ====="
###############################################################################

for f in "$BA" "$SR"; do
    echo "----------------------------------------------------------------------------"

    if [ -f "$f" ]; then
        echo "[OK] Fichier trouvé : $f"
        echo "[INFO] Taille : $(stat -c%s "$f") octets"
        echo "[INFO] SHA256 :"
        sha256sum "$f"
    else
        echo "[CRITICAL] Fichier absent : $f"
    fi
done

echo

###############################################################################
echo "===== 2. EXTRACTION CRISTALLOGRAPHIQUE ====="
###############################################################################

python3 - "$BA" "$SR" <<'PY'
import sys
import os
import re

for path in sys.argv[1:]:

    print("----------------------------------------------------------------------------")
    print("FILE:", path)

    if not os.path.isfile(path):
        print("[CRITICAL] Fichier absent")
        continue

    text = open(path, encoding="utf-8", errors="ignore").read()

    def get(tag):
        pattern = rf"^{re.escape(tag)}\s+(.+)$"
        m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        return m.group(1).strip() if m else None

    a  = get("_cell_length_a")
    b  = get("_cell_length_b")
    c  = get("_cell_length_c")
    al = get("_cell_angle_alpha")
    be = get("_cell_angle_beta")
    ga = get("_cell_angle_gamma")

    sg = get("_symmetry_space_group_name_H-M")
    if sg is None:
        sg = get("_space_group_name_H-M_alt")

    it = get("_space_group_IT_number")
    formula = get("_chemical_formula_sum")

    print("Formula       :", formula if formula else "NOT_DECLARED")
    print("Space group   :", sg if sg else "NOT_FOUND")
    print("IT number     :", it if it else "NOT_FOUND")
    print("a             :", a if a else "NOT_FOUND")
    print("b             :", b if b else "NOT_FOUND")
    print("c             :", c if c else "NOT_FOUND")
    print("alpha         :", al if al else "NOT_FOUND")
    print("beta          :", be if be else "NOT_FOUND")
    print("gamma         :", ga if ga else "NOT_FOUND")

    try:
        av = float(a)
        bv = float(b)
        cv = float(c)

        print()
        print("===== ANALYSE MAILLE =====")

        if abs(av - 1.0) < 1e-8 and \
           abs(bv - 1.0) < 1e-8 and \
           abs(cv - 1.0) < 1e-8:

            print("[CRITICAL] a=b=c=1.000000 Å")
            print("[CRITICAL] Echelle placeholder détectée")
            print("[CRITICAL] PAS DE CALCUL QE POSSIBLE")

        elif abs(av-bv) < 1e-6 and abs(av-cv) < 1e-6:

            print("[OK] Maille cubique détectée")
            print(f"[INFO] a = {av:.8f} Å")

        else:

            print("[WARN] Maille non cubique ou paramètres différents")

    except Exception:

        print("[CRITICAL] Paramètres de maille non exploitables")

    print()

    if sg:
        sg_clean = sg.lower().replace(" ", "")

        if "pm-3m" in sg_clean or "p-m-3m" in sg_clean:
            print("[OK] Pm-3m détecté")
        else:
            print("[WARN] Pm-3m non identifié automatiquement")

    if it:
        if "221" in it:
            print("[OK] IT number 221")
        else:
            print("[WARN] IT number différent de 221 ou absent")

    print()
PY

###############################################################################
echo "===== 3. INVENTAIRE DES ATOMES ====="
###############################################################################

python3 - "$BA" "$SR" <<'PY'
import sys
import os
import re
from collections import Counter

for path in sys.argv[1:]:

    print("----------------------------------------------------------------------------")
    print("FILE:", path)

    if not os.path.isfile(path):
        print("[CRITICAL] absent")
        continue

    lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()

    atom_loop = False
    headers = []
    rows = []

    for i, line in enumerate(lines):

        s = line.strip()

        if s.lower() == "loop_":

            j = i + 1
            local_headers = []

            while j < len(lines):
                x = lines[j].strip()

                if x.startswith("_"):
                    local_headers.append(x)
                    j += 1
                else:
                    break

            if any("_atom_site_" in h for h in local_headers):

                atom_loop = True
                headers = local_headers
                rows = []

                k = j

                while k < len(lines):

                    x = lines[k].strip()

                    if not x:
                        k += 1
                        continue

                    if x.startswith("_") or x.lower() == "loop_":
                        break

                    if x.startswith("#"):
                        break

                    parts = x.split()

                    if len(parts) >= len(headers):
                        rows.append(parts)

                    k += 1

    if not headers:
        print("[WARN] Aucun atom loop détecté")
        continue

    print("[OK] Colonnes atomiques :", len(headers))
    print("[INFO] Sites détectés   :", len(rows))

    symbol_idx = None

    for idx, h in enumerate(headers):
        if "_atom_site_type_symbol" in h:
            symbol_idx = idx
            break

    if symbol_idx is not None:

        counts = Counter()

        for row in rows:
            if symbol_idx < len(row):
                symbol = re.sub(r"[^A-Za-z]", "", row[symbol_idx])
                counts[symbol] += 1

        print("[INFO] Composition atomique :")

        for element, count in sorted(counts.items()):
            print(f"       {element:>3s} : {count}")

    print()
PY

###############################################################################
echo "===== 4. VERIFICATION DES PSEUDOPOTENTIELS ====="
###############################################################################

PSEUDO_DIR="calculations/m2tih6/pseudo"

if [ -d "$PSEUDO_DIR" ]; then

    echo "[OK] Répertoire pseudo trouvé : $PSEUDO_DIR"

    echo
    echo "[INFO] Fichiers Ba :"
    find "$PSEUDO_DIR" -maxdepth 1 -type f \
        -iname '*Ba*' -printf '       %f\n' 2>/dev/null

    echo "[INFO] Fichiers Sr :"
    find "$PSEUDO_DIR" -maxdepth 1 -type f \
        -iname '*Sr*' -printf '       %f\n' 2>/dev/null

    echo "[INFO] Fichiers Ti :"
    find "$PSEUDO_DIR" -maxdepth 1 -type f \
        -iname '*Ti*' -printf '       %f\n' 2>/dev/null

    echo "[INFO] Fichiers H :"
    find "$PSEUDO_DIR" -maxdepth 1 -type f \
        -iname '*H*' -printf '       %f\n' 2>/dev/null

else

    echo "[WARN] Répertoire pseudo absent : $PSEUDO_DIR"

fi

echo

###############################################################################
echo "===== 5. VERIFICATION QE 7.5 ====="
###############################################################################

QE="/home/hk/software/qe-7.5/bin/pw.x"

if [ -x "$QE" ]; then

    echo "[OK] pw.x disponible"
    echo "[INFO] $QE"

    "$QE" -h 2>&1 | head -n 5

else

    echo "[WARN] pw.x absent ou non executable : $QE"

fi

echo

###############################################################################
echo "===== 6. RECHERCHE DES INPUTS EXISTANTS ====="
###############################################################################

echo "[INFO] Recherche Ba2TiH6 / Sr2TiH6 / M2TiH6..."

find calculations scripts reports \
    -type f \
    \( \
        -iname '*Ba2TiH6*' \
        -o -iname '*Sr2TiH6*' \
        -o -iname '*M2TiH6*' \
    \) \
    2
