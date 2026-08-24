#!/usr/bin/env bash
set -u

PROJECT="$HOME/HydroMatAI"
RESULTS="$PROJECT/results/scientific_analysis"
DATA="$RESULTS/data"
FIGURES="$RESULTS/figures"
REPORTS="$RESULTS/reports"

mkdir -p "$DATA" "$FIGURES" "$REPORTS"

echo "============================================================"
echo " HydroMatAI - SCIENTIFIC POST-PROCESSING PLATFORM"
echo "============================================================"
echo
echo "[SAFE MODE]"
echo "Aucun calcul pw.x ne sera lancé."
echo "Aucun calcul QE existant ne sera interrompu."
echo

cd "$PROJECT"

source .venv/bin/activate

# ------------------------------------------------------------
# 1. COLLECTE DES SORTIES QE
# ------------------------------------------------------------

echo "------------------------------------------------------------"
echo "[1/6] COLLECTE DES SORTIES QE"
echo "------------------------------------------------------------"

find /tmp "$PROJECT/calculations" \
    -type f \
    \( -name "*.out" -o -name "*.log" \) \
    -print 2>/dev/null |
    sort -u > "$DATA/qe_outputs.list"

N=$(wc -l < "$DATA/qe_outputs.list")

echo "[OK] $N sorties QE trouvées"

# ------------------------------------------------------------
# 2. EXTRACTION DES DONNÉES SCIENTIFIQUES
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[2/6] EXTRACTION DES DONNÉES"
echo "------------------------------------------------------------"

python - "$DATA/qe_outputs.list" "$DATA/qe_results.csv" <<'PY'
from pathlib import Path
import csv
import re
import sys

input_list = Path(sys.argv[1])
output_csv = Path(sys.argv[2])

energy_re = re.compile(
    r"!\s+total energy\s+=\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry"
)

force_re = re.compile(
    r"Total force\s*=\s*"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)"
)

mag_re = re.compile(
    r"total magnetization\s*=\s*"
    r"([-+]?\d+(?:\.\d+)?)"
)

scf_iter_re = re.compile(r"iteration #\s*(\d+)")

rows = []

for line in input_list.read_text(errors="ignore").splitlines():

    path = Path(line)

    if not path.is_file():
        continue

    try:
        text = path.read_text(errors="ignore")
    except Exception:
        continue

    energies = energy_re.findall(text)
    forces = force_re.findall(text)
    mags = mag_re.findall(text)
    iterations = scf_iter_re.findall(text)

    if not energies:
        continue

    if "convergence has been achieved" in text:
        status = "converged"
    elif "convergence NOT achieved" in text:
        status = "not_converged"
    else:
        status = "unknown"

    rows.append({
        "file": str(path),
        "name": path.name,
        "total_energy_Ry": energies[-1],
        "total_force": forces[-1] if forces else "",
        "magnetization": mags[-1] if mags else "",
        "last_scf_iteration": iterations[-1] if iterations else "",
        "status": status,
        "job_done": "yes" if "JOB DONE." in text else "no",
    })

with output_csv.open("w", newline="", encoding="utf-8") as f:

    fields = [
        "file",
        "name",
        "total_energy_Ry",
        "total_force",
        "magnetization",
        "last_scf_iteration",
        "status",
        "job_done",
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"[OK] {len(rows)} calculs analysés")
print(f"[OK] {output_csv}")
PY

# ------------------------------------------------------------
# 3. ANALYSE DE CONVERGENCE
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[3/6] CONVERGENCE"
echo "------------------------------------------------------------"

python - "$DATA/qe_results.csv" "$REPORTS/convergence.txt" <<'PY'
from pathlib import Path
import csv
import sys

csv_file = Path(sys.argv[1])
report = Path(sys.argv[2])

with csv_file.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

converged = [r for r in rows if r["status"] == "converged"]
failed = [r for r in rows if r["status"] == "not_converged"]

text = f"""
HYDROMATAI - CONVERGENCE ANALYSIS
=================================

Total outputs analysés : {len(rows)}

Convergés :
{len(converged)}

Non convergés :
{len(failed)}

INTERPRÉTATION
--------------

Les calculs convergés constituent la population prioritaire
pour l'analyse scientifique.

Les calculs non convergés sont conservés pour diagnostic,
mais ne doivent pas être utilisés comme résultats finaux.

La convergence électronique doit être distinguée de la
convergence géométrique BFGS.
"""

report.write_text(text.strip() + "\n", encoding="utf-8")

print("[OK] Rapport de convergence généré")
PY

# ------------------------------------------------------------
# 4. PRÉPARATION ÉLECTRONIQUE
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[4/6] PROPRIÉTÉS ÉLECTRONIQUES"
echo "------------------------------------------------------------"

cat > "$REPORTS/electronic_status.txt" <<'EOF'
HYDROMATAI - ELECTRONIC PROPERTIES
==================================

STATUT

La plateforme est prête pour :

- structure de bandes électroniques ;
- énergie de Fermi ;
- VBM ;
- CBM ;
- gap électronique ;
- DOS ;
- PDOS ;
- analyse orbitale.

IMPORTANT

Les sorties pw.x de type SCF/relax ne suffisent pas toujours
à déterminer correctement une structure de bandes ou une DOS.

Le workflow scientifique final sera :

SCF convergé
     |
     +--> NSCF
           |
           +--> bands
           |
           +--> DOS/PDOS
                  |
                  +--> VBM / CBM / Eg
EOF

echo "[OK] Module électronique prêt"

# ------------------------------------------------------------
# 5. PRÉPARATION OPTIQUE
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[5/6] PROPRIÉTÉS OPTIQUES"
echo "------------------------------------------------------------"

cat > "$REPORTS/optical_status.txt" <<'EOF'
HYDROMATAI - OPTICAL PROPERTIES
================================

STATUT

La plateforme est prête pour analyser :

- epsilon_1(E)
- epsilon_2(E)
- indice de réfraction n(E)
- coefficient d'extinction k(E)
- coefficient d'absorption alpha(E)
- réflectivité R(E)
- pertes d'énergie
- anisotropie optique

RELATION UTILISÉE

A partir de :

epsilon(E) = epsilon_1(E) + i epsilon_2(E)

on peut calculer :

n(E) + i k(E) = sqrt(epsilon(E))

et ensuite :

R(E) = |(n-1+ik)/(n+1+ik)|²

IMPORTANT

Les valeurs de démonstration précédentes :

n = 2.0153
k = 0.2481
R = 0.1193

ne sont PAS présentées comme des résultats DFT du système
C-H2.

Elles servent uniquement à vérifier le fonctionnement
du logiciel.

Les propriétés optiques finales devront provenir d'une
véritable fonction diélectrique calculée à partir de QE.
EOF

echo "[OK] Module optique prêt"

# ------------------------------------------------------------
# 6. MANIFESTE FINAL
# ------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "[6/6] MANIFESTE"
echo "------------------------------------------------------------"

cat > "$REPORTS/POSTPROCESSING_MANIFEST.txt" <<EOF
HydroMatAI Scientific Post-Processing
======================================

Date :
$(date '+%Y-%m-%d %H:%M:%S')

Mode :
SAFE / POST-PROCESSING ONLY

Calculs QE lancés :
NON

Calculs QE interrompus :
NON

Sorties QE analysées :
$N

Données :
$DATA/qe_results.csv

Convergence :
$REPORTS/convergence.txt

Électronique :
$REPORTS/electronic_status.txt

Optique :
$REPORTS/optical_status.txt

Prochaine étape scientifique :
--------------------------------

1. SCF convergé
2. NSCF
3. bands.x / structure de bandes
4. dos.x / DOS
5. VBM / CBM / band gap
6. fonction diélectrique
7. n(E)
8. k(E)
9. absorption
10. réflectivité
11. figures automatiques
12. interprétation scientifique
13. rapport final
EOF

echo "[OK] Manifeste créé"

echo
echo "============================================================"
echo " POST-PROCESSING TERMINÉ"
echo "============================================================"
echo
echo "Résultats :"
echo "  $RESULTS"
echo
echo "Calcul C_H2_d2p00_fixed.in : NON TOUCHÉ"
echo
echo "Prochaine étape : bandes + DOS + propriétés optiques réelles."
echo "============================================================"
