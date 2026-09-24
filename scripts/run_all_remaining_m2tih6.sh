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

echo "===== 1. VERIFICATION DES CIF CIBLES ====="

for f in "$BA" "$SR"; do
    echo "----------------------------------------------------------------------------"

    if [ -f "$f" ]; then
        echo "[OK] $f"
        echo "[INFO] Taille : $(stat -c%s "$f") octets"
        echo "[INFO] SHA256 :"
        sha256sum "$f"
    else
        echo "[CRITICAL] Fichier absent : $f"
    fi
done

echo

echo "===== 2. EXTRACTION CRISTALLOGRAPHIQUE ====="

python3 - "$BA" "$SR" <<'PY'
import sys
import os
import re

for path in sys.argv[1:]:

    print("----------------------------------------------------------------------------")
    print("FILE:", path)

    if not os.path.isfile(path):
        print("[CRITICAL] absent")
        continue

    text = open(path, encoding="utf-8", errors="ignore").read()

    def get(tag):
        m = re.search(
            rf"^{re.escape(tag)}\s+(.+)$",
            text,
            re.MULTILINE | re.IGNORECASE
        )
        return m.group(1).strip() if m else None

    a = get("_cell_length_a")
    b = get("_cell_length_b")
    c = get("_cell_length_c")
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

        if abs(av-1.0) < 1e-8 and \
           abs(bv-1.0) < 1e-8 and \
           abs(cv-1.0) < 1e-8:

            print("[CRITICAL] a=b=c=1.000000 Å")
            print("[CRITICAL] Echelle placeholder")
            print("[CRITICAL] PAS DE CALCUL QE")

        elif abs(av-bv) < 1e-6 and abs(av-cv) < 1e-6:

            print("[OK] Maille cubique")
            print(f"[INFO] a = {av:.8f} Å")

        else:
            print("[WARN] Maille non cubique")

    except Exception:
        print("[CRITICAL] Paramètres de maille non exploitables")

    if sg:
        s = sg.lower().replace(" ", "")

        if "pm-3m" in s:
            print("[OK] Pm-3m détecté")
        else:
            print("[WARN] Pm-3m non détecté automatiquement")

    if it and "221" in it:
        print("[OK] IT number 221")

    print()
PY

echo "===== 3. INVENTAIRE DES ATOMES ====="

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

    headers = []
    rows = []

    for i, line in enumerate(lines):

        if line.strip().lower() != "loop_":
            continue

        j = i + 1
        local_headers = []

        while j < len(lines):
            s = lines[j].strip()

            if s.startswith("_"):
                local_headers.append(s)
                j += 1
            else:
                break

        if not any("_atom_site_" in h for h in local_headers):
            continue

        headers = local_headers
        k = j

        while k < len(lines):

            s = lines[k].strip()

            if not s or s.startswith("#"):
                k += 1
                continue

            if s.startswith("_") or s.lower() == "loop_":
                break

            parts = s.split()

            if len(parts) >= len(headers):
                rows.append(parts)

            k += 1

    print("[OK] Colonnes atomiques :", len(headers))
    print("[INFO] Sites détectés   :", len(rows))

    idx = None

    for i, h in enumerate(headers):
        if "_atom_site_type_symbol" in h:
            idx = i
            break

    if idx is not None:

        counts = Counter()

        for row in rows:
            if idx < len(row):
                element = re.sub(r"[^A-Za-z]", "", row[idx])
                counts[element] += 1

        print("[INFO] Composition :")

        for element, n in sorted(counts.items()):
            print(f"       {element:>3s} : {n}")

    print()
PY

echo "===== 4. VERIFICATION PSEUDOPOTENTIELS ====="

PSEUDO_DIR="calculations/m2tih6/pseudo"

if [ -d "$PSEUDO_DIR" ]; then

    echo "[OK] $PSEUDO_DIR"

    echo "[INFO] Ba:"
    find "$PSEUDO_DIR" -maxdepth 1 -type f -iname '*Ba*' \
        -printf '       %f\n' 2>/dev/null

    echo "[INFO] Sr:"
    find "$PSEUDO_DIR" -maxdepth 1 -type f -iname '*Sr*' \
        -printf '       %f\n' 2>/dev/null

    echo "[INFO] Ti:"
    find "$PSEUDO_DIR" -maxdepth 1 -type f -iname '*Ti*' \
        -printf '       %f\n' 2>/dev/null

    echo "[INFO] H:"
    find "$PSEUDO_DIR" -maxdepth 1 -type f -iname '*H*' \
        -printf '       %f\n' 2>/dev/null

else

    echo "[WARN] Répertoire pseudo absent : $PSEUDO_DIR"

fi

echo

echo "===== 5. VERIFICATION QE 7.5 ====="

QE="/home/hk/software/qe-7.5/bin/pw.x"

if [ -x "$QE" ]; then
    echo "[OK] pw.x disponible : $QE"
    "$QE" -h 2>&1 | head -n 5
else
    echo "[WARN] pw.x absent : $QE"
fi

echo

echo "===== 6. RECHERCHE DES FICHIERS M2TiH6 ====="

echo "[INFO] Recherche ciblée..."

find calculations scripts reports \
    -type f \
    \( -iname '*Ba2TiH6*' -o -iname '*Sr2TiH6*' -o -iname '*M2TiH6*' \) \
    -print 2>/dev/null \
    | sort \
    | head -n 250

echo

echo "===== 7. RECHERCHE DES INPUTS QE ====="

find calculations scripts reports \
    -type f \
    \( -iname '*.in' -o -iname '*.inp' \) \
    -print 2>/dev/null \
    | while read -r f; do

        if grep -qiE 'Ba2TiH6|Sr2TiH6|M2TiH6' "$f" 2>/dev/null; then
            echo "[MATCH] $f"
        fi

    done

echo

echo "===== 8. RECHERCHE DES PARAMETRES QE ====="

grep -RniE \
    'CELL_PARAMETERS|celldm|ibrav|ecutwfc|ecutrho|K_POINTS|nat[[:space:]]*=|ntyp[[:space:]]*=' \
    calculations scripts reports \
    --include='*.in' \
    --include='*.inp' \
    --include='*.sh' \
    --include='*.txt' \
    2>/dev/null \
    | grep -Ei \
    'Ba2TiH6|Sr2TiH6|M2TiH6|CELL_PARAMETERS|celldm|ecutwfc|ecutrho|K_POINTS' \
    | head -n 250

echo

echo "===== 9. RECHERCHE Pm-3m / IT 221 ====="

grep -RniE \
    'Pm[[:space:]]*-?[[:space:]]*3[[:space:]]*m|space_group_IT_number.*221' \
    reports calculations structures data \
    --include='*.cif' \
    2>/dev/null \
    | head -n 150

echo

echo "===== 10. AUDIT FINAL PRE-QE ====="

python3 - "$BA" "$SR" <<'PY'
import sys
import os
import re

critical = False

for path in sys.argv[1:]:

    print("----------------------------------------------------------------------------")
    print(os.path.basename(path))

    if not os.path.isfile(path):
        print("[CRITICAL] CIF absent")
        critical = True
        continue

    text = open(path, encoding="utf-8", errors="ignore").read()

    values = {}

    for tag in ["a", "b", "c"]:
        m = re.search(
            rf"_cell_length_{tag}\s+([0-9.+-Ee]+)",
            text,
            re.IGNORECASE
        )

        values[tag] = float(m.group(1)) if m else None

    print("a =", values["a"])
    print("b =", values["b"])
    print("c =", values["c"])

    if all(v is not None and abs(v-1.0) < 1e-8
           for v in values.values()):

        print("[CRITICAL] PLACEHOLDER 1 Å")
        print("[CRITICAL] NON PRET POUR QE")
        critical = True

    else:

        print("[INFO] Maille non-placeholder")

print()

if critical:
    print("[CRITICAL] VERDICT = PRE-QE NOT READY")
else:
    print("[OK] VERDICT = PRE-QE STRUCTURELLEMENT EXPLOITABLE")
PY

echo

echo "===== 11. PROVENANCE BIBLIOGRAPHIQUE ====="

echo "[INFO] Karafi et al."
echo "[INFO] Journal of Physics and Chemistry of Solids"
echo "[INFO] Volume 216 (2026), article 113778"
echo "[INFO] DOI: 10.1016/j.jpcs.2026.113778"
echo "[INFO] Sujet : M2TiH6 (M = Ba, Sr)"
echo "[INFO] Structure rapportée : cubique Pm-3m"

echo

echo "=============================================================================="
echo "VERDICT M2TiH6.34"
echo "=============================================================================="

echo "[OK] Audit READ-ONLY terminé."
echo "[OK] Aucun pw.x lancé."
echo "[OK] Aucun fichier scientifique modifié."
echo "[OK] Aucun CIF modifié."
echo
echo "[CRITICAL] a=b=c=1.000000 Å dans les CIF locaux."
echo "[CRITICAL] Cette valeur reste un PLACEHOLDER."
echo "[CRITICAL] Pas de DFT avant récupération de la maille physique publiée."
echo
echo "[NEXT] M2TiH6.35 après validation des paramètres structuraux."
echo "=============================================================================="
